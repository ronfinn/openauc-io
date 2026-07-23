"""The public ``load`` entry point and source/delimiter resolution.

Resolves a directory or data-file path to a manifest and data file, reads the
delimited table deterministically, selects a parser (explicit, manifest-declared
or detected), parses into an :class:`~openauc.models.AUCExperiment`, and attaches
import provenance.
"""

from __future__ import annotations

import dataclasses
from datetime import UTC, datetime
from pathlib import Path

from openauc.exceptions import (
    AmbiguousFormatError,
    DataConflictError,
    ManifestError,
    ParseError,
)
from openauc.formats.base import Parser, ParseResult, ResolvedSource, Table
from openauc.formats.manifest import GenericManifest, load_manifest
from openauc.formats.registry import detect_parser, get_parser
from openauc.models import AUCExperiment, ImportProvenance

__all__ = ["load"]

_MANIFEST_NAMES = ("manifest.json", "manifest.yaml", "manifest.yml")
_MANIFEST_SUFFIXES = (".json", ".yaml", ".yml")


def load(
    path: str | Path,
    *,
    format: str | None = None,
    manifest: str | Path | None = None,
) -> AUCExperiment:
    """Load a generic delimited AUC experiment into an ``AUCExperiment``.

    Args:
        path: A directory containing a manifest and data file, a data-file path
            with an adjacent manifest, or a manifest-file path.
        format: Optional explicit format id (overrides detection and the
            manifest's declared format for parser selection).
        manifest: Optional explicit manifest-file path.

    Returns:
        A canonical :class:`AUCExperiment` with import provenance attached.
    """
    target = Path(path)
    explicit_manifest = Path(manifest) if manifest is not None else None
    if not target.exists():
        raise ParseError(f"path does not exist: {target}")

    base_dir, manifest_file, explicit_data = _resolve_layout(target, explicit_manifest)
    manifest_model = load_manifest(manifest_file)
    data_file = _resolve_data_file(base_dir, manifest_model, explicit_data)
    source = ResolvedSource(
        base_dir=base_dir, data_file=data_file, manifest_file=manifest_file
    )

    delimiter = _resolve_delimiter(data_file, manifest_model)
    table = _read_table(data_file, delimiter)

    parser, selection_warnings = _select_parser(format, manifest_model, table)
    result = parser.parse(table, source, manifest_model)
    return _with_provenance(result, parser, source, selection_warnings)


# --------------------------------------------------------------------------- #
# Source resolution
# --------------------------------------------------------------------------- #


def _resolve_layout(
    target: Path, explicit_manifest: Path | None
) -> tuple[Path, Path, Path | None]:
    """Return (base_dir, manifest_file, explicit_data_file_or_None)."""
    if target.is_dir():
        manifest_file = _find_manifest(target, explicit_manifest)
        if manifest_file is None:
            raise ManifestError(
                f"no manifest found in {target} "
                f"(expected one of {list(_MANIFEST_NAMES)})"
            )
        return target, manifest_file, None

    if explicit_manifest is None and target.suffix.lower() in _MANIFEST_SUFFIXES:
        return target.parent, target, None

    manifest_file = _find_manifest(target.parent, explicit_manifest)
    if manifest_file is None:
        raise ManifestError(
            f"no adjacent manifest found for {target.name} in {target.parent}"
        )
    return target.parent, manifest_file, target


def _find_manifest(base_dir: Path, explicit: Path | None) -> Path | None:
    if explicit is not None:
        if not explicit.is_file():
            raise ManifestError(f"manifest file not found: {explicit}")
        return explicit
    present = [
        base_dir / name for name in _MANIFEST_NAMES if (base_dir / name).is_file()
    ]
    json_present = [p for p in present if p.suffix == ".json"]
    yaml_present = [p for p in present if p.suffix in (".yaml", ".yml")]
    if json_present and yaml_present:
        raise AmbiguousFormatError(
            f"{base_dir} contains both a JSON and a YAML manifest; "
            "pass an explicit manifest to choose"
        )
    if len(present) > 1:
        raise AmbiguousFormatError(f"multiple manifests found in {base_dir}")
    return present[0] if present else None


