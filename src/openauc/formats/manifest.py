"""Typed experiment manifest (schema version 1.0).

JSON is the canonical manifest format; YAML is accepted as an authoring
convenience. The manifest declares the data file, the format, experiment
identity, and optional instrument/sample/default metadata. It never invents
scientific values: absent metadata stays absent.

The manifest uses author-friendly scalar fields with unit-suffixed names (e.g.
``wavelength_nm``); the parsers convert these into canonical
:class:`~openauc.models.Quantity` values with their declared units. Unit text is
never inferred from a value here.
"""

from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path, PurePosixPath
from typing import Any

import yaml
from pydantic import (
    BaseModel,
    ConfigDict,
    ValidationError,
    field_validator,
    model_validator,
)

from openauc.exceptions import ManifestError
from openauc.models import ExperimentType, OpticalSystem

__all__ = [
    "GenericManifest",
    "ManifestDefaults",
    "ManifestExperiment",
    "ManifestInstrument",
    "ManifestSample",
    "WideColumns",
    "WideScanColumn",
    "load_manifest",
    "parse_timestamp",
]

SUPPORTED_SCHEMA_VERSION = "1.0"


class _Base(BaseModel):
    model_config = ConfigDict(extra="forbid")


def parse_timestamp(value: object) -> datetime:
    """Parse an acquisition timestamp strictly; never guess, never convert.

    Accepts an ISO-8601 date-time string, or a ``datetime`` (which is what a YAML
    parser yields for an unquoted timestamp). An explicit UTC offset is preserved
    exactly; a timestamp with no offset stays timezone-naive, meaning "timezone
    not stated". Nothing is converted to another zone.

    A date without a time of day is rejected rather than padded with midnight,
    and so are numbers (an epoch value would imply a timezone and an origin).

    Raises:
        ValueError: if ``value`` is not an ISO-8601 date-time.
    """
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        raise ValueError(
            f"{value.isoformat()!r} is a date without a time of day; supply an "
            "ISO-8601 date-time such as '2026-03-02T09:30:00+01:00'"
        )
    if not isinstance(value, str):
        raise ValueError(
            f"{value!r} is not an ISO-8601 date-time string "
            f"(got {type(value).__name__})"
        )
    text = value.strip()
    try:
        date.fromisoformat(text)
    except ValueError:
        pass
    else:
        raise ValueError(
            f"{value!r} is a date without a time of day; supply an ISO-8601 "
            "date-time such as '2026-03-02T09:30:00+01:00'"
        )
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        raise ValueError(f"{value!r} is not an ISO-8601 date-time") from None


class ManifestExperiment(_Base):
    """Experiment identity, mirroring the canonical experiment metadata."""

    experiment_id: str
    name: str | None = None
    description: str | None = None
    experiment_type: ExperimentType = ExperimentType.UNKNOWN
    acquired_at: datetime | None = None
    operator: str | None = None
    notes: str | None = None

    @field_validator("acquired_at", mode="before")
    @classmethod
    def _strict_timestamp(cls, value: object) -> datetime | None:
        return None if value is None else parse_timestamp(value)


class ManifestInstrument(_Base):
    """Optional instrument and run metadata. All fields optional."""

    manufacturer: str | None = None
    model: str | None = None
    serial_number: str | None = None
    rotor_id: str | None = None
    nominal_speed_rpm: float | None = None
    temperature_c: float | None = None
    cell: str | None = None
    channel: str | None = None
    centrepiece: str | None = None
    optical_system: OpticalSystem | None = None
    wavelength_nm: float | None = None


class ManifestSample(_Base):
    """Optional sample/buffer metadata."""

    sample_id: str
    description: str | None = None
    buffer_description: str | None = None
    concentration_value: float | None = None
    concentration_unit: str | None = None
    density: float | None = None
    viscosity: float | None = None
    partial_specific_volume: float | None = None
    notes: str | None = None


class ManifestDefaults(_Base):
    """Scan-level defaults applied where the table does not supply a value.

    A default that conflicts with a value supplied in the table is an error, not
    an override (the parser raises :class:`DataConflictError`).
    """

    optical_system: OpticalSystem | None = None
    signal_unit: str | None = None
    sample_id: str | None = None
    cell: str | None = None
    channel: str | None = None
    wavelength_nm: float | None = None
    rotor_speed_rpm: float | None = None
    temperature_c: float | None = None


