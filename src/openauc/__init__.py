"""openauc — import, validate, standardise, visualise and archive AUC data.

Implemented: the canonical in-memory data model, generic CSV/TSV ingestion via
:func:`openauc.load`, tiered structural validation, analysis-readiness reporting
and structured experiment summaries.

Not implemented: plotting, AUCX archival, vendor/instrument format readers, unit
conversion, and any form of scientific analysis or quality control. See
``development-log/`` and ``docs/decisions/``.
"""

from __future__ import annotations

from openauc.formats import available_formats, load

__all__ = ["__version__", "available_formats", "load"]

__version__ = "0.1.0.dev0"
