"""Structured summaries: fields, serialisation and text rendering
(scenarios 13, 14, 21, 22, 24)."""

from __future__ import annotations

import json

from openauc.models import (
    AUCExperiment,
    ExperimentMetadata,
    ExperimentSummary,
    ExperimentType,
    ImportProvenance,
    MetadataPresence,
    Observations,
    OpticalSystem,
    Quantity,
    RadiusAxisMode,
    SampleMetadata,
    ScanMetadata,
    Unit,
    ValidationCounts,
    ValueRange,
    summarise_experiment,
)


def _scan(scan_id: str, index: int, *, elapsed: float | None = None) -> ScanMetadata:
    return ScanMetadata(
        scan_id=scan_id,
        index=index,
        elapsed_time=(
            Quantity.of(elapsed, Unit.SECOND)
            if elapsed is not None
            else Quantity.missing()
        ),
        cell="1",
        channel="A",
        wavelength=Quantity.of(280.0, Unit.NANOMETRE),
        optical_system=OpticalSystem.ABSORBANCE,
        rotor_speed=Quantity.of(45000.0, Unit.RPM),
        temperature=Quantity.of(20.0, Unit.DEGREE_CELSIUS),
    )


def _shared_experiment() -> AUCExperiment:
    scans = (_scan("a", 0, elapsed=0.0), _scan("b", 1, elapsed=600.0))
    return AUCExperiment(
        metadata=ExperimentMetadata(
            experiment_id="exp-shared",
            name="Shared axis",
            experiment_type=ExperimentType.SEDIMENTATION_VELOCITY,
            operator="synthetic",
        ),
        scans=scans,
        observations=Observations.from_shared_axis(
            radius=[6.0, 6.1, 6.2],
            signal=[[0.1, 0.2, 0.3], [0.2, 0.3, 0.4]],
            scan_ids=["a", "b"],
            signal_unit=Unit.ABSORBANCE_UNIT,
        ),
        samples=(
            SampleMetadata(
                sample_id="s1",
                buffer_description="synthetic buffer",
                density=Quantity.of(1.0, Unit.OTHER, unit_label="g/mL"),
            ),
        ),
        provenance=ImportProvenance(parser_name="generic-long"),
    )


def _per_scan_experiment() -> AUCExperiment:
    return AUCExperiment(
        metadata=ExperimentMetadata(experiment_id="exp-per-scan"),
        scans=(_scan("a", 0, elapsed=0.0), _scan("b", 1, elapsed=600.0)),
        observations=Observations.from_per_scan(
            radii=[[6.0, 6.1, 6.2], [6.0, 6.05]],
            signals=[[0.1, 0.2, 0.3], [0.4, 0.5]],
            scan_ids=["a", "b"],
            signal_unit=Unit.ABSORBANCE_UNIT,
        ),
    )


# --------------------------------------------------------------------------- #
# 13 & 14 — both radius-axis modes
# --------------------------------------------------------------------------- #


def test_shared_axis_summary_reports_structure() -> None:
    """Scenario 13."""
    summary = _shared_experiment().summary_data()
    assert isinstance(summary, ExperimentSummary)
    assert summary.experiment_id == "exp-shared"
    assert summary.name == "Shared axis"
    assert summary.experiment_type is ExperimentType.SEDIMENTATION_VELOCITY
    assert summary.operator == "synthetic"
    assert summary.n_scans == 2
    assert summary.n_samples == 1
    assert summary.radius_axis_mode is RadiusAxisMode.SHARED
    assert summary.radius_unit is Unit.CENTIMETRE
    assert summary.signal_unit is Unit.ABSORBANCE_UNIT
    assert summary.signal_unit_declared
    assert summary.points_per_scan == (3, 3)
    assert summary.total_valid_observations == 6
    assert summary.optical_systems == (OpticalSystem.ABSORBANCE,)
    assert summary.wavelengths_nm == (280.0,)
    assert summary.scans_without_wavelength == 0
    assert summary.cells == ("1",)
    assert summary.channels == ("A",)
    assert summary.radius == ValueRange(
        minimum=6.0, maximum=6.2, unit=Unit.CENTIMETRE, n_present=6, n_absent=0
    )
    assert summary.elapsed_time.minimum == 0.0
    assert summary.elapsed_time.maximum == 600.0
    assert summary.elapsed_time.unit is Unit.SECOND
    assert summary.rotor_speed.render() == "45000 to 45000 rpm (observed)"
    assert summary.temperature.n_present == 2
    assert summary.provenance_available
    assert summary.parser_name == "generic-long"
    assert not summary.checksum_available


