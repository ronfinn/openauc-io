"""CLI behaviour: output, JSON, exit codes and clean domain-error reporting."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
from typer.testing import CliRunner

import openauc
from openauc.cli import ExitCode, app

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "generic_delimited"
runner = CliRunner()


@pytest.fixture
def archive(tmp_path: Path) -> Path:
    experiment = openauc.load(FIXTURES / "readiness_rich")
    return experiment.export(tmp_path / "sample.aucx")


# --------------------------------------------------------------------------- #
# version / formats / help
# --------------------------------------------------------------------------- #


def test_version_prints_the_installed_version() -> None:
    result = runner.invoke(app, ["version"])
    assert result.exit_code == ExitCode.OK
    assert result.stdout.strip() == openauc.__version__


def test_help_lists_every_command() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == ExitCode.OK
    for command in ("version", "formats", "inspect", "validate", "convert"):
        assert command in result.stdout


def test_no_arguments_shows_help() -> None:
    result = runner.invoke(app, [])
    assert "Usage" in result.stdout


def test_formats_lists_ids_suffixes_layouts_and_limitations() -> None:
    result = runner.invoke(app, ["formats"])
    assert result.exit_code == ExitCode.OK
    assert "generic-long" in result.stdout
    assert "generic-wide" in result.stdout
    assert "aucx" in result.stdout
    assert ".aucx" in result.stdout
    assert "layouts:" in result.stdout
    assert "limitations:" in result.stdout


def test_formats_json_is_structured() -> None:
    result = runner.invoke(app, ["formats", "--json"])
    assert result.exit_code == ExitCode.OK
    payload = json.loads(result.stdout)
    ids = {entry["format_id"] for entry in payload["formats"]}
    assert {"aucx", "generic-long", "generic-wide"} <= ids
    entry = next(e for e in payload["formats"] if e["format_id"] == "aucx")
    assert entry["suffixes"] == [".aucx"]
    assert entry["limitations"]
    assert entry["doc_reference"]


# --------------------------------------------------------------------------- #
# inspect
# --------------------------------------------------------------------------- #


def test_inspect_prints_a_factual_summary() -> None:
    result = runner.invoke(app, ["inspect", str(FIXTURES / "long_csv")])
    assert result.exit_code == ExitCode.OK
    assert "Experiment: synthetic-long-001" in result.stdout
    assert "no assessment of scientific validity" in result.stdout.lower()


def test_inspect_json_matches_summary_data() -> None:
    result = runner.invoke(app, ["inspect", str(FIXTURES / "long_csv"), "--json"])
    assert result.exit_code == ExitCode.OK
    payload = json.loads(result.stdout)
    expected = openauc.load(FIXTURES / "long_csv").summary_data().to_dict()
    assert payload == expected


def test_inspect_reads_an_archive(archive: Path) -> None:
    result = runner.invoke(app, ["inspect", str(archive)])
    assert result.exit_code == ExitCode.OK
    assert "synthetic-readiness-001" in result.stdout


def test_inspect_reports_a_missing_input_cleanly(tmp_path: Path) -> None:
    result = runner.invoke(app, ["inspect", str(tmp_path / "absent")])
    assert result.exit_code == ExitCode.INPUT_ERROR
    assert "error:" in result.output
    assert "Traceback" not in result.output


def test_inspect_reports_malformed_input_cleanly(tmp_path: Path) -> None:
    broken = tmp_path / "experiment"
    broken.mkdir()
    (broken / "manifest.json").write_text("{ not json", encoding="utf-8")
    result = runner.invoke(app, ["inspect", str(broken)])
    assert result.exit_code == ExitCode.INPUT_ERROR
    assert "Traceback" not in result.output


# --------------------------------------------------------------------------- #
# validate
# --------------------------------------------------------------------------- #


def test_validate_passes_with_exit_zero() -> None:
    result = runner.invoke(app, ["validate", str(FIXTURES / "long_csv")])
    assert result.exit_code == ExitCode.OK
    assert "structural validation: OK" in result.stdout
    assert "no claim is made about scientific validity" in result.stdout


def test_validate_readiness_reports_status_without_claiming_validity() -> None:
    result = runner.invoke(app, ["validate", str(FIXTURES / "per_scan"), "--readiness"])
    assert result.exit_code == ExitCode.OK
    assert "readiness (metadata presence only)" in result.stdout
    assert "not_assessed" in result.stdout
    assert "scientific_suitability" in result.stdout


def test_validate_json_carries_structural_and_readiness() -> None:
    result = runner.invoke(
        app, ["validate", str(FIXTURES / "per_scan"), "--readiness", "--json"]
    )
    assert result.exit_code == ExitCode.OK
    payload = json.loads(result.stdout)
    assert payload["structural"]["is_valid"] is True
    assert "all_tiers" in payload
    entries = payload["readiness"]["entries"]
    scientific = next(e for e in entries if e["analysis"] == "scientific_suitability")
    assert scientific["status"] == "not_assessed"


def test_validate_fails_with_exit_one_on_structural_error(tmp_path: Path) -> None:
    """A wide manifest naming a column the data lacks is a structural failure."""
    experiment_dir = tmp_path / "broken"
    experiment_dir.mkdir()
    (experiment_dir / "scans.csv").write_text(
        "radius_cm,scan_001\n0.0,0.1\n6.1,0.2\n", encoding="utf-8"
    )
    (experiment_dir / "manifest.json").write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "format": "generic-wide",
                "data_file": "scans.csv",
                "experiment": {"experiment_id": "bad-radius"},
                "columns": {
                    "radius": "radius_cm",
                    "scans": [{"column": "scan_001", "scan_id": "scan_001"}],
                },
            }
        ),
        encoding="utf-8",
    )
    result = runner.invoke(app, ["validate", str(experiment_dir)])
    assert result.exit_code == ExitCode.VALIDATION_FAILED
    assert "non_physical_radius" in result.stdout
    assert "Traceback" not in result.output


def test_validate_verifies_archive_integrity_first(archive: Path) -> None:
    result = runner.invoke(app, ["validate", str(archive)])
    assert result.exit_code == ExitCode.OK
    assert "archive integrity: OK" in result.stdout


def test_validate_reports_a_corrupt_archive_as_an_input_error(
    archive: Path, tmp_path: Path
) -> None:
    import zipfile

    corrupt = tmp_path / "corrupt.aucx"
    with zipfile.ZipFile(archive) as original:
        payloads = {name: original.read(name) for name in original.namelist()}
    payloads["experiment.json"] = payloads["experiment.json"].replace(
        b"synthetic-readiness-001", b"tampered-identifier-1"
    )
    with zipfile.ZipFile(corrupt, "w", zipfile.ZIP_DEFLATED) as rebuilt:
        for name, payload in payloads.items():
            rebuilt.writestr(name, payload)

    result = runner.invoke(app, ["validate", str(corrupt)])
    assert result.exit_code == ExitCode.INPUT_ERROR
    assert "Traceback" not in result.output
    assert "checksum" in result.output.lower()


def test_validate_of_a_missing_input_is_an_input_error(tmp_path: Path) -> None:
    result = runner.invoke(app, ["validate", str(tmp_path / "absent")])
    assert result.exit_code == ExitCode.INPUT_ERROR


# --------------------------------------------------------------------------- #
# convert
# --------------------------------------------------------------------------- #


def test_convert_writes_an_archive_that_round_trips(tmp_path: Path) -> None:
    target = tmp_path / "out.aucx"
    result = runner.invoke(app, ["convert", str(FIXTURES / "long_csv"), str(target)])
    assert result.exit_code == ExitCode.OK
    assert target.exists()
    original = openauc.load(FIXTURES / "long_csv")
    restored = openauc.load(target)
    # Everything but provenance must match exactly. Provenance carries
    # imported_at, which differs between two separate reads of the same CSV.
    for key in ("metadata", "instrument", "samples", "scans", "observations"):
        assert restored.to_dict()[key] == original.to_dict()[key]
    assert restored.provenance is not None
    assert restored.provenance.sha256 == original.provenance.sha256  # type: ignore[union-attr]


def test_convert_json_reports_what_was_written(tmp_path: Path) -> None:
    target = tmp_path / "out.aucx"
    result = runner.invoke(
        app, ["convert", str(FIXTURES / "wide_csv"), str(target), "--json"]
    )
    payload = json.loads(result.stdout)
    assert payload["output"] == str(target)
    assert payload["n_scans"] == 3
    assert payload["bytes"] == target.stat().st_size


def test_convert_refuses_to_overwrite_without_the_flag(tmp_path: Path) -> None:
    target = tmp_path / "out.aucx"
    runner.invoke(app, ["convert", str(FIXTURES / "long_csv"), str(target)])
    before = target.read_bytes()
    result = runner.invoke(app, ["convert", str(FIXTURES / "long_csv"), str(target)])
    assert result.exit_code == ExitCode.OUTPUT_EXISTS
    assert target.read_bytes() == before
    assert "--overwrite" in result.output


def test_convert_overwrites_when_asked(tmp_path: Path) -> None:
    target = tmp_path / "out.aucx"
    runner.invoke(app, ["convert", str(FIXTURES / "long_csv"), str(target)])
    result = runner.invoke(
        app,
        ["convert", str(FIXTURES / "wide_csv"), str(target), "--overwrite"],
    )
    assert result.exit_code == ExitCode.OK
    assert openauc.load(target).metadata.experiment_id == "synthetic-wide-001"


def test_convert_rejects_a_non_aucx_output(tmp_path: Path) -> None:
    result = runner.invoke(
        app, ["convert", str(FIXTURES / "long_csv"), str(tmp_path / "out.csv")]
    )
    assert result.exit_code == ExitCode.INPUT_ERROR
    assert "must be an .aucx archive" in result.output


def test_convert_rewrites_an_existing_archive(archive: Path, tmp_path: Path) -> None:
    """Archive in, archive out — useful for verifying and re-writing one."""
    target = tmp_path / "rewritten.aucx"
    result = runner.invoke(app, ["convert", str(archive), str(target)])
    assert result.exit_code == ExitCode.OK
    assert openauc.load(target).to_dict() == openauc.load(archive).to_dict()


def test_convert_of_a_missing_input_is_an_input_error(tmp_path: Path) -> None:
    result = runner.invoke(
        app, ["convert", str(tmp_path / "absent"), str(tmp_path / "out.aucx")]
    )
    assert result.exit_code == ExitCode.INPUT_ERROR
    assert not (tmp_path / "out.aucx").exists()


# --------------------------------------------------------------------------- #
# Real process invocation
# --------------------------------------------------------------------------- #


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "openauc.cli", *args],
        capture_output=True,
        text=True,
        check=False,
    )


def test_console_entry_point_runs_as_a_subprocess() -> None:
    result = _run("version")
    assert result.returncode == ExitCode.OK
    assert result.stdout.strip() == openauc.__version__


def test_subprocess_exit_codes_and_stderr(tmp_path: Path) -> None:
    result = _run("inspect", str(tmp_path / "absent"))
    assert result.returncode == ExitCode.INPUT_ERROR
    assert "error:" in result.stderr
    assert "Traceback" not in result.stderr


# --------------------------------------------------------------------------- #
# generate
# --------------------------------------------------------------------------- #


def test_generate_writes_a_loadable_generic_long_dataset(tmp_path: Path) -> None:
    target = tmp_path / "out"
    result = runner.invoke(
        app,
        [
            "generate",
            str(target),
            "--scenario",
            "moving-boundary",
            "--scans",
            "4",
            "--points",
            "12",
            "--seed",
            "7",
        ],
    )
    assert result.exit_code == ExitCode.OK
    assert "synthetic" in result.stdout.lower()
    restored = openauc.load(target)
    assert len(restored.scans) == 4
    assert restored.validate_structure().is_valid


def test_generate_writes_an_aucx_archive(tmp_path: Path) -> None:
    target = tmp_path / "demo.aucx"
    result = runner.invoke(
        app,
        ["generate", str(target), "--format", "aucx", "--scans", "3", "--points", "8"],
    )
    assert result.exit_code == ExitCode.OK
    assert openauc.validate_aucx(target).is_valid
    assert len(openauc.load(target).scans) == 3


def test_generate_is_reproducible_for_a_given_seed(tmp_path: Path) -> None:
    args = [
        "--format",
        "aucx",
        "--scans",
        "3",
        "--points",
        "8",
        "--seed",
        "5",
        "--noise",
        "0.01",
    ]
    first = tmp_path / "a.aucx"
    second = tmp_path / "b.aucx"
    runner.invoke(app, ["generate", str(first), *args])
    runner.invoke(app, ["generate", str(second), *args])
    assert openauc.load(first).to_dict() == openauc.load(second).to_dict()


def test_generate_json_output_declares_synthetic(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        ["generate", str(tmp_path / "out"), "--scans", "3", "--points", "5", "--json"],
    )
    payload = json.loads(result.stdout)
    assert payload["synthetic"] is True
    assert payload["scenario"] == "moving-boundary"
    assert "not a physically validated simulation" in payload["note"]


def test_generate_refuses_to_overwrite(tmp_path: Path) -> None:
    target = tmp_path / "out"
    base = ["generate", str(target), "--scans", "3", "--points", "5"]
    assert runner.invoke(app, base).exit_code == ExitCode.OK
    repeat = runner.invoke(app, base)
    assert repeat.exit_code == ExitCode.OUTPUT_EXISTS
    assert runner.invoke(app, [*base, "--overwrite"]).exit_code == ExitCode.OK


def test_generate_rejects_an_unknown_scenario(tmp_path: Path) -> None:
    result = runner.invoke(
        app, ["generate", str(tmp_path / "out"), "--scenario", "warp-drive"]
    )
    assert result.exit_code == ExitCode.INPUT_ERROR
    assert "unknown scenario" in result.output
    assert "Traceback" not in result.output


def test_generate_rejects_an_unknown_format(tmp_path: Path) -> None:
    result = runner.invoke(
        app, ["generate", str(tmp_path / "out"), "--format", "parquet"]
    )
    assert result.exit_code == ExitCode.INPUT_ERROR
    assert "unknown format" in result.output


def test_generate_rejects_an_invalid_configuration(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        [
            "generate",
            str(tmp_path / "out"),
            "--scenario",
            "invalid-structure",
            "--scans",
            "1",
        ],
    )
    assert result.exit_code == ExitCode.INPUT_ERROR
    assert "invalid configuration" in result.output
    assert "Traceback" not in result.output


def test_generate_refuses_wide_output_for_per_scan_axes(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        [
            "generate",
            str(tmp_path / "out"),
            "--scenario",
            "per-scan-radius",
            "--format",
            "generic-wide",
        ],
    )
    assert result.exit_code == ExitCode.INPUT_ERROR
    assert "shared radius axis" in result.output


def test_generate_help_states_the_output_is_not_a_simulation() -> None:
    result = runner.invoke(app, ["generate", "--help"])
    assert result.exit_code == ExitCode.OK
    text = " ".join(result.stdout.split()).lower()
    assert "illustrative synthetic" in text
    assert "not a physically validated simulation" in text
    assert "lamm-equation" in text
    for claim in ("scientifically valid", "accurate simulation"):
        assert claim not in text
