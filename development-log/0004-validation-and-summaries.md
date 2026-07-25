# Development Log 0004 — Validation tiers and scan summaries (Phase 4)

- **Date:** 2026-07-25
- **Branch:** `feat/validation-and-summaries` (based on `main` at `7536b9c`,
  the Phase 3 merge)
- **Status:** Phase 4 complete. Structural validation, analysis-readiness
  reporting and structured summaries. No scientific analysis or quality control.
- **Author:** Ron Finn

## 1. Objective

Give the library a clear, explainable validation boundary and richer structural
summaries, for both imported and hand-built experiments — and, in doing so,
resolve open question **Q3** (the minimum metadata for structural validation to
pass) without making faithful archival of sparse historical data impossible.

## 2. Accepted validation tiers

Validation asks four independent questions, and refuses a fifth.

| Tier | `ValidationTier` | Question |
|------|------------------|----------|
| A | `ARCHIVAL` | Can it be stored and returned unchanged and unambiguously? |
| B | `STRUCTURAL` | Are metadata, scans and observations internally consistent? |
| C | `SV_READINESS` | Is the metadata a velocity workflow needs present? |
| D | `SE_READINESS` | Is the metadata an equilibrium workflow needs present? |

Scientific suitability is **not a tier**. It is represented as
`AnalysisKind.SCIENTIFIC_SUITABILITY` with a constant status of
`ReadinessStatus.NOT_ASSESSED`, present in every assessment. Making it a
machine-readable entry rather than a prose disclaimer means a programmatic
consumer cannot omit it.

`ReadinessStatus` is `POTENTIALLY_READY` / `BLOCKED` / `NOT_APPLICABLE` /
`NOT_ASSESSED`. Nothing in the library describes an experiment as "ready",
"scientifically valid" or "suitable for analysis".

The four categories of check named in the phase brief map onto the code as:
construction invariants (raise, unchanged from Phase 2), structural validation
(tiers A+B), readiness assessment (tiers C+D), and scientific quality control
(out of scope, permanently).

## 3. Minimum metadata decision (resolves Q3)

**The minimum is exactly what construction already guarantees, plus unambiguous
keying and internal consistency. No metadata field was added as a requirement.**

- **ARCHIVAL blocks on:** `duplicate_scan_id`, `duplicate_sample_id`,
  `scan_count_mismatch`, `scan_id_mismatch`.
- **STRUCTURAL blocks on:** `no_scans`, `non_physical_radius`,
  `optical_signal_unit_conflict`.

That is the complete blocking set; nothing else in the library can make an
experiment invalid.

Two items from the brief's list are deliberately **not checks**:

- **A missing experiment identifier is unreachable** — `experiment_id` is
  required and rejects blank strings at construction. It is a category-1
  invariant, not a validation rule.
- **Differing radius axes are not a defect** — that is
  `RadiusAxisMode.PER_SCAN`, an accepted first-class representation. Flagging it
  would contradict ADR-0002. It appears as a summary field only.

**Reconciliation with the standing boundary.** Development-log 0001 §6 and
ADR-0002 require that "missing required metadata must fail validation loudly".
That is upheld on the reading that *required* means the construction-invariant
set — which does fail loudly, by raising. Metadata that is merely conventionally
desirable was never in that set; requiring it would make a historical dataset
carrying only an identifier, a radius vector and a signal vector unrepresentable.
Absence is reported explicitly, never inferred or defaulted, so the
no-silent-inference boundary is untouched. Recorded in the ADR-0002 Phase 4
amendment.

## 4. Severity rules

| Severity | May block | Meaning |
|----------|-----------|---------|
| `ERROR` | `ARCHIVAL`, `STRUCTURAL` | The only severity affecting `is_valid`. |
| `WARNING` | readiness tiers only | Never blocks archival or structural validity. |
| `INFO` | nothing | Descriptive only. |

**Readiness findings never carry `ERROR`.** This one rule is what keeps the
tiers from collapsing into each other, and it is what preserves the existing
meaning of `validate_structure().is_valid` exactly.

Every finding carries both `tiers` (what it speaks to) and `blocks` (what it
prevents), so a finding can pertain to a tier without blocking it — the normal
case for advisory metadata.

### Complete check list

26 check functions producing 31 distinct codes, executed in registry order. Full
rationale per rule is in `docs/concepts/validation-tiers.md`.

