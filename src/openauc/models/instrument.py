"""Instrument and run metadata (area B).

Every field is optional. Nominal rotor speed lives here; *actual* per-scan speed
is retained separately on each :class:`~openauc.models.scan.ScanMetadata`.
Quantities retain their declared units and are never converted.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, field_validator

from openauc.models.enums import OpticalSystem, Unit
from openauc.models.metadata import Quantity, reject_negative, require_unit

__all__ = ["InstrumentMetadata"]


class InstrumentMetadata(BaseModel):
    """Instrument, rotor and run-level acquisition metadata."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    manufacturer: str | None = None
    model: str | None = None
    serial_number: str | None = None
    rotor_id: str | None = None
    nominal_speed: Quantity | None = None
    temperature: Quantity | None = None
    cell: str | None = None
    channel: str | None = None
    centrepiece: str | None = None
    optical_system: OpticalSystem = OpticalSystem.UNKNOWN
    wavelength: Quantity | None = None

    @field_validator("nominal_speed")
    @classmethod
    def _check_speed(cls, value: Quantity | None) -> Quantity | None:
        return require_unit(
            reject_negative(value, "nominal_speed"), "nominal_speed", {Unit.RPM}
        )

    @field_validator("temperature")
    @classmethod
    def _check_temperature(cls, value: Quantity | None) -> Quantity | None:
        return require_unit(value, "temperature", {Unit.DEGREE_CELSIUS})

    @field_validator("wavelength")
    @classmethod
    def _check_wavelength(cls, value: Quantity | None) -> Quantity | None:
        return require_unit(
            reject_negative(value, "wavelength"), "wavelength", {Unit.NANOMETRE}
        )