def test_per_scan_summary_reports_ragged_structure() -> None:
    """Scenario 14: points per scan and totals respect the validity mask."""
    summary = _per_scan_experiment().summary_data()
    assert summary.radius_axis_mode is RadiusAxisMode.PER_SCAN
    assert summary.points_per_scan == (3, 2)
    assert summary.total_valid_observations == 5
    assert summary.radius.minimum == 6.0
    assert summary.radius.maximum == 6.2
    assert not summary.provenance_available
    assert summary.parser_name is None


def test_absent_values_are_counted_not_defaulted() -> None:
    experiment = AUCExperiment(
        metadata=ExperimentMetadata(experiment_id="sparse"),
        scans=(
            ScanMetadata(scan_id="a", index=0, elapsed_time=Quantity.missing()),
            ScanMetadata(scan_id="b", index=1, elapsed_time=Quantity.unknown()),
        ),
        observations=Observations.from_shared_axis(
            radius=[6.0, 6.1], signal=[[0.1, 0.2], [0.2, 0.3]], scan_ids=["a", "b"]
        ),
    )
    summary = experiment.summary_data()
    assert summary.elapsed_time.minimum is None
    assert summary.elapsed_time.n_present == 0
    assert summary.elapsed_time.n_absent == 2
    assert summary.elapsed_time.render() == "unknown"
    assert not summary.elapsed_time.is_observed
    assert summary.scans_without_cell == 2
    assert summary.cells == ()

    presence = {
        (entry.component, entry.field): entry for entry in summary.metadata_presence
    }
    elapsed = presence[("scan", "elapsed_time")]
    # MISSING and UNKNOWN are never collapsed into one another.
    assert elapsed.missing == 1
    assert elapsed.unknown == 1
    assert elapsed.present == 0
    assert elapsed.unrecorded == 2
    assert presence[("scan", "wavelength")].absent == 2


def test_sample_presence_is_reported() -> None:
    summary = _shared_experiment().summary_data()
    presence = {
        (entry.component, entry.field): entry for entry in summary.metadata_presence
    }
    assert presence[("sample", "density")].present == 1
    assert presence[("sample", "viscosity")].absent == 1
    assert presence[("sample", "buffer_description")].present == 1


# --------------------------------------------------------------------------- #
# 21 — serialisation
# --------------------------------------------------------------------------- #


def test_summary_serialises_to_json() -> None:
    """Scenario 21."""
    payload = _shared_experiment().summary_data().to_dict()
    restored = json.loads(json.dumps(payload))
    assert restored["experiment_id"] == "exp-shared"
    assert restored["radius_axis_mode"] == "shared"
    assert restored["signal_unit"] == "AU"
    assert restored["points_per_scan"] == [3, 3]
    assert restored["radius"]["minimum"] == 6.0
    assert restored["validation"]["error"] == 0
    assert any(
        entry["field"] == "elapsed_time" for entry in restored["metadata_presence"]
    )


def test_summary_is_frozen() -> None:
    summary = _shared_experiment().summary_data()
    assert summary.model_config["frozen"] is True
    assert isinstance(summary.points_per_scan, tuple)
    assert isinstance(summary.metadata_presence, tuple)
    assert isinstance(summary.metadata_presence[0], MetadataPresence)
    assert isinstance(summary.validation, ValidationCounts)


def test_validation_counts_total() -> None:
    counts = ValidationCounts(error=1, warning=2, info=3)
    assert counts.total == 6


def test_summarise_experiment_matches_the_method() -> None:
    experiment = _shared_experiment()
    assert summarise_experiment(experiment) == experiment.summary_data()


# --------------------------------------------------------------------------- #
# 22 & 24 — text rendering and the absence of any scientific claim
# --------------------------------------------------------------------------- #


