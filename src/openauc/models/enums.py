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
    "ExperimentType",
    "OpticalSystem",
    "RadiusAxisMode",
    "Unit",
    "ValidationSeverity",
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
    """Severity of a structural-validation issue."""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
