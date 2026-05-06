"""Qdrant collection management for persona segment embeddings.

One collection per environment: `persona_segments`.
Each point represents one segment; the payload stores metadata so
the segment can be retrieved without a DB round-trip.
"""

from __future__ import annotations

import logging
import os
from typing import Any

from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels

logger = logging.getLogger(__name__)

COLLECTION_NAME = "persona_segments"
VECTOR_SIZE     = 384   # all-MiniLM-L6-v2 output dimension
DISTANCE        = qmodels.Distance.COSINE


def get_qdrant_client() -> QdrantClient:
    """Return a QdrantClient configured from environment variables."""
    return QdrantClient(
        host=os.getenv("QDRANT_HOST", "localhost"),
        port=int(os.getenv("QDRANT_PORT", "6333")),
    )


class QdrantSegmentStore:
    """Manages the persona_segments Qdrant collection.

    Args:
        client: Optional QdrantClient. If None, builds one from env vars.
    """

    def __init__(self, client: QdrantClient | None = None) -> None:
        self._client = client or get_qdrant_client()

    def ensure_collection(self) -> None:
        """Create the collection if it does not already exist.

        Safe to call on every startup — idempotent.
        """
        existing = {c.name for c in self._client.get_collections().collections}
        if COLLECTION_NAME in existing:
            logger.debug("Collection '%s' already exists.", COLLECTION_NAME)
            return

        self._client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=qmodels.VectorParams(size=VECTOR_SIZE, distance=DISTANCE),
        )
        logger.info("Created Qdrant collection '%s' (dim=%d, dist=%s).", COLLECTION_NAME, VECTOR_SIZE, DISTANCE)

    def upsert_segment(
        self,
        segment_id: str,
        vector: list[float],
        payload: dict[str, Any],
    ) -> None:
        """Insert or replace a segment vector.

        Args:
            segment_id: UUID string used as the Qdrant point id (hashed to int).
            vector:     384-dim float list from the embedding service.
            payload:    Metadata stored alongside the vector (name, stats, etc.).
        """
        # Qdrant point ids must be uint64 or UUID string; we use UUID string directly.
        self._client.upsert(
            collection_name=COLLECTION_NAME,
            points=[
                qmodels.PointStruct(
                    id=segment_id,
                    vector=vector,
                    payload=payload,
                )
            ],
        )
        logger.info("Upserted segment '%s' into Qdrant.", segment_id)

    def search_similar(
        self,
        query_vector: list[float],
        top_k: int = 5,
        score_threshold: float = 0.5,
    ) -> list[dict[str, Any]]:
        """Return the top-k segments most similar to a query vector.

        Args:
            query_vector:    Embedding to search against.
            top_k:           Number of results to return.
            score_threshold: Minimum cosine similarity score.

        Returns:
            List of dicts with keys: id, score, payload.
        """
        results = self._client.search(
            collection_name=COLLECTION_NAME,
            query_vector=query_vector,
            limit=top_k,
            score_threshold=score_threshold,
            with_payload=True,
        )
        return [{"id": r.id, "score": r.score, "payload": r.payload} for r in results]

    def delete_segment(self, segment_id: str) -> None:
        """Remove a segment vector from the collection."""
        self._client.delete(
            collection_name=COLLECTION_NAME,
            points_selector=qmodels.PointIdsList(points=[segment_id]),
        )
        logger.info("Deleted segment '%s' from Qdrant.", segment_id)
