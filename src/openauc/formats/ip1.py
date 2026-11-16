"""Narrow reader for Beckman Coulter XL-I interference scan files (``.ip1``).

Supported scope is deliberately small and documented in ``docs/formats/ip1.md``.
Header semantics follow the manufacturer's *ProteomeLab XL-A/XL-I Instructions
For Use* (PN LXLAI-IM-10AB, February 2014). The two observation columns are
less explicitly specified than the header; reading them as radius and
interference signal is part of the narrow supported contract.

Nothing is interpolated, regridded, sorted, normalised or reconstructed. Every
recorded number is parsed straight from the text. Anything that does not match
the supported layout raises :class:`~openauc.exceptions.ParseError`.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

from openauc.exceptions import DataConflictError, ParseError, UnsupportedFormatError
from openauc.models import (
    AUCExperiment,
    ExperimentMetadata,
    ImportProvenance,
    Observations,
    OpticalSystem,
    Quantity,
    ScanMetadata,
    SourceChecksum,
    Unit,
)

__all__ = ["IP1_FORMAT_ID", "IP1_SUFFIX", "is_ip1_path", "read_ip1"]

IP1_FORMAT_ID = "ip1"
IP1_SUFFIX = ".ip1"

_SCAN_FILE_RE = re.compile(r"(\d+)\.(ip1)", re.IGNORECASE)
# Other XL-A/XL-I scan-file names (e.g. 00001.RA1, 00001.IP2): never read here.
_OTHER_SCAN_FILE_RE = re.compile(r"\d+\.[a-z]{2}\d", re.IGNORECASE)
_LINE1_RE = re.compile(r"cm/pixel:\s*([^,\s]+)\s*,(.*)", re.DOTALL)
_HEADER_TOKENS = 8
_LINE_SPLIT_RE = re.compile(r"\r\n|\n")


def is_ip1_path(path: Path) -> bool:
    """True if ``path`` is a file named like a supported interference scan."""
    return path.is_file() and _SCAN_FILE_RE.fullmatch(path.name) is not None


def read_ip1(path: str | Path) -> AUCExperiment:
    """Read one ``.ip1`` file, or a directory of them, into an experiment.

    Raises:
        ParseError: on any deviation from the supported layout.
        UnsupportedFormatError: if a directory holds other scan-file variants.
    """
    target = Path(path)
    if target.is_dir():
        files = _scan_files_in(target)
        experiment_id = target.resolve().name
    elif target.is_file():
        _require_ip1_name(target)
        files = [target]
        experiment_id = target.stem
    else:
        raise ParseError(f"path does not exist: {target}")

    scans: list[ScanMetadata] = []
    radii: list[np.ndarray] = []
    signals: list[np.ndarray] = []
    checksums: list[SourceChecksum] = []
    for index, file in enumerate(files):
        scan, radius, signal, checksum = _read_scan_file(file, index)
        scans.append(scan)
        radii.append(radius)
        signals.append(signal)
        checksums.append(checksum)

    scan_ids = [scan.scan_id for scan in scans]
    if len(set(scan_ids)) != len(scan_ids):
        raise DataConflictError(f"{target}: duplicate scan numbers in {scan_ids}")

    # Axis meaning is preserved, never reconciled: one shared axis only if every
    # scan recorded bit-identical radii, otherwise each scan keeps its own.
    if all(np.array_equal(radii[0], other) for other in radii[1:]):
        observations = Observations.from_shared_axis(
            radius=radii[0], signal=signals, scan_ids=scan_ids
        )
        axis = "shared"
    else:
        observations = Observations.from_per_scan(
            radii=radii, signals=signals, scan_ids=scan_ids
        )
        axis = "per-scan"

    from openauc import __version__

    provenance = ImportProvenance(
        source_path=str(target),
        source_filename=target.name,
        source_checksums=tuple(checksums),
        parser_name=IP1_FORMAT_ID,
        parser_version=__version__,
        imported_at=datetime.now(UTC),
        assumptions=(
            "narrow reader for Beckman XL-I interference scan files (.ip1); "
            "no manufacturer endorsement or general Beckman support is implied",
            "header layout per ProteomeLab XL-A/XL-I Instructions For Use, "
            "PN LXLAI-IM-10AB, February 2014",
            "temperature degC, rotor speed rpm and elapsed seconds are the units "
            "documented by the manual; the files themselves carry no units",
            "column 1 read as radius in cm and column 2 as interference signal; "
            "this column layout is part of the narrow supported contract",
            "signal unit not documented: recorded as unknown",
            "wavelength token (675 in public data; the manual states 665 nm) is "
            "preserved raw and not mapped",
            "no sample, timestamp or experiment type inferred",
            f"radius axis: {axis}",
        ),
    )
    return AUCExperiment(
        metadata=ExperimentMetadata(experiment_id=experiment_id),
        scans=tuple(scans),
        observations=observations,
        provenance=provenance,
    )


def _require_ip1_name(file: Path) -> None:
    if _SCAN_FILE_RE.fullmatch(file.name) is None:
        raise UnsupportedFormatError(
            f"{file.name}: not a supported scan file name "
            "(expected digits followed by .ip1, e.g. 00001.ip1)"
        )


def _scan_files_in(directory: Path) -> list[Path]:
    files = sorted(p for p in directory.iterdir() if p.is_file())
    supported = sorted(
        (p for p in files if _SCAN_FILE_RE.fullmatch(p.name)),
        key=lambda p: (int(p.stem), p.name),
    )
    unsupported = [
        p.name
        for p in files
        if _OTHER_SCAN_FILE_RE.fullmatch(p.name) and p not in supported
    ]
    if unsupported:
        raise UnsupportedFormatError(
            f"{directory}: unsupported XL-A/XL-I scan file variant(s) "
            f"{unsupported}; only .ip1 interference files are read"
        )
    if not supported:
        raise ParseError(f"{directory}: no .ip1 scan files found")
    return supported


def _read_scan_file(
    file: Path, index: int
) -> tuple[ScanMetadata, np.ndarray, np.ndarray, SourceChecksum]:
    raw = file.read_bytes()
    try:
        text = raw.decode("ascii")
    except UnicodeDecodeError as error:
        raise ParseError(f"{file.name}: not ASCII text ({error})") from None

    lines = _LINE_SPLIT_RE.split(text)
    # The file ends with a line terminator, possibly followed by blanks; one such
    # trailing whitespace-only fragment is accepted, any other blank line is not.
    if lines and not lines[-1].strip():
        lines.pop()
    if len(lines) < 3:
        raise ParseError(f"{file.name}: expected two header lines and data rows")

    cm_text, comment = _parse_line1(lines[0], file.name)
    tokens = lines[1].split()
    if len(tokens) != _HEADER_TOKENS:
        raise ParseError(
            f"{file.name}: header line 2 must have {_HEADER_TOKENS} tokens, "
            f"got {len(tokens)}"
        )
    cell = _parse_cell(tokens[1], file.name)
    temperature = _number(tokens[2], "temperature (token 3)", file.name)
    speed = _number(tokens[3], "rotor speed (token 4)", file.name, non_negative=True)
    seconds = _number(
        tokens[4], "total seconds (token 5)", file.name, non_negative=True
    )
    for position in (5, 6, 7):  # integrated omega^2 t, wavelength, replicates
        _number(tokens[position], f"token {position + 1}", file.name)

    radius, signal = _parse_rows(lines[2:], file.name)

    scan_number = file.stem
    scan = ScanMetadata(
        scan_id=scan_number,
        index=index,
        elapsed_time=Quantity.of(seconds, Unit.SECOND),
        cell=cell,
        optical_system=OpticalSystem.INTERFERENCE,
        rotor_speed=Quantity.of(speed, Unit.RPM),
        temperature=Quantity.of(temperature, Unit.DEGREE_CELSIUS),
        source_file=file.name,
        annotations=(
            f"ip1:cm_per_pixel={cm_text}",
            f"ip1:comment={comment}",
            f"ip1:header_tokens={json.dumps(tokens)}",
        ),
    )
    digest = hashlib.sha256(raw).hexdigest()
    checksum = SourceChecksum(
        role="scan_file", filename=file.name, value=digest, byte_size=len(raw)
    )
    return scan, radius, signal, checksum


def _parse_line1(line: str, name: str) -> tuple[str, str]:
    match = _LINE1_RE.fullmatch(line)
    if match is None:
        raise ParseError(f"{name}: line 1 must be 'cm/pixel: <value>, <comment>'")
    value_text, comment = match.group(1), match.group(2).strip()
    value = _number(value_text, "cm/pixel", name)
    if value <= 0:
        raise ParseError(f"{name}: cm/pixel must be positive, got {value_text!r}")
    return value_text, comment


def _parse_cell(token: str, name: str) -> str:
    if not token.isdigit() or int(token) < 1:
        raise ParseError(f"{name}: cell number (token 2) must be a positive integer")
    return str(int(token))


def _number(text: str, what: str, name: str, *, non_negative: bool = False) -> float:
    try:
        value = float(text)
    except ValueError:
        raise ParseError(f"{name}: {what} is not numeric: {text!r}") from None
    if not math.isfinite(value):
        raise ParseError(f"{name}: {what} is not finite: {text!r}")
    if non_negative and value < 0:
        raise ParseError(f"{name}: {what} must be non-negative: {text!r}")
    return value


def _parse_rows(rows: list[str], name: str) -> tuple[np.ndarray, np.ndarray]:
    radius: list[float] = []
    signal: list[float] = []
    for line_number, row in enumerate(rows, start=3):
        fields = row.split()
        if len(fields) != 2:
            raise ParseError(
                f"{name} (line {line_number}): expected 2 numeric columns, "
                f"got {len(fields)}"
            )
        radius.append(_number(fields[0], f"line {line_number} radius", name))
        signal.append(_number(fields[1], f"line {line_number} signal", name))
    return np.array(radius, dtype=float), np.array(signal, dtype=float)
