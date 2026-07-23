"""Ingestion layer: parser registry, manifest handling and the ``load`` API.

Importing this package registers the first-party parsers (generic long and wide
delimited) with the registry, so :func:`available_formats` and :func:`load`
reflect them immediately.
"""

from __future__ import annotations

# Importing the parser module triggers registration via the @register_parser
# decorators; keep this import for its side effect.
from openauc.formats import generic_delimited as _generic_delimited  # noqa: F401
from openauc.formats.base import (
    DetectionResult,
    FormatInfo,
    Parser,
    ParseResult,
    ResolvedSource,
    Table,
)
from openauc.formats.loader import load
from openauc.formats.manifest import GenericManifest, load_manifest
from openauc.formats.registry import (
    available_formats,
    detect_parser,
    get_parser,
    register_parser,
    registered_ids,
)

__all__ = [
    "DetectionResult",
    "FormatInfo",
    "GenericManifest",
    "ParseResult",
    "Parser",
    "ResolvedSource",
    "Table",
    "available_formats",
    "detect_parser",
    "get_parser",
    "load",
    "load_manifest",
    "register_parser",
    "registered_ids",
]