| Code | Severity | Tiers | Blocks |
|------|----------|-------|--------|
| `duplicate_scan_id` | ERROR | A | A, B, C, D |
| `duplicate_sample_id` | ERROR | A | A, B |
| `no_scans` | ERROR | B | B, C, D |
| `scan_count_mismatch` | ERROR | A | A, B, C, D |
| `scan_id_mismatch` | ERROR | A | A, B, C, D |
| `non_physical_radius` | ERROR | B | B, C, D |
| `optical_signal_unit_conflict` | ERROR | B | B, C, D |
| `empty_scan` | WARNING | B | — |
| `no_observations` | WARNING | B | C, D |
| `radius_not_monotonic` | WARNING | B | — |
| `duplicate_radius_within_scan` | WARNING | B | — |
| `elapsed_time_not_monotonic` | WARNING | B | — |
| `mixed_optical_systems` | WARNING | B | — |
| `mixed_declared_units` | WARNING | B | — |
| `cell_absent`, `channel_absent` | INFO | B | — |
| `elapsed_time_absent` | WARNING | C | C |
| `insufficient_scans_for_sv` | WARNING | C | C |
| `rotor_speed_absent` | WARNING | C, D | C, D |
| `experiment_type_unknown` | WARNING | C, D | — |
| `temperature_absent` | WARNING | C, D | — |
| `absorbance_wavelength_absent` | WARNING | C, D | — |
| `signal_unit_unknown` | WARNING | C, D | — |
| `optical_system_unknown` | WARNING | C, D | — |
| `no_samples` | WARNING | C, D | — |
| `density_absent`, `viscosity_absent` | WARNING | C, D | — |
| `partial_specific_volume_absent` | WARNING | D | — |
| `buffer_description_absent` | INFO | D | — |
| `provenance_absent` | INFO | A | — |
| `source_checksum_absent` | INFO | A | — |

Notable rulings:

- **Elapsed time blocks SV but not SE.** An equilibrium distribution is
  time-independent, so elapsed time is not a prerequisite for it.
- **Rotor speed blocks both**, and is satisfied by *either* a per-scan speed on
  every scan *or* the instrument's nominal speed.
- **Temperature, wavelength, density, viscosity and partial specific volume
  block nothing.** They enable standard-condition correction and molar-mass
  interpretation, which are downstream of the workflows themselves. Requiring
  them would be exactly the "conventional AUC analysis would prefer it" reasoning
  the brief forbids.
- **Descending radius order is not flagged** — inward scans are legitimate. Only
  a *change of direction* is reported.
- **A mix of `UNKNOWN` and one declared optical system is not a mix** — it is
  partial metadata. Only two or more *declared* systems trigger
  `mixed_optical_systems`.
- **`source_checksum_absent` is INFO and never appears in
  `validate_structure()`.** `sha256` is always `None` by an accepted deferral
  (ADR-0003); warning on every load would be noise contradicting a decision the
  project already made. Its message says the deferral is intentional.

### Determinism and aggregation

Checks run in the fixed order of the `CHECKS` registry, so report order is
determined entirely by experiment content. A condition affecting many scans
produces **one** finding carrying every affected identifier in `scan_ids`,
sorted; `location` is set only when exactly one subject is affected. A 200-scan
import missing wavelengths yields one finding, not two hundred. Equal
experiments produce equal reports, including `to_dict()` output. No machine
learning, heuristics or scientific interpretation are used anywhere.

## 5. Summary design

`ExperimentSummary` is a frozen pydantic model. Every collection field is a
tuple or a nested frozen model (`ValueRange`, `MetadataPresence`,
`ValidationCounts`) — there are no mutable dict or list fields, so a summary
cannot be mutated after construction and `model_dump(mode="json")` gives
serialisation for free.

It reports: identity, type, acquisition time and operator; scan and sample
counts; radius-axis mode, radius and signal units and whether the signal unit is
declared; points per scan and total valid observations; optical systems,
wavelengths, cells and channels with their unknown counts; elapsed-time,
rotor-speed, temperature and radius ranges as `ValueRange` (min, max, declared
unit, present/absent counts); per-field `MetadataPresence` across scans and
samples, keeping `present`/`missing`/`unknown`/`not_applicable`/`absent`
separate; provenance and checksum availability with the parser name; and
finding counts from the full report.

Nothing is calculated scientifically. No sedimentation or diffusion
coefficients, no molecular weights, no quality scores, no inferred values — a
field is either read from the model or counted.

`summary()` now returns `summary_data().to_text()`. Every previously rendered
line is reproduced verbatim, in place; nine new lines (points per scan, total
observations, wavelengths, cells, channels, rotor speed, temperature, source
checksum, validation counts) are inserted before the closing note, so the
no-scientific-claim note remains last.

## 6. API changes

Added, all additive:

```python
experiment.validate()          -> ValidationReport   # all four tiers
experiment.summary_data()      -> ExperimentSummary
experiment.assess_readiness()  -> ReadinessAssessment
```

New public types: `ValidationTier`, `ReadinessStatus`, `AnalysisKind`,
`AnalysisReadiness`, `ReadinessAssessment`, `ExperimentSummary`, `ValueRange`,
`MetadataPresence`, `ValidationCounts`; functions `validate_experiment`,
`assess_experiment_readiness`, `summarise_experiment`. All exported through both
`openauc.models` and `openauc.api`.

`ValidationIssue` gains `tiers`, `blocks`, `observed`, `expected`,
`remediation`, `component` and `scan_ids` — all with defaults, appended after
the existing fields, so existing construction remains valid. It also gains a
`tier` property (the primary tier), `blocks_structural_validity`,
`blocks_tier()`, `describe()` and `to_dict()`. `__str__` is **unchanged**,
because its output is asserted in the existing suite.

