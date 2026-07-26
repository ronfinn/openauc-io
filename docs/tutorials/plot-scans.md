# Plot scans

**Goal:** draw radial scans and save a figure, including headless.

**Prerequisites:** [Installation](../getting-started/installation.md).

Runnable version:
[`examples/04_plot_scans.py`](https://github.com/ronfinn/openauc-io/blob/main/examples/04_plot_scans.py).

## Basic use

```python
import openauc
from openauc.plotting import plot_scans

experiment = openauc.load("examples/data/demo_experiment")
ax = plot_scans(experiment)
ax.figure.savefig("scans.png", dpi=150, bbox_inches="tight")
```

`plot_scans` returns a `matplotlib.axes.Axes` with one line per scan carrying
observations. The figure is reachable as `ax.figure`.

## A single scan

```python
from openauc.plotting import plot_scan

ax = plot_scan(experiment, "scan_001")
```

## Options

```python
ax = plot_scans(
    experiment,
    ax=None,               # draw on your own Axes instead
    scan_ids=["scan_001", "scan_003"],  # restrict and order
    title="Custom title",
    legend=True,
    label_elapsed=True,    # append 't = 600 s' to legend entries
    colormap="viridis",
    linewidth=1.0,
    marker=".",            # mark individual observations
)
```

## Passing your own Axes

Essential for subplot grids, overlays and interactive display:

```python
import matplotlib.pyplot as plt

fig, (left, right) = plt.subplots(1, 2, figsize=(12, 4))
plot_scans(first_experiment, ax=left, title="Run A")
plot_scans(second_experiment, ax=right, title="Run B")
fig.savefig("comparison.png")
plt.show()
```

## Headless operation

`openauc.plotting` **never uses pyplot**. Figures are built from
`matplotlib.figure.Figure` directly, so:

- no interactive backend is required — this works on CI and servers;
- nothing accumulates in pyplot's global figure registry, so long-running
  processes and test suites cannot leak figures;
- to get a window, create your own axes with pyplot and pass them in.

matplotlib is imported on the **first draw**, not at import time, so
`import openauc` stays fast for the ingestion and validation paths.

## What plotting does not do

- **No interpolation.** Each scan is drawn from its own stored vectors.
- **No resampling.** Point counts are exactly as stored.
- **No sorting.** Descending (inward) scans render as acquired.
- **No smoothing**, fitting, baseline correction or derived overlay.
- **No alignment onto a common radius grid.** In per-scan mode every scan keeps
  its own axis; the scans are simply overlaid on shared *display* axes.
- **Colour encodes display order only** — scans are coloured along a
  perceptually uniform colormap so a time series reads as a progression. It
  asserts nothing about the data.

Only the measured series are drawn. A plot contains no texts, patches or
collections beyond the lines and the axes furniture.

## Both radius modes

```python
shared = openauc.load("examples/data/demo_experiment")
plot_scans(shared)     # every line shares one radius axis

from openauc.synthetic import SyntheticExperimentConfig, generate_experiment
ragged = generate_experiment(
    SyntheticExperimentConfig(scenario="per-scan-radius", n_scans=5)
)
ax = plot_scans(ragged)
print([len(line.get_xdata()) for line in ax.lines])   # differing lengths
```

Scans carrying no observations are skipped.

## Labels

Axis labels report the **declared** units verbatim:

```text
radius (cm)
signal (AU)
```

An undeclared unit is labelled honestly rather than guessed:

```text
signal (unit not declared)
```

## Common failure modes

| Error | Cause | Fix |
|-------|-------|-----|
| `PlottingError: no observations for scan id(s)` | A `scan_ids` entry is not in the observations | Check `experiment.observations.scan_ids` |
| `PlottingError: no scan ... carries any observation` | Every selected scan is empty | Check `points_per_scan()` |
| No window appears | Expected — pyplot is not used | Save the figure, or pass your own axes |

## Next step

- [Plotting concepts](../concepts/plotting.md)
- [Recipes](../how-to/recipes.md) — batch plotting
