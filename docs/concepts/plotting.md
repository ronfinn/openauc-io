# Plotting

`openauc.plotting` draws basic radial scan plots from the canonical model.

```python
import openauc
from openauc.plotting import plot_scans

experiment = openauc.load("path/to/experiment")
axes = plot_scans(experiment)
axes.figure.savefig("scans.png")
```

## A plot is a rendering, not an interpretation

Only the measured series are drawn. There is no fitting, smoothing, baseline
correction, derivative, envelope, meniscus marker or annotation of any derived
quantity — those are scientific interpretation and are out of scope. Axis labels
report the **declared** units verbatim, and an undeclared unit is labelled
`unit not declared` rather than guessed.

## Nothing is interpolated

Each scan is drawn from its own stored `(radius, signal)` vectors, **in stored
order**:

- **Shared axis** — every scan is drawn against the one shared radius axis.
- **Per-scan axis** — every scan keeps its own radius vector. Scans of differing
  lengths are simply overlaid on shared *display* axes; no scan is ever placed
  onto another scan's grid.

Order is never sorted, so a descending (inward) scan renders exactly as
acquired. Padding is excluded via the authoritative validity mask, and scans
carrying no observations are skipped.

This satisfies [ADR-0002](../decisions/ADR-0002-canonical-data-model.md), which
requires any operation placing per-scan data onto a common grid to be an
explicit, opt-in, recorded transformation. **This module performs no such
transformation**, so no regridding API is offered here. If one is ever added it
will be a separate, explicitly named call that records its interpolation choice
in provenance.

## No pyplot

Figures are built from `matplotlib.figure.Figure` directly. Consequences:

- plotting needs **no interactive backend** and works headless (CI, servers);
- nothing accumulates in pyplot's global figure registry, so long-running
  processes and test suites do not leak figures;
- to display interactively, create your own axes and pass them in.

```python
import matplotlib.pyplot as plt

fig, ax = plt.subplots()
plot_scans(experiment, ax=ax)
plt.show()
```

Passing `ax` also lets you overlay several experiments, or build subplot grids.

## Import cost

matplotlib is **not** imported by `import openauc`, nor by importing
`openauc.plotting` — it loads on the first actual draw. The ingestion,
validation and summary paths never pay for it. `openauc.api.plot_scans` resolves
lazily for the same reason.

## API

```python
plot_scans(experiment, *, ax=None, scan_ids=None, title=None, legend=True,
           label_elapsed=True, colormap="viridis", linewidth=1.0,
           marker=None) -> matplotlib.axes.Axes

plot_scan(experiment, scan_id, *, ax=None, ...) -> matplotlib.axes.Axes
```

- `scan_ids` restricts and orders the scans drawn; an unknown identifier raises
  `PlottingError`.
- `label_elapsed` appends each scan's elapsed time to its legend entry when the
  value is present, and falls back to the bare identifier when it is not.
- `colormap` colours scans by their order using a perceptually uniform
  colormap, so time progression reads as a progression. This is a display
  choice and asserts nothing about the data.
- `PlottingError` is raised when a requested scan is absent, or when no selected
  scan carries any observation to draw.

Plotting reads the observations directly, so an experiment whose scan metadata
and observations do not correspond is still plottable — inspection is exactly
when you need a picture. Scans without a matching metadata record are labelled
with their observation identifier.

## Not implemented

Multi-panel layouts, residual plots, time-series projections, cell/channel
faceting, interactive widgets and any analysis-derived overlay. Plot styling
beyond the options above is the caller's to apply to the returned axes.
