"""Deterministic generation of illustrative synthetic AUC-like datasets.

For examples, integration tests, demonstrations and performance work.

**What this is not.** Generated curves are closed-form shapes chosen for being
smooth, cheap and reproducible. They are not Lamm-equation solutions, not
simulations of sedimentation, and carry no physical parameters. A generated
experiment is structurally valid test data; it is never scientifically valid
data, and nothing physical may be inferred from it.

    from openauc.synthetic import SyntheticExperimentConfig, generate_experiment

    experiment = generate_experiment(
        SyntheticExperimentConfig(scenario="moving-boundary", n_scans=20, seed=42)
    )

See ``docs/concepts/synthetic-data.md``.
"""

from __future__ import annotations

from openauc.synthetic.config import (
    MetadataCompleteness,
    Scenario,
    SyntheticExperimentConfig,
)
from openauc.synthetic.generators import SYNTHETIC_NOTE, generate_experiment
from openauc.synthetic.writers import (
    SyntheticWriteError,
    write_aucx,
    write_generic_long,
    write_generic_wide,
)

__all__ = [
    "SYNTHETIC_NOTE",
    "MetadataCompleteness",
    "Scenario",
    "SyntheticExperimentConfig",
    "SyntheticWriteError",
    "generate_experiment",
    "write_aucx",
    "write_generic_long",
    "write_generic_wide",
]
