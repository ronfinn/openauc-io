# ADR-0002 — Canonical in-memory AUC data model

- **Status:** Accepted (refined by the Phase 2 and Phase 4 amendments below)
- **Date:** 2026-07-23 (proposed); amended 2026-07-23 (Phase 2) and 2026-07-25
  (Phase 4)
- **Deciders:** Ron Finn
- **Related:** ADR-0001, ADR-0003, ADR-0004; development-log/0001;
  development-log/0002; development-log/0004

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

---

## Amendment — Phase 2 implementation (2026-07-23)

The following previously-open points are now **accepted** and implemented. Where
the implementation refined the original wording, the refinement is recorded
here.

**Optical systems (resolves the "optical systems in v1" question).** The model
represents five optical-system values: `absorbance`, `interference`,
`fluorescence`, `intensity`, `unknown`. Representation is explicitly **not** a
claim that import or scientific interpretation is implemented for each system.

**Canonical units and unit behaviour (resolves the "canonical units"
question).** Canonical units are fixed (radius cm; time s; speed rpm; temperature
°C; wavelength nm; sedimentation coefficient s; diffusion coefficient cm²/s;
absorbance AU; interference fringes; fluorescence/intensity instrument or
calibrated units). The model **retains** declared units and never infers or
silently converts. Unknown units are represented explicitly (`Unit.UNKNOWN`);
open-ended units (e.g. concentration) use `Unit.OTHER` with the verbatim text in
`Quantity.unit_label`. No unit library (Pint) is added in this phase; any future
adoption requires a further amendment.

**Missing/unknown/not-applicable.** These are modelled distinctly via
`Quantity.status` (`PRESENT`/`MISSING`/`UNKNOWN`/`NOT_APPLICABLE`); unknown
scientific values are never replaced by defaults. Per-value provenance is carried
via `Quantity.provenance`.

**Radius-axis representation (settles the open "scan-set container" question).**
A single `Observations` class supports both modes with an explicit
`RadiusAxisMode`. Per-scan axes use **padded 2-D `(scan, point)` arrays with an
authoritative boolean validity mask**; a value is a real observation iff its mask
entry is `True`, and padding (`NaN`) is never presented as measured data. No
interpolation or resampling occurs. Consequence: a single `signal_unit` is
carried per `Observations` set in this phase (heterogeneous per-scan signal units
are a documented limitation), while each scan retains its own `optical_system`.

**Container type.** `AUCExperiment` is a **frozen dataclass** composing the
pydantic metadata models with the xarray-backed `Observations`, rather than a
pydantic model, so the array layer is not forced through pydantic serialisation.
It exposes `summary()`, `validate_structure()`, and `to_dict()`/`from_dict()`.

**Validation placement.** Data-model (structural) validation lives in
`openauc/models/validation.py` for this phase. The top-level `validation/`
subpackage anticipated in ADR-0001 is reserved for later cross-cutting or
scientific validation. Structural validation is representational only and makes
no scientific-suitability judgement.

**Provenance timing.** The in-memory provenance representation
(`ImportProvenance`) is implemented now (usable with hand-built synthetic
experiments); AUCX archive serialisation of provenance remains Phase 6
(ADR-0003).

---

## Amendment — Phase 4: validation tiers and the minimum metadata set (2026-07-25)

This amendment resolves **development-log Q3** — "what must be present for
structural validation to pass?" — and records the tier model that answers it.

### Four questions, not one

Validation is **tiered**. `ValidationTier` names four independent questions:
`ARCHIVAL` (can it be stored and returned unambiguously?), `STRUCTURAL` (is it
internally consistent and inspectable?), and `SV_READINESS` / `SE_READINESS` (is
the metadata a future workflow needs present?). Each finding names the tier(s)
it speaks to and the tier(s) it blocks.

A fifth question — scientific validity or suitability — is **not a tier and is
never answered**. It is represented permanently as
`AnalysisKind.SCIENTIFIC_SUITABILITY` with status `ReadinessStatus.NOT_ASSESSED`,
a constant that is never derived from any finding.

### Four categories, three of them in scope

1. **Construction invariants** — raise at construction; an invalid object cannot
   exist. Unchanged from Phase 2.
2. **Structural validation** — cross-object consistency; reported, not raised.
3. **Analysis-readiness assessment** — metadata presence; reported.
4. **Scientific quality control** — out of scope, permanently.

### Resolution of Q3

**The minimum for a valid experiment is exactly what construction already
guarantees, plus unambiguous keying and internal consistency. No metadata field
is added as a requirement.**

`ARCHIVAL` blocks only on duplicate scan identifiers, duplicate sample
identifiers, a scan-count mismatch, and a scan-identifier/ordering mismatch.
`STRUCTURAL` blocks only on no scans, non-positive radial positions, and a
well-defined optical-system/signal-unit contradiction. That is the complete
blocking set.

This is deliberately permissive. A historical dataset carrying nothing but an
identifier, a radius vector and a signal vector is archivable and structurally
valid. Its sparse metadata is reported explicitly as warnings and informational
findings — never inferred, never defaulted, and never fatal.

### Reconciliation with "missing required metadata must fail loudly"

The original ADR text and development-log 0001 §6 state that *required* metadata
must fail validation loudly and that nothing is silently inferred. That boundary
is **upheld**, on the reading that "required" means the construction-invariant
set — which does fail loudly, by raising, at construction. Metadata that is
merely *conventionally desirable* for an analysis was never in that set, and
adding it would make faithful archival of historical data impossible, defeating
the project's purpose. Absence is reported explicitly rather than inferred, so
the no-silent-inference boundary is untouched.

### Severity policy

`ERROR` may block `ARCHIVAL` or `STRUCTURAL` and is the only severity affecting
`ValidationReport.is_valid`; `WARNING` never blocks either and may block a
readiness tier; `INFO` blocks nothing. **Readiness findings never carry
`ERROR`.** This rule is what prevents "structurally valid", "analysis ready" and
"scientifically valid" from collapsing into one another, and it preserves the
existing meaning of `validate_structure().is_valid` exactly.

### Determinism

Checks execute in the fixed order of a registry; affected scan identifiers are
sorted; a condition affecting many scans yields one aggregated finding rather
than one per scan. Equivalent experiments produce equal reports. No machine
learning, heuristics or scientific interpretation are involved anywhere.

### Placement and API

Validation, checks, readiness and summaries live under `models/` (see the
ADR-0001 Phase 4 amendment); the top-level `validation/` package remains
reserved for future scientific quality control. `AUCExperiment` gains
`validate()`, `summary_data()` and `assess_readiness()`; `validate_structure()`
and `summary()` are preserved unchanged in meaning, with `summary()` now
rendering the structured `ExperimentSummary`.

### Deferred

Two model-level limitations are recorded, not addressed: there is **no
sample-to-scan linkage** (`ScanMetadata` carries no `sample_id`), so sample
metadata can only be assessed experiment-wide; and an `Observations` set still
carries a **single signal unit**, which is why more than one declared optical
system in one set is reported as an anomaly.