class WideScanColumn(_Base):
    """Maps one wide-format signal column to a scan and its metadata."""

    column: str
    scan_id: str
    elapsed_seconds: float | None = None
    acquisition_timestamp: datetime | None = None
    sample_id: str | None = None
    wavelength_nm: float | None = None
    optical_system: OpticalSystem | None = None
    rotor_speed_rpm: float | None = None
    temperature_c: float | None = None
    cell: str | None = None
    channel: str | None = None
    source_scan_id: str | None = None

    @field_validator("acquisition_timestamp", mode="before")
    @classmethod
    def _strict_timestamp(cls, value: object) -> datetime | None:
        return None if value is None else parse_timestamp(value)


class WideColumns(_Base):
    """Wide-format column mapping: the radius column and the signal columns."""

    radius: str
    scans: tuple[WideScanColumn, ...]


class GenericManifest(_Base):
    """The top-level manifest model."""

    schema_version: str
    format: str | None = None
    data_file: str
    experiment: ManifestExperiment
    instrument: ManifestInstrument | None = None
    samples: tuple[ManifestSample, ...] = ()
    defaults: ManifestDefaults = ManifestDefaults()
    columns: WideColumns | None = None
    delimiter: str | None = None
    notes: str | None = None
    extension: dict[str, Any] | None = None

    @field_validator("schema_version")
    @classmethod
    def _check_version(cls, value: str) -> str:
        if value != SUPPORTED_SCHEMA_VERSION:
            raise ValueError(
                f"unsupported schema_version {value!r}; "
                f"this build supports {SUPPORTED_SCHEMA_VERSION!r}"
            )
        return value

    @model_validator(mode="after")
    def _sample_references_resolve(self) -> GenericManifest:
        declared = {sample.sample_id for sample in self.samples}
        references = [("defaults.sample_id", self.defaults.sample_id)]
        if self.columns is not None:
            references.extend(
                (f"columns.scans[{scan.column!r}].sample_id", scan.sample_id)
                for scan in self.columns.scans
            )
        for location, sample_id in references:
            if sample_id is not None and sample_id not in declared:
                raise ValueError(
                    f"{location} names sample {sample_id!r}, which is not "
                    f"declared in 'samples' (declared: {sorted(declared)})"
                )
        return self

    @field_validator("data_file")
    @classmethod
    def _safe_data_file(cls, value: str) -> str:
        _reject_unsafe_relative_path(value)
        return value

    @field_validator("delimiter")
    @classmethod
    def _known_delimiter(cls, value: str | None) -> str | None:
        if value is None:
            return None
        token = value.strip().lower()
        if token not in {",", "\t", "comma", "tab"}:
            raise ValueError("delimiter must be one of ',', '\\t', 'comma' or 'tab'")
        return value


def _reject_unsafe_relative_path(value: str) -> None:
    """Raise ``ValueError`` if ``value`` is absolute or escapes its directory."""
    if not value or value.strip() == "":
        raise ValueError("data_file must be a non-empty relative path")
    pure = PurePosixPath(value)
    if pure.is_absolute() or value.startswith(("/", "\\")):
        raise ValueError(f"data_file must be relative, got {value!r}")
    if ".." in pure.parts:
        raise ValueError(
            f"data_file must not escape the experiment directory: {value!r}"
        )
    # Reject Windows-style drive/absolute forms too.
    if len(value) >= 2 and value[1] == ":":
        raise ValueError(f"data_file must be relative, got {value!r}")


def load_manifest(path: Path) -> GenericManifest:
    """Load and validate a manifest from a JSON or YAML file.

    Raises:
        ManifestError: if the file is missing, unparseable, or fails schema
            validation.
    """
    if not path.is_file():
        raise ManifestError(f"manifest file not found: {path}")
    text = path.read_text(encoding="utf-8")
    suffix = path.suffix.lower()
    try:
        if suffix in {".yaml", ".yml"}:
            raw = yaml.safe_load(text)
        elif suffix == ".json":
            raw = json.loads(text)
        else:
            raise ManifestError(
                f"unsupported manifest suffix {suffix!r} (expected .json/.yaml/.yml)"
            )
    except (json.JSONDecodeError, yaml.YAMLError) as exc:
        raise ManifestError(f"could not parse manifest {path.name}: {exc}") from exc

    if not isinstance(raw, dict):
        raise ManifestError(
            f"manifest {path.name} must contain a mapping at the top level"
        )
    try:
        return GenericManifest.model_validate(raw)
    except ValidationError as exc:
        raise ManifestError(f"manifest {path.name} failed validation: {exc}") from exc
