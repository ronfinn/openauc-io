"""The canonical in-memory AUC experiment (top-level container).

``AUCExperiment`` is a frozen dataclass composing the pydantic metadata models
with the xarray-backed :class:`~openauc.models.observations.Observations`. It is
a data-representation layer: it preserves what was supplied and never decides
whether a run is scientifically valid or suitable for analysis.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from openauc.models.enums import OpticalSystem, ValueStatus
from openauc.models.instrument import InstrumentMetadata
from openauc.models.metadata import ExperimentMetadata
from openauc.models.observations import Observations
from openauc.models.provenance import ImportProvenance
from openauc.models.sample import SampleMetadata
from openauc.models.scan import ScanMetadata
from openauc.models.validation import (
    ValidationReport,
    validate_experiment_structure,
)

__all__ = ["AUCExperiment"]


@dataclass(frozen=True)
class AUCExperiment:
    """A complete canonical AUC experiment.

    Args:
        metadata: Experiment identity (area A).
        scans: Per-scan metadata, one record per scan.
        observations: The radial signal data (shared or per-scan axes).
        samples: Optional sample/buffer metadata.
        instrument: Optional instrument and run metadata.
        provenance: Optional import-provenance record.

    Construction does not enforce cross-object consistency (e.g. that scan
    identifiers match the observations); use :meth:`validate_structure` to check
    that and obtain a report. Field-level invariants are enforced by the
    component models at their own construction.
    """

    metadata: ExperimentMetadata
    scans: tuple[ScanMetadata, ...]
    observations: Observations
    samples: tuple[SampleMetadata, ...] = ()
    instrument: InstrumentMetadata | None = None
    provenance: ImportProvenance | None = field(default=None)

    def __post_init__(self) -> None:
        # Accept any sequence for the collection fields; store as tuples.
        object.__setattr__(self, "scans", tuple(self.scans))
        object.__setattr__(self, "samples", tuple(self.samples))

    # -- behaviour -----------------------------------------------------------

    def validate_structure(self) -> ValidationReport:
        """Run structural validation and return a report (does not raise)."""
        return validate_experiment_structure(self)

    def optical_systems(self) -> tuple[OpticalSystem, ...]:
        """Distinct optical systems named across scans (and the instrument)."""
        systems = {scan.optical_system for scan in self.scans}
        if self.instrument is not None:
            systems.add(self.instrument.optical_system)
        return tuple(sorted(systems, key=lambda s: s.value))

    def summary(self) -> str:
        """A factual, human-readable summary of the experiment's structure.

        The summary describes structure and metadata only. It makes no claim
        about scientific validity or suitability for sedimentation analysis.
        """
        meta = self.metadata
        name_suffix = f" - {meta.name}" if meta.name else ""
        acquired = meta.acquired_at.isoformat() if meta.acquired_at else "unknown"
        lines = [
            f"Experiment: {meta.experiment_id}{name_suffix}",
            f"  Type: {meta.experiment_type.value}",
            f"  Acquired: {acquired}",
            f"  Operator: {meta.operator or 'unknown'}",
            f"  Scans: {len(self.scans)}",
            f"  Samples: {len(self.samples)}",
            "  Optical systems: " + ", ".join(s.value for s in self.optical_systems()),
            f"  Radius axis: {self.observations.mode.value}",
            f"  Radius unit: {self.observations.radius_unit.value}",
            f"  Signal unit: {self.observations.signal_unit.value}",
        ]

        radius_range = self.observations.radius_range()
        if radius_range is not None:
            low, high = radius_range
            lines.append(
                f"  Radius range: {low:g} to {high:g} "
                f"{self.observations.radius_unit.value} (observed)"
            )
        else:
            lines.append("  Radius range: n/a (no observations)")

        elapsed = [
            scan.elapsed_time.value
            for scan in self.scans
            if scan.elapsed_time.status is ValueStatus.PRESENT
            and scan.elapsed_time.value is not None
        ]
        if elapsed:
            lines.append(
                f"  Elapsed time: {min(elapsed):g} to {max(elapsed):g} s (observed)"
            )
        else:
            lines.append("  Elapsed time: unknown")

        if self.provenance is not None:
            parser = self.provenance.parser_name or "unspecified parser"
            lines.append(f"  Provenance: recorded ({parser})")
        else:
            lines.append("  Provenance: not recorded")

        lines.append(
            "  Note: structural summary only; no assessment of scientific "
            "validity or suitability for analysis."
        )
        return "\n".join(lines)

    # -- serialisation -------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        """Serialise the experiment to plain JSON-friendly Python types."""
        return {
            "metadata": self.metadata.model_dump(mode="json"),
            "instrument": (
                self.instrument.model_dump(mode="json")
                if self.instrument is not None
                else None
            ),
            "samples": [s.model_dump(mode="json") for s in self.samples],
            "scans": [s.model_dump(mode="json") for s in self.scans],
            "observations": self.observations.to_dict(),
            "provenance": (
                self.provenance.model_dump(mode="json")
                if self.provenance is not None
                else None
            ),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AUCExperiment:
        """Reconstruct an experiment from :meth:`to_dict` output."""
        instrument = data.get("instrument")
        provenance = data.get("provenance")
        return cls(
            metadata=ExperimentMetadata.model_validate(data["metadata"]),
            scans=tuple(ScanMetadata.model_validate(item) for item in data["scans"]),
            observations=Observations.from_dict(data["observations"]),
            samples=tuple(
                SampleMetadata.model_validate(item) for item in data.get("samples", [])
            ),
            instrument=(
                InstrumentMetadata.model_validate(instrument)
                if instrument is not None
                else None
            ),
            provenance=(
                ImportProvenance.model_validate(provenance)
                if provenance is not None
                else None
            ),
        )
