"""The canonical in-memory AUC experiment (top-level container).

``AUCExperiment`` is a frozen dataclass composing the pydantic metadata models
with the xarray-backed :class:`~openauc.models.observations.Observations`. It is
a data-representation layer: it preserves what was supplied and never decides
whether a run is scientifically valid or suitable for analysis.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from openauc.models.enums import OpticalSystem
from openauc.models.instrument import InstrumentMetadata
from openauc.models.metadata import ExperimentMetadata
from openauc.models.observations import Observations
from openauc.models.provenance import ImportProvenance
from openauc.models.readiness import (
    ReadinessAssessment,
    assess_experiment_readiness,
)
from openauc.models.sample import SampleMetadata
from openauc.models.scan import ScanMetadata
from openauc.models.summary import ExperimentSummary, summarise_experiment
from openauc.models.validation import (
    ValidationReport,
    validate_experiment,
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
        """Run archival and structural validation (does not raise).

        Returns the ``ARCHIVAL`` and ``STRUCTURAL`` findings of ``ERROR`` or
        ``WARNING`` severity. Use :meth:`validate` for the full report across
        all four tiers, including informational findings.
        """
        return validate_experiment_structure(self)

    def validate(self) -> ValidationReport:
        """Run every check across all four tiers (does not raise).

        The report covers archival, structural and both readiness tiers. It
        makes no claim about scientific validity: see :meth:`assess_readiness`.
        """
        return validate_experiment(self)

    def assess_readiness(self) -> ReadinessAssessment:
        """Report whether the metadata a future workflow needs is present.

        This assesses metadata presence only. Scientific suitability is always
        reported as ``NOT_ASSESSED``.
        """
        return assess_experiment_readiness(self)

    def optical_systems(self) -> tuple[OpticalSystem, ...]:
        """Distinct optical systems named across scans (and the instrument)."""
        systems = {scan.optical_system for scan in self.scans}
        if self.instrument is not None:
            systems.add(self.instrument.optical_system)
        return tuple(sorted(systems, key=lambda s: s.value))

    def summary_data(self) -> ExperimentSummary:
        """A structured, factual summary of the experiment's structure.

        Holds counts, ranges and metadata-presence facts only — no scientific
        calculation, quality score or inferred value.
        """
        return summarise_experiment(self)

    def summary(self) -> str:
        """A factual, human-readable summary of the experiment's structure.

        The summary describes structure and metadata only. It makes no claim
        about scientific validity or suitability for sedimentation analysis.
        Equivalent to ``self.summary_data().to_text()``.
        """
        return self.summary_data().to_text()

    # -- archival ------------------------------------------------------------

    def export(
        self,
        path: str | Path,
        *,
        overwrite: bool = False,
        exported_at: datetime | None = None,
    ) -> Path:
        """Write this experiment to an AUCX archive and return the path.

        The archive is written atomically and verified before it replaces
        anything. See :func:`openauc.export_aucx`.
        """
        # Imported here so the model layer does not depend on the format layer
        # at import time.
        from openauc.formats.aucx import export_aucx

        return export_aucx(self, path, overwrite=overwrite, exported_at=exported_at)

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
