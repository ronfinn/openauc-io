"""Example 7 — generate an illustrative synthetic experiment.

The generated data is invented. It is NOT a physically validated simulation of
an analytical ultracentrifugation experiment, not a Lamm-equation solution, and
carries no physical parameters. Nothing scientific may be inferred from it.

Run: ``python examples/generate_synthetic_experiment.py``
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import openauc
from openauc.synthetic import (
    Scenario,
    SyntheticExperimentConfig,
    generate_experiment,
    write_aucx,
    write_generic_long,
)


def main() -> None:
    config = SyntheticExperimentConfig(
        scenario=Scenario.MOVING_BOUNDARY,
        experiment_id="synthetic-demo-001",
        n_scans=8,
        n_points=120,
        seed=42,
        noise_level=0.002,
    )
    experiment = generate_experiment(config)

    print(f"generated {experiment.metadata.experiment_id!r}")
    print(f"  scans:        {len(experiment.scans)}")
    print(f"  observations: {sum(experiment.observations.points_per_scan())}")
    print(f"  structurally valid: {experiment.validate_structure().is_valid}")
    print(f"  note: {experiment.metadata.notes}")

    # The same config and seed always reproduce the same data.
    again = generate_experiment(config)
    print(f"  reproducible: {again.to_dict() == experiment.to_dict()}")

    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)

        long_dir = write_generic_long(experiment, root / "long")
        reloaded = openauc.load(long_dir)
        print(f"  generic-long reload: {len(reloaded.scans)} scans")

        archive = write_aucx(experiment, root / "demo.aucx")
        restored = openauc.load(archive)
        # AUCX round-trips the model exactly; delimited output cannot carry the
        # unknown/missing distinction.
        print(
            f"  aucx round trip identical: {restored.to_dict() == experiment.to_dict()}"
        )

    print("\nEvery scenario, for reference:")
    for scenario in Scenario:
        small = SyntheticExperimentConfig(scenario=scenario, n_scans=4, n_points=10)
        built = generate_experiment(small)
        report = built.validate_structure()
        codes = sorted(set(report.codes())) or ["(none)"]
        print(f"  {scenario.value:20s} valid={report.is_valid!s:5s} findings={codes}")


if __name__ == "__main__":
    main()
