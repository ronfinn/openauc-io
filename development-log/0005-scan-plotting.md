# Development Log 0005 — Basic scan plotting (Phase 5)

- **Date:** 2026-07-25
- **Branch:** `feat/validation-and-summaries` (continuous build mode; Phase 5
  developed on the Phase 4 branch at the maintainer's instruction)
- **Status:** Phase 5 complete. Basic matplotlib scan plots. No analysis, no
  regridding.
- **Author:** Ron Finn

## 1. Objective

Draw basic radial scan plots from the canonical model, handling both radius-axis
modes, without interpolating, resampling, reordering or interpreting anything.

## 2. Accepted decisions

**No `pyplot`.** Figures are constructed from `matplotlib.figure.Figure`
directly. Consequences: no interactive backend is required (the developer
machine defaults to `macosx`, CI has no display at all), nothing accumulates in
pyplot's global figure registry, and a long-running process or test suite cannot
leak figures. Callers wanting interactive display create their own axes with
pyplot and pass them via `ax=`. This is the standard library-side choice and it
removed backend handling from the problem entirely.

**No regridding, and no regridding API.** ADR-0002 requires any operation that
places per-scan data onto a common grid to be an explicit, opt-in transformation
with its interpolation choice recorded. Rather than build a half-measure, Phase
5 offers none: ragged scans are overlaid on shared *display* axes while each
keeps its own data. The constraint is therefore satisfied by construction, and
`docs/concepts/plotting.md` states that a future regridding call must be
separately named and record its choice in provenance.

**matplotlib is imported on first draw, not at import time.** It costs ~213 ms
on top of a ~518 ms `import openauc`. The top-level package does not import
plotting; `openauc.plotting` itself imports matplotlib only inside the functions
that need it; and `openauc.api` re-exports `plot_scans`/`plot_scan` through a
PEP 562 module `__getattr__`, with a `TYPE_CHECKING` import so type checkers
still see real signatures. The ingestion, validation and summary paths never pay
for matplotlib.

**Plotting reads the observations, not the scan metadata.** An experiment whose
scan metadata and observations do not correspond is exactly when a picture is
most useful, so plotting does not require structural validity. Metadata is
matched by identifier to enrich legend labels; an observation scan with no
matching record is labelled with its identifier.

**Colour encodes order, nothing else.** Scans are coloured along a perceptually
uniform colormap (`viridis`) by their stored order, so a time series reads as a
progression. This is a display choice and asserts nothing about the data.

## 3. Implementation

New package `src/openauc/plotting/`:

| Module | Contents |
|--------|----------|
| `__init__.py` | public facade: `plot_scans`, `plot_scan`, `DEFAULT_COLORMAP` |
| `scans.py` | rendering, label construction, selection and colour assignment |

```python
plot_scans(experiment, *, ax=None, scan_ids=None, title=None, legend=True,
           label_elapsed=True, colormap="viridis", linewidth=1.0,
           marker=None) -> Axes
plot_scan(experiment, scan_id, *, ax=None, ...) -> Axes
```

Behaviour: one line per scan with observations; scans carrying none are skipped;
axis labels report declared units verbatim and label an undeclared unit
`unit not declared`; the title defaults to the experiment identifier and name;
legend entries carry the elapsed time when present and fall back to the bare
identifier when not.

Supporting additions:

- `Observations.scan_vectors(scan_id)` → `(radius, signal)` with padding removed
  via the authoritative mask, values and order exactly as stored. Raises
  `KeyError` for an unknown identifier, matching the lookup precedent already
  set by `ReadinessAssessment.for_analysis`.
- `Observations.iter_scan_vectors()` → `(scan_id, radius, signal)` per scan.
- `PlottingError(OpenAUCError)` — raised for an absent requested scan, or when
  no selected scan has anything to draw.

`scan_vectors` is the accessor plotting needed; it also stops downstream code
reaching into `observations.dataset`, which is how `models/checks.py` currently
gets per-scan radius vectors. Converting that call site is a candidate tidy-up,
not done here to keep the diff to one capability.

## 4. Tests

47 new tests across three modules:

- `tests/unit/test_scan_vectors.py` (7) — exactness, masking, stored order,
  dtype/shape agreement with `points_per_scan()`, `KeyError`.
- `tests/unit/test_plotting.py` (28) — data fidelity against the source vectors,
  ragged per-scan axes staying distinct, descending order preserved, standalone
  figure construction, axes reuse, headless `savefig`, unit labelling including
  the undeclared case, titles, legends, elapsed labelling, selection and
  ordering, colouring, line options, both error paths, and an assertion that a
  plot adds no texts, patches or collections.
- `tests/integration/test_plotting_imported.py` (12) — the same over
  `openauc.load` for long/wide CSV/TSV, ragged imports, determinism across
  reloads, and that plotting does not mutate the experiment.

The fidelity tests are the load-bearing ones: they compare plotted `xdata`/
`ydata` against `scan_vectors()` element by element, so any future interpolation
or sorting would fail immediately.

## 5. Known limitations

- Single-panel overlay only. No subplot grids, faceting by cell/channel,
  residual panels or time-series projections.
- No regridding of per-scan axes onto a common grid (deliberate, see above).
- No styling beyond the exposed options; callers style the returned axes.
- matplotlib's own deprecations are not shielded — the colormap name is passed
  through to `matplotlib.colormaps`.
- `plot_scans` is O(scans); no downsampling for very large scan sets.

## 6. Rejected alternatives

- **Using `pyplot.subplots()`.** Rejected: pulls in a backend (interactive on
  the dev machine, absent in CI) and leaks figures into a global registry.
- **Offering `plot_scans(..., regrid="linear")`.** Rejected: ADR-0002 makes
  regridding an explicit recorded transformation, which needs provenance
  support; a convenience keyword would be exactly the implicit side effect the
  ADR forbids.
- **Requiring structural validity before plotting.** Rejected: inspection is
  most valuable precisely when something is wrong.
- **Returning a `Figure` instead of `Axes`.** Rejected: returning `Axes`
  composes with caller-supplied subplots, and the figure remains reachable as
  `axes.figure`.
- **Eagerly importing matplotlib in `api.py`.** Rejected on import cost;
  resolved with PEP 562 lazy attribute access instead.

## 7. Next steps

Phase 6 (AUCX): zip-of-parts export and reload with checksums and provenance,
resolving Q1 (in-archive data encoding) and Q5 (provenance schema, SHA-256
confirmation). That phase finally computes `ImportProvenance.sha256`, which
currently makes `source_checksum_absent` fire on every import by design.
