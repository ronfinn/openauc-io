"""Tests for the narrow Beckman XL-I ``.ip1`` interference reader.

All fixtures are tiny synthetic files written into ``tmp_path``. No real
instrument data is committed.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

import openauc
from openauc.exceptions import (
    DataConflictError,
    ManifestError,
    OpenAUCError,
    ParseError,
    UnsupportedFormatError,
)
from openauc.models import OpticalSystem, Unit

HEADER = "P 1 20.1 40000 0000536 7.7182E09 675 40"
ROWS: tuple[tuple[str, ...], ...] = (
    ("5.9677", "0.00000E+00"),
    ("5.9684", "-1.25000E-02"),
    ("5.9691", "3.5E-01"),
)


def _write(
    path: Path,
    *,
    line1: str = "cm/pixel:  0.00069667737, Sample",
    header: str = HEADER,
    rows: tuple[tuple[str, ...], ...] = ROWS,
    eol: str = "\r\n",
    tail: str = "",
) -> Path:
    body = [line1, header, *("  " + "   ".join(row) for row in rows)]
    path.write_bytes((eol.join(body) + eol + tail).encode("ascii"))
    return path


def test_valid_single_scan(tmp_path: Path) -> None:
    experiment = openauc.load(_write(tmp_path / "00001.ip1"))
    assert [s.scan_id for s in experiment.scans] == ["00001"]
    scan = experiment.scans[0]
    assert scan.optical_system is OpticalSystem.INTERFERENCE
    assert scan.source_file == "00001.ip1"
    assert experiment.provenance is not None
    assert experiment.provenance.parser_name == "ip1"
    assert experiment.validate().is_valid


def test_extension_is_case_insensitive(tmp_path: Path) -> None:
    experiment = openauc.load(_write(tmp_path / "00007.IP1"))
    assert experiment.scans[0].scan_id == "00007"


def test_multiple_scans_directory_in_numeric_order(tmp_path: Path) -> None:
    _write(tmp_path / "00002.ip1")
    _write(tmp_path / "00001.IP1")
    _write(tmp_path / "00010.ip1")
    experiment = openauc.load(tmp_path)
    assert [s.scan_id for s in experiment.scans] == ["00001", "00002", "00010"]
    assert [s.index for s in experiment.scans] == [0, 1, 2]
    assert experiment.observations.mode.value == "shared"
    assert experiment.provenance is not None
    assert len(experiment.provenance.source_checksums) == 3


def test_observations_preserved_exactly(tmp_path: Path) -> None:
    _write(tmp_path / "00001.ip1")
    experiment = openauc.load(tmp_path / "00001.ip1")
    dataset = experiment.observations.dataset
    assert dataset["radius"].values.tolist() == [float(r) for r, *_ in ROWS]
    assert dataset["signal"].values[0].tolist() == [float(s) for *_, s in ROWS]
    assert experiment.observations.signal_unit is Unit.UNKNOWN


def test_header_fields_mapped(tmp_path: Path) -> None:
    scan = openauc.load(_write(tmp_path / "00001.ip1")).scans[0]
    assert scan.cell == "1"
    assert scan.temperature is not None
    assert (scan.temperature.value, scan.temperature.unit) == (
        20.1,
        Unit.DEGREE_CELSIUS,
    )
    assert scan.rotor_speed is not None
    assert (scan.rotor_speed.value, scan.rotor_speed.unit) == (40000.0, Unit.RPM)
    assert (scan.elapsed_time.value, scan.elapsed_time.unit) == (536.0, Unit.SECOND)


def test_unmapped_fields_preserved_raw(tmp_path: Path) -> None:
    scan = openauc.load(_write(tmp_path / "00001.ip1")).scans[0]
    assert "ip1:comment=Sample" in scan.annotations
    assert "ip1:cm_per_pixel=0.00069667737" in scan.annotations
    tokens = '["P", "1", "20.1", "40000", "0000536", "7.7182E09", "675", "40"]'
    assert f"ip1:header_tokens={tokens}" in scan.annotations
    # 675 is recorded, never replaced by the manual's 665 nm, and not mapped.
    assert scan.wavelength is None


def test_comment_with_commas_preserved(tmp_path: Path) -> None:
    path = _write(tmp_path / "00001.ip1", line1="cm/pixel: 0.0007, IgG, 1 mg/mL")
    assert "ip1:comment=IgG, 1 mg/mL" in openauc.load(path).scans[0].annotations


def test_no_sample_or_timestamp_inferred(tmp_path: Path) -> None:
    experiment = openauc.load(_write(tmp_path / "00001.ip1"))  # comment is "Sample"
    assert experiment.samples == ()
    assert experiment.scans[0].sample_id is None
    assert experiment.scans[0].acquired_at is None
    assert experiment.metadata.acquired_at is None


def test_lf_line_endings_and_no_trailing_newline_fragment(tmp_path: Path) -> None:
    path = _write(tmp_path / "00001.ip1", eol="\n", tail="    ")
    assert openauc.load(path).observations.dataset["radius"].shape == (3,)


def test_differing_radius_grids_stay_per_scan_without_regridding(
    tmp_path: Path,
) -> None:
    _write(tmp_path / "00001.ip1")
    _write(tmp_path / "00002.ip1", rows=(("5.9677", "1.0"), ("5.9700", "2.0")))
    experiment = openauc.load(tmp_path)
    assert experiment.observations.mode.value == "per_scan"
    assert experiment.validate().is_valid


def test_aucx_round_trip(tmp_path: Path) -> None:
    scans = tmp_path / "scans"
    scans.mkdir()
    _write(scans / "00001.ip1")
    experiment = openauc.load(scans)
    restored = openauc.load(experiment.export(tmp_path / "ip1.aucx"))
    assert restored.scans == experiment.scans
    assert np.array_equal(
        restored.observations.dataset["signal"].values,
        experiment.observations.dataset["signal"].values,
    )


def test_explicit_format_and_manifest_rejected(tmp_path: Path) -> None:
    path = _write(tmp_path / "00001.ip1")
    assert openauc.load(path, format="ip1").scans[0].scan_id == "00001"
    manifest = tmp_path / "m.json"
    manifest.write_text("{}")
    with pytest.raises(ManifestError, match="does not use a manifest"):
        openauc.load(path, format="ip1", manifest=manifest)


# -- failures: nothing is silently repaired ---------------------------------


@pytest.mark.parametrize(
    "header",
    [
        "P 1 20.1 40000 0000536 7.7182E09 675",  # 7 tokens
        "P 1 20.1 40000 0000536 7.7182E09 675 40 9",  # 9 tokens
        "",
    ],
)
def test_wrong_token_count(tmp_path: Path, header: str) -> None:
    with pytest.raises(ParseError, match="8 tokens"):
        openauc.load(_write(tmp_path / "00001.ip1", header=header))


@pytest.mark.parametrize(
    "header, message",
    [
        ("P 1 warm 40000 0000536 7.7182E09 675 40", "temperature"),
        ("P 1 20.1 fast 0000536 7.7182E09 675 40", "rotor speed"),
        ("P 1 20.1 40000 -5 7.7182E09 675 40", "total seconds"),
        ("P 1 20.1 40000 0000536 x 675 40", "token 6"),
        ("P one 20.1 40000 0000536 7.7182E09 675 40", "cell number"),
        ("P 0 20.1 40000 0000536 7.7182E09 675 40", "cell number"),
        ("P 1 nan 40000 0000536 7.7182E09 675 40", "not finite"),
    ],
)
def test_malformed_line2(tmp_path: Path, header: str, message: str) -> None:
    with pytest.raises(ParseError, match=message):
        openauc.load(_write(tmp_path / "00001.ip1", header=header))


@pytest.mark.parametrize(
    "line1",
    [
        "cm/pixel 0.0007, Sample",
        "cm/pixel: 0.0007 Sample",
        "cm/pixel: abc, x",
        "cm/pixel: -1, x",
        "Sample",
    ],
)
def test_malformed_line1(tmp_path: Path, line1: str) -> None:
    with pytest.raises(ParseError):
        openauc.load(_write(tmp_path / "00001.ip1", line1=line1))


@pytest.mark.parametrize(
    "rows",
    [
        (("5.9677", "abc"),),
        (("5.9677", "nan"),),
        (("5.9677", "1.0"), ("5.9684",)),
        (("5.9677", "1.0", "9"),),
        (("5.9677", "1.0"), ("", "")),
    ],
)
def test_malformed_data_row(tmp_path: Path, rows: tuple[tuple[str, ...], ...]) -> None:
    with pytest.raises(ParseError):
        openauc.load(_write(tmp_path / "00001.ip1", rows=rows))


def test_no_data_rows_rejected(tmp_path: Path) -> None:
    with pytest.raises(ParseError, match="data rows"):
        openauc.load(_write(tmp_path / "00001.ip1", rows=()))


def test_non_ascii_rejected(tmp_path: Path) -> None:
    path = tmp_path / "00001.ip1"
    path.write_bytes("cm/pixel: 0.0007, café\r\n".encode() + b"x\r\n1 2\r\n")
    with pytest.raises(ParseError, match="ASCII"):
        openauc.load(path, format="ip1")


def test_duplicate_scan_numbers_rejected(tmp_path: Path) -> None:
    _write(tmp_path / "00001.ip1")
    _write(tmp_path / "00001.IP1")
    # Same name differing only in case can coexist only on case-sensitive disks.
    if len(list(tmp_path.iterdir())) == 2:
        with pytest.raises(DataConflictError, match="duplicate scan"):
            openauc.load(tmp_path)


def test_interior_blank_line_rejected(tmp_path: Path) -> None:
    path = _write(tmp_path / "00001.ip1")
    text = path.read_bytes().decode("ascii").replace("\r\n  5.9684", "\r\n\r\n  5.9684")
    path.write_bytes(text.encode("ascii"))
    with pytest.raises(ParseError, match="2 numeric columns"):
        openauc.load(path)


@pytest.mark.parametrize("name", ["00001.ra1", "00001.ip2", "00001.wa1", "scan.ip1"])
def test_unsupported_single_file_variants(tmp_path: Path, name: str) -> None:
    path = _write(tmp_path / name)
    with pytest.raises((UnsupportedFormatError, ParseError)):
        openauc.load(path, format="ip1")


def test_directory_with_other_scan_variants_rejected(tmp_path: Path) -> None:
    _write(tmp_path / "00001.ip1")
    _write(tmp_path / "00001.ra1")
    with pytest.raises(UnsupportedFormatError, match="unsupported XL-A/XL-I"):
        openauc.load(tmp_path)


def test_directory_without_scans_rejected(tmp_path: Path) -> None:
    with pytest.raises(ParseError, match=r"no \.ip1 scan files"):
        openauc.load(tmp_path, format="ip1")


def test_detection_is_conservative(tmp_path: Path) -> None:
    # Not claimed without .ip1 input: falls through to the manifest path.
    (tmp_path / "data.csv").write_text("a,b\n1,2\n")
    with pytest.raises(ManifestError):
        openauc.load(tmp_path)
    # An adjacent manifest keeps the generic path in charge of a .ip1 name.
    _write(tmp_path / "00001.ip1")
    (tmp_path / "manifest.json").write_text("{}")
    with pytest.raises(OpenAUCError) as info:
        openauc.load(tmp_path / "00001.ip1")
    assert not isinstance(info.value, UnsupportedFormatError)


def test_format_is_listed() -> None:
    ids = {info.format_id for info in openauc.available_formats()}
    assert "ip1" in ids
