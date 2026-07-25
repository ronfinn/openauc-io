"""Canonical in-memory AUC data model (Phase 2).

Public model surface. Import model types from here:

    from openauc.models import AUCExperiment, ExperimentMetadata, ScanMetadata

This layer represents an AUC experiment faithfully — retaining raw observations,
declared units, explicit missing/unknown/not-applicable semantics, and value
provenance. It performs no interpolation, resampling, unit inference or
conversion, and makes no judgement about scientific validity.
"""

from __future__ import annotations

from openauc.models.enums import (
    AnalysisKind,
    ExperimentType,
    OpticalSystem,
    RadiusAxisMode,
    ReadinessStatus,
    Unit,
    ValidationSeverity,
    ValidationTier,
    ValueProvenance,
    ValueStatus,
)
from openauc.models.experiment import AUCExperiment
from openauc.models.instrument import InstrumentMetadata
from openauc.models.metadata import ExperimentMetadata, Quantity
from openauc.models.observations import Observations
from openauc.models.provenance import ImportProvenance
from openauc.models.readiness import (
    AnalysisReadiness,
    ReadinessAssessment,
    assess_experiment_readiness,
)
from openauc.models.sample import SampleMetadata
from openauc.models.scan import ScanMetadata
from openauc.models.summary import (
    ExperimentSummary,
    MetadataPresence,
    ValidationCounts,
    ValueRange,
    summarise_experiment,
)
from openauc.models.validation import (
    ValidationIssue,
    ValidationReport,
    validate_experiment,
    validate_experiment_structure,
)

__all__ = [
    "AUCExperiment",
    "AnalysisKind",
    "AnalysisReadiness",
    "ExperimentMetadata",
    "ExperimentSummary",
    "ExperimentType",
    "ImportProvenance",
    "InstrumentMetadata",
    "MetadataPresence",
    "Observations",
    "OpticalSystem",
    "Quantity",
    "RadiusAxisMode",
    "ReadinessAssessment",
    "ReadinessStatus",
    "SampleMetadata",
    "ScanMetadata",
    "Unit",
    "ValidationCounts",
    "ValidationIssue",
    "ValidationReport",
    "ValidationSeverity",
    "ValidationTier",
    "ValueProvenance",
    "ValueRange",
    "ValueStatus",
    "assess_experiment_readiness",
    "summarise_experiment",
    "validate_experiment",
    "validate_experiment_structure",
]
