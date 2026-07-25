"""Validation, readiness and summaries over imported generic delimited data
(scenarios 18, 19, plus determinism and axis-mode coverage).

Uses the synthetic repository-owned fixtures only; no real instrument data.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import openauc
from openauc.models import (
    AUCExperiment,
    ExperimentType,
    RadiusAxisMode,
    ReadinessStatus,
    Unit,
    ValidationSeverity,
    ValidationTier,
)

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "generic_delimited"


def _load(name: str) -> AUCExperiment:
    return openauc.load(FIXTURES / name)


# --------------------------------------------------------------------------- #
# 18 & 19 — imported long and wide experiments
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("fixture", ["long_csv", "wide_csv", "long_tsv", "wide_tsv"])
def test_imported_experiments_are_archivally_and_structurally_valid(
    fixture: str,
) -> None:
    """Scenarios 18 and 19."""
    experiment = _load(fixture)
    structural = experiment.validate_structure()
    assert structural.is_valid, str(structural)
    assert structural.errors == ()
    full = experiment.validate()
    assert full.is_valid
    assert full.blocking_for(ValidationTier.ARCHIVAL) == ()
    assert full.blocking_for(ValidationTier.STRUCTURAL) == ()


@pytest.mark.parametrize("fixture", ["long_csv", "wide_csv"])
def test_imported_experiments_produce_summaries(fixture: str) -> None:
    experiment = _load(fixture)
    summary = experiment.summary_data()
    assert summary.n_scans == len(experiment.scans)
    assert summary.total_valid_observations > 0
    assert summary.signal_unit is Unit.ABSORBANCE_UNIT
    assert summary.signal_unit_declared
    assert summary.provenance_available
    assert summary.parser_name == experiment.provenance.parser_name  # type: ignore[union-attr]
    assert not summary.checksum_available
    text = experiment.summary()
    assert f"Experiment: {summary.experiment_id}" in text
    assert "no assessment of scientific validity" in text.lower()
    assert json.loads(json.dumps(summary.to_dict()))["n_scans"] == summary.n_scans


def test_metadata_rich_import_is_potentially_ready_for_velocity() -> None:
    experiment = _load("readiness_rich")
    assert experiment.metadata.experiment_type is ExperimentType.SEDIMENTATION_VELOCITY
    report = experiment.validate()
    assert report.is_valid
    assert report.warnings == ()
    # The only finding is the accepted checksum deferral, and it is INFO.
    assert report.codes() == ("source_checksum_absent",)
    assert report.infos[0].severity is ValidationSeverity.INFO
    assert experiment.validate_structure().issues == ()

    assessment = experiment.assess_readiness()
    assert assessment.sedimentation_velocity.status is ReadinessStatus.POTENTIALLY_READY
    assert assessment.sedimentation_velocity.blocking_issues == ()
    assert assessment.sedimentation_equilibrium.status is ReadinessStatus.NOT_APPLICABLE
    assert assessment.scientific_suitability.status is ReadinessStatus.NOT_ASSESSED


def test_sparse_import_reports_missing_optional_metadata() -> None:
    """The per-scan fixture declares no elapsed time, speed, or samples."""
    experiment = _load("per_scan")
    report = experiment.validate()
    assert report.is_valid
    codes = set(report.codes())
    assert {
        "elapsed_time_absent",
        "rotor_speed_absent",
        "temperature_absent",
        "absorbance_wavelength_absent",
        "no_samples",
    }.issubset(codes)
    # The fixture declares a velocity run, so SE is not applicable and SV is
    # blocked by the absent elapsed times and rotor speed — while the
    # experiment itself stays archivally and structurally valid.
    assessment = experiment.assess_readiness()
    assert assessment.sedimentation_velocity.status is ReadinessStatus.BLOCKED
    assert {
        issue.code for issue in assessment.sedimentation_velocity.blocking_issues
    } == {"elapsed_time_absent", "rotor_speed_absent"}
    assert assessment.sedimentation_equilibrium.status is ReadinessStatus.NOT_APPLICABLE


def test_import_distinguishes_shared_and_per_scan_axes() -> None:
    assert _load("long_csv").summary_data().radius_axis_mode is RadiusAxisMode.SHARED
    per_scan = _load("per_scan").summary_data()
    assert per_scan.radius_axis_mode is RadiusAxisMode.PER_SCAN
    assert per_scan.points_per_scan == (2, 3)
    assert per_scan.total_valid_observations == 5


def test_import_preserves_unknown_values_without_defaulting() -> None:
    summary = _load("per_scan").summary_data()
    presence = {
        (entry.component, entry.field): entry for entry in summary.metadata_presence
    }
    elapsed = presence[("scan", "elapsed_time")]
    assert elapsed.present == 0
    assert elapsed.missing == elapsed.total
    assert summary.elapsed_time.minimum is None
    assert summary.rotor_speed.minimum is None
    assert summary.wavelengths_nm == ()
    assert summary.scans_without_wavelength == summary.n_scans


def test_imported_validation_is_deterministic() -> None:
    """Scenario 20 over real imported data."""
    first = _load("long_csv")
    second = _load("long_csv")
    assert first.validate().issues == second.validate().issues
    assert first.summary_data().to_dict() == second.summary_data().to_dict()
    # summary_data() excludes provenance timestamps, so repeated loads agree.
    assert first.summary() == second.summary()


def test_round_tripped_experiment_validates_identically() -> None:
    experiment = _load("long_csv")
    restored = AUCExperiment.from_dict(experiment.to_dict())
    assert restored.validate().issues == experiment.validate().issues
    assert restored.summary_data().to_dict() == experiment.summary_data().to_dict()