def _resolve_data_file(
    base_dir: Path, manifest: GenericManifest, explicit_data: Path | None
) -> Path:
    declared = (base_dir / manifest.data_file).resolve()
    base_resolved = base_dir.resolve()
    if declared.parent != base_resolved and base_resolved not in declared.parents:
        raise ManifestError(
            f"data_file {manifest.data_file!r} resolves outside the experiment "
            f"directory {base_dir}"
        )
    if not declared.is_file():
        raise ParseError(f"declared data_file not found: {declared}")
    if explicit_data is not None and explicit_data.resolve() != declared:
        raise DataConflictError(
            f"supplied data file {explicit_data.name!r} does not match the "
            f"manifest's data_file {manifest.data_file!r}"
        )
    return declared


# --------------------------------------------------------------------------- #
# Delimiter detection and table reading
# --------------------------------------------------------------------------- #

_DELIMITERS = (",", "\t")
_SUFFIX_DELIMITER = {".csv": ",", ".tsv": "\t"}


def _delimiter_token(declared: str) -> str:
    token = declared.strip().lower()
    return {"comma": ",", "tab": "\t"}.get(token, declared)


def _resolve_delimiter(data_file: Path, manifest: GenericManifest) -> str:
    lines = _nonempty_lines(data_file)
    if not lines:
        raise ParseError(f"{data_file.name}: file is empty")
    declared = _delimiter_token(manifest.delimiter) if manifest.delimiter else None
    return _detect_delimiter(lines, data_file.suffix.lower(), declared, data_file)


def _detect_delimiter(
    lines: list[str], suffix: str, declared: str | None, data_file: Path
) -> str:
    viable = {d for d in _DELIMITERS if _is_consistent(lines, d)}
    if declared is not None:
        if declared not in viable:
            raise ParseError(
                f"{data_file.name}: declared delimiter does not yield a "
                "consistent table"
            )
        return declared
    if not viable:
        raise ParseError(
            f"{data_file.name}: could not determine a consistent delimiter"
        )
    if len(viable) == 1:
        return next(iter(viable))
    suffix_delimiter = _SUFFIX_DELIMITER.get(suffix)
    if suffix_delimiter is not None and suffix_delimiter in viable:
        return suffix_delimiter
    raise AmbiguousFormatError(
        f"{data_file.name}: delimiter is ambiguous between comma and tab"
    )


def _is_consistent(lines: list[str], delimiter: str) -> bool:
    header_count = len(lines[0].split(delimiter))
    if header_count < 2:
        return False
    return all(len(line.split(delimiter)) == header_count for line in lines)


def _nonempty_lines(data_file: Path) -> list[str]:
    text = data_file.read_text(encoding="utf-8")
    return [line for line in text.splitlines() if line.strip()]


def _read_table(data_file: Path, delimiter: str) -> Table:
    lines = _nonempty_lines(data_file)
    header = tuple(field.strip() for field in lines[0].split(delimiter))
    rows = tuple(tuple(line.split(delimiter)) for line in lines[1:])
    return Table(path=data_file, delimiter=delimiter, header=header, rows=rows)


# --------------------------------------------------------------------------- #
# Parser selection and provenance
# --------------------------------------------------------------------------- #


def _select_parser(
    explicit_format: str | None,
    manifest: GenericManifest,
    table: Table,
) -> tuple[Parser, tuple[str, ...]]:
    """Select a parser.

    Precedence: an explicit ``format=`` override, then the manifest's declared
    ``format``, then confidence-based detection (used when the manifest omits a
    format). A declared or overridden format goes straight to ``parse``, which
    produces precise structural errors if the file does not match.
    """
    if explicit_format is not None:
        return get_parser(explicit_format), ()
    if manifest.format:
        return get_parser(manifest.format), ()
    return detect_parser(table, manifest), ()


def _with_provenance(
    result: ParseResult,
    parser: Parser,
    source: ResolvedSource,
    selection_warnings: tuple[str, ...],
) -> AUCExperiment:
    from openauc import __version__

    manifest_name = (
        source.manifest_file.name if source.manifest_file is not None else "(none)"
    )
    assumptions = (
        *result.assumptions,
        f"manifest: {manifest_name}",
        f"data_file: {source.data_file.name}",
    )
    provenance = ImportProvenance(
        source_path=str(source.data_file),
        source_filename=source.data_file.name,
        sha256=None,  # checksum computation is deferred to Phase 6 (ADR-0003)
        parser_name=parser.format_id,
        parser_version=__version__,
        imported_at=datetime.now(UTC),
        warnings=(*selection_warnings, *result.warnings),
        assumptions=assumptions,
    )
    return dataclasses.replace(result.experiment, provenance=provenance)
