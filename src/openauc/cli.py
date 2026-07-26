"""Command-line interface for openauc.

Commands mirror the Python API and add nothing scientific:

* ``version``  — print the installed version
* ``formats``  — list the formats this build can read
* ``inspect``  — load an input and print its factual structural summary
* ``validate`` — report archival and structural findings, optionally readiness
* ``convert``  — write a generic delimited experiment, or an archive, to AUCX
* ``generate`` — write an illustrative synthetic dataset (never a simulation)

Every command accepts ``--json`` where structured output is useful, so the CLI
composes with other tools.

Exit codes are stable and documented (see :class:`ExitCode`): ``0`` success,
``1`` structural validation failed, ``2`` the input could not be read, ``3`` the
requested output already exists. Expected domain errors print a single clear
message — never a traceback.
"""

from __future__ import annotations

import json
from enum import IntEnum
from pathlib import Path
from typing import Annotated, Any

import typer
from pydantic import ValidationError

from openauc import __version__
from openauc.exceptions import ArchiveError, OpenAUCError
from openauc.formats.aucx import AUCX_SUFFIX

SYNTHETIC_DISCLAIMER = (
    "illustrative synthetic data; not a physically validated simulation"
)

__all__ = ["ExitCode", "app", "main"]


class ExitCode(IntEnum):
    """Documented process exit codes."""

    #: The command completed and, where applicable, validation passed.
    OK = 0
    #: Structural validation reported at least one ERROR-severity finding.
    VALIDATION_FAILED = 1
    #: The input could not be read, parsed or verified.
    INPUT_ERROR = 2
    #: The output already exists and ``--overwrite`` was not given.
    OUTPUT_EXISTS = 3


app = typer.Typer(
    name="openauc",
    help="Import, validate, standardise, visualise and archive AUC data.",
    no_args_is_help=True,
    add_completion=False,
)

JsonOption = Annotated[
    bool, typer.Option("--json", help="Emit machine-readable JSON instead of text.")
]


@app.callback()
def _root() -> None:
    """Import, validate, standardise and archive analytical ultracentrifugation data.

    openauc reports structure and metadata only. It makes no claim about
    scientific validity, data quality or suitability for analysis.
    """


def _echo_json(payload: dict[str, Any]) -> None:
    typer.echo(json.dumps(payload, indent=2, sort_keys=True))


def _fail(message: str, code: ExitCode) -> None:
    """Print a single-line error to stderr and exit. No traceback."""
    typer.secho(f"error: {message}", err=True, fg=typer.colors.RED)
    raise typer.Exit(code=int(code))


def _load(path: Path) -> Any:
    """Load an experiment, converting domain errors into a clean exit."""
    from openauc import load

    try:
        return load(path)
    except OpenAUCError as exc:
        _fail(f"{path}: {exc}", ExitCode.INPUT_ERROR)


@app.command()
def version() -> None:
    """Print the installed openauc version."""
    typer.echo(__version__)


@app.command()
def formats(as_json: JsonOption = False) -> None:
    """List the formats this build can read."""
    from openauc import available_formats

    infos = available_formats()
    if as_json:
        _echo_json(
            {
                "formats": [
                    {
                        "format_id": info.format_id,
                        "name": info.name,
                        "suffixes": list(info.suffixes),
                        "layouts": list(info.layouts),
                        "limitations": list(info.limitations),
                        "doc_reference": info.doc_reference,
                    }
                    for info in infos
                ]
            }
        )
        return
    for info in infos:
        typer.echo(f"{info.format_id}  {info.name}")
        typer.echo(f"  suffixes:    {', '.join(info.suffixes) or '(none)'}")
        typer.echo(f"  layouts:     {'; '.join(info.layouts) or '(none)'}")
        for index, limitation in enumerate(info.limitations):
            label = "limitations:" if index == 0 else "            "
            typer.echo(f"  {label} {limitation}")
        typer.echo(f"  docs:        {info.doc_reference}")


