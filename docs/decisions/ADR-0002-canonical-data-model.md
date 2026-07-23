# ADR-0002 — Canonical in-memory AUC data model

- **Status:** Proposed
- **Date:** 2026-07-23
- **Deciders:** Ron Finn
- **Related:** ADR-0001, ADR-0003, ADR-0004; development-log/0001

## Context

Every import path (generic CSV/TSV, manifests, and later AUCX and instrument
formats) must converge on a single canonical in-memory representation of an AUC
experiment. Validation, summaries, plotting, and archival all operate on that
representation, so its shape determines what the rest of the library can express.

An AUC experiment is, at heart, a set of **radial scans**. Each scan records a
signal (absorbance, or interference fringes, or fluorescence) as a function of
radial position, acquired at a given time, rotor speed, temperature, and
wavelength, within a cell/channel under a defined optical system. A scan set is
naturally two-dimensional: `signal(scan, radius)`, with per-scan scalar
coordinates.

A critical domain fact constrains the model: **scans in a set do not always share
an identical radius axis.** Different acquisitions, instruments, or export paths
can produce different radial grids. Forcing a common grid would require
interpolation or resampling, which alters measured data — explicitly forbidden by
the project's scientific boundaries.

## Decision under consideration

Represent the canonical model as a **two-layer structure**:

1. **Metadata layer — pydantic v2 models.** Experiment, sample, buffer, rotor,
   instrument, cell/channel, and optical-system metadata are pydantic models.
   This gives strict validation, precise error locations, and clean
   JSON/dict (de)serialisation. Required metadata is required: **missing values
   fail validation loudly; nothing is silently inferred.**

2. **Numeric layer — xarray.** Scan signal data is held in `xarray` structures
   (`DataArray`/`Dataset`) with a `radius` dimension and a `scan` dimension, and
   per-scan coordinates for time, rotor speed, temperature, and wavelength.
   `numpy` provides the underlying arrays.

**Radius-axis handling (the load-bearing decision):** the model supports **both**
representations explicitly and never interpolates silently:

- **Shared-axis form** — when every scan genuinely shares one radius grid, the
  scan set is stored as a dense `(scan × radius)` array on that single axis.
- **Per-scan-axis form** — when scans differ, each scan retains its own radius
  array; the set is stored as a collection of scans rather than forced onto a
  common grid.

Whether a set is shared-axis or per-scan-axis is an explicit, inspectable
property of the model, not a heuristic guess. Any future operation that *does*
place per-scan data onto a common grid (e.g. for a specific plot) must be an
explicit, opt-in transformation with its interpolation choice recorded — never an
implicit side effect of import.

## Alternatives considered

- **Require a shared radius axis for all scan sets in v1.** Simpler and more
  compact, but rejects legitimate ragged data and narrows real-world support.
  Rejected as too restrictive for a faithful-archive tool.
- **Always interpolate onto a common grid at import.** Rejected outright: it
  silently modifies measured data, violating the no-silent-inference boundary.
- **Pure pandas DataFrames for everything.** Rejected: pandas is retained for
  *tabular import only*; it is awkward for labelled N-D scientific arrays and
  per-scan coordinates, which xarray models directly.
- **Pure numpy arrays with side-car metadata dicts.** Rejected: loses labelled
  axes and coordinate alignment, and pushes validation into ad-hoc code that
  pydantic does properly.
- **A single monolithic pydantic model containing raw arrays.** Rejected:
  pydantic is excellent for metadata but a poor container for large numeric
  arrays and coordinate-aware operations; xarray is the right tool there.

## Consequences

**Positive**

- Faithful to acquired data: no resampling, both axis regimes representable.
- Strong, localised validation of metadata via pydantic v2.
- Coordinate-aware numeric operations, slicing, and plotting via xarray.
- Clean serialisation boundary: metadata ↔ JSON/YAML; numeric ↔ arrays, which
  aligns naturally with the AUCX zip-of-parts container (ADR-0003).

**Negative / costs**

- Two representations for a scan set (shared vs per-scan) mean downstream code
  (summaries, plotting, export) must handle both, or explicitly narrow to one.
- A metadata layer plus a numeric layer is more moving parts than a single
  object; the seam between pydantic and xarray must be defined carefully.
- Guarding against accidental silent alignment requires discipline and tests.

## Unresolved questions

- **Optical systems in v1:** absorbance only, or absorbance + interference (and a
  fluorescence stub)? (development-log Q4.) This affects how signal type and its
  units are modelled.
- **Canonical units:** which units are mandatory and declared (radius cm, rpm,
  temperature K vs °C, wavelength nm), and does the model reject rather than
  convert on mismatch? (development-log Q2.)
- **Minimum required metadata set** for a valid experiment. (development-log Q3.)
- Exact typing of the scan-set container (a single class parameterised by axis
  regime vs two classes) — to be settled during Phase 2 implementation.

## References

- P. Schuck et al., published literature on AUC data organisation and the
  radius/scan structure of sedimentation-velocity data (cited as background,
  not as an implementation source).
- xarray documentation — data model, coordinates, and alignment semantics.
- pydantic v2 documentation — strict validation and serialisation.
