"""Scan metadata (area D).

One :class:`ScanMetadata` describes a single radial acquisition. It carries a
stable identifier and index, the elapsed time, and optional per-scan acquisition
conditions (the *actual* rotor speed and temperature at the time of the scan, as
distinct from the instrument's nominal speed). The observational arrays
themselves live in :class:`~openauc.models.observations.Observations`, keyed by
``scan_id``.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from openauc.models.enums import OpticalSystem, Unit
from openauc.models.metadata import Quantity, reject_negative, require_unit

__all__ = ["ScanMetadata"]


class ScanMetadata(BaseModel):
    """Metadata for a single radial scan."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    scan_id: str
    index: int = Field(ge=0)
    elapsed_time: Quantity
    acquired_at: datetime | None = None
    cell: str | None = None
    channel: str | None = None
    wavelength: Quantity | None = None
    optical_system: OpticalSystem = OpticalSystem.UNKNOWN
    rotor_speed: Quantity | None = None
    temperature: Quantity | None = None
    source_file: str | None = None
    annotations: tuple[str, ...] = ()

    @field_validator("scan_id")
    @classmethod
    def _non_empty_id(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("scan_id must be a non-empty string")
        return value

    @field_validator("elapsed_time")
    @classmethod
    def _check_elapsed_time(cls, value: Quantity) -> Quantity:
        require_unit(value, "elapsed_time", {Unit.SECOND})
        checked = reject_negative(value, "elapsed_time")
        # reject_negative returns the same object; narrow for the type checker.
        assert checked is not None
        return checked

    @field_validator("wavelength")
    @classmethod
    def _check_wavelength(cls, value: Quantity | None) -> Quantity | None:
        return require_unit(
            reject_negative(value, "wavelength"), "wavelength", {Unit.NANOMETRE}
        )

    @field_validator("rotor_speed")
    @classmethod
    def _check_rotor_speed(cls, value: Quantity | None) -> Quantity | None:
        return require_unit(
            reject_negative(value, "rotor_speed"), "rotor_speed", {Unit.RPM}
        )

    @field_validator("temperature")
    @classmethod
    def _check_temperature(cls, value: Quantity | None) -> Quantity | None:
        return require_unit(value, "temperature", {Unit.DEGREE_CELSIUS})
