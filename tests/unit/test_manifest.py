"""Manifest model validation: schema version, safe paths, strictness."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from openauc.exceptions import ManifestError
from openauc.formats.manifest import GenericManifest, load_manifest


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
