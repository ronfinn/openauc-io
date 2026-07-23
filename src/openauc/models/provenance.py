"""Provenance representation (area F).

This is an in-memory record of how an experiment was obtained and which values
were supplied, converted, inferred, user-confirmed or left unknown. It is a
*representation* only: no parser is implemented in this phase, so provenance is
constructed by hand for synthetic experiments, and no checksum is computed here.
AUCX archive serialisation is deliberately out of scope for Phase 2.
"""

from __future__ import annotations

import re
from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator

__all__ = ["ImportProvenance"]

_SHA256_RE = re.compile(r"[0-9a-fA-F]{64}")


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
    sha256: str | None = None
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
