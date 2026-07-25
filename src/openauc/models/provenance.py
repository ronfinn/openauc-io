"""Provenance representation (area F).

This is an in-memory record of how an experiment was obtained and which values
were supplied, converted, inferred, user-confirmed or left unknown. It is
populated by :func:`openauc.load` for imported experiments and may be
constructed by hand for synthetic ones.

No checksum is computed here: ``sha256`` is validated when supplied but is left
``None`` on import, because checksum computation is deferred to the AUCX phase
(ADR-0003). AUCX archive serialisation of provenance is likewise out of scope.
"""

from __future__ import annotations

import re
from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator

__all__ = ["ImportProvenance", "SourceChecksum"]

_SHA256_RE = re.compile(r"[0-9a-fA-F]{64}")


class SourceChecksum(BaseModel):
    """A checksum of one source file an experiment was read from.

    An import can draw on more than one file — a manifest and a data file, for
    instance — and each is recorded separately rather than collapsed into a
    single field. ``role`` names what the file was to the import (``manifest``,
    ``data_file``), not what it contains.

    A checksum establishes **integrity** — that the bytes are unchanged since
    they were read. It says nothing about authenticity or origin.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    role: str
    filename: str
    algorithm: str = "sha256"
    value: str
    byte_size: int | None = None

    @field_validator("value")
    @classmethod
    def _validate_digest(cls, value: str) -> str:
        if not _SHA256_RE.fullmatch(value):
            raise ValueError("checksum value must be exactly 64 hexadecimal characters")
        return value.lower()

    @field_validator("role", "filename")
    @classmethod
    def _non_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("role and filename must be non-empty strings")
        return value


class ImportProvenance(BaseModel):
    """Record of an experiment's origin and per-category value provenance.

    The value-category tuples (``supplied_values`` etc.) hold references — for
    example dotted field names — to the values in each provenance category. They
    complement the per-value :class:`~openauc.models.metadata.Quantity`
    ``provenance`` tag, giving an experiment-level audit list.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    source_path: str | None = None
    source_filename: str | None = None
    #: Digest of the primary source (the data file). ``source_checksums`` carries
    #: every source individually; this field remains for the common single-file
    #: case and always mirrors the ``data_file`` entry when one exists.
    sha256: str | None = None
    source_checksums: tuple[SourceChecksum, ...] = ()
    parser_name: str | None = None
    parser_version: str | None = None
    imported_at: datetime | None = None
    transformations: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    assumptions: tuple[str, ...] = ()
    supplied_values: tuple[str, ...] = ()
    converted_values: tuple[str, ...] = ()
    inferred_values: tuple[str, ...] = ()
    user_confirmed_values: tuple[str, ...] = ()
    unknown_values: tuple[str, ...] = ()

    @field_validator("sha256")
    @classmethod
    def _validate_sha256(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not _SHA256_RE.fullmatch(value):
            raise ValueError("sha256 must be exactly 64 hexadecimal characters")
        return value.lower()
