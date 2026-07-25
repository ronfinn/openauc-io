"""Ingestion layer: parser registry, manifest handling and the ``load`` API.

Importing this package registers the first-party parsers (generic long and wide
delimited) with the registry, so :func:`available_formats` and :func:`load`
reflect them immediately.
"""

from __future__ import annotations

# Importing the parser module triggers registration via the @register_parser
# decorators; keep this import for its side effect.
from openauc.formats import generic_delimited as _generic_delimited  # noqa: F401
from openauc.formats.aucx import (
    AUCX_FORMAT_ID,
    AUCX_FORMAT_VERSION,
    AUCX_SUFFIX,
    ArchiveValidationReport,
    AUCXExport,
    AUCXInfo,
    export_aucx,
    inspect_aucx,
    read_aucx,
    validate_aucx,
)
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
    register_archive_format,
    register_parser,
    registered_ids,
)

register_archive_format(
    FormatInfo(
        format_id=AUCX_FORMAT_ID,
        name="AUCX archive",
        suffixes=(AUCX_SUFFIX,),
        layouts=("zip-of-parts (JSON metadata + NumPy .npy arrays)",),
        limitations=(
            f"format version {AUCX_FORMAT_VERSION} only; archives are never "
            "migrated silently",
            "every checksum is verified before a model is built",
            "checksums establish integrity, not authenticity",
        ),
        doc_reference="docs/formats/aucx.md",
    )
)

__all__ = [
    "AUCX_FORMAT_ID",
    "AUCX_FORMAT_VERSION",
    "AUCX_SUFFIX",
    "AUCXExport",
    "AUCXInfo",
    "ArchiveValidationReport",
    "DetectionResult",
    "FormatInfo",
    "GenericManifest",
    "ParseResult",
    "Parser",
    "ResolvedSource",
    "Table",
    "available_formats",
    "detect_parser",
    "export_aucx",
    "get_parser",
    "inspect_aucx",
    "load",
    "load_manifest",
    "read_aucx",
    "register_archive_format",
    "register_parser",
    "registered_ids",
    "validate_aucx",
]
