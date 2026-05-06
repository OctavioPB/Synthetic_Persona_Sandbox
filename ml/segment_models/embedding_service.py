"""Segment embedding service.

Converts a SegmentFeatureMatrix into a 384-dim vector using the
all-MiniLM-L6-v2 sentence transformer and stores it in Qdrant.

Model choice is fixed to all-MiniLM-L6-v2 for consistency with the
OPB AI Mastery Lab stack. Do not change without explicit discussion.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from sentence_transformers import SentenceTransformer

from ml.segment_models.qdrant_setup import QdrantSegmentStore
from ml.segment_models.segment_schema import SegmentDefinition, SegmentFeatureMatrix

logger = logging.getLogger(__name__)

_MODEL_NAME = "all-MiniLM-L6-v2"


class SegmentEmbeddingService:
    """Encode segment profiles and persist them in Qdrant.

    The embedding input is a natural-language description generated from the
    SegmentFeatureMatrix aggregate statistics.  This encodes behavioral
    characteristics (purchase patterns, session depth, recency) rather than
    raw PII or demographic assumptions.

    Args:
        store:  QdrantSegmentStore instance (creates one if None).
        model:  SentenceTransformer model name. Changing this invalidates
                all existing embeddings — requires a full re-index.
    """

    def __init__(
        self,
        store: QdrantSegmentStore | None = None,
        model: str = _MODEL_NAME,
    ) -> None:
        self._store  = store or QdrantSegmentStore()
        self._model  = SentenceTransformer(model)
        self._store.ensure_collection()
        logger.info("SegmentEmbeddingService ready (model=%s).", model)

    def encode_and_store(
        self,
        matrix: SegmentFeatureMatrix,
        definition: SegmentDefinition,
    ) -> list[float]:
        """Embed a segment's feature matrix and upsert it in Qdrant.

        Args:
            matrix:     Feature matrix from the engineering pipeline.
            definition: The SegmentDefinition used to produce the matrix
                        (stored in the Qdrant payload for retrieval).

        Returns:
            The 384-dim embedding vector (float list).
        """
        text = matrix.to_text_description()
        vector: list[float] = self._model.encode(text, normalize_embeddings=True).tolist()

        stats = matrix.aggregate_stats()
        payload: dict[str, Any] = {
            "segment_id":             matrix.segment_id,
            "segment_name":           matrix.segment_name,
            "user_count":             len(matrix),
            "window_days":            matrix.window_days,
            "category_affinities":    definition.category_affinities,
            "text_description":       text,
            "feature_stats":          stats,
            "embedded_at":            datetime.utcnow().isoformat(),
        }

        self._store.upsert_segment(
            segment_id=matrix.segment_id,
            vector=vector,
            payload=payload,
        )
        logger.info(
            "Embedded segment '%s': %d users, vector norm=%.4f.",
            matrix.segment_name,
            len(matrix),
            sum(x ** 2 for x in vector) ** 0.5,
        )
        return vector

    def encode_query(self, text: str) -> list[float]:
        """Encode an arbitrary text query for similarity search.

        Args:
            text: Natural-language description of a desired segment profile.

        Returns:
            384-dim normalized embedding vector.
        """
        return self._model.encode(text, normalize_embeddings=True).tolist()
