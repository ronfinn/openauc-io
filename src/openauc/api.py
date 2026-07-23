"""Public API surface for openauc.

Import from here (or the top-level ``openauc`` package) for the stable public
contract. Internal module paths are not part of that contract and may change
between releases without notice.

Phase 2 adds the canonical data model. The model types are also available from
``openauc.models``; they are re-exported here as the curated top-level surface.
"""

from __future__ import annotations

from openauc import __version__
from openauc.exceptions import (
    ArchiveError,
    FormatError,
    ObservationError,
    OpenAUCError,
    StructuralValidationError,
    ValidationError,
)
from openauc.models import (
    AUCExperiment,
    ExperimentMetadata,
    ExperimentType,
    ImportProvenance,
    InstrumentMetadata,
    Observations,
    OpticalSystem,
    Quantity,
    RadiusAxisMode,
    SampleMetadata,
    ScanMetadata,
    Unit,
    ValidationIssue,
    ValidationReport,
    ValidationSeverity,
    ValueProvenance,
    ValueStatus,
    validate_experiment_structure,
)

__all__ = [
    "AUCExperiment",
    "ArchiveError",
    "ExperimentMetadata",
    "ExperimentType",
    "FormatError",
    "ImportProvenance",
    "InstrumentMetadata",
    "ObservationError",
    "Observations",
    "OpenAUCError",
    "OpticalSystem",
    "Quantity",
    "RadiusAxisMode",
    "SampleMetadata",
    "ScanMetadata",
    "StructuralValidationError",
    "Unit",
    "ValidationError",
    "ValidationIssue",
    "ValidationReport",
    "ValidationSeverity",
    "ValueProvenance",
    "ValueStatus",
    "__version__",
    "validate_experiment_structure",
]
