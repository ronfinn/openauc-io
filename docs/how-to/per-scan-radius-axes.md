# Work with per-scan radius axes

**Goal:** handle experiments whose scans do **not** share one radius vector.

## Why this exists

Different acquisitions, instruments or export paths can produce different radial
grids. Forcing them onto a common grid would require interpolation, which alters
measured data. So the canonical model supports **both** regimes explicitly, and
which one is in use is an inspectable property rather than a guess.

```python
from openauc.models import RadiusAxisMode

experiment.observations.mode is RadiusAxisMode.SHARED  # one axis for all
experiment.observations.mode is RadiusAxisMode.PER_SCAN  # each scan its own
```

## How the mode is chosen on import

For generic-long input: if **every** scan has an identical radius vector — same
values, same order — shared-axis observations are built. Otherwise per-scan-axis
observations are built. Generic-wide is always shared, by construction.

You never select this; it follows from the data.

## Reading the data

```python
radius, signal = experiment.observations.scan_vectors("scan_002")
```

In shared mode every scan returns the same radius array; in per-scan mode each
returns its own, with padding removed via the authoritative validity mask.
Values and order are exactly as stored.

```python
for scan_id, radius, signal in experiment.observations.iter_scan_vectors():
    print(scan_id, len(radius), radius[0], radius[-1])

experiment.observations.points_per_scan()  # e.g. (300, 298, 300)
```

## How per-scan data is stored

Padded 2-D `(scan, point)` arrays plus a **boolean validity mask**. Shorter
scans are padded with `NaN` *and* `mask=False`. A value is a real observation
**if and only if** its mask entry is `True`.

Padding is never identified by testing for `NaN` — a measured signal could
itself legitimately be `NaN`. The mask is authoritative.

## What works unchanged

Validation, summaries, readiness, plotting and AUCX all handle both modes.
Plotting overlays ragged scans on shared *display* axes while each keeps its own
data:

```python
from openauc.plotting import plot_scans

ax = plot_scans(ragged_experiment)
print([len(line.get_xdata()) for line in ax.lines])  # differing lengths
```

## What refuses

**Generic-wide export**, because a wide table has one radius column:

```text
SyntheticWriteError: wide layout needs one shared radius axis, but this
experiment uses 'per_scan' axes. Writing it wide would require resampling onto
a common grid, which openauc never does; use write_generic_long or write_aucx
instead.
```

Use generic-long or AUCX — both represent per-scan axes natively, and AUCX
round-trips them exactly.

## Regridding

There is **no regridding API**. Per ADR-0002, any operation placing per-scan
data onto a common grid must be an explicit, opt-in transformation that records
its interpolation choice in provenance. No such operation exists today, and a
convenience keyword would be exactly the implicit side effect the decision
forbids.

If you need a common grid, do it deliberately in your own code, on arrays you
extracted with `scan_vectors()`, and record what you did.

## Empty scans

A scan may carry no observations at all. That is representable **only** in
per-scan mode:

```python
experiment.observations.points_per_scan()  # (300, 0, 300)
```

It produces an `empty_scan` warning and does not invalidate the experiment.
Plotting skips such scans.

## Next step

- [Canonical data model](../concepts/data-model.md)
- [Load generic-long data](../tutorials/load-generic-long.md)
