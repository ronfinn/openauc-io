"""Basic matplotlib plots of the canonical model.

Importing this subpackage pulls in matplotlib, which is why the top-level
``openauc`` package does not import it eagerly — ``import openauc`` stays light
for the ingestion, validation and summary paths. Import plotting explicitly:

    from openauc.plotting import plot_scans

Plots render what is stored: no interpolation, resampling, sorting, smoothing,
fitting or derived quantity. See ``docs/concepts/plotting.md``.
"""

from __future__ import annotations

from openauc.plotting.scans import DEFAULT_COLORMAP, plot_scan, plot_scans

__all__ = ["DEFAULT_COLORMAP", "plot_scan", "plot_scans"]