def test_text_summary_retains_every_previously_asserted_line() -> None:
    """Scenario 22: the human-readable form is additive, never rewritten."""
    text = _shared_experiment().summary()
    for expected in (
        "Experiment: exp-shared - Shared axis",
        "  Type: sedimentation_velocity",
        "  Acquired: unknown",
        "  Operator: synthetic",
        "  Scans: 2",
        "  Samples: 1",
        "  Optical systems: absorbance",
        "  Radius axis: shared",
        "  Radius unit: cm",
        "  Signal unit: AU",
        "  Radius range: 6 to 6.2 cm (observed)",
        "  Elapsed time: 0 to 600 s (observed)",
        "  Provenance: recorded (generic-long)",
    ):
        assert expected in text.splitlines()


def test_text_summary_renders_the_new_structural_lines() -> None:
    text = _per_scan_experiment().summary()
    lines = text.splitlines()
    assert "  Points per scan: 2 to 3 (varies)" in lines
    assert "  Total observations: 5" in lines
    assert "  Wavelengths: 280 nm" in lines
    assert "  Cells: 1" in lines
    assert "  Channels: A" in lines
    assert "  Rotor speed: 45000 to 45000 rpm (observed)" in lines
    assert "  Temperature: 20 to 20 degC (observed)" in lines
    assert "  Source checksum: not recorded (deferred to the AUCX phase)" in lines
    assert any(line.startswith("  Validation: ") for line in lines)


def test_text_summary_renders_absent_metadata_honestly() -> None:
    experiment = AUCExperiment(
        metadata=ExperimentMetadata(experiment_id="bare"),
        scans=(ScanMetadata(scan_id="a", index=0, elapsed_time=Quantity.missing()),),
        observations=Observations.from_per_scan(
            radii=[[]], signals=[[]], scan_ids=["a"]
        ),
    )
    lines = experiment.summary().splitlines()
    assert "  Radius range: n/a (no observations)" in lines
    assert "  Elapsed time: unknown" in lines
    assert "  Points per scan: 0 (uniform)" in lines
    assert "  Wavelengths: unknown" in lines
    assert "  Cells: none recorded" in lines
    assert "  Rotor speed: unknown" in lines
    assert "  Provenance: not recorded" in lines


def test_partial_metadata_is_rendered_with_unknown_counts() -> None:
    experiment = AUCExperiment(
        metadata=ExperimentMetadata(experiment_id="partial"),
        scans=(
            _scan("a", 0, elapsed=0.0),
            ScanMetadata(scan_id="b", index=1, elapsed_time=Quantity.missing()),
        ),
        observations=Observations.from_shared_axis(
            radius=[6.0, 6.1], signal=[[0.1, 0.2], [0.2, 0.3]], scan_ids=["a", "b"]
        ),
    )
    lines = experiment.summary().splitlines()
    assert "  Wavelengths: 280 nm (1 scan(s) unknown)" in lines
    assert "  Cells: 1 (1 scan(s) unknown)" in lines


def test_summary_of_an_experiment_with_no_scans() -> None:
    experiment = AUCExperiment(
        metadata=ExperimentMetadata(experiment_id="empty"),
        scans=(),
        observations=Observations.from_per_scan(radii=[], signals=[], scan_ids=[]),
    )
    summary = experiment.summary_data()
    assert summary.n_scans == 0
    assert summary.points_per_scan == ()
    assert summary.total_valid_observations == 0
    assert summary.validation.error == 1
    lines = experiment.summary().splitlines()
    assert "  Points per scan: n/a" in lines
    assert "  Optical systems: " in lines


def test_checksum_line_reports_a_recorded_checksum() -> None:
    experiment = AUCExperiment(
        metadata=ExperimentMetadata(experiment_id="checked"),
        scans=(_scan("a", 0, elapsed=0.0),),
        observations=Observations.from_shared_axis(
            radius=[6.0], signal=[[0.1]], scan_ids=["a"]
        ),
        provenance=ImportProvenance(parser_name="p", sha256="c" * 64),
    )
    summary = experiment.summary_data()
    assert summary.checksum_available
    assert "  Source checksum: recorded" in experiment.summary().splitlines()


def test_summary_makes_no_scientific_claim() -> None:
    """Scenario 24: no output surface may imply scientific validity."""
    text = _shared_experiment().summary().lower()
    assert "no assessment of scientific validity" in text
    assert "suitable for analysis" not in text.replace("suitability for analysis", "")
    for forbidden in ("scientifically valid", "quality score", "sedimentation coeff"):
        assert forbidden not in text
