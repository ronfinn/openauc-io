"""Enumerations for the canonical AUC data model.

All categorical vocabularies used by the model live here so they have a single
definition and stable string values (the enums are ``StrEnum``, so their members
serialise to their declared string). Representing an optical system or unit here
does **not** imply that importing or scientifically interpreting it is
implemented — representation and support are deliberately separate.
"""

from __future__ import annotations

from enum import StrEnum

__all__ = [
    "AnalysisKind",
    "ExperimentType",
    "OpticalSystem",
    "RadiusAxisMode",
    "ReadinessStatus",
    "Unit",
    "ValidationSeverity",
    "ValidationTier",
    "ValueProvenance",
    "ValueStatus",
]


class ExperimentType(StrEnum):
    """The kind of AUC experiment. ``UNKNOWN`` is explicit, never inferred."""

    SEDIMENTATION_VELOCITY = "sedimentation_velocity"
    SEDIMENTATION_EQUILIBRIUM = "sedimentation_equilibrium"
    OTHER = "other"
    UNKNOWN = "unknown"


class OpticalSystem(StrEnum):
    """Optical detection systems the model can *represent*.

    Representation support is not a claim that file import or scientific
    interpretation is implemented or validated for every system.
    """

    ABSORBANCE = "absorbance"
    INTERFERENCE = "interference"
    FLUORESCENCE = "fluorescence"
    INTENSITY = "intensity"
    UNKNOWN = "unknown"


class Unit(StrEnum):
    """Declared units retained by the model.

    The canonical unit for each physical quantity is listed below. The model
    **retains** the declared unit and never infers or silently converts. Units
    that are open-ended (e.g. concentration) or absent are represented by
    ``OTHER`` (carry the verbatim text in ``Quantity.unit_label``) or
    ``UNKNOWN``.
    """

    # radius
    CENTIMETRE = "cm"
    # elapsed time and sedimentation coefficient (canonical: seconds)
    SECOND = "s"
    # rotor speed
    RPM = "rpm"
    # temperature
    DEGREE_CELSIUS = "degC"
    # wavelength
    NANOMETRE = "nm"
    # diffusion coefficient
    SQUARE_CENTIMETRE_PER_SECOND = "cm2/s"
    # absorbance signal
    ABSORBANCE_UNIT = "AU"
    # interference signal
    FRINGE = "fringe"
    # fluorescence / intensity signal
    INSTRUMENT_UNIT = "instrument_unit"
    CALIBRATED_UNIT = "calibrated_unit"
    # open-ended or absent
    OTHER = "other"
    UNKNOWN = "unknown"


class RadiusAxisMode(StrEnum):
    """Whether scans share one radius axis or each carry their own."""

    SHARED = "shared"
    PER_SCAN = "per_scan"


class ValueStatus(StrEnum):
    """Explicit presence semantics for a scientific value.

    ``MISSING``, ``UNKNOWN`` and ``NOT_APPLICABLE`` are conceptually different
    and must not be collapsed into a single sentinel or a default value.
    """

    PRESENT = "present"
    MISSING = "missing"
    UNKNOWN = "unknown"
    NOT_APPLICABLE = "not_applicable"


class ValueProvenance(StrEnum):
    """Where a value came from, retained per value."""

    SUPPLIED = "supplied"
    CONVERTED = "converted"
    INFERRED = "inferred"
    USER_CONFIRMED = "user_confirmed"
    UNKNOWN = "unknown"


class ValidationSeverity(StrEnum):
    """Severity of a validation finding.

    The severity policy is fixed and applied uniformly:

    * ``ERROR`` — may block ``ARCHIVAL`` or ``STRUCTURAL`` validity. Only errors
      affect :attr:`~openauc.models.validation.ValidationReport.is_valid`.
    * ``WARNING`` — never blocks archival or structural validity. It either
      blocks a readiness tier or flags a representational anomaly.
    * ``INFO`` — descriptive only; blocks nothing.

    Readiness findings never use ``ERROR``.
    """

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class ValidationTier(StrEnum):
    """The question a validation finding speaks to.

    Tiers are answered independently; a finding may pertain to more than one.
    Scientific suitability is deliberately **not** a tier — see
    :class:`ReadinessStatus` and :class:`AnalysisKind`.
    """

    #: Can the experiment be stored and returned unchanged and unambiguously?
    ARCHIVAL = "archival"
    #: Are metadata, scans and observations internally consistent?
    STRUCTURAL = "structural"
    #: Is the metadata a future sedimentation-velocity workflow needs present?
    SV_READINESS = "sv_readiness"
    #: Is the metadata a future sedimentation-equilibrium workflow needs present?
    SE_READINESS = "se_readiness"


class ReadinessStatus(StrEnum):
    """Outcome of an analysis-readiness assessment.

    ``POTENTIALLY_READY`` reports that the metadata a future workflow needs is
    *present*. It is never a statement that the data are correct, of good
    quality, or scientifically suitable — that is never assessed.
    """

    POTENTIALLY_READY = "potentially_ready"
    BLOCKED = "blocked"
    NOT_APPLICABLE = "not_applicable"
    NOT_ASSESSED = "not_assessed"


class AnalysisKind(StrEnum):
    """A workflow whose metadata prerequisites can be reported on.

    ``SCIENTIFIC_SUITABILITY`` is included so that "not assessed" is a
    machine-readable, always-present part of every assessment rather than a
    prose disclaimer. Its status is permanently
    :attr:`ReadinessStatus.NOT_ASSESSED`.
    """

    SEDIMENTATION_VELOCITY = "sedimentation_velocity"
    SEDIMENTATION_EQUILIBRIUM = "sedimentation_equilibrium"
    SCIENTIFIC_SUITABILITY = "scientific_suitability"
