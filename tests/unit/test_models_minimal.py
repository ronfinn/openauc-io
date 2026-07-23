"""Minimal valid experiment, summary output, and structural validation (1, 15, 16)."""

from __future__ import annotations

from openauc.models import (
    AUCExperiment,
    ExperimentMetadata,
    Observations,
    OpticalSystem,
    Quantity,
    ScanMetadata,
    Unit,
)


def _minimal_experiment() -> AUCExperiment:
    metadata = ExperimentMetadata(experiment_id="exp-min")
    scan = ScanMetadata(
        scan_id="scan-1",
        index=0,
        elapsed_time=Quantity.of(0.0, Unit.SECOND),
        optical_system=OpticalSystem.ABSORBANCE,
    )
    observations = Observations.from_shared_axis(
        radius=[6.0, 6.1, 6.2],
        signal=[[0.10, 0.20, 0.30]],
        scan_ids=["scan-1"],
        signal_unit=Unit.ABSORBANCE_UNIT,
    )
    return AUCExperiment(metadata=metadata, scans=(scan,), observations=observations)


def test_minimal_valid_experiment_constructs() -> None:
    experiment = _minimal_experiment()
    assert experiment.metadata.experiment_id == "exp-min"
    assert experiment.observations.n_scans == 1
    assert experiment.scans[0].scan_id == "scan-1"


def test_minimal_experiment_is_structurally_valid() -> None:
    report = _minimal_experiment().validate_structure()
    assert report.is_valid
    assert report.errors == ()


def test_summary_is_factual_and_makes_no_scientific_claim() -> None:
    summary = _minimal_experiment().summary()
    assert "Experiment: exp-min" in summary
    assert "Radius axis: shared" in summary
    assert "Scans: 1" in summary
    # The summary must not assert scientific validity or analysis suitability.
    lowered = summary.lower()
    assert "no assessment of scientific validity" in lowered
    assert "suitable for analysis" not in lowered.replace(
        "suitability for analysis", ""
    )


def test_collections_are_stored_as_tuples() -> None:
    # A list (not a tuple) is accepted and coerced to a tuple by __post_init__.
    experiment = AUCExperiment(
        metadata=ExperimentMetadata(experiment_id="exp"),
        scans=[  # type: ignore[arg-type]
            ScanMetadata(
                scan_id="s", index=0, elapsed_time=Quantity.of(0.0, Unit.SECOND)
            )
        ],
        observations=Observations.from_shared_axis(
            radius=[6.0], signal=[[0.0]], scan_ids=["s"]
        ),
    )
    assert isinstance(experiment.scans, tuple)
    assert isinstance(experiment.samples, tuple)
