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
    ExperimentType,
    OpticalSystem,
    RadiusAxisMode,
    Unit,
    ValidationSeverity,
    ValueProvenance,
    ValueStatus,
)
from openauc.models.experiment import AUCExperiment
from openauc.models.instrument import InstrumentMetadata
from openauc.models.metadata import ExperimentMetadata, Quantity
from openauc.models.observations import Observations
from openauc.models.provenance import ImportProvenance
from openauc.models.sample import SampleMetadata
from openauc.models.scan import ScanMetadata
from openauc.models.validation import (
    ValidationIssue,
    ValidationReport,
    validate_experiment_structure,
)

__all__ = [
    "AUCExperiment",
    "ExperimentMetadata",
    "ExperimentType",
    "ImportProvenance",
    "InstrumentMetadata",
    "Observations",
    "OpticalSystem",
    "Quantity",
    "RadiusAxisMode",
    "SampleMetadata",
    "ScanMetadata",
    "Unit",
    "ValidationIssue",
    "ValidationReport",
    "ValidationSeverity",
    "ValueProvenance",
    "ValueStatus",
    "validate_experiment_structure",
]
