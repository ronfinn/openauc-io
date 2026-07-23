"""Public API surface for openauc.

Import from here (or the top-level ``openauc`` package) for the stable public
contract. Internal module paths are not part of that contract and may change
between releases without notice.

The surface is intentionally minimal in Phase 1: it exposes the version and the
exception hierarchy. Domain functions are added to this facade as later phases
land.
"""

from __future__ import annotations

from openauc import __version__
from openauc.exceptions import (
    ArchiveError,
    FormatError,
    OpenAUCError,
    ValidationError,
)

__all__ = [
    "ArchiveError",
    "FormatError",
    "OpenAUCError",
    "ValidationError",
    "__version__",
]
