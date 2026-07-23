"""Parser registry: listing, lookup, detection, duplicate registration."""

from __future__ import annotations

from pathlib import Path

import pytest

from openauc.exceptions import UnsupportedFormatError
from openauc.formats.base import (
    DetectionResult,
    Parser,
    ParseResult,
    ResolvedSource,
    Table,
)
from openauc.formats.manifest import GenericManifest
from openauc.formats.registry import (
    available_formats,
    detect_parser,
    get_parser,
    register_parser,
    registered_ids,
)


def _table(header: tuple[str, ...]) -> Table:
    return Table(
        path=Path("scans.csv"),
        delimiter=",",
        header=header,
        rows=(("x",) * len(header),),
    )


def test_available_formats_lists_generic_parsers() -> None:
    ids = {info.format_id for info in available_formats()}
    assert {"generic-long", "generic-wide"} <= ids
    for info in available_formats():
        assert info.name
        assert info.suffixes
        assert info.doc_reference


def test_registered_ids_sorted() -> None:
    ids = registered_ids()
    assert list(ids) == sorted(ids)
    assert "generic-long" in ids


def test_get_parser_known() -> None:
    assert get_parser("generic-long").format_id == "generic-long"


def test_get_parser_unknown_raises() -> None:
    with pytest.raises(UnsupportedFormatError, match="unknown format"):
        get_parser("beckman-xla")


def test_detect_selects_long_for_long_header() -> None:
    parser = detect_parser(_table(("scan", "radius_cm", "signal")), None)
    assert parser.format_id == "generic-long"


def test_detect_unsupported_when_no_columns_match() -> None:
    with pytest.raises(UnsupportedFormatError, match="confident"):
        detect_parser(_table(("a", "b", "c")), None)


def test_register_duplicate_raises() -> None:
    class Dup(Parser):
        format_id = "generic-long"  # already registered
        name = "dup"
        suffixes = (".csv",)
        layouts = ("long",)
        limitations: tuple[str, ...] = ()
        doc_reference = "x"

        def detect(
            self, table: Table, manifest: GenericManifest | None
        ) -> DetectionResult:
            raise NotImplementedError

        def parse(
            self,
            table: Table,
            source: ResolvedSource,
            manifest: GenericManifest | None,
        ) -> ParseResult:
            raise NotImplementedError

    with pytest.raises(ValueError, match="already registered"):
        register_parser(Dup)
