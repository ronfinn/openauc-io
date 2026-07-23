"""Core types and the parser interface for the ingestion layer.

A *parser plugin* identifies and loads a particular on-disk layout into the
canonical :class:`~openauc.models.AUCExperiment`. Plugins are registered with
the registry (see :mod:`openauc.formats.registry`) and selected either
explicitly, from a manifest, or by confidence-based detection.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from openauc.formats.manifest import GenericManifest
    from openauc.models import AUCExperiment

__all__ = [
    "DetectionResult",
    "FormatInfo",
    "ParseResult",
    "Parser",
    "ResolvedSource",
    "Table",
]


@dataclass(frozen=True)
class Table:
    """A delimited table read into memory as raw strings.

    Values are never coerced or reordered here; conversion and validation are
    the parser's responsibility, which keeps error reporting precise.
    """

    path: Path
    delimiter: str
    header: tuple[str, ...]
    rows: tuple[tuple[str, ...], ...]

    def has_columns(self, names: tuple[str, ...]) -> bool:
        """True if every name in ``names`` is present in the header."""
        header = set(self.header)
        return all(name in header for name in names)

    def column_index(self, name: str) -> int:
        """Index of ``name`` in the header, or -1 if absent."""
        try:
            return self.header.index(name)
        except ValueError:
            return -1


@dataclass(frozen=True)
class ResolvedSource:
    """The resolved on-disk locations for one experiment load."""

    base_dir: Path
    data_file: Path
    manifest_file: Path | None


@dataclass(frozen=True)
class DetectionResult:
    """The outcome of a parser's detection attempt.

    ``confidence`` is in the closed interval [0.0, 1.0].
    """

    parser_id: str
    confidence: float
    evidence: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class ParseResult:
    """A parsed experiment plus provenance breadcrumbs from the parser."""

    experiment: AUCExperiment
    warnings: tuple[str, ...] = ()
    assumptions: tuple[str, ...] = ()


@dataclass(frozen=True)
class FormatInfo:
    """Public description of a registered parser (for ``available_formats``)."""

    format_id: str
    name: str
    suffixes: tuple[str, ...]
    layouts: tuple[str, ...]
    limitations: tuple[str, ...]
    doc_reference: str


class Parser(ABC):
    """Abstract base class for a format parser plugin.

    Concrete subclasses set the class attributes below and implement
    :meth:`detect` and :meth:`parse`.
    """

    format_id: str
    name: str
    suffixes: tuple[str, ...]
    layouts: tuple[str, ...]
    limitations: tuple[str, ...]
    doc_reference: str

    @abstractmethod
    def detect(self, table: Table, manifest: GenericManifest | None) -> DetectionResult:
        """Report how confidently this parser can handle ``table``."""

    @abstractmethod
    def parse(
        self,
        table: Table,
        source: ResolvedSource,
        manifest: GenericManifest | None,
    ) -> ParseResult:
        """Parse ``table`` into an :class:`AUCExperiment` (without provenance)."""

    def info(self) -> FormatInfo:
        """Return the public :class:`FormatInfo` description of this parser."""
        return FormatInfo(
            format_id=self.format_id,
            name=self.name,
            suffixes=self.suffixes,
            layouts=self.layouts,
            limitations=self.limitations,
            doc_reference=self.doc_reference,
        )
