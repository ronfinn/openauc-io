"""Edge cases lifting coverage of the parsers and loader."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

import openauc
from openauc.exceptions import (
    DataConflictError,
    ManifestError,
    ParseError,
)
from openauc.models import Unit, ValueProvenance


def _experiment(
    tmp_path: Path,
    manifest: dict[str, Any],
    data: str,
    *,
    data_name: str = "scans.csv",
) -> Path:
    (tmp_path / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    (tmp_path / data_name).write_text(data, encoding="utf-8")
    return tmp_path


def _long(manifest_extra: dict[str, Any] | None = None) -> dict[str, Any]:
    manifest: dict[str, Any] = {
        "schema_version": "1.0",
        "format": "generic-long",
        "data_file": "scans.csv",
        "experiment": {"experiment_id": "edge"},
        "defaults": {"signal_unit": "absorbance_unit"},
    }
    if manifest_extra:
        manifest.update(manifest_extra)
    return manifest


def test_non_numeric_value_raises(tmp_path: Path) -> None:
    data = "scan,radius_cm,signal\nA,6.0,oops\n"
    with pytest.raises(ParseError, match="expected a finite number"):
        openauc.load(_experiment(tmp_path, _long(), data))


def test_inconsistent_per_scan_metadata_raises(tmp_path: Path) -> None:
    data = "scan,radius_cm,signal,cell\nA,6.0,0.1,1\nA,6.1,0.2,2\n"
    with pytest.raises(DataConflictError, match="inconsistent"):
        openauc.load(_experiment(tmp_path, _long(), data))


def test_multiple_signal_units_in_file_raises(tmp_path: Path) -> None:
    manifest = _long()
    manifest["defaults"] = {}
    data = "scan,radius_cm,signal,signal_unit\nA,6.0,0.1,AU\nB,6.0,0.2,fringe\n"
    with pytest.raises(DataConflictError, match="multiple signal_unit"):
        openauc.load(_experiment(tmp_path, manifest, data))


def test_signal_unit_conflicts_with_default(tmp_path: Path) -> None:
    manifest = _long({"defaults": {"signal_unit": "fringe"}})
    data = "scan,radius_cm,signal,signal_unit\nA,6.0,0.1,AU\n"
    with pytest.raises(DataConflictError, match="signal_unit"):
        openauc.load(_experiment(tmp_path, manifest, data))


def test_numeric_metadata_conflict_with_default(tmp_path: Path) -> None:
    manifest = _long({"defaults": {"wavelength_nm": 280, "signal_unit": "AU"}})
    data = "scan,radius_cm,signal,wavelength_nm\nA,6.0,0.1,230\n"
    with pytest.raises(DataConflictError, match="wavelength_nm"):
        openauc.load(_experiment(tmp_path, manifest, data))


def test_invalid_acquisition_timestamp_raises(tmp_path: Path) -> None:
    data = "scan,radius_cm,signal,acquisition_timestamp\nA,6.0,0.1,not-a-date\n"
    with pytest.raises(ParseError, match="ISO-8601"):
        openauc.load(_experiment(tmp_path, _long(), data))


def test_unknown_optical_string_raises(tmp_path: Path) -> None:
    data = "scan,radius_cm,signal,optical_system\nA,6.0,0.1,xray\n"
    with pytest.raises(ParseError, match="optical_system"):
        openauc.load(_experiment(tmp_path, _long(), data))


def test_field_count_mismatch_raises(tmp_path: Path) -> None:
    # Consistent counts pass delimiter detection, but this file is intentionally
    # ragged so detection fails first with a clear message.
    data = "scan,radius_cm,signal\nA,6.0\n"
    with pytest.raises(ParseError):
        openauc.load(_experiment(tmp_path, _long(), data))


def test_empty_scan_id_raises(tmp_path: Path) -> None:
    data = "scan,radius_cm,signal\n,6.0,0.1\n"
    with pytest.raises(ParseError, match="empty scan identifier"):
        openauc.load(_experiment(tmp_path, _long(), data))


def test_full_metadata_long(tmp_path: Path) -> None:
    manifest = _long(
        {
            "instrument": {
                "manufacturer": "Synthetic",
                "nominal_speed_rpm": 50000,
                "temperature_c": 20,
                "optical_system": "absorbance",
                "wavelength_nm": 280,
            },
            "samples": [
                {
                    "sample_id": "s1",
                    "concentration_value": 0.5,
                    "concentration_unit": "mg/mL",
                    "density": 1.005,
                }
            ],
        }
    )
    data = (
        "scan,radius_cm,signal,elapsed_seconds,cell,channel,wavelength_nm,"
        "optical_system,rotor_speed_rpm,temperature_c,source_scan_id\n"
        "A,6.0,0.1,0,1,A,280,absorbance,50000,20,orig-A\n"
        "A,6.1,0.2,0,1,A,280,absorbance,50000,20,orig-A\n"
    )
    exp = openauc.load(_experiment(tmp_path, manifest, data))
    scan = exp.scans[0]
    assert scan.cell == "1"
    assert scan.wavelength is not None and scan.wavelength.value == 280
    assert scan.rotor_speed is not None and scan.rotor_speed.unit is Unit.RPM
    assert "source_scan_id=orig-A" in scan.annotations
    assert exp.instrument is not None
    assert exp.instrument.nominal_speed is not None
    assert exp.samples[0].concentration is not None
    assert exp.samples[0].concentration.unit_label == "mg/mL"
    assert exp.samples[0].concentration.provenance is ValueProvenance.SUPPLIED


def test_wide_missing_radius_column(tmp_path: Path) -> None:
    manifest: dict[str, Any] = {
        "schema_version": "1.0",
        "format": "generic-wide",
        "data_file": "scans.csv",
        "experiment": {"experiment_id": "w"},
        "defaults": {"signal_unit": "absorbance_unit"},
        "columns": {
            "radius": "radius_cm",
            "scans": [{"column": "scan_001", "scan_id": "scan_001"}],
        },
    }
    data = "not_radius,scan_001\n6.0,0.1\n"
    with pytest.raises(ParseError, match="radius column"):
        openauc.load(_experiment(tmp_path, manifest, data))


def test_wide_missing_scan_column(tmp_path: Path) -> None:
    manifest: dict[str, Any] = {
        "schema_version": "1.0",
        "format": "generic-wide",
        "data_file": "scans.csv",
        "experiment": {"experiment_id": "w"},
        "defaults": {"signal_unit": "absorbance_unit"},
        "columns": {
            "radius": "radius_cm",
            "scans": [{"column": "absent", "scan_id": "scan_001"}],
        },
    }
    data = "radius_cm,scan_001\n6.0,0.1\n"
    with pytest.raises(ParseError, match="scan column"):
        openauc.load(_experiment(tmp_path, manifest, data))


def test_wide_duplicate_radius(tmp_path: Path) -> None:
    manifest: dict[str, Any] = {
        "schema_version": "1.0",
        "format": "generic-wide",
        "data_file": "scans.csv",
        "experiment": {"experiment_id": "w"},
        "defaults": {"signal_unit": "absorbance_unit"},
        "columns": {
            "radius": "radius_cm",
            "scans": [{"column": "scan_001", "scan_id": "scan_001"}],
        },
    }
    data = "radius_cm,scan_001\n6.0,0.1\n6.0,0.2\n"
    with pytest.raises(DataConflictError, match="duplicate radius"):
        openauc.load(_experiment(tmp_path, manifest, data))


def test_wide_missing_columns_mapping(tmp_path: Path) -> None:
    manifest: dict[str, Any] = {
        "schema_version": "1.0",
        "format": "generic-wide",
        "data_file": "scans.csv",
        "experiment": {"experiment_id": "w"},
        "defaults": {"signal_unit": "absorbance_unit"},
    }
    data = "radius_cm,scan_001\n6.0,0.1\n"
    with pytest.raises(ManifestError, match="columns"):
        openauc.load(_experiment(tmp_path, manifest, data))


def test_load_nonexistent_path_raises() -> None:
    with pytest.raises(ParseError, match="does not exist"):
        openauc.load("/no/such/openauc/path")


def test_load_manifest_file_path_directly(tmp_path: Path) -> None:
    _experiment(tmp_path, _long(), "scan,radius_cm,signal\nA,6.0,0.1\n")
    exp = openauc.load(tmp_path / "manifest.json")
    assert exp.metadata.experiment_id == "edge"


def test_direct_file_without_manifest_raises(tmp_path: Path) -> None:
    (tmp_path / "scans.csv").write_text(
        "scan,radius_cm,signal\nA,6.0,0.1\n", encoding="utf-8"
    )
    with pytest.raises(ManifestError, match="no adjacent manifest"):
        openauc.load(tmp_path / "scans.csv")


def test_explicit_manifest_not_a_file_raises(tmp_path: Path) -> None:
    _experiment(tmp_path, _long(), "scan,radius_cm,signal\nA,6.0,0.1\n")
    with pytest.raises(ManifestError, match="not found"):
        openauc.load(tmp_path, manifest=tmp_path / "absent.json")


def test_declared_delimiter_inconsistent_raises(tmp_path: Path) -> None:
    manifest = _long({"delimiter": "tab", "data_file": "scans.csv"})
    data = "scan,radius_cm,signal\nA,6.0,0.1\n"  # comma data, tab declared
    with pytest.raises(ParseError, match="delimiter"):
        openauc.load(_experiment(tmp_path, manifest, data))


def test_optical_system_by_name_form(tmp_path: Path) -> None:
    data = "scan,radius_cm,signal,optical_system\nA,6.0,0.1,ABSORBANCE\n"
    exp = openauc.load(_experiment(tmp_path, _long(), data))
    assert exp.scans[0].optical_system.value == "absorbance"
