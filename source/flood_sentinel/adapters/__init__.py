"""Domain adapters and independent recomputation tools for Flood Sentinel."""

from .ranking import DomainPrediction, RankingAdapter, UncalibratedProbabilityError
from .ancestry import (
    RecordAncestry,
    AncestryAdapter,
    SourceDuplicationError,
    MissingSourceError,
)
from .availability import (
    AvailabilityAdapter,
    AvailabilityAuditResult,
    CausalLeakageError,
)
from .exposure import (
    HydrologicExposure,
    ExposureAdapter,
    LabelConsistencyError,
)
from .population import (
    PopulationAdapter,
    GroupAggregationResult,
    InsufficientGroupSupportError,
)
from .recompute import (
    recompute_auroc,
    recompute_average_precision,
    recompute_classification_metrics,
    recompute_probabilistic_metrics,
    recompute_binary_metrics,
    recompute_student_t_critical,
    recompute_paired_sign_flip_pvalue,
    recompute_holm,
    verify_metric_parity,
    RecomputationDiscrepancyError,
)

__all__ = [
    "DomainPrediction",
    "RankingAdapter",
    "UncalibratedProbabilityError",
    "RecordAncestry",
    "AncestryAdapter",
    "SourceDuplicationError",
    "MissingSourceError",
    "AvailabilityAdapter",
    "AvailabilityAuditResult",
    "CausalLeakageError",
    "HydrologicExposure",
    "ExposureAdapter",
    "LabelConsistencyError",
    "PopulationAdapter",
    "GroupAggregationResult",
    "InsufficientGroupSupportError",
    "recompute_auroc",
    "recompute_average_precision",
    "recompute_classification_metrics",
    "recompute_probabilistic_metrics",
    "recompute_binary_metrics",
    "recompute_student_t_critical",
    "recompute_paired_sign_flip_pvalue",
    "recompute_holm",
    "verify_metric_parity",
    "RecomputationDiscrepancyError",
]
