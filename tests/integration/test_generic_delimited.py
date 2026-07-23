"""End-to-end ingestion tests for the generic delimited parsers."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest

import openauc
from openauc.exceptions import (
    AmbiguousFormatError,
    DataConflictError,
    ManifestError,
    ParseError,
)
from openauc.models import (
    AUCExperiment,
    OpticalSystem,
    RadiusAxisMode,
    Unit,
    ValueStatus,
)

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "generic_delimited"


def _write_experiment(
    tmp_path: Path,
    manifest: dict[str, Any],
    data_text: str,
    *,
    data_name: str = "scans.csv",
) -> Path:
    (tmp_path / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    (tmp_path / data_name).write_text(data_text, encoding="utf-8")
    return tmp_path


# --------------------------------------------------------------------------- #
# Valid loads (scenarios 1-9, 17, 18, 25)
# --------------------------------------------------------------------------- #


def test_long_csv_directory_load() -> None:
    exp = openauc.load(FIXTURES / "long_csv")
    assert isinstance(exp, AUCExperiment)
    assert exp.observations.mode is RadiusAxisMode.SHARED
    assert exp.observations.scan_ids == ("scan_001", "scan_002")
    assert exp.validate_structure().is_valid


def test_long_tsv_yaml_manifest_load() -> None:
    exp = openauc.load(FIXTURES / "long_tsv")
    assert exp.observations.n_scans == 2
    assert exp.provenance is not None
    assert exp.provenance.parser_name == "generic-long"


def test_wide_csv_load() -> None:
    exp = openauc.load(FIXTURES / "wide_csv")
    assert exp.observations.mode is RadiusAxisMode.SHARED
    assert exp.observations.scan_ids == ("scan_001", "scan_002", "scan_003")
    assert exp.validate_structure().is_valid


def test_wide_tsv_load() -> None:
    exp = openauc.load(FIXTURES / "wide_tsv")
    assert exp.observations.n_scans == 2


def test_directory_load_and_direct_file_load_agree() -> None:
    from_dir = openauc.load(FIXTURES / "long_csv")
    from_file = openauc.load(FIXTURES / "long_csv" / "scans.csv")
    assert from_file.observations == from_dir.observations
    assert from_file.scans == from_dir.scans


def test_explicit_format_override() -> None:
    exp = openauc.load(FIXTURES / "long_csv", format="generic-long")
    assert exp.provenance is not None
    assert exp.provenance.parser_name == "generic-long"


def test_explicit_wrong_format_override_fails_clearly() -> None:
    # Overriding a long file as wide has no column mapping -> clear ManifestError.
    with pytest.raises(ManifestError, match="columns"):
        openauc.load(FIXTURES / "long_csv", format="generic-wide")


def test_format_detection_when_manifest_omits_format() -> None:
    exp = openauc.load(FIXTURES / "detect_long")
    assert exp.provenance is not None
    assert exp.provenance.parser_name == "generic-long"


def test_shared_radius_construction() -> None:
    exp = openauc.load(FIXTURES / "long_csv")
    assert exp.observations.mode is RadiusAxisMode.SHARED
    assert exp.observations.radius_range() == (5.90, 5.92)


def test_per_scan_radius_construction() -> None:
    exp = openauc.load(FIXTURES / "per_scan")
    assert exp.observations.mode is RadiusAxisMode.PER_SCAN
    assert exp.observations.points_per_scan() == (2, 3)


# --------------------------------------------------------------------------- #
# Order preservation and no silent transforms (scenarios 19, 28)
# --------------------------------------------------------------------------- #


def test_row_order_is_preserved_not_sorted(tmp_path: Path) -> None:
    # Radii deliberately out of ascending order; must be preserved verbatim.
    manifest = {
        "schema_version": "1.0",
        "format": "generic-long",
        "data_file": "scans.csv",
        "experiment": {"experiment_id": "order-1"},
        "defaults": {"signal_unit": "absorbance_unit"},
    }
    data = "scan,radius_cm,signal\nA,6.20,0.3\nA,6.10,0.2\nA,6.00,0.1\n"
    exp = openauc.load(_write_experiment(tmp_path, manifest, data))
    radius = exp.observations.dataset["radius"].to_numpy().tolist()
    assert radius == [6.20, 6.10, 6.00]


def test_scan_order_follows_first_appearance(tmp_path: Path) -> None:
    manifest = {
        "schema_version": "1.0",
        "format": "generic-long",
        "data_file": "scans.csv",
        "experiment": {"experiment_id": "order-2"},
        "defaults": {"signal_unit": "absorbance_unit"},
    }
    data = "scan,radius_cm,signal\nlate,6.0,0.1\nearly,6.0,0.2\n"
    exp = openauc.load(_write_experiment(tmp_path, manifest, data))
    assert exp.observations.scan_ids == ("late", "early")


# --------------------------------------------------------------------------- #
# Metadata handling (scenarios 20, 21)
# --------------------------------------------------------------------------- #


def test_missing_optional_metadata_is_explicit() -> None:
    exp = openauc.load(FIXTURES / "per_scan")
    # No elapsed_seconds column -> elapsed_time is explicitly MISSING.
    assert exp.scans[0].elapsed_time.status is ValueStatus.MISSING


def test_unknown_optical_system(tmp_path: Path) -> None:
    manifest = {
        "schema_version": "1.0",
        "format": "generic-long",
        "data_file": "scans.csv",
        "experiment": {"experiment_id": "optical-1"},
        "defaults": {"signal_unit": "absorbance_unit"},
    }
    data = (
        "scan,radius_cm,signal,optical_system\nA,6.0,0.1,unknown\nA,6.1,0.2,unknown\n"
    )
    exp = openauc.load(_write_experiment(tmp_path, manifest, data))
    assert exp.scans[0].optical_system is OpticalSystem.UNKNOWN


def test_absent_optical_system_defaults_to_unknown(tmp_path: Path) -> None:
    manifest = {
        "schema_version": "1.0",
        "format": "generic-long",
        "data_file": "scans.csv",
        "experiment": {"experiment_id": "optical-2"},
        "defaults": {"signal_unit": "absorbance_unit"},
    }
    data = "scan,radius_cm,signal\nA,6.0,0.1\n"
    exp = openauc.load(_write_experiment(tmp_path, manifest, data))
    assert exp.scans[0].optical_system is OpticalSystem.UNKNOWN


def test_declared_units_are_retained() -> None:
    exp = openauc.load(FIXTURES / "long_csv")
    assert exp.observations.signal_unit is Unit.ABSORBANCE_UNIT
    assert exp.observations.radius_unit is Unit.CENTIMETRE


# --------------------------------------------------------------------------- #
# Errors (scenarios 11-16, 22, 23, 27)
# --------------------------------------------------------------------------- #


def test_ambiguous_manifest_directory() -> None:
    with pytest.raises(AmbiguousFormatError, match="both a JSON and a YAML"):
        openauc.load(FIXTURES / "ambiguous_manifest")


def test_ambiguous_manifest_resolved_by_explicit_choice() -> None:
    exp = openauc.load(
        FIXTURES / "ambiguous_manifest",
        manifest=FIXTURES / "ambiguous_manifest" / "manifest.json",
    )
    assert exp.metadata.experiment_id == "synthetic-ambiguous-001"


def test_ambiguous_delimiter(tmp_path: Path) -> None:
    # Both comma and tab yield a consistent 2-column table; a .dat suffix gives
    # no tie-breaker, so detection must refuse.
    manifest = {
        "schema_version": "1.0",
        "format": "generic-long",
        "data_file": "scans.dat",
        "experiment": {"experiment_id": "delim-1"},
    }
    data = "x,y\tz\n1,2\t3\n"
    directory = _write_experiment(tmp_path, manifest, data, data_name="scans.dat")
    with pytest.raises(AmbiguousFormatError, match="delimiter"):
        openauc.load(directory)


def test_declared_delimiter_resolves_ambiguity(tmp_path: Path) -> None:
    manifest = {
        "schema_version": "1.0",
        "format": "generic-long",
        "data_file": "scans.dat",
        "delimiter": "tab",
        "experiment": {"experiment_id": "delim-2"},
        "defaults": {"signal_unit": "absorbance_unit"},
    }
    data = "scan\tradius_cm\tsignal\nA\t6.0\t0.1\n"
    directory = _write_experiment(tmp_path, manifest, data, data_name="scans.dat")
    exp = openauc.load(directory)
    assert exp.observations.n_scans == 1


def test_missing_required_columns_raises_parse_error() -> None:
    with pytest.raises(ParseError, match="missing required column"):
        openauc.load(FIXTURES / "malformed_missing_column")


def test_nonfinite_value_raises_parse_error() -> None:
    with pytest.raises(ParseError, match="finite"):
        openauc.load(FIXTURES / "malformed_nonfinite")


def test_duplicate_observation_raises_conflict() -> None:
    with pytest.raises(DataConflictError, match="duplicate observation"):
        openauc.load(FIXTURES / "malformed_duplicate")


def test_conflicting_manifest_and_table_metadata() -> None:
    with pytest.raises(DataConflictError, match="cell"):
        openauc.load(FIXTURES / "conflict")


def test_invalid_schema_version_via_load(tmp_path: Path) -> None:
    manifest = {
        "schema_version": "9.9",
        "format": "generic-long",
        "data_file": "scans.csv",
        "experiment": {"experiment_id": "v-1"},
    }
    data = "scan,radius_cm,signal\nA,6.0,0.1\n"
    directory = _write_experiment(tmp_path, manifest, data)
    with pytest.raises(ManifestError, match="schema_version"):
        openauc.load(directory)


def test_unsafe_data_path_via_load(tmp_path: Path) -> None:
    (tmp_path / "manifest.json").write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "format": "generic-long",
                "data_file": "../escape.csv",
                "experiment": {"experiment_id": "unsafe-1"},
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ManifestError):
        openauc.load(tmp_path)


def test_error_messages_identify_file_and_location() -> None:
    with pytest.raises(ParseError) as excinfo:
        openauc.load(FIXTURES / "malformed_nonfinite")
    message = str(excinfo.value)
    assert "scans.csv" in message
    assert "row" in message
    assert "signal" in message


# --------------------------------------------------------------------------- #
# Manifests, provenance and serialisation (scenarios 5, 6, 26)
# --------------------------------------------------------------------------- #


def test_matching_json_and_yaml_manifests_agree() -> None:
    directory = FIXTURES / "matching_manifests"
    from_json = openauc.load(directory, manifest=directory / "manifest.json")
    from_yaml = openauc.load(directory, manifest=directory / "manifest.yaml")
    assert from_json.metadata == from_yaml.metadata
    assert from_json.scans == from_yaml.scans
    assert from_json.observations == from_yaml.observations


def test_provenance_is_populated() -> None:
    exp = openauc.load(FIXTURES / "long_csv")
    prov = exp.provenance
    assert prov is not None
    assert prov.parser_name == "generic-long"
    assert prov.parser_version == openauc.__version__
    assert prov.source_filename == "scans.csv"
    assert prov.sha256 is None  # deferred to Phase 6
    assert isinstance(prov.imported_at, datetime)
    assert any("manifest:" in a for a in prov.assumptions)
    assert any("data_file:" in a for a in prov.assumptions)


def test_result_serialises_through_to_dict_roundtrip() -> None:
    exp = openauc.load(FIXTURES / "long_csv")
    payload = exp.to_dict()
    assert payload["provenance"]["parser_name"] == "generic-long"
    restored = AUCExperiment.from_dict(payload)
    assert restored.observations == exp.observations
    assert restored.scans == exp.scans
    assert restored.to_dict() == payload
