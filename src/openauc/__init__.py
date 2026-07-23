"""openauc — import, validate, standardise, visualise and archive AUC data.

This is the Phase 1 package scaffold. The canonical data model, parsers,
validation, plotting and AUCX archival are introduced in later phases; see
``development-log/0001-project-foundation.md`` and ``docs/decisions/``.
"""

from __future__ import annotations

from openauc.formats import available_formats, load

__all__ = ["__version__", "available_formats", "load"]

__version__ = "0.1.0.dev0"