@app.command()
def inspect(
    input_path: Annotated[
        Path, typer.Argument(help="Experiment directory, data file or .aucx archive.")
    ],
    as_json: JsonOption = False,
) -> None:
    """Load an input and print its factual structural summary.

    Describes structure and metadata only; it makes no scientific claim.
    """
    experiment = _load(input_path)
    summary = experiment.summary_data()
    if as_json:
        _echo_json(summary.to_dict())
        return
    typer.echo(summary.to_text())


@app.command()
def validate(
    input_path: Annotated[
        Path, typer.Argument(help="Experiment directory, data file or .aucx archive.")
    ],
    readiness: Annotated[
        bool,
        typer.Option(
            "--readiness",
            help="Also report analysis-readiness findings and per-workflow status.",
        ),
    ] = False,
    as_json: JsonOption = False,
) -> None:
    """Report archival and structural findings for an input.

    Exits 0 when structural validation passes, 1 when it fails, and 2 when the
    input cannot be read. Structural validity is never a claim of scientific
    validity.
    """
    if input_path.suffix.lower() == AUCX_SUFFIX:
        _report_archive_integrity(input_path, as_json=as_json)

    experiment = _load(input_path)
    structural = experiment.validate_structure()
    full = experiment.validate() if readiness else structural
    assessment = experiment.assess_readiness() if readiness else None

    if as_json:
        payload: dict[str, Any] = {
            "path": str(input_path),
            "structural": structural.to_dict(),
        }
        if readiness and assessment is not None:
            payload["all_tiers"] = full.to_dict()
            payload["readiness"] = assessment.to_dict()
        _echo_json(payload)
    else:
        typer.echo(str(structural))
        if readiness and assessment is not None:
            typer.echo("")
            typer.echo("readiness (metadata presence only):")
            typer.echo(str(assessment))
        typer.echo("")
        typer.echo(
            "note: structural validation only; no claim is made about "
            "scientific validity or data quality."
        )
    if not structural.is_valid:
        raise typer.Exit(code=int(ExitCode.VALIDATION_FAILED))


def _report_archive_integrity(path: Path, *, as_json: bool) -> None:
    """Verify archive integrity first; a broken container stops validation."""
    from openauc import validate_aucx

    report = validate_aucx(path)
    if report.is_valid:
        if not as_json:
            typer.echo(f"archive integrity: OK ({path})")
        return
    if as_json:
        _echo_json({"path": str(path), "archive": report.to_dict()})
    else:
        typer.secho(str(report), err=True, fg=typer.colors.RED)
    raise typer.Exit(code=int(ExitCode.INPUT_ERROR))


@app.command()
def convert(
    input_path: Annotated[
        Path, typer.Argument(help="Experiment directory, data file or .aucx archive.")
    ],
    output_path: Annotated[Path, typer.Argument(help="Destination .aucx archive.")],
    overwrite: Annotated[
        bool, typer.Option("--overwrite", help="Replace the output if it exists.")
    ] = False,
    as_json: JsonOption = False,
) -> None:
    """Write an experiment to an AUCX archive.

    Reads generic delimited input or an existing archive (useful for verifying
    and rewriting one). Model data is preserved exactly: nothing is
    interpolated, resampled or unit-converted.
    """
    if output_path.suffix.lower() != AUCX_SUFFIX:
        _fail(
            f"output must be an {AUCX_SUFFIX} archive, got {output_path.name!r}",
            ExitCode.INPUT_ERROR,
        )
    if output_path.exists() and not overwrite:
        _fail(
            f"{output_path} already exists; pass --overwrite to replace it",
            ExitCode.OUTPUT_EXISTS,
        )

    experiment = _load(input_path)
    try:
        written = experiment.export(output_path, overwrite=overwrite)
    except ArchiveError as exc:
        _fail(str(exc), ExitCode.INPUT_ERROR)
    except OpenAUCError as exc:  # pragma: no cover - defensive
        _fail(str(exc), ExitCode.INPUT_ERROR)

    if as_json:
        _echo_json(
            {
                "input": str(input_path),
                "output": str(written),
                "n_scans": len(experiment.scans),
                "bytes": written.stat().st_size,
            }
        )
    else:
        typer.echo(f"wrote {written} ({written.stat().st_size} bytes)")


