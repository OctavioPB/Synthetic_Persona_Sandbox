"""Holdout evaluator — AUC-based scoring of synthetic persona conversion predictions.

Compares ConversionScorer predictions against a labeled holdout set of real
(stimulus, segment) → conversion_outcome pairs to measure persona calibration.

The evaluator is designed for Sprint 6 calibration work.  In Sprint 4, it is
scaffolded and smoke-tested; full calibration requires a real holdout dataset.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

try:
    from sklearn.metrics import roc_auc_score, average_precision_score
    _SKLEARN_AVAILABLE = True
except ImportError:  # pragma: no cover
    _SKLEARN_AVAILABLE = False
    logger.warning(
        "scikit-learn not installed. HoldoutEvaluator will raise on evaluate()."
    )


@dataclass
class HoldoutSample:
    """A single labeled example for holdout evaluation.

    Args:
        segment_id:   UUID of the segment evaluated.
        stimulus_id:  UUID of the stimulus presented.
        predicted:    ConversionScorer output (float 0–1).
        actual:       Ground-truth binary outcome (1 = converted, 0 = did not convert).
        metadata:     Optional dict for logging/tracing.
    """

    segment_id: str
    stimulus_id: str
    predicted: float
    actual: int                             # 0 or 1
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.actual not in (0, 1):
            raise ValueError(f"actual must be 0 or 1, got {self.actual}.")
        if not 0.0 <= self.predicted <= 1.0:
            raise ValueError(
                f"predicted must be in [0, 1], got {self.predicted}."
            )


@dataclass
class EvaluationReport:
    """Summary of a holdout evaluation run."""

    n_samples: int
    auc_roc: float
    auc_pr: float
    mean_predicted: float
    mean_actual: float
    positive_rate: float            # fraction of actual=1 in holdout
    calibration_error: float        # |mean_predicted - mean_actual|, lower is better

    def __str__(self) -> str:
        return (
            f"HoldoutEvaluator Report\n"
            f"  Samples:            {self.n_samples}\n"
            f"  AUC-ROC:            {self.auc_roc:.4f}\n"
            f"  AUC-PR:             {self.auc_pr:.4f}\n"
            f"  Mean predicted:     {self.mean_predicted:.4f}\n"
            f"  Mean actual:        {self.mean_actual:.4f}\n"
            f"  Positive rate:      {self.positive_rate:.4f}\n"
            f"  Calibration error:  {self.calibration_error:.4f}"
        )


class HoldoutEvaluator:
    """Evaluates ConversionScorer accuracy against labeled ground truth.

    Usage::

        evaluator = HoldoutEvaluator()
        samples = [
            HoldoutSample(segment_id="...", stimulus_id="...", predicted=0.72, actual=1),
            HoldoutSample(segment_id="...", stimulus_id="...", predicted=0.21, actual=0),
        ]
        report = evaluator.evaluate(samples)
        print(report)

    Metrics:
        - AUC-ROC: discrimination ability; 0.5 = random, 1.0 = perfect.
        - AUC-PR:  precision-recall AUC; more informative than AUC-ROC when positives are rare.
        - Calibration error: mean absolute difference between predicted and actual rates.
    """

    MIN_SAMPLES_FOR_AUC = 10

    def evaluate(self, samples: list[HoldoutSample]) -> EvaluationReport:
        """Compute evaluation metrics over the holdout set.

        Args:
            samples: List of HoldoutSample with predicted and actual labels.

        Returns:
            EvaluationReport with AUC-ROC, AUC-PR, and calibration metrics.

        Raises:
            ImportError:  If scikit-learn is not installed.
            ValueError:   If samples are too few or all-one-class (AUC undefined).
        """
        if not _SKLEARN_AVAILABLE:
            raise ImportError(
                "scikit-learn is required for HoldoutEvaluator. "
                "Install it with: uv add scikit-learn"
            )
        if len(samples) < self.MIN_SAMPLES_FOR_AUC:
            raise ValueError(
                f"Need at least {self.MIN_SAMPLES_FOR_AUC} samples for AUC computation, "
                f"got {len(samples)}."
            )

        y_true  = [s.actual    for s in samples]
        y_score = [s.predicted for s in samples]

        unique_classes = set(y_true)
        if len(unique_classes) < 2:
            raise ValueError(
                f"Holdout set contains only class(es) {unique_classes}. "
                "AUC requires at least one positive and one negative sample."
            )

        auc_roc = float(roc_auc_score(y_true, y_score))
        auc_pr  = float(average_precision_score(y_true, y_score))

        n = len(samples)
        mean_predicted = sum(y_score) / n
        mean_actual    = sum(y_true)  / n

        report = EvaluationReport(
            n_samples=n,
            auc_roc=auc_roc,
            auc_pr=auc_pr,
            mean_predicted=mean_predicted,
            mean_actual=mean_actual,
            positive_rate=mean_actual,
            calibration_error=abs(mean_predicted - mean_actual),
        )

        logger.info(
            "HoldoutEvaluator: n=%d AUC-ROC=%.4f AUC-PR=%.4f cal_error=%.4f",
            n, auc_roc, auc_pr, report.calibration_error,
        )
        return report

    def evaluate_by_segment(
        self, samples: list[HoldoutSample]
    ) -> dict[str, EvaluationReport]:
        """Compute per-segment evaluation reports.

        Segments with fewer than MIN_SAMPLES_FOR_AUC samples are skipped with
        a warning rather than raising.

        Returns:
            Dict mapping segment_id → EvaluationReport.
        """
        by_segment: dict[str, list[HoldoutSample]] = {}
        for s in samples:
            by_segment.setdefault(s.segment_id, []).append(s)

        reports: dict[str, EvaluationReport] = {}
        for seg_id, seg_samples in by_segment.items():
            if len(seg_samples) < self.MIN_SAMPLES_FOR_AUC:
                logger.warning(
                    "Skipping segment %s: only %d samples (need %d).",
                    seg_id, len(seg_samples), self.MIN_SAMPLES_FOR_AUC,
                )
                continue
            try:
                reports[seg_id] = self.evaluate(seg_samples)
            except ValueError as exc:
                logger.warning("Segment %s evaluation failed: %s", seg_id, exc)

        return reports