`ValidationReport` gains `infos`, `counts()`, `codes()`, `by_code()`,
`for_tiers()`, `blocking_for()` and `to_dict()`. `is_valid`, `errors`,
`warnings`, `raise_if_invalid()` and `__str__` are unchanged.

`validate_structure()` is now defined as the `ARCHIVAL`+`STRUCTURAL` findings of
`ERROR` or `WARNING` severity — informational findings and readiness findings
reach `validate()` only. This keeps its historical content and meaning intact
while giving `source_checksum_absent` a home that satisfies the policy above.

## 7. Tests

Four new modules, 71 new tests (126 → 197):

- `tests/unit/test_validation_tiers.py` — tiers, blocking sets, severities,
  aggregation, determinism, report/issue plumbing.
- `tests/unit/test_readiness.py` — routing, blocking, advisory findings, the
  structural/readiness separation, the permanent non-assessment.
- `tests/unit/test_summary_data.py` — both axis modes, presence counting,
  serialisation, text rendering, no-scientific-claim.
- `tests/integration/test_validation_summaries.py` — the same over
  `openauc.load` for long and wide, CSV and TSV, plus round-trip equivalence.

One new synthetic fixture, `tests/fixtures/generic_delimited/readiness_rich/`,
carries full instrument, sample and default metadata so a
`POTENTIALLY_READY` path can be exercised end-to-end. All 24 scenarios required
by the phase brief are covered; every fixture remains synthetic and
redistributable.

**Backward compatibility: all 126 pre-existing tests pass unmodified.**

## 8. Commands run

```
uv sync --all-groups
uv run ruff format .
uv run ruff format --check .
uv run ruff check .
uv run mypy
uv run pytest --cov=openauc --cov-report=term-missing
uv build
git diff --check
```

Results are recorded in the phase completion report; total coverage 95%, with
the four new modules at 99–100%. No coverage gate was added — enforcement stays
deferred until before the first alpha release.

## 9. Known limitations

- **No sample-to-scan linkage.** `ScanMetadata` carries no `sample_id`, so
  sample metadata can only be assessed experiment-wide; a per-scan sample
  readiness question cannot be asked. Deferred deliberately.
- **One signal unit per `Observations` set** (a standing Phase 2 limitation).
  This is why `mixed_optical_systems` is reported at all.
- **`ExperimentMetadata.acquired_at` is always `None` on import** — the manifest
  schema has no `acquired_at` field. A manifest-schema gap, not a defect; the
  summary reports "unknown" honestly.
- **`optical_systems()` includes the instrument's system**, so a scan set with a
  declared system and an undeclared instrument renders as
  `absorbance, unknown`. Pre-existing behaviour, left unchanged for
  compatibility.
- Readiness reflects **metadata presence only**. It never inspects signal values.
- No checksum is computed; no AUCX, plotting, vendor formats, unit conversion or
  scientific analysis.

## 10. Rejected alternatives

- **A single `tier` field per finding.** Rejected: `rotor_speed_absent` speaks to
  both readiness tiers, and forcing one primary tier would make
  `for_tiers(SE_READINESS)` silently miss a finding that blocks SE. `tiers` is a
  tuple with a `tier` convenience property.
- **Making readiness gaps errors.** Rejected outright: it would make historical
  datasets invalid and destroy the distinction the phase exists to draw.
- **`source_checksum_absent` as a WARNING.** Rejected: it would fire on every
  single load, contradicting an accepted deferral. INFO, excluded from
  `validate_structure()`.
- **One finding per affected scan.** Rejected: a large import would drown in
  identical findings. Aggregated with sorted `scan_ids` instead.
- **Requiring temperature, wavelength or partial specific volume.** Rejected as
  exactly the "conventional analysis would prefer it" reasoning the phase brief
  forbids.
- **A top-level `validation/` package.** Rejected for this phase: these modules
  operate solely on the canonical model. The top-level package stays reserved
  for genuine scientific quality control (ADR-0001 Phase 4 amendment).
- **Treating `ExperimentType.OTHER` like `UNKNOWN`.** Rejected: `OTHER` is an
  explicit statement that the run is neither SV nor SE, so both tiers are
  `NOT_APPLICABLE`; `UNKNOWN` is the absence of a statement, so both are assessed.
- **Deriving a scientific-suitability conclusion from findings.** Rejected as a
  matter of principle; the status is a constant.

## 11. Next steps

Phase 5 (plotting): basic matplotlib scan plots over the canonical model,
handling both radius-axis modes without interpolating onto a common grid. Any
plot that does place per-scan data on a shared grid must be explicit, opt-in and
recorded, per ADR-0002.

Candidate follow-ups, none blocking: a `sample_id` link on `ScanMetadata`;
heterogeneous per-scan signal units; an `acquired_at` field in the manifest
schema; and reconsidering a coverage gate (`fail_under`) before the alpha
release.