@app.command()
def generate(
    output_path: Annotated[
        Path,
        typer.Argument(
            help="Destination: a directory for CSV output, or an .aucx file."
        ),
    ],
    scenario: Annotated[
        str, typer.Option("--scenario", help="Which synthetic scenario to generate.")
    ] = "moving-boundary",
    scans: Annotated[int, typer.Option("--scans", help="Number of scans.")] = 10,
    points: Annotated[
        int, typer.Option("--points", help="Radial points per scan.")
    ] = 100,
    seed: Annotated[
        int,
        typer.Option(
            "--seed",
            help="Random seed; the same seed always produces the same dataset.",
        ),
    ] = 0,
    noise: Annotated[
        float, typer.Option("--noise", help="Deterministic noise level (0 disables).")
    ] = 0.0,
    output_format: Annotated[
        str,
        typer.Option(
            "--format", help="generic-long | generic-wide | aucx.", show_default=True
        ),
    ] = "generic-long",
    overwrite: Annotated[
        bool, typer.Option("--overwrite", help="Replace existing output.")
    ] = False,
    as_json: JsonOption = False,
) -> None:
    """Generate an ILLUSTRATIVE SYNTHETIC dataset for testing and demonstration.

    The output is invented data. It is NOT a physically validated simulation of
    an analytical ultracentrifugation experiment, not a Lamm-equation solution,
    and carries no sedimentation coefficient, molar mass or any other physical
    parameter. Nothing scientific may be inferred from it.

    Scenarios: moving-boundary, equilibrium-profile, static-profile,
    per-scan-radius, sparse-metadata, mixed-optics, empty-scans,
    invalid-structure.
    """
    from openauc.synthetic import (
        Scenario,
        SyntheticExperimentConfig,
        SyntheticWriteError,
        generate_experiment,
        write_aucx,
        write_generic_long,
        write_generic_wide,
    )

    try:
        chosen = Scenario(scenario)
    except ValueError:
        _fail(
            f"unknown scenario {scenario!r}; choose one of "
            f"{[s.value for s in Scenario]}",
            ExitCode.INPUT_ERROR,
        )
    writers = {
        "generic-long": write_generic_long,
        "generic-wide": write_generic_wide,
        "aucx": write_aucx,
    }
    if output_format not in writers:
        _fail(
            f"unknown format {output_format!r}; choose one of {sorted(writers)}",
            ExitCode.INPUT_ERROR,
        )

    try:
        config = SyntheticExperimentConfig(
            scenario=chosen,
            n_scans=scans,
            n_points=points,
            seed=seed,
            noise_level=noise,
        )
    except ValidationError as exc:
        _fail(f"invalid configuration: {exc}", ExitCode.INPUT_ERROR)

    experiment = generate_experiment(config)
    try:
        written = writers[output_format](experiment, output_path, overwrite=overwrite)
    except (SyntheticWriteError, ArchiveError) as exc:
        code = (
            ExitCode.OUTPUT_EXISTS if "overwrite" in str(exc) else ExitCode.INPUT_ERROR
        )
        _fail(str(exc), code)

    if as_json:
        _echo_json(
            {
                "output": str(written),
                "scenario": chosen.value,
                "format": output_format,
                "seed": seed,
                "n_scans": len(experiment.scans),
                "synthetic": True,
                "note": SYNTHETIC_DISCLAIMER,
            }
        )
    else:
        typer.echo(f"wrote {written}")
        typer.echo(f"  scenario: {chosen.value}  seed: {seed}  scans: {scans}")
        typer.echo(f"  note: {SYNTHETIC_DISCLAIMER}")


def main() -> None:
    """Console-script entry point."""
    app()


if __name__ == "__main__":
    main()
