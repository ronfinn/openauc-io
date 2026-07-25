"""Generic delimited import -> AUCX -> model, through the public entry points."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pytest

import openauc
from openauc.models import AUCExperiment, RadiusAxisMode

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "generic_delimited"
FIXED_TIME = datetime(2026, 1, 1, tzinfo=UTC)


def _load(name: str) -> AUCExperiment:
    return openauc.load(FIXTURES / name)


@pytest.mark.parametrize(
    "fixture",
    ["long_csv", "wide_csv", "long_tsv", "wide_tsv", "per_scan", "readiness_rich"],
)
def test_csv_to_aucx_to_model_round_trip(fixture: str, tmp_path: Path) -> None:
    original = _load(fixture)
    archive = original.export(tmp_path / f"{fixture}.aucx", exported_at=FIXED_TIME)
    restored = openauc.load(archive)
    assert restored.to_dict() == original.to_dict()
    assert restored.observations.mode is original.observations.mode
    for scan_id in original.observations.scan_ids:
        before = original.observations.scan_vectors(scan_id)
        after = restored.observations.scan_vectors(scan_id)
        assert np.array_equal(before[0], after[0])
        assert np.array_equal(before[1], after[1])


def test_public_load_dispatches_on_suffix_and_explicit_format(tmp_path: Path) -> None:
    original = _load("long_csv")
    archive = openauc.export_aucx(original, tmp_path / "x.aucx", exported_at=FIXED_TIME)
    assert openauc.load(archive).to_dict() == original.to_dict()
    assert openauc.load(archive, format="aucx").to_dict() == original.to_dict()
    # A path without the suffix still loads when the format is named explicitly.
    renamed = tmp_path / "no-suffix"
    renamed.write_bytes(archive.read_bytes())
    assert openauc.load(renamed, format="aucx").to_dict() == original.to_dict()


def test_source_checksums_survive_the_archive(tmp_path: Path) -> None:
    original = _load("long_csv")
    restored = openauc.load(
        original.export(tmp_path / "x.aucx", exported_at=FIXED_TIME)
    )
    assert restored.provenance is not None
    assert restored.provenance.sha256 == original.provenance.sha256  # type: ignore[union-attr]
    roles = {c.role: c.value for c in restored.provenance.source_checksums}
    assert set(roles) == {"manifest", "data_file"}


def test_archive_of_an_archive_is_stable(tmp_path: Path) -> None:
    """Re-exporting a loaded archive reproduces it byte-for-byte."""
    original = _load("long_csv")
    first = original.export(tmp_path / "a.aucx", exported_at=FIXED_TIME)
    reloaded = openauc.load(first)
    second = reloaded.export(tmp_path / "b.aucx", exported_at=FIXED_TIME)
    assert first.read_bytes() == second.read_bytes()


def test_ragged_import_keeps_its_axis_mode_through_the_archive(tmp_path: Path) -> None:
    original = _load("per_scan")
    assert original.observations.mode is RadiusAxisMode.PER_SCAN
    restored = openauc.load(
        original.export(tmp_path / "x.aucx", exported_at=FIXED_TIME)
    )
    assert restored.observations.mode is RadiusAxisMode.PER_SCAN
    assert restored.observations.points_per_scan() == (2, 3)


def test_inspect_and_validate_over_an_imported_archive(tmp_path: Path) -> None:
    original = _load("readiness_rich")
    archive = original.export(tmp_path / "x.aucx", exported_at=FIXED_TIME)
    info = openauc.inspect_aucx(archive)
    assert info.experiment_id == "synthetic-readiness-001"
    assert info.n_scans == len(original.scans)
    assert openauc.validate_aucx(archive).is_valid
    # Archive integrity and structural validity are separate questions.
    restored = openauc.load(archive)
    assert restored.validate().is_valid
