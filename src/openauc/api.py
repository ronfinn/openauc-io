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
    AmbiguousFormatError,
    ArchiveError,
    DataConflictError,
    FormatError,
    ManifestError,
    ObservationError,
    OpenAUCError,
    ParseError,
    StructuralValidationError,
    UnsupportedFormatError,
    ValidationError,
)
from openauc.formats import (
    DetectionResult,
    FormatInfo,
    GenericManifest,
    available_formats,
    load,
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
    "AmbiguousFormatError",
    "ArchiveError",
    "DataConflictError",
    "DetectionResult",
    "ExperimentMetadata",
    "ExperimentType",
    "FormatError",
    "FormatInfo",
    "GenericManifest",
    "ImportProvenance",
    "InstrumentMetadata",
    "ManifestError",
    "ObservationError",
    "Observations",
    "OpenAUCError",
    "OpticalSystem",
    "ParseError",
    "Quantity",
    "RadiusAxisMode",
    "SampleMetadata",
    "ScanMetadata",
    "StructuralValidationError",
    "Unit",
    "UnsupportedFormatError",
    "ValidationError",
    "ValidationIssue",
    "ValidationReport",
    "ValidationSeverity",
    "ValueProvenance",
    "ValueStatus",
    "__version__",
    "available_formats",
    "load",
    "validate_experiment_structure",
]
