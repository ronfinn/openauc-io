"""Public API surface for openauc.

Import from here (or the top-level ``openauc`` package) for the stable public
contract. Internal module paths are not part of that contract and may change
between releases without notice.

The model types are also available from ``openauc.models``; they are re-exported
here as the curated top-level surface.

The plotting helpers (``plot_scans``, ``plot_scan``) are part of this contract
but are resolved **lazily**, because importing them pulls in matplotlib. Reading
``openauc.api.plot_scans`` imports :mod:`openauc.plotting` on first access; the
ingestion, validation and summary paths never pay that cost.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from openauc import __version__
from openauc.exceptions import (
    AmbiguousFormatError,
    ArchiveError,
    ArchiveIntegrityError,
    ArchiveVersionError,
    DataConflictError,
    FormatError,
    ManifestError,
    ObservationError,
    OpenAUCError,
    ParseError,
    PlottingError,
    StructuralValidationError,
    UnsupportedFormatError,
    ValidationError,
)
from openauc.formats import (
    AUCX_FORMAT_VERSION,
    ArchiveValidationReport,
    AUCXExport,
    AUCXInfo,
    DetectionResult,
    FormatInfo,
    GenericManifest,
    available_formats,
    export_aucx,
    inspect_aucx,
    load,
    validate_aucx,
)
from openauc.models import (
    AnalysisKind,
    AnalysisReadiness,
    AUCExperiment,
    ExperimentMetadata,
    ExperimentSummary,
    ExperimentType,
    ImportProvenance,
    InstrumentMetadata,
    MetadataPresence,
    Observations,
    OpticalSystem,
    Quantity,
    RadiusAxisMode,
    ReadinessAssessment,
    ReadinessStatus,
    SampleMetadata,
    ScanMetadata,
    SourceChecksum,
    Unit,
    ValidationCounts,
    ValidationIssue,
    ValidationReport,
    ValidationSeverity,
    ValidationTier,
    ValueProvenance,
    ValueRange,
    ValueStatus,
    assess_experiment_readiness,
    summarise_experiment,
    validate_experiment,
    validate_experiment_structure,
)

__all__ = [
    "AUCX_FORMAT_VERSION",
    "AUCExperiment",
    "AUCXExport",
    "AUCXInfo",
    "AmbiguousFormatError",
    "AnalysisKind",
    "AnalysisReadiness",
    "ArchiveError",
    "ArchiveIntegrityError",
    "ArchiveValidationReport",
    "ArchiveVersionError",
    "DataConflictError",
    "DetectionResult",
    "ExperimentMetadata",
    "ExperimentSummary",
    "ExperimentType",
    "FormatError",
    "FormatInfo",
    "GenericManifest",
    "ImportProvenance",
    "InstrumentMetadata",
    "ManifestError",
    "MetadataPresence",
    "ObservationError",
    "Observations",
    "OpenAUCError",
    "OpticalSystem",
    "ParseError",
    "PlottingError",
    "Quantity",
    "RadiusAxisMode",
    "ReadinessAssessment",
    "ReadinessStatus",
    "SampleMetadata",
    "ScanMetadata",
    "SourceChecksum",
    "StructuralValidationError",
    "Unit",
    "UnsupportedFormatError",
    "ValidationCounts",
    "ValidationError",
    "ValidationIssue",
    "ValidationReport",
    "ValidationSeverity",
    "ValidationTier",
    "ValueProvenance",
    "ValueRange",
    "ValueStatus",
    "__version__",
    "assess_experiment_readiness",
    "available_formats",
    "export_aucx",
    "inspect_aucx",
    "load",
    "plot_scan",
    "plot_scans",
    "summarise_experiment",
    "validate_aucx",
    "validate_experiment",
    "validate_experiment_structure",
]

# Plotting is re-exported lazily so that importing the public facade does not
# pull in matplotlib. The TYPE_CHECKING import gives type checkers the real
# signatures; ``__getattr__`` (PEP 562) resolves them at first attribute access.
if TYPE_CHECKING:
    from openauc.plotting import plot_scan, plot_scans

_LAZY_PLOTTING = frozenset({"plot_scan", "plot_scans"})


def __getattr__(name: str) -> Any:
    """Resolve the lazily re-exported plotting helpers on first access."""
    if name in _LAZY_PLOTTING:
        import openauc.plotting as plotting

        return getattr(plotting, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    return sorted(__all__)
