"""Synthetic generator: determinism, scenarios, writers and honesty of claims."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
from pydantic import ValidationError

import openauc
from openauc.models import (
    ExperimentType,
    OpticalSystem,
    RadiusAxisMode,
    Unit,
    ValueStatus,
)
from openauc.synthetic import (
    SYNTHETIC_NOTE,
    MetadataCompleteness,
    Scenario,
    SyntheticExperimentConfig,
    SyntheticWriteError,
    generate_experiment,
    write_aucx,
    write_generic_long,
    write_generic_wide,
)

SRC = Path(__file__).resolve().parents[2] / "src" / "openauc" / "synthetic"
DOC = Path(__file__).resolve().parents[2] / "docs" / "concepts" / "synthetic-data.md"


def _config(**overrides: object) -> SyntheticExperimentConfig:
    base: dict[str, object] = {"n_scans": 5, "n_points": 20, "seed": 11}
    base.update(overrides)
    return SyntheticExperimentConfig(**base)  # type: ignore[arg-type]


# --------------------------------------------------------------------------- #
# Determinism
# --------------------------------------------------------------------------- #


def test_same_seed_and_config_produce_identical_experiments() -> None:
    config = _config(noise_level=0.05)
    first = generate_experiment(config)
    second = generate_experiment(config)
    assert first.to_dict() == second.to_dict()


def test_different_seeds_differ_when_noise_is_enabled() -> None:
    a = generate_experiment(_config(seed=1, noise_level=0.05))
    b = generate_experiment(_config(seed=2, noise_level=0.05))
    assert a.to_dict() != b.to_dict()
    # Only the numbers differ; the structure is the same.
    assert a.observations.scan_ids == b.observations.scan_ids
    assert a.observations.points_per_scan() == b.observations.points_per_scan()


def test_seeds_are_irrelevant_to_the_data_without_noise() -> None:
    a = generate_experiment(_config(seed=1, noise_level=0.0))
    b = generate_experiment(_config(seed=999, noise_level=0.0))
    assert a.to_dict()["observations"] == b.to_dict()["observations"]
    # Provenance still records the seed honestly, so the full dicts differ.
    assert a.to_dict()["provenance"] != b.to_dict()["provenance"]


def test_global_numpy_random_state_is_never_touched() -> None:
    np.random.seed(1234)
    before = np.random.get_state()

    generate_experiment(_config(noise_level=0.5, n_scans=8))

    after = np.random.get_state()
    assert after[0] == before[0]
    assert np.array_equal(after[1], before[1])
    assert after[2:] == before[2:]

    # And the global stream still yields exactly what it would have.
    np.random.seed(1234)
    expected = np.random.random(4)
    np.random.seed(1234)
    generate_experiment(_config(noise_level=0.5, n_scans=8))
    assert np.array_equal(np.random.random(4), expected)


def test_generated_order_is_preserved_exactly() -> None:
    experiment = generate_experiment(_config(scenario=Scenario.PER_SCAN_RADIUS))
    for scan_id in experiment.observations.scan_ids:
        radius, _ = experiment.observations.scan_vectors(scan_id)
        assert list(radius) == sorted(radius), "generated ascending, never re-sorted"
    ids = experiment.observations.scan_ids
    assert ids == tuple(sorted(ids))


# --------------------------------------------------------------------------- #
# Scenarios
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("scenario", list(Scenario))
def test_every_scenario_generates_a_usable_experiment(scenario: Scenario) -> None:
    experiment = generate_experiment(_config(scenario=scenario))
    assert len(experiment.scans) == 5
    assert experiment.observations.n_scans == 5
    # Every scenario except the deliberately broken one is structurally valid.
    report = experiment.validate_structure()
    if scenario is Scenario.INVALID_STRUCTURE:
        assert not report.is_valid
    else:
        assert report.is_valid, str(report)
    # Readiness works everywhere and never claims scientific suitability.
    assessment = experiment.assess_readiness()
    assert assessment.scientific_suitability.status.value == "not_assessed"


def test_moving_boundary_advances_outward() -> None:
    experiment = generate_experiment(_config(scenario=Scenario.MOVING_BOUNDARY))
    midpoints = []
    for scan_id in experiment.observations.scan_ids:
        radius, signal = experiment.observations.scan_vectors(scan_id)
        midpoints.append(float(radius[int(np.argmin(np.abs(signal - 0.5)))]))
    assert midpoints == sorted(midpoints)
    assert midpoints[0] < midpoints[-1]


def test_equilibrium_and_static_profiles_repeat_across_scans() -> None:
    for scenario in (Scenario.EQUILIBRIUM_PROFILE, Scenario.STATIC_PROFILE):
        experiment = generate_experiment(_config(scenario=scenario, noise_level=0.0))
        vectors = [
            experiment.observations.scan_vectors(s)[1]
            for s in experiment.observations.scan_ids
        ]
        for other in vectors[1:]:
            assert np.array_equal(vectors[0], other)


def test_per_scan_radius_produces_distinct_axes() -> None:
    experiment = generate_experiment(_config(scenario=Scenario.PER_SCAN_RADIUS))
    assert experiment.observations.mode is RadiusAxisMode.PER_SCAN
    axes = {
        tuple(experiment.observations.scan_vectors(s)[0])
        for s in experiment.observations.scan_ids
    }
    assert len(axes) > 1
    assert len(set(experiment.observations.points_per_scan())) > 1


def test_sparse_metadata_keeps_every_absence_kind_distinct() -> None:
    experiment = generate_experiment(
        _config(scenario=Scenario.SPARSE_METADATA, n_scans=6)
    )
    statuses = {scan.elapsed_time.status for scan in experiment.scans}
    assert ValueStatus.PRESENT in statuses
    assert ValueStatus.MISSING in statuses
    assert ValueStatus.UNKNOWN in statuses

    sample = experiment.samples[0]
    assert sample.density is not None
    assert sample.density.status is ValueStatus.UNKNOWN
    assert sample.viscosity is not None
    assert sample.viscosity.status is ValueStatus.MISSING
    assert sample.partial_specific_volume is not None
    assert sample.partial_specific_volume.status is ValueStatus.NOT_APPLICABLE

    presence = {
        (e.component, e.field): e for e in experiment.summary_data().metadata_presence
    }
    elapsed = presence[("scan", "elapsed_time")]
    assert elapsed.missing and elapsed.unknown and elapsed.present


def test_mixed_optics_declares_several_systems_without_a_unit_conflict() -> None:
    experiment = generate_experiment(_config(scenario=Scenario.MIXED_OPTICS, n_scans=6))
    systems = {scan.optical_system for scan in experiment.scans}
    assert len(systems) >= 2
    report = experiment.validate()
    assert "mixed_optical_systems" in report.codes()
    # Deliberately no concrete signal unit, so no defined conflict is created.
    assert experiment.observations.signal_unit is Unit.UNKNOWN
    assert "optical_signal_unit_conflict" not in report.codes()
    assert report.is_valid


def test_empty_scans_are_representable_and_reported() -> None:
    experiment = generate_experiment(_config(scenario=Scenario.EMPTY_SCANS, n_scans=6))
    counts = experiment.observations.points_per_scan()
    assert 0 in counts
    assert any(count > 0 for count in counts)
    assert "empty_scan" in experiment.validate().codes()
    assert experiment.validate_structure().is_valid


def test_invalid_structure_produces_documented_findings_only() -> None:
    experiment = generate_experiment(_config(scenario=Scenario.INVALID_STRUCTURE))
    codes = set(experiment.validate_structure().codes())
    assert codes == {"duplicate_scan_id", "scan_id_mismatch"}
    assert not experiment.validate_structure().is_valid
    # The objects themselves are still legal: nothing bypassed construction.
    assert all(scan.scan_id for scan in experiment.scans)
    assert experiment.observations.n_scans == len(experiment.scans)


@pytest.mark.parametrize("completeness", list(MetadataCompleteness))
def test_metadata_completeness_levels(completeness: MetadataCompleteness) -> None:
    experiment = generate_experiment(_config(metadata_completeness=completeness))
    if completeness is MetadataCompleteness.MINIMAL:
        assert experiment.samples == ()
        assert experiment.instrument is None
        assert experiment.scans[0].wavelength is None
    else:
        assert experiment.samples
        assert experiment.instrument is not None
    if completeness is MetadataCompleteness.COMPLETE:
        assert experiment.metadata.operator is not None
        assert experiment.samples[0].partial_specific_volume is not None


def test_configuration_is_honoured() -> None:
    experiment = generate_experiment(
        _config(
            experiment_id="custom-id",
            n_scans=3,
            n_points=7,
            radius_min=6.0,
            radius_max=6.5,
            elapsed_seconds_step=120.0,
            signal_scale=2.0,
            experiment_type=ExperimentType.SEDIMENTATION_EQUILIBRIUM,
            optical_system=OpticalSystem.INTERFERENCE,
            signal_unit=Unit.FRINGE,
        )
    )
    assert experiment.metadata.experiment_id == "custom-id"
    assert (
        experiment.metadata.experiment_type is ExperimentType.SEDIMENTATION_EQUILIBRIUM
    )
    assert experiment.observations.signal_unit is Unit.FRINGE
    assert experiment.scans[0].optical_system is OpticalSystem.INTERFERENCE
    assert experiment.scans[1].elapsed_time.value == 120.0
    low, high = experiment.observations.radius_range()  # type: ignore[misc]
    assert (low, high) == (6.0, 6.5)
    assert experiment.observations.points_per_scan() == (7, 7, 7)


# --------------------------------------------------------------------------- #
# Invalid configuration
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "overrides",
    [
        {"radius_min": 7.0, "radius_max": 6.0},
        {"radius_min": 6.0, "radius_max": 6.0},
        {"n_scans": 0},
        {"n_points": 0},
        {"noise_level": -1.0},
        {"signal_scale": 0.0},
        {"radius_min": -1.0},
        {"seed": -5},
        {"scenario": Scenario.INVALID_STRUCTURE, "n_scans": 1},
        {"scenario": Scenario.MIXED_OPTICS, "n_scans": 1},
        {"scenario": Scenario.EMPTY_SCANS, "n_scans": 1},
        {"bogus_field": 1},
    ],
)
def test_invalid_configurations_are_rejected(overrides: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        _config(**overrides)


# --------------------------------------------------------------------------- #
# Writers
# --------------------------------------------------------------------------- #


def test_generic_long_export_reloads(tmp_path: Path) -> None:
    experiment = generate_experiment(_config())
    directory = write_generic_long(experiment, tmp_path / "long")
    assert (directory / "manifest.json").is_file()
    assert (directory / "scans.csv").is_file()

    restored = openauc.load(directory)
    assert restored.validate_structure().is_valid
    assert restored.observations.scan_ids == experiment.observations.scan_ids
    assert restored.observations.points_per_scan() == (
        experiment.observations.points_per_scan()
    )
    for scan_id in experiment.observations.scan_ids:
        before = experiment.observations.scan_vectors(scan_id)
        after = restored.observations.scan_vectors(scan_id)
        assert np.allclose(before[0], after[0])
        assert np.allclose(before[1], after[1])


def test_generic_wide_export_reloads(tmp_path: Path) -> None:
    experiment = generate_experiment(_config())
    directory = write_generic_wide(experiment, tmp_path / "wide")
    restored = openauc.load(directory)
    assert restored.validate_structure().is_valid
    assert restored.observations.mode is RadiusAxisMode.SHARED
    assert restored.observations.scan_ids == experiment.observations.scan_ids


def test_wide_export_refuses_per_scan_axes(tmp_path: Path) -> None:
    experiment = generate_experiment(_config(scenario=Scenario.PER_SCAN_RADIUS))
    with pytest.raises(SyntheticWriteError, match="shared radius axis"):
        write_generic_wide(experiment, tmp_path / "wide")


def test_aucx_export_round_trips_exactly(tmp_path: Path) -> None:
    for scenario in (
        Scenario.MOVING_BOUNDARY,
        Scenario.PER_SCAN_RADIUS,
        Scenario.SPARSE_METADATA,
        Scenario.EMPTY_SCANS,
        Scenario.MIXED_OPTICS,
    ):
        experiment = generate_experiment(_config(scenario=scenario))
        archive = write_aucx(experiment, tmp_path / f"{scenario.value}.aucx")
        restored = openauc.load(archive)
        assert restored.to_dict() == experiment.to_dict(), scenario


def test_delimited_output_cannot_carry_unknown_but_aucx_can(tmp_path: Path) -> None:
    """A documented limitation, asserted rather than glossed over."""
    experiment = generate_experiment(_config(scenario=Scenario.SPARSE_METADATA))
    long_dir = write_generic_long(experiment, tmp_path / "long")
    from_csv = openauc.load(long_dir)
    from_aucx = openauc.load(write_aucx(experiment, tmp_path / "a.aucx"))

    original = {s.elapsed_time.status for s in experiment.scans}
    assert ValueStatus.UNKNOWN in original
    assert {s.elapsed_time.status for s in from_aucx.scans} == original
    # CSV collapses unknown into missing; the column simply is not written.
    assert ValueStatus.UNKNOWN not in {s.elapsed_time.status for s in from_csv.scans}


@pytest.mark.parametrize("writer", ["long", "wide"])
def test_directory_writers_refuse_to_overwrite(tmp_path: Path, writer: str) -> None:
    experiment = generate_experiment(_config())
    write = write_generic_long if writer == "long" else write_generic_wide
    directory = write(experiment, tmp_path / writer)
    before = (directory / "scans.csv").read_bytes()
    with pytest.raises(SyntheticWriteError, match="refusing to overwrite"):
        write(experiment, directory)
    assert (directory / "scans.csv").read_bytes() == before
    write(experiment, directory, overwrite=True)


def test_aucx_writer_refuses_to_overwrite(tmp_path: Path) -> None:
    from openauc.exceptions import ArchiveError

    experiment = generate_experiment(_config())
    archive = write_aucx(experiment, tmp_path / "a.aucx")
    with pytest.raises(ArchiveError, match="refusing to overwrite"):
        write_aucx(experiment, archive)
    write_aucx(experiment, archive, overwrite=True)


# --------------------------------------------------------------------------- #
# Compatibility with the rest of the library
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "scenario",
    [Scenario.MOVING_BOUNDARY, Scenario.PER_SCAN_RADIUS, Scenario.EMPTY_SCANS],
)
def test_generated_experiments_plot(scenario: Scenario) -> None:
    from openauc.plotting import plot_scans

    experiment = generate_experiment(_config(scenario=scenario))
    axes = plot_scans(experiment)
    populated = sum(1 for c in experiment.observations.points_per_scan() if c)
    assert len(axes.lines) == populated


def test_generated_experiments_summarise_and_assess() -> None:
    experiment = generate_experiment(_config(metadata_completeness="complete"))
    summary = experiment.summary_data()
    assert summary.n_scans == 5
    assert summary.total_valid_observations == 100
    assert json.loads(json.dumps(summary.to_dict()))["n_scans"] == 5
    assert "no assessment of scientific validity" in experiment.summary().lower()
    assessment = experiment.assess_readiness()
    assert assessment.sedimentation_velocity.status.value in {
        "potentially_ready",
        "blocked",
    }


def test_provenance_records_generation_without_inventing_a_source() -> None:
    experiment = generate_experiment(_config(seed=3))
    provenance = experiment.provenance
    assert provenance is not None
    assert provenance.parser_name == "openauc.synthetic"
    # Nothing was read from disk, so no path or checksum is invented.
    assert provenance.source_path is None
    assert provenance.sha256 is None
    assert provenance.source_checksums == ()
    assert any("seed=3" in a for a in provenance.assumptions)
    assert any(SYNTHETIC_NOTE in a for a in provenance.assumptions)


# --------------------------------------------------------------------------- #
# Honesty of claims
# --------------------------------------------------------------------------- #


def test_generated_experiments_are_labelled_synthetic() -> None:
    experiment = generate_experiment(_config())
    assert experiment.metadata.notes == SYNTHETIC_NOTE
    assert "not a physically validated simulation" in SYNTHETIC_NOTE.lower()
    assert "not a lamm-equation solution" in SYNTHETIC_NOTE.lower()


def _normalised(path: Path) -> str:
    """Lowercased text with line wrapping collapsed, for prose matching."""
    return " ".join(path.read_text(encoding="utf-8").lower().split())


def test_no_module_makes_an_affirmative_scientific_claim() -> None:
    """Only affirmative claims are forbidden; the denials of them are required."""
    forbidden = (
        "is scientifically valid",
        "are scientifically valid",
        "is a physically validated",
        "physically accurate",
        "accurate simulation",
        "realistic simulation",
        "simulates sedimentation",
        "computes the sedimentation coefficient",
        "derives the molecular weight",
        "fits physical parameters",
    )
    for path in (*SRC.glob("*.py"), DOC):
        text = _normalised(path)
        for phrase in forbidden:
            assert phrase not in text, (path.name, phrase)


def test_the_disclaimer_is_stated_where_it_matters() -> None:
    required = "not a physically validated simulation"
    for path in (SRC / "__init__.py", SRC / "generators.py", SRC / "config.py"):
        text = _normalised(path)
        assert "not" in text and "simulation" in text, path.name
    doc = _normalised(DOC)
    assert "illustrative" in doc
    assert required in doc
    assert "lamm" in doc
    assert required in SYNTHETIC_NOTE.lower()


def test_no_physical_parameters_appear_on_generated_models() -> None:
    """The model has no field for them, and the generator invents none."""
    experiment = generate_experiment(_config(metadata_completeness="complete"))
    dumped = json.dumps(experiment.to_dict()).lower()
    for term in ("svedberg", "sedimentation_coefficient", "molar_mass", "diffusion"):
        assert term not in dumped


# --------------------------------------------------------------------------- #
# Performance
# --------------------------------------------------------------------------- #


@pytest.mark.slow
def test_moderate_dataset_generates_and_archives(tmp_path: Path) -> None:
    config = SyntheticExperimentConfig(
        scenario=Scenario.MOVING_BOUNDARY, n_scans=60, n_points=3000, seed=5
    )
    experiment = generate_experiment(config)
    assert experiment.observations.n_scans == 60
    assert sum(experiment.observations.points_per_scan()) == 180_000
    assert experiment.validate_structure().is_valid
    archive = write_aucx(experiment, tmp_path / "big.aucx")
    restored = openauc.load(archive)
    assert restored.observations.n_scans == 60
    assert np.allclose(
        restored.observations.valid_radius_values(),
        experiment.observations.valid_radius_values(),
    )
