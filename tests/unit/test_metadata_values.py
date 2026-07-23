"""Quantity semantics, units, unknown optical system, and field invariants (5, 8, 9)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError as PydanticValidationError

from openauc.models import (
    ExperimentMetadata,
    OpticalSystem,
    Quantity,
    ScanMetadata,
    Unit,
    ValueProvenance,
    ValueStatus,
)


def test_quantity_present_requires_finite_value() -> None:
    with pytest.raises(PydanticValidationError):
        Quantity(value=float("nan"), unit=Unit.SECOND, status=ValueStatus.PRESENT)
    with pytest.raises(PydanticValidationError):
        Quantity(value=None, unit=Unit.SECOND, status=ValueStatus.PRESENT)


def test_quantity_non_present_must_not_carry_value() -> None:
    with pytest.raises(PydanticValidationError):
        Quantity(value=1.0, status=ValueStatus.MISSING)


def test_quantity_status_distinctions_are_preserved() -> None:
    missing = Quantity.missing()
    unknown = Quantity.unknown()
    not_applicable = Quantity.not_applicable()
    assert missing.status is ValueStatus.MISSING
    assert unknown.status is ValueStatus.UNKNOWN
    assert not_applicable.status is ValueStatus.NOT_APPLICABLE
    # The three absence kinds are distinct, never collapsed into one sentinel.
    assert len({missing.status, unknown.status, not_applicable.status}) == 3
    assert not any(q.is_present for q in (missing, unknown, not_applicable))


def test_quantity_retains_declared_unit_and_label_and_provenance() -> None:
    q = Quantity.of(
        0.5, Unit.OTHER, unit_label="mg/mL", provenance=ValueProvenance.USER_CONFIRMED
    )
    assert q.unit is Unit.OTHER
    assert q.unit_label == "mg/mL"
    assert q.provenance is ValueProvenance.USER_CONFIRMED
    assert q.is_present


def test_unknown_optical_system_is_representable() -> None:
    scan = ScanMetadata(
        scan_id="s",
        index=0,
        elapsed_time=Quantity.of(0.0, Unit.SECOND),
        optical_system=OpticalSystem.UNKNOWN,
    )
    assert scan.optical_system is OpticalSystem.UNKNOWN


def test_all_five_optical_systems_exist() -> None:
    values = {member.value for member in OpticalSystem}
    assert values == {
        "absorbance",
        "interference",
        "fluorescence",
        "intensity",
        "unknown",
    }


def test_negative_elapsed_time_raises_at_construction() -> None:
    with pytest.raises(PydanticValidationError, match="non-negative"):
        ScanMetadata(
            scan_id="s",
            index=0,
            elapsed_time=Quantity.of(-1.0, Unit.SECOND),
        )


def test_negative_wavelength_raises_at_construction() -> None:
    with pytest.raises(PydanticValidationError, match="non-negative"):
        ScanMetadata(
            scan_id="s",
            index=0,
            elapsed_time=Quantity.of(0.0, Unit.SECOND),
            wavelength=Quantity.of(-280.0, Unit.NANOMETRE),
        )


def test_unexpected_unit_is_rejected() -> None:
    with pytest.raises(PydanticValidationError, match="unexpected unit"):
        ScanMetadata(
            scan_id="s",
            index=0,
            elapsed_time=Quantity.of(1.0, Unit.RPM),  # wrong unit for time
        )


def test_unknown_unit_is_always_accepted() -> None:
    scan = ScanMetadata(
        scan_id="s",
        index=0,
        elapsed_time=Quantity(value=1.0, unit=Unit.UNKNOWN, status=ValueStatus.PRESENT),
    )
    assert scan.elapsed_time.unit is Unit.UNKNOWN


def test_negative_scan_index_raises() -> None:
    with pytest.raises(PydanticValidationError):
        ScanMetadata(scan_id="s", index=-1, elapsed_time=Quantity.of(0.0, Unit.SECOND))


def test_empty_experiment_id_raises() -> None:
    with pytest.raises(PydanticValidationError, match="non-empty"):
        ExperimentMetadata(experiment_id="   ")


def test_extra_fields_are_forbidden() -> None:
    with pytest.raises(PydanticValidationError):
        ExperimentMetadata(experiment_id="e", unexpected_field=1)  # type: ignore[call-arg]
