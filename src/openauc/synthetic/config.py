"""Configuration for the synthetic-data generator.

Every generated dataset is **illustrative synthetic data**. The curves are
closed-form shapes chosen because they are cheap, smooth and reproducible — they
are *not* solutions of the Lamm equation, not simulations of sedimentation, and
carry no physical parameters. See ``docs/concepts/synthetic-data.md``.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator

from openauc.models.enums import (
    ExperimentType,
    OpticalSystem,
    RadiusAxisMode,
    Unit,
)

__all__ = [
    "MetadataCompleteness",
    "Scenario",
    "SyntheticExperimentConfig",
]


class Scenario(StrEnum):
    """The shape of dataset to generate.

    Names describe the *structure* being exercised, never a physical regime.
    """

    #: A smooth step whose midpoint advances outward between scans.
    MOVING_BOUNDARY = "moving-boundary"
    #: A stationary curved profile, repeated across scans.
    EQUILIBRIUM_PROFILE = "equilibrium-profile"
    #: The same profile in every scan; useful for archive and plotting tests.
    STATIC_PROFILE = "static-profile"
    #: Each scan carries its own radius vector, of differing length.
    PER_SCAN_RADIUS = "per-scan-radius"
    #: Valid, but carrying explicit missing/unknown/not-applicable metadata.
    SPARSE_METADATA = "sparse-metadata"
    #: More than one declared optical system across scans.
    MIXED_OPTICS = "mixed-optics"
    #: Some scans carry no observations at all.
    EMPTY_SCANS = "empty-scans"
    #: Deliberate cross-object inconsistency, for exercising ValidationReport.
    INVALID_STRUCTURE = "invalid-structure"


class MetadataCompleteness(StrEnum):
    """How much optional metadata to attach."""

    #: Only what the model requires.
    MINIMAL = "minimal"
    #: The fields a routine import usually carries.
    TYPICAL = "typical"
    #: Every optional field the model can hold.
    COMPLETE = "complete"


class SyntheticExperimentConfig(BaseModel):
    """A reproducible description of a synthetic dataset.

    The same configuration and seed always produce the same experiment. Noise,
    when enabled, is drawn from a generator seeded only by :attr:`seed`; NumPy's
    global random state is never touched.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    scenario: Scenario = Scenario.MOVING_BOUNDARY
    experiment_id: str = "synthetic-001"
    name: str | None = "Synthetic illustrative dataset"

    n_scans: int = Field(default=10, ge=1, le=10_000)
    n_points: int = Field(default=100, ge=1, le=1_000_000)

    radius_min: float = Field(default=5.9, gt=0.0)
    radius_max: float = Field(default=7.2, gt=0.0)

    elapsed_seconds_step: float = Field(default=600.0, ge=0.0)
    signal_scale: float = Field(default=1.0, gt=0.0)
    noise_level: float = Field(default=0.0, ge=0.0)
    seed: int = Field(default=0, ge=0)

    radius_axis_mode: RadiusAxisMode = RadiusAxisMode.SHARED
    optical_system: OpticalSystem = OpticalSystem.ABSORBANCE
    signal_unit: Unit = Unit.ABSORBANCE_UNIT
    experiment_type: ExperimentType = ExperimentType.SEDIMENTATION_VELOCITY
    metadata_completeness: MetadataCompleteness = MetadataCompleteness.TYPICAL

    @model_validator(mode="after")
    def _check_radius_domain(self) -> SyntheticExperimentConfig:
        if self.radius_max <= self.radius_min:
            raise ValueError(
                f"radius_max ({self.radius_max}) must be greater than radius_min "
                f"({self.radius_min})"
            )
        return self

    @model_validator(mode="after")
    def _check_scenario_requirements(self) -> SyntheticExperimentConfig:
        if self.scenario is Scenario.INVALID_STRUCTURE and self.n_scans < 2:
            raise ValueError(
                "the 'invalid-structure' scenario needs n_scans >= 2 to produce a "
                "meaningful cross-object inconsistency"
            )
        if self.scenario is Scenario.MIXED_OPTICS and self.n_scans < 2:
            raise ValueError(
                "the 'mixed-optics' scenario needs n_scans >= 2 to declare more "
                "than one optical system"
            )
        if self.scenario is Scenario.EMPTY_SCANS and self.n_scans < 2:
            raise ValueError(
                "the 'empty-scans' scenario needs n_scans >= 2 so that at least "
                "one scan still carries observations"
            )
        return self

    @property
    def effective_radius_axis_mode(self) -> RadiusAxisMode:
        """The axis mode actually used, after scenario requirements.

        Two scenarios require per-scan axes to express what they describe:
        ``per-scan-radius`` by definition, and ``empty-scans`` because the
        canonical model can only represent an empty scan when each scan owns its
        own axis.
        """
        if self.scenario in (Scenario.PER_SCAN_RADIUS, Scenario.EMPTY_SCANS):
            return RadiusAxisMode.PER_SCAN
        return self.radius_axis_mode

    @property
    def effective_signal_unit(self) -> Unit:
        """The signal unit actually used.

        ``mixed-optics`` declares several optical systems against one shared
        signal unit, so it uses ``UNKNOWN``: any concrete unit would contradict
        at least one of the declared systems and produce a structural error,
        which is not what that scenario is for.
        """
        if self.scenario is Scenario.MIXED_OPTICS:
            return Unit.UNKNOWN
        return self.signal_unit
