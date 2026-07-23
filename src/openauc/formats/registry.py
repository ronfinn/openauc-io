"""Parser plugin registry and confidence-based selection (ADR-0004).

First-party parsers register themselves with the :func:`register_parser`
decorator. Selection is either explicit (by format identifier), driven by a
manifest's declared format, or resolved by detection. Detection never guesses
when the outcome is ambiguous.
"""

from __future__ import annotations

from openauc.exceptions import AmbiguousFormatError, UnsupportedFormatError
from openauc.formats.base import DetectionResult, FormatInfo, Parser, Table
from openauc.formats.manifest import GenericManifest

__all__ = [
    "MINIMUM_CONFIDENCE",
    "TIE_MARGIN",
    "available_formats",
    "detect_parser",
    "get_parser",
    "register_parser",
    "registered_ids",
]

# A parser must clear this to be selectable by detection.
MINIMUM_CONFIDENCE = 0.5
# Two viable parsers within this margin are treated as an ambiguous tie.
TIE_MARGIN = 0.15

_REGISTRY: dict[str, Parser] = {}


def register_parser(cls: type[Parser]) -> type[Parser]:
    """Class decorator that registers a parser instance by its ``format_id``."""
    instance = cls()
    format_id = instance.format_id
    if format_id in _REGISTRY:
        raise ValueError(f"a parser is already registered for {format_id!r}")
    _REGISTRY[format_id] = instance
    return cls


def get_parser(format_id: str) -> Parser:
    """Return the parser registered under ``format_id``.

    Raises:
        UnsupportedFormatError: if no parser is registered under that id.
    """
    try:
        return _REGISTRY[format_id]
    except KeyError:
        available = ", ".join(sorted(_REGISTRY)) or "(none)"
        raise UnsupportedFormatError(
            f"unknown format {format_id!r}; registered formats: {available}"
        ) from None


def registered_ids() -> tuple[str, ...]:
    """All registered format identifiers, sorted."""
    return tuple(sorted(_REGISTRY))


def available_formats() -> tuple[FormatInfo, ...]:
    """Public descriptions of all registered parsers, sorted by id."""
    return tuple(_REGISTRY[key].info() for key in sorted(_REGISTRY))


def detect_parser(table: Table, manifest: GenericManifest | None) -> Parser:
    """Select a parser by detection confidence.

    Raises:
        UnsupportedFormatError: if no parser clears ``MINIMUM_CONFIDENCE``.
        AmbiguousFormatError: if two parsers are within ``TIE_MARGIN``.
    """
    if not _REGISTRY:
        raise UnsupportedFormatError("no parsers are registered")

    results: list[tuple[Parser, DetectionResult]] = [
        (parser, parser.detect(table, manifest)) for parser in _REGISTRY.values()
    ]
    results.sort(key=lambda item: item[1].confidence, reverse=True)

    best_parser, best = results[0]
    if best.confidence < MINIMUM_CONFIDENCE:
        detail = "; ".join(f"{p.format_id}={r.confidence:.2f}" for p, r in results)
        raise UnsupportedFormatError(
            f"no parser is confident enough to read {table.path.name} "
            f"(threshold {MINIMUM_CONFIDENCE:.2f}); scores: {detail}"
        )

    if len(results) > 1:
        runner_parser, runner = results[1]
        if (
            runner.confidence >= MINIMUM_CONFIDENCE
            and best.confidence - runner.confidence < TIE_MARGIN
        ):
            raise AmbiguousFormatError(
                f"cannot choose between {best_parser.format_id!r} "
                f"({best.confidence:.2f}) and {runner_parser.format_id!r} "
                f"({runner.confidence:.2f}) for {table.path.name}; "
                "supply an explicit format or a manifest"
            )

    return best_parser
