"""Structured, factual summaries of an experiment's structure.

:class:`ExperimentSummary` is a frozen pydantic model holding counts, ranges and
metadata-presence facts. Every collection field is a tuple or a nested frozen
model, so a summary cannot be mutated after construction.

Nothing here is calculated scientifically: there are no sedimentation or
diffusion coefficients, no molecular weights, no quality scores and no inferred
values. A field is either read from the model or counted.

:meth:`ExperimentSummary.to_text` renders the human-readable form returned by
``AUCExperiment.summary()``.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, ConfigDict

from openauc.models.enums import (
    ExperimentType,
    OpticalSystem,
    RadiusAxisMode,
    Unit,
    ValueStatus,
)

if TYPE_CHECKING:
    from openauc.models.experiment import AUCExperiment
    from openauc.models.metadata import Quantity
    from openauc.models.sample import SampleMetadata
    from openauc.models.scan import ScanMetadata

__all__ = [
    "ExperimentSummary",
    "MetadataPresence",
    "ValidationCounts",
    "ValueRange",
    "summarise_experiment",
]

_SCAN_PRESENCE_QUANTITIES: tuple[
    tuple[str, Callable[[ScanMetadata], Quantity | None]], ...
] = (
    ("elapsed_time", lambda scan: scan.elapsed_time),
    ("wavelength", lambda scan: scan.wavelength),
    ("rotor_speed", lambda scan: scan.rotor_speed),
    ("temperature", lambda scan: scan.temperature),
)

_SAMPLE_PRESENCE_QUANTITIES: tuple[
    tuple[str, Callable[[SampleMetadata], Quantity | None]], ...
] = (
    ("concentration", lambda sample: sample.concentration),
    ("density", lambda sample: sample.density),
    ("viscosity", lambda sample: sample.viscosity),
    ("partial_specific_volume", lambda sample: sample.partial_specific_volume),
)


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class ValueRange(_Frozen):
    """The observed span of one quantity, with presence counts.

    ``minimum`` and ``maximum`` are ``None`` when nothing was present. The unit
    is the declared unit, retained verbatim; nothing is converted.
    """

    minimum: float | None = None
    maximum: float | None = None
    unit: Unit = Unit.UNKNOWN
    n_present: int = 0
    n_absent: int = 0

    @property
    def is_observed(self) -> bool:
        return self.minimum is not None and self.maximum is not None

    def render(self) -> str:
        """``'6 to 7.2 cm (observed)'``, or ``'unknown'`` when nothing present."""
        if self.minimum is None or self.maximum is None:
            return "unknown"
        return f"{self.minimum:g} to {self.maximum:g} {self.unit.value} (observed)"


class MetadataPresence(_Frozen):
    """Presence counts for one metadata field across scans or samples.

    ``absent`` counts records where the field itself is structurally absent
    (``None``); the remaining counters record the explicit
    :class:`~openauc.models.enums.ValueStatus` of the values that are present as
    quantities. The two levels of absence are never collapsed.
    """

    component: str
    field: str
    total: int = 0
    present: int = 0
    missing: int = 0
    unknown: int = 0
    not_applicable: int = 0
    absent: int = 0

    @property
    def unrecorded(self) -> int:
        """Records carrying no usable value, however that absence is expressed."""
        return self.total - self.present


class ValidationCounts(_Frozen):
    """Finding counts from the full (all-tier) validation report."""

    error: int = 0
    warning: int = 0
    info: int = 0

    @property
    def total(self) -> int:
        return self.error + self.warning + self.info


class ExperimentSummary(_Frozen):
    """A factual, structural description of an experiment.

    The summary describes structure and metadata only. It makes no claim about
    scientific validity or suitability for sedimentation analysis.
    """

    experiment_id: str
    name: str | None = None
    experiment_type: ExperimentType = ExperimentType.UNKNOWN
    acquired_at: datetime | None = None
    operator: str | None = None

    n_scans: int = 0
    n_samples: int = 0

    radius_axis_mode: RadiusAxisMode = RadiusAxisMode.SHARED
    radius_unit: Unit = Unit.CENTIMETRE
    signal_unit: Unit = Unit.UNKNOWN
    signal_unit_declared: bool = False

    points_per_scan: tuple[int, ...] = ()
    total_valid_observations: int = 0

    optical_systems: tuple[OpticalSystem, ...] = ()
    wavelengths_nm: tuple[float, ...] = ()
    scans_without_wavelength: int = 0
    cells: tuple[str, ...] = ()
    scans_without_cell: int = 0
    channels: tuple[str, ...] = ()
    scans_without_channel: int = 0

    radius: ValueRange = ValueRange()
    elapsed_time: ValueRange = ValueRange()
    rotor_speed: ValueRange = ValueRange()
    temperature: ValueRange = ValueRange()

    metadata_presence: tuple[MetadataPresence, ...] = ()

    provenance_available: bool = False
    parser_name: str | None = None
    checksum_available: bool = False

    validation: ValidationCounts = ValidationCounts()

    def to_dict(self) -> dict[str, Any]:
        """Serialise to plain JSON-friendly Python types."""
        return self.model_dump(mode="json")

    def to_text(self) -> str:
        """Render the human-readable summary.

        Describes structure and metadata only; it makes no claim about
        scientific validity or suitability for sedimentation analysis.
        """
        name_suffix = f" - {self.name}" if self.name else ""
        acquired = self.acquired_at.isoformat() if self.acquired_at else "unknown"
        lines = [
            f"Experiment: {self.experiment_id}{name_suffix}",
            f"  Type: {self.experiment_type.value}",
            f"  Acquired: {acquired}",
            f"  Operator: {self.operator or 'unknown'}",
            f"  Scans: {self.n_scans}",
            f"  Samples: {self.n_samples}",
            "  Optical systems: "
            + ", ".join(system.value for system in self.optical_systems),
            f"  Radius axis: {self.radius_axis_mode.value}",
            f"  Radius unit: {self.radius_unit.value}",
            f"  Signal unit: {self.signal_unit.value}",
        ]

        if self.radius.is_observed:
            lines.append(f"  Radius range: {self.radius.render()}")
        else:
            lines.append("  Radius range: n/a (no observations)")

        if self.elapsed_time.is_observed:
            lines.append(f"  Elapsed time: {self.elapsed_time.render()}")
        else:
            lines.append("  Elapsed time: unknown")

        lines.append(f"  Points per scan: {self._render_points_per_scan()}")
        lines.append(f"  Total observations: {self.total_valid_observations}")
        lines.append(f"  Wavelengths: {self._render_wavelengths()}")
        lines.append("  Cells: " + _render_labels(self.cells, self.scans_without_cell))
        lines.append(
            "  Channels: " + _render_labels(self.channels, self.scans_without_channel)
        )
        lines.append(f"  Rotor speed: {self.rotor_speed.render()}")
        lines.append(f"  Temperature: {self.temperature.render()}")

        if self.provenance_available:
            parser = self.parser_name or "unspecified parser"
            lines.append(f"  Provenance: recorded ({parser})")
        else:
            lines.append("  Provenance: not recorded")

        if self.checksum_available:
            lines.append("  Source checksum: recorded")
        else:
            lines.append("  Source checksum: not recorded (deferred to the AUCX phase)")

        lines.append(
            f"  Validation: {self.validation.error} error(s), "
            f"{self.validation.warning} warning(s), {self.validation.info} info"
        )
        lines.append(
            "  Note: structural summary only; no assessment of scientific "
            "validity or suitability for analysis."
        )
        return "\n".join(lines)

    def _render_points_per_scan(self) -> str:
        if not self.points_per_scan:
            return "n/a"
        low, high = min(self.points_per_scan), max(self.points_per_scan)
        if low == high:
            return f"{low} (uniform)"
        return f"{low} to {high} (varies)"

    def _render_wavelengths(self) -> str:
        rendered = ", ".join(f"{value:g}" for value in self.wavelengths_nm)
        if not rendered:
            return "unknown"
        if self.scans_without_wavelength:
            return (
                f"{rendered} {Unit.NANOMETRE.value} "
                f"({self.scans_without_wavelength} scan(s) unknown)"
            )
        return f"{rendered} {Unit.NANOMETRE.value}"


def _render_labels(labels: tuple[str, ...], unknown: int) -> str:
    if not labels:
        return "none recorded"
    rendered = ", ".join(labels)
    if unknown:
        return f"{rendered} ({unknown} scan(s) unknown)"
    return rendered


def _quantity_range(
    quantities: list[Quantity | None], *, default_unit: Unit
) -> ValueRange:
    """Span and presence counts over ``quantities``. Nothing is converted."""
    present = [
        quantity
        for quantity in quantities
        if quantity is not None
        and quantity.status is ValueStatus.PRESENT
        and quantity.value is not None
    ]
    values = [quantity.value for quantity in present if quantity.value is not None]
    unit = present[0].unit if present else default_unit
    if not values:
        return ValueRange(
            minimum=None,
            maximum=None,
            unit=unit,
            n_present=0,
            n_absent=len(quantities),
        )
    return ValueRange(
        minimum=min(values),
        maximum=max(values),
        unit=unit,
        n_present=len(values),
        n_absent=len(quantities) - len(values),
    )


def _presence(
    component: str, field: str, quantities: list[Quantity | None]
) -> MetadataPresence:
    counts = dict.fromkeys(ValueStatus, 0)
    absent = 0
    for quantity in quantities:
        if quantity is None:
            absent += 1
        else:
            counts[quantity.status] += 1
    return MetadataPresence(
        component=component,
        field=field,
        total=len(quantities),
        present=counts[ValueStatus.PRESENT],
        missing=counts[ValueStatus.MISSING],
        unknown=counts[ValueStatus.UNKNOWN],
        not_applicable=counts[ValueStatus.NOT_APPLICABLE],
        absent=absent,
    )


def _string_presence(
    component: str, field: str, values: list[str | None]
) -> MetadataPresence:
    present = sum(1 for value in values if value is not None)
    return MetadataPresence(
        component=component,
        field=field,
        total=len(values),
        present=present,
        absent=len(values) - present,
    )


def _distinct_wavelengths(scans: tuple[ScanMetadata, ...]) -> tuple[float, ...]:
    values = {
        scan.wavelength.value
        for scan in scans
        if scan.wavelength is not None
        and scan.wavelength.status is ValueStatus.PRESENT
        and scan.wavelength.value is not None
    }
    return tuple(sorted(values))


def summarise_experiment(experiment: AUCExperiment) -> ExperimentSummary:
    """Build the structured summary for ``experiment``."""
    observations = experiment.observations
    scans = experiment.scans
    report = experiment.validate()
    errors, warnings, infos = report.counts()

    radius_range = observations.radius_range()
    points = observations.points_per_scan()

    presence: list[MetadataPresence] = [
        _presence("scan", field, [accessor(scan) for scan in scans])
        for field, accessor in _SCAN_PRESENCE_QUANTITIES
    ]
    presence.append(_string_presence("scan", "cell", [scan.cell for scan in scans]))
    presence.append(
        _string_presence("scan", "channel", [scan.channel for scan in scans])
    )
    presence.extend(
        _presence("sample", field, [accessor(sample) for sample in experiment.samples])
        for field, accessor in _SAMPLE_PRESENCE_QUANTITIES
    )
    presence.append(
        _string_presence(
            "sample",
            "buffer_description",
            [sample.buffer_description for sample in experiment.samples],
        )
    )

    provenance = experiment.provenance
    return ExperimentSummary(
        experiment_id=experiment.metadata.experiment_id,
        name=experiment.metadata.name,
        experiment_type=experiment.metadata.experiment_type,
        acquired_at=experiment.metadata.acquired_at,
        operator=experiment.metadata.operator,
        n_scans=len(scans),
        n_samples=len(experiment.samples),
        radius_axis_mode=observations.mode,
        radius_unit=observations.radius_unit,
        signal_unit=observations.signal_unit,
        signal_unit_declared=observations.signal_unit is not Unit.UNKNOWN,
        points_per_scan=points,
        total_valid_observations=sum(points),
        optical_systems=experiment.optical_systems(),
        wavelengths_nm=_distinct_wavelengths(scans),
        scans_without_wavelength=sum(
            1
            for scan in scans
            if scan.wavelength is None
            or scan.wavelength.status is not ValueStatus.PRESENT
        ),
        cells=tuple(sorted({scan.cell for scan in scans if scan.cell is not None})),
        scans_without_cell=sum(1 for scan in scans if scan.cell is None),
        channels=tuple(
            sorted({scan.channel for scan in scans if scan.channel is not None})
        ),
        scans_without_channel=sum(1 for scan in scans if scan.channel is None),
        radius=ValueRange(
            minimum=radius_range[0] if radius_range else None,
            maximum=radius_range[1] if radius_range else None,
            unit=observations.radius_unit,
            n_present=sum(points),
            n_absent=0,
        ),
        elapsed_time=_quantity_range(
            [scan.elapsed_time for scan in scans], default_unit=Unit.SECOND
        ),
        rotor_speed=_quantity_range(
            [scan.rotor_speed for scan in scans], default_unit=Unit.RPM
        ),
        temperature=_quantity_range(
            [scan.temperature for scan in scans], default_unit=Unit.DEGREE_CELSIUS
        ),
        metadata_presence=tuple(presence),
        provenance_available=provenance is not None,
        parser_name=provenance.parser_name if provenance is not None else None,
        checksum_available=provenance is not None and provenance.sha256 is not None,
        validation=ValidationCounts(error=errors, warning=warnings, info=infos),
    )
