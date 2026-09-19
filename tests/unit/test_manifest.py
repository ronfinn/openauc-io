"""Manifest model validation: schema version, safe paths, strictness."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from openauc.exceptions import ManifestError
from openauc.formats.manifest import GenericManifest, load_manifest, parse_timestamp


def _write(path: Path, payload: dict[str, object]) -> Path:
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _valid_payload() -> dict[str, object]:
    return {
        "schema_version": "1.0",
        "format": "generic-long",
        "data_file": "scans.csv",
        "experiment": {"experiment_id": "e-1"},
    }


def test_valid_manifest_loads(tmp_path: Path) -> None:
    path = _write(tmp_path / "manifest.json", _valid_payload())
    manifest = load_manifest(path)
    assert manifest.schema_version == "1.0"
    assert manifest.format == "generic-long"
    assert manifest.data_file == "scans.csv"
    assert manifest.experiment.experiment_id == "e-1"


def test_invalid_schema_version_raises(tmp_path: Path) -> None:
    payload = _valid_payload()
    payload["schema_version"] = "2.0"
    path = _write(tmp_path / "manifest.json", payload)
    with pytest.raises(ManifestError, match="schema_version"):
        load_manifest(path)


def test_missing_manifest_file_raises(tmp_path: Path) -> None:
    with pytest.raises(ManifestError, match="not found"):
        load_manifest(tmp_path / "absent.json")


@pytest.mark.parametrize(
    "bad_path",
    ["../escape.csv", "/etc/passwd", "sub/../../escape.csv", "C:/data.csv"],
)
def test_unsafe_data_path_rejected(tmp_path: Path, bad_path: str) -> None:
    payload = _valid_payload()
    payload["data_file"] = bad_path
    path = _write(tmp_path / "manifest.json", payload)
    with pytest.raises(ManifestError):
        load_manifest(path)


def test_nested_relative_data_path_is_allowed(tmp_path: Path) -> None:
    payload = _valid_payload()
    payload["data_file"] = "data/scans.csv"
    path = _write(tmp_path / "manifest.json", payload)
    manifest = load_manifest(path)
    assert manifest.data_file == "data/scans.csv"


def test_extra_top_level_field_forbidden(tmp_path: Path) -> None:
    payload = _valid_payload()
    payload["unexpected"] = "x"
    path = _write(tmp_path / "manifest.json", payload)
    with pytest.raises(ManifestError):
        load_manifest(path)


def test_extension_field_is_allowed(tmp_path: Path) -> None:
    payload = _valid_payload()
    payload["extension"] = {"vendor_hint": "synthetic"}
    path = _write(tmp_path / "manifest.json", payload)
    manifest = load_manifest(path)
    assert manifest.extension == {"vendor_hint": "synthetic"}


def test_format_is_optional(tmp_path: Path) -> None:
    payload = _valid_payload()
    del payload["format"]
    path = _write(tmp_path / "manifest.json", payload)
    assert load_manifest(path).format is None


def test_bad_delimiter_rejected(tmp_path: Path) -> None:
    payload = _valid_payload()
    payload["delimiter"] = ";"
    path = _write(tmp_path / "manifest.json", payload)
    with pytest.raises(ManifestError):
        load_manifest(path)


def test_notes_are_retained(tmp_path: Path) -> None:
    payload = _valid_payload()
    payload["notes"] = "keep me"
    path = _write(tmp_path / "manifest.json", payload)
    assert load_manifest(path).notes == "keep me"


def test_model_schema_has_expected_required_fields() -> None:
    schema = GenericManifest.model_json_schema()
    assert set(schema["required"]) == {"schema_version", "data_file", "experiment"}


# --------------------------------------------------------------------------- #
# Acquisition timestamps and sample references
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("text", "iso"),
    [
        ("2026-03-02T09:30:00+01:00", "2026-03-02T09:30:00+01:00"),
        ("2026-03-02T09:30:00", "2026-03-02T09:30:00"),
        ("2026-03-02 09:30:00", "2026-03-02T09:30:00"),
        ("2026-03-02T09:30:00Z", "2026-03-02T09:30:00+00:00"),
    ],
)
def test_timestamp_is_preserved_without_conversion(text: str, iso: str) -> None:
    parsed = parse_timestamp(text)
    assert parsed.isoformat() == iso
    assert (parsed.tzinfo is None) == ("+" not in iso)


@pytest.mark.parametrize(
    "bad", ["2026-03-02", "20260302", "not-a-date", "", 1772440200, 1.5, True]
)
def test_timestamp_rejects_dates_numbers_and_garbage(bad: object) -> None:
    with pytest.raises(ValueError):
        parse_timestamp(bad)


def test_yaml_datetime_is_accepted_and_yaml_date_is_rejected(tmp_path: Path) -> None:
    body = (
        'schema_version: "1.0"\ndata_file: scans.csv\nexperiment:\n'
        "  experiment_id: e\n  acquired_at: %s\n"
    )
    ok = tmp_path / "ok.yaml"
    ok.write_text(body % "2026-03-02T10:00:00+01:00", encoding="utf-8")
    acquired = load_manifest(ok).experiment.acquired_at
    assert acquired is not None
    assert acquired.isoformat() == "2026-03-02T10:00:00+01:00"
    bad = tmp_path / "bad.yaml"
    bad.write_text(body % "2026-03-02", encoding="utf-8")
    with pytest.raises(ManifestError, match="without a time of day"):
        load_manifest(bad)


def test_manifest_experiment_acquired_at_defaults_to_none(tmp_path: Path) -> None:
    manifest = load_manifest(_write(tmp_path / "m.json", _valid_payload()))
    assert manifest.experiment.acquired_at is None


def test_default_sample_id_must_be_declared(tmp_path: Path) -> None:
    payload = _valid_payload()
    payload["defaults"] = {"sample_id": "ghost"}
    with pytest.raises(ManifestError, match="defaults.sample_id"):
        load_manifest(_write(tmp_path / "m.json", payload))
    payload["samples"] = [{"sample_id": "ghost"}]
    assert load_manifest(_write(tmp_path / "m.json", payload)).defaults.sample_id


def test_wide_column_sample_id_must_be_declared(tmp_path: Path) -> None:
    payload = _valid_payload()
    payload["columns"] = {
        "radius": "r",
        "scans": [{"column": "c1", "scan_id": "a", "sample_id": "ghost"}],
    }
    with pytest.raises(ManifestError, match="ghost"):
        load_manifest(_write(tmp_path / "m.json", payload))
