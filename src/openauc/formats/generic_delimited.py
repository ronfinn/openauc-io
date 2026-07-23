"""Generic long- and wide-format delimited (CSV/TSV) parsers.

These parsers read plain delimited radial-scan data into the canonical
:class:`~openauc.models.AUCExperiment`. They preserve raw values and row order,
never interpolate or resample, never infer units from values, and never invent
metadata. Ambiguity and conflicts are reported as domain-specific errors.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from openauc.exceptions import DataConflictError, ManifestError, ParseError
from openauc.formats.base import (
    DetectionResult,
    Parser,
    ParseResult,
    ResolvedSource,
    Table,
)
from openauc.formats.manifest import (
    GenericManifest,
    ManifestDefaults,
    ManifestInstrument,
    ManifestSample,
    WideScanColumn,
)
from openauc.formats.registry import register_parser
from openauc.models import (
    AUCExperiment,
    ExperimentMetadata,
    InstrumentMetadata,
    Observations,
    OpticalSystem,
    Quantity,
    SampleMetadata,
    ScanMetadata,
    Unit,
)

__all__ = ["GenericLongParser", "GenericWideParser"]

_LONG_REQUIRED = ("scan", "radius_cm", "signal")
_LONG_OPTIONAL = (
    "elapsed_seconds",
    "acquisition_timestamp",
    "cell",
    "channel",
    "wavelength_nm",
    "optical_system",
    "signal_unit",
    "rotor_speed_rpm",
    "temperature_c",
    "source_scan_id",
)


# --------------------------------------------------------------------------- #
# Scalar helpers
# --------------------------------------------------------------------------- #


def _to_float(raw: str, *, column: str, location: str, path: Path) -> float:
    text = raw.strip()
    try:
        value = float(text)
    except ValueError:
        raise ParseError(
            f"{path.name} ({location}, column {column!r}): "
            f"expected a finite number, got {raw!r}"
        ) from None
    if not math.isfinite(value):
        raise ParseError(
            f"{path.name} ({location}, column {column!r}): "
            f"value must be finite, got {raw!r}"
        )
    return value


def _parse_unit(text: str) -> tuple[Unit, str | None]:
    """Map a unit string to a ``Unit`` (by value or name), else OTHER + label."""
    try:
        return (Unit(text), None)
    except ValueError:
        pass
    try:
        return (Unit[text.upper()], None)
    except KeyError:
        return (Unit.OTHER, text)


def _parse_optical(text: str) -> OpticalSystem:
    try:
        return OpticalSystem(text)
    except ValueError:
        pass
    try:
        return OpticalSystem[text.upper()]
    except KeyError:
        raise ParseError(f"unknown optical_system {text!r}") from None


def _quantity_or_none(value: float | None, unit: Unit) -> Quantity | None:
    return Quantity.of(value, unit) if value is not None else None


# --------------------------------------------------------------------------- #
# Conflict-aware resolution (table value vs manifest default)
# --------------------------------------------------------------------------- #


def _resolve_str(
    table_value: str | None, default_value: str | None, field: str, scan_id: str
) -> str | None:
    if (
        table_value is not None
        and default_value is not None
        and table_value != default_value
    ):
        raise DataConflictError(
            f"scan {scan_id!r}: {field} is {table_value!r} in the data but "
            f"{default_value!r} in the manifest defaults"
        )
    return table_value if table_value is not None else default_value


def _resolve_float(
    table_value: float | None,
    default_value: float | None,
    field: str,
    scan_id: str,
) -> float | None:
    if (
        table_value is not None
        and default_value is not None
        and table_value != default_value
    ):
        raise DataConflictError(
            f"scan {scan_id!r}: {field} is {table_value} in the data but "
            f"{default_value} in the manifest defaults"
        )
    return table_value if table_value is not None else default_value


def _resolve_optical(
    table_value: OpticalSystem | None,
    default_value: OpticalSystem | None,
    scan_id: str,
) -> OpticalSystem:
    if (
        table_value is not None
        and default_value is not None
        and table_value is not default_value
    ):
        raise DataConflictError(
            f"scan {scan_id!r}: optical_system is {table_value.value!r} in the "
            f"data but {default_value.value!r} in the manifest defaults"
        )
    chosen = table_value if table_value is not None else default_value
    return chosen if chosen is not None else OpticalSystem.UNKNOWN


# --------------------------------------------------------------------------- #
# Per-scan metadata inputs (a normalised, typed view shared by both layouts)
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class _ScanInputs:
    scan_id: str
    elapsed_seconds: float | None = None
    acquired_at: datetime | None = None
    cell: str | None = None
    channel: str | None = None
    wavelength_nm: float | None = None
    optical_system: OpticalSystem | None = None
    rotor_speed_rpm: float | None = None
    temperature_c: float | None = None
    source_scan_id: str | None = None


def _build_scan_metadata(
    inputs: _ScanInputs,
    index: int,
    defaults: ManifestDefaults,
    source_file: str,
) -> ScanMetadata:
    scan_id = inputs.scan_id
    elapsed = (
        Quantity.of(inputs.elapsed_seconds, Unit.SECOND)
        if inputs.elapsed_seconds is not None
        else Quantity.missing()
    )
    wavelength = _resolve_float(
        inputs.wavelength_nm, defaults.wavelength_nm, "wavelength_nm", scan_id
    )
    rotor = _resolve_float(
        inputs.rotor_speed_rpm, defaults.rotor_speed_rpm, "rotor_speed_rpm", scan_id
    )
    temperature = _resolve_float(
        inputs.temperature_c, defaults.temperature_c, "temperature_c", scan_id
    )
    annotations = (
        (f"source_scan_id={inputs.source_scan_id}",) if inputs.source_scan_id else ()
    )
    return ScanMetadata(
        scan_id=scan_id,
        index=index,
        elapsed_time=elapsed,
        acquired_at=inputs.acquired_at,
        cell=_resolve_str(inputs.cell, defaults.cell, "cell", scan_id),
        channel=_resolve_str(inputs.channel, defaults.channel, "channel", scan_id),
        wavelength=_quantity_or_none(wavelength, Unit.NANOMETRE),
        optical_system=_resolve_optical(
            inputs.optical_system, defaults.optical_system, scan_id
        ),
        rotor_speed=_quantity_or_none(rotor, Unit.RPM),
        temperature=_quantity_or_none(temperature, Unit.DEGREE_CELSIUS),
        source_file=source_file,
        annotations=annotations,
    )


def _resolve_signal_unit(
    table_units: set[str], default_unit: str | None, path: Path
) -> Unit:
    """Resolve the single signal unit for an observation set."""
    if len(table_units) > 1:
        raise DataConflictError(
            f"{path.name}: multiple signal_unit values in one file: "
            f"{sorted(table_units)}"
        )
    table_unit = next(iter(table_units)) if table_units else None
    if (
        table_unit is not None
        and default_unit is not None
        and table_unit != default_unit
    ):
        raise DataConflictError(
            f"{path.name}: signal_unit is {table_unit!r} in the data but "
            f"{default_unit!r} in the manifest defaults"
        )
    chosen = table_unit if table_unit is not None else default_unit
    if chosen is None:
        return Unit.UNKNOWN
    return _parse_unit(chosen)[0]


# --------------------------------------------------------------------------- #
# Manifest → canonical metadata (shared)
# --------------------------------------------------------------------------- #


def _experiment_metadata(manifest: GenericManifest) -> ExperimentMetadata:
    me = manifest.experiment
    return ExperimentMetadata(
        experiment_id=me.experiment_id,
        name=me.name,
        description=me.description,
        experiment_type=me.experiment_type,
        operator=me.operator,
        notes=me.notes,
    )


def _instrument_metadata(
    manifest: GenericManifest,
) -> InstrumentMetadata | None:
    mi: ManifestInstrument | None = manifest.instrument
    if mi is None:
        return None
    return InstrumentMetadata(
        manufacturer=mi.manufacturer,
        model=mi.model,
        serial_number=mi.serial_number,
        rotor_id=mi.rotor_id,
        nominal_speed=_quantity_or_none(mi.nominal_speed_rpm, Unit.RPM),
        temperature=_quantity_or_none(mi.temperature_c, Unit.DEGREE_CELSIUS),
        cell=mi.cell,
        channel=mi.channel,
        centrepiece=mi.centrepiece,
        optical_system=mi.optical_system or OpticalSystem.UNKNOWN,
        wavelength=_quantity_or_none(mi.wavelength_nm, Unit.NANOMETRE),
    )


def _sample_metadata(sample: ManifestSample) -> SampleMetadata:
    concentration: Quantity | None = None
    if sample.concentration_value is not None:
        if sample.concentration_unit is not None:
            unit, label = _parse_unit(sample.concentration_unit)
        else:
            unit, label = Unit.UNKNOWN, None
        concentration = Quantity.of(sample.concentration_value, unit, unit_label=label)
    return SampleMetadata(
        sample_id=sample.sample_id,
        description=sample.description,
        buffer_description=sample.buffer_description,
        concentration=concentration,
        density=_quantity_or_none(sample.density, Unit.UNKNOWN),
        viscosity=_quantity_or_none(sample.viscosity, Unit.UNKNOWN),
        partial_specific_volume=_quantity_or_none(
            sample.partial_specific_volume, Unit.UNKNOWN
        ),
        notes=sample.notes,
    )


def _samples(manifest: GenericManifest) -> tuple[SampleMetadata, ...]:
    return tuple(_sample_metadata(s) for s in manifest.samples)


def _require_manifest(manifest: GenericManifest | None, path: Path) -> GenericManifest:
    if manifest is None:
        raise ManifestError(
            f"loading {path.name} requires a manifest (for experiment identity "
            "and format), but none was found"
        )
    return manifest


# --------------------------------------------------------------------------- #
# Long-format parser
# --------------------------------------------------------------------------- #


@register_parser
class GenericLongParser(Parser):
    """Generic long-format CSV/TSV: one row per radial observation."""

    format_id = "generic-long"
    name = "Generic long-format delimited"
    suffixes = (".csv", ".tsv")
    layouts = ("long",)
    limitations = (
        "one signal unit per file; no vendor-specific columns; "
        "requires a manifest for experiment identity",
    )
    doc_reference = "docs/formats/generic-delimited.md"

    def detect(self, table: Table, manifest: GenericManifest | None) -> DetectionResult:
        present = tuple(c for c in _LONG_REQUIRED if c in table.header)
        evidence = (f"columns present: {', '.join(present) or 'none'}",)
        if len(present) == len(_LONG_REQUIRED):
            confidence = 0.8
            if manifest is not None and manifest.format == self.format_id:
                confidence = 0.95
        else:
            confidence = 0.1 * len(present)
        return DetectionResult(
            parser_id=self.format_id, confidence=confidence, evidence=evidence
        )

    def parse(
        self,
        table: Table,
        source: ResolvedSource,
        manifest: GenericManifest | None,
    ) -> ParseResult:
        manifest = _require_manifest(manifest, table.path)
        missing = [c for c in _LONG_REQUIRED if c not in table.header]
        if missing:
            raise ParseError(
                f"{table.path.name}: missing required column(s) "
                f"{missing}; long format needs {list(_LONG_REQUIRED)}"
            )

        idx = {name: table.column_index(name) for name in table.header}
        scan_i = idx["scan"]
        radius_i = idx["radius_cm"]
        signal_i = idx["signal"]

        order: list[str] = []
        radii: dict[str, list[float]] = {}
        signals: dict[str, list[float]] = {}
        seen_pairs: set[tuple[str, float]] = set()
        per_scan_cols: dict[str, dict[str, str]] = {}
        signal_units: set[str] = set()

        for row_number, row in enumerate(table.rows, start=2):
            if len(row) != len(table.header):
                raise ParseError(
                    f"{table.path.name} (row {row_number}): expected "
                    f"{len(table.header)} fields, got {len(row)}"
                )
            scan_id = row[scan_i].strip()
            if not scan_id:
                raise ParseError(
                    f"{table.path.name} (row {row_number}): empty scan identifier"
                )
            location = f"row {row_number}"
            radius = _to_float(
                row[radius_i], column="radius_cm", location=location, path=table.path
            )
            signal = _to_float(
                row[signal_i], column="signal", location=location, path=table.path
            )
            pair = (scan_id, radius)
            if pair in seen_pairs:
                raise DataConflictError(
                    f"{table.path.name} (row {row_number}): duplicate observation "
                    f"for scan {scan_id!r} at radius {radius}"
                )
            seen_pairs.add(pair)

            if scan_id not in radii:
                order.append(scan_id)
                radii[scan_id] = []
                signals[scan_id] = []
                per_scan_cols[scan_id] = {}
            radii[scan_id].append(radius)
            signals[scan_id].append(signal)

            self._accumulate_optional(
                row, idx, scan_id, row_number, table, per_scan_cols, signal_units
            )

        signal_unit = _resolve_signal_unit(
            signal_units, manifest.defaults.signal_unit, table.path
        )
        scans = tuple(
            _build_scan_metadata(
                self._scan_inputs(scan_id, per_scan_cols[scan_id], table),
                index,
                manifest.defaults,
                table.path.name,
            )
            for index, scan_id in enumerate(order)
        )
        observations = self._observations(order, radii, signals, signal_unit)
        experiment = AUCExperiment(
            metadata=_experiment_metadata(manifest),
            scans=scans,
            observations=observations,
            samples=_samples(manifest),
            instrument=_instrument_metadata(manifest),
        )
        assumptions = (
            "radius column 'radius_cm' interpreted as centimetres",
            f"signal unit resolved to {signal_unit.value!r}",
            f"radius axis: {observations.mode.value}",
        )
        return ParseResult(experiment=experiment, assumptions=assumptions)

    @staticmethod
    def _accumulate_optional(
        row: tuple[str, ...],
        idx: dict[str, int],
        scan_id: str,
        row_number: int,
        table: Table,
        per_scan_cols: dict[str, dict[str, str]],
        signal_units: set[str],
    ) -> None:
        for column in _LONG_OPTIONAL:
            if column not in idx:
                continue
            value = row[idx[column]].strip()
            if not value:
                continue
            if column == "signal_unit":
                signal_units.add(value)
                continue
            existing = per_scan_cols[scan_id].get(column)
            if existing is not None and existing != value:
                raise DataConflictError(
                    f"{table.path.name} (row {row_number}): scan {scan_id!r} has "
                    f"inconsistent {column!r} values {existing!r} and {value!r}"
                )
            per_scan_cols[scan_id][column] = value

    @staticmethod
    def _scan_inputs(
        scan_id: str, columns: dict[str, str], table: Table
    ) -> _ScanInputs:
        def as_float(column: str) -> float | None:
            raw = columns.get(column)
            if raw is None:
                return None
            return _to_float(
                raw, column=column, location=f"scan {scan_id}", path=table.path
            )

        acquired_raw = columns.get("acquisition_timestamp")
        acquired_at: datetime | None = None
        if acquired_raw is not None:
            try:
                acquired_at = datetime.fromisoformat(acquired_raw)
            except ValueError:
                raise ParseError(
                    f"{table.path.name} (scan {scan_id}): "
                    f"acquisition_timestamp {acquired_raw!r} is not ISO-8601"
                ) from None

        optical_raw = columns.get("optical_system")
        return _ScanInputs(
            scan_id=scan_id,
            elapsed_seconds=as_float("elapsed_seconds"),
            acquired_at=acquired_at,
            cell=columns.get("cell"),
            channel=columns.get("channel"),
            wavelength_nm=as_float("wavelength_nm"),
            optical_system=(
                _parse_optical(optical_raw) if optical_raw is not None else None
            ),
            rotor_speed_rpm=as_float("rotor_speed_rpm"),
            temperature_c=as_float("temperature_c"),
            source_scan_id=columns.get("source_scan_id"),
        )

    @staticmethod
    def _observations(
        order: list[str],
        radii: dict[str, list[float]],
        signals: dict[str, list[float]],
        signal_unit: Unit,
    ) -> Observations:
        if not order:
            raise ParseError("no scans found in data file")
        first = radii[order[0]]
        shared = all(radii[scan_id] == first for scan_id in order)
        if shared:
            return Observations.from_shared_axis(
                radius=first,
                signal=[signals[scan_id] for scan_id in order],
                scan_ids=order,
                signal_unit=signal_unit,
                radius_unit=Unit.CENTIMETRE,
            )
        return Observations.from_per_scan(
            radii=[radii[scan_id] for scan_id in order],
            signals=[signals[scan_id] for scan_id in order],
            scan_ids=order,
            signal_unit=signal_unit,
            radius_unit=Unit.CENTIMETRE,
        )


# --------------------------------------------------------------------------- #
# Wide-format parser
# --------------------------------------------------------------------------- #


@register_parser
class GenericWideParser(Parser):
    """Generic wide-format CSV/TSV: one radius column, one column per scan."""

    format_id = "generic-wide"
    name = "Generic wide-format delimited"
    suffixes = (".csv", ".tsv")
    layouts = ("wide",)
    limitations = (
        "scans must share one radius axis; requires a manifest column mapping",
    )
    doc_reference = "docs/formats/generic-delimited.md"

    def detect(self, table: Table, manifest: GenericManifest | None) -> DetectionResult:
        if manifest is None or manifest.columns is None:
            return DetectionResult(
                parser_id=self.format_id,
                confidence=0.0,
                evidence=("wide format requires a manifest column mapping",),
            )
        columns = manifest.columns
        wanted = (columns.radius, *(s.column for s in columns.scans))
        present = table.has_columns(wanted)
        if not present:
            confidence = 0.6 if manifest.format == self.format_id else 0.0
            evidence = ("declared wide columns not all present in header",)
        else:
            confidence = 0.95 if manifest.format == self.format_id else 0.8
            evidence = (f"radius column {columns.radius!r} and scan columns found",)
        return DetectionResult(
            parser_id=self.format_id, confidence=confidence, evidence=evidence
        )

    def parse(
        self,
        table: Table,
        source: ResolvedSource,
        manifest: GenericManifest | None,
    ) -> ParseResult:
        manifest = _require_manifest(manifest, table.path)
        if manifest.columns is None:
            raise ManifestError(
                f"{table.path.name}: wide format requires a 'columns' mapping "
                "in the manifest (radius column and scan columns)"
            )
        columns = manifest.columns
        radius_i = table.column_index(columns.radius)
        if radius_i < 0:
            raise ParseError(
                f"{table.path.name}: radius column {columns.radius!r} not in header"
            )
        scan_indices: list[tuple[WideScanColumn, int]] = []
        for scan_col in columns.scans:
            col_i = table.column_index(scan_col.column)
            if col_i < 0:
                raise ParseError(
                    f"{table.path.name}: scan column {scan_col.column!r} not in header"
                )
            scan_indices.append((scan_col, col_i))

        radius: list[float] = []
        seen_radii: set[float] = set()
        signals: list[list[float]] = [[] for _ in scan_indices]
        for row_number, row in enumerate(table.rows, start=2):
            if len(row) != len(table.header):
                raise ParseError(
                    f"{table.path.name} (row {row_number}): expected "
                    f"{len(table.header)} fields, got {len(row)}"
                )
            location = f"row {row_number}"
            r = _to_float(
                row[radius_i],
                column=columns.radius,
                location=location,
                path=table.path,
            )
            if r in seen_radii:
                raise DataConflictError(
                    f"{table.path.name} (row {row_number}): duplicate radius {r}"
                )
            seen_radii.add(r)
            radius.append(r)
            for position, (scan_col, col_i) in enumerate(scan_indices):
                signals[position].append(
                    _to_float(
                        row[col_i],
                        column=scan_col.column,
                        location=location,
                        path=table.path,
                    )
                )

        signal_unit = _resolve_signal_unit(
            set(), manifest.defaults.signal_unit, table.path
        )
        scan_ids = [scan_col.scan_id for scan_col, _ in scan_indices]
        scans = tuple(
            _build_scan_metadata(
                _wide_scan_inputs(scan_col),
                index,
                manifest.defaults,
                table.path.name,
            )
            for index, (scan_col, _) in enumerate(scan_indices)
        )
        observations = Observations.from_shared_axis(
            radius=radius,
            signal=signals,
            scan_ids=scan_ids,
            signal_unit=signal_unit,
            radius_unit=Unit.CENTIMETRE,
        )
        experiment = AUCExperiment(
            metadata=_experiment_metadata(manifest),
            scans=scans,
            observations=observations,
            samples=_samples(manifest),
            instrument=_instrument_metadata(manifest),
        )
        assumptions = (
            f"radius column {columns.radius!r} interpreted as centimetres",
            f"signal unit resolved to {signal_unit.value!r}",
            "radius axis: shared",
        )
        return ParseResult(experiment=experiment, assumptions=assumptions)


def _wide_scan_inputs(scan_col: WideScanColumn) -> _ScanInputs:
    return _ScanInputs(
        scan_id=scan_col.scan_id,
        elapsed_seconds=scan_col.elapsed_seconds,
        cell=scan_col.cell,
        channel=scan_col.channel,
        wavelength_nm=scan_col.wavelength_nm,
        optical_system=scan_col.optical_system,
        rotor_speed_rpm=scan_col.rotor_speed_rpm,
        temperature_c=scan_col.temperature_c,
        source_scan_id=scan_col.source_scan_id,
    )
