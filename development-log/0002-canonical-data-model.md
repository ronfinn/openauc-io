# Development Log 0002 — Canonical data model (Phase 2)

- **Date:** 2026-07-23
- **Branch:** `feat/canonical-data-model` (recreated from the Phase-1 tip
  `6680e90`; see the branch/recovery note below)
- **Status:** Phase 2 complete. Data representation and structural validation
  only — no parsers, archives, plotting, or scientific analysis.
- **Author:** Ron Finn

> **Branch / recovery note.** Phase 2 was first implemented against the working
> tree while `feat/canonical-data-model` did not yet exist. During a subsequent
> housekeeping step an external `git reset --hard` + `git clean -fd` wiped the
> uncommitted Phase 2 work, and a separate commit (`6680e90`, "docs: fix Code of
> Conduct reporting section") advanced the base branch. The Phase 2 files were
> then regenerated verbatim from the authoring session and placed on a freshly
> created `feat/canonical-data-model` branched from `6680e90` (Phase 1 + the CoC
> fix). Nothing is committed on this branch yet.

## 1. Objective

Implement a typed, validated, scientifically conservative canonical in-memory
representation of an AUC experiment: preserve raw observations, represent missing
metadata explicitly, support shared and per-scan radius axes, and retain the
provenance of supplied, converted, inferred, user-confirmed and unknown values —
without silent interpolation, resampling, unit inference/conversion, or any claim
that a dataset is suitable for analysis.

## 2. Accepted decisions

Confirmed for this phase (also recorded in the ADR-0002 amendment):

- Metadata via **pydantic v2** (frozen, `extra="forbid"`); observations via
  **NumPy/xarray**.
- **Both** radius-axis regimes; per-scan uses **padded 2-D arrays with an
  authoritative validity mask**; padding is never presented as measured data.
- No silent interpolation, resampling, unit inference or conversion; declared
  units retained; unknown units explicit; no Pint.
- Five optical systems represented: absorbance, interference, fluorescence,
  intensity, unknown (representation ≠ import/interpretation support).
- Field-level invariant violations **raise at construction**; cross-object
  issues are reported by `validate_structure()`.
- `AUCExperiment` is a **frozen dataclass**; the constructor takes
  `observations=` (not `data=`).
- In-memory provenance now; **no AUCX serialisation**.
- Data-model validation in `models/validation.py`; top-level `validation/`
  reserved for later cross-cutting/scientific validation.

## 3. Implementation structure

New package `src/openauc/models/`:

| Module | Contents |
|--------|----------|
| `enums.py` | `ExperimentType`, `OpticalSystem`, `Unit`, `RadiusAxisMode`, `ValueStatus`, `ValueProvenance`, `ValidationSeverity` |
| `metadata.py` | `Quantity` value type + helpers; `ExperimentMetadata` (area A) |
| `instrument.py` | `InstrumentMetadata` (area B) |
| `sample.py` | `SampleMetadata` (area C) |
| `scan.py` | `ScanMetadata` (area D) |
| `observations.py` | `Observations` + `from_shared_axis`/`from_per_scan` (area E) |
| `provenance.py` | `ImportProvenance` (area F) |
| `validation.py` | `ValidationIssue`, `ValidationReport`, `validate_experiment_structure` (area G) |
| `experiment.py` | `AUCExperiment` (frozen dataclass; `summary()`, `validate_structure()`, `to_dict`/`from_dict`) |
| `__init__.py` | public model facade |

Modified: `exceptions.py` (adds `ObservationError`, `StructuralValidationError`),
`api.py` (re-exports the model surface), `pyproject.toml` (mypy override for
numpy stubs — see §11).

## 4. Shared and per-scan radius representation

- **Shared:** dataset with 1-D `radius` coordinate and `signal` of dims
  `(scan, radius)`; all signal values must be finite.
- **Per-scan:** `radius`, `signal` and `mask` variables of dims `(scan, point)`.
  Each scan's vectors are validated (1-D, equal length, finite) and copied into
  arrays padded to the longest scan with `NaN`; the mask marks real points
  (`True`) versus padding (`False`). The mask is authoritative — a value is a
  real observation iff its mask entry is `True`. `valid_radius_values()` and
  `points_per_scan()` respect the mask. Nothing is interpolated.

The constructor validates any hand-built dataset too, so an invalid
`Observations` cannot exist (raises `ObservationError`).

## 5. Unit policy

Canonical units are fixed per the brief and retained verbatim. Metadata fields
perform representational unit checks only (e.g. rotor speed must be `RPM` or
`UNKNOWN`); `Unit.UNKNOWN` is always accepted; open-ended units use `Unit.OTHER`
with `Quantity.unit_label`. No conversion is performed anywhere; a future
`CONVERTED` provenance tag exists for when conversions are introduced. No Pint.

## 6. Missing-value policy

Field-level absence is `None`. Value-level absence uses `Quantity.status`
(`PRESENT`/`MISSING`/`UNKNOWN`/`NOT_APPLICABLE`), which are kept distinct and
never collapsed or defaulted. A `PRESENT` quantity must be finite; all others
carry `None`. Enforced at construction.

## 7. Optical-system scope

Five values represented. Structural validation flags only **well-defined**
optical-system/signal-unit conflicts (e.g. absorbance with fringes); `UNKNOWN`
systems and `UNKNOWN`/`OTHER` units are never flagged. One `signal_unit` per
`Observations` set this phase (documented limitation); each scan keeps its own
`optical_system`.

## 8. Tests added

`tests/unit/`: `test_models_minimal.py`, `test_models_complete.py`,
`test_observations.py`, `test_metadata_values.py`, `test_model_validation.py`,
`test_model_edges.py`. Synthetic data only. Covers all sixteen required
scenarios: minimal (1) and complete (2) experiments; shared (3) and per-scan (4)
axes; unknown optical system (5); missing optional metadata (6); duplicate scan
identifiers (7); negative elapsed time (8); non-finite radius/signal (9);
scan/observation mismatch (10); valid (11) and invalid (12) masks; serialisation
(13) and reconstruction (14); summary (15); structured validation report (16).
Plus defensive dataset-validation and summary-branch edge cases.

## 9. Commands run

```
uv sync --all-groups
uv run ruff format .
uv run ruff format --check .
uv run ruff check .
uv run mypy
uv run pytest --cov=openauc --cov-report=term-missing
uv build
```

Results: ruff format clean; ruff check clean; mypy clean; **54 tests passed**;
total coverage **93%** (all model modules ≥ 88%); sdist + wheel built. Python
3.12.13 locally; 3.11/3.13 rest on CI.

## 10. Design compromises

- **Padded + mask** for per-scan data trades some memory (padding to the longest
  scan) for a single rectangular, vectorisable, serialisable structure with an
  unambiguous validity signal. Chosen over separate per-scan DataArrays (harder
  to validate/serialise uniformly) and long-form indexing (poorer for
  shared-grid work).
- **`AUCExperiment` as a frozen dataclass**, not pydantic, to avoid forcing the
  xarray layer through pydantic serialisation. Cross-object consistency is
  deliberately *not* enforced at construction so a mismatch can be built and then
  reported by `validate_structure()` (test scenario 10).
- **One `signal_unit` per observation set** this phase; heterogeneous per-scan
  signal units deferred.
- **mypy targets 3.11 but skips numpy stubs** (numpy 2.5 ships PEP 695 `type`
  statements that only parse under a 3.12+ target). See §11.

## 11. Scientific limitations

- No scientific quality control (convection, aggregation, equilibrium, meniscus)
  and no sedimentation analysis — out of scope by design.
- Structural validation checks representation only: identifier uniqueness,
  scan/observation agreement, positive radius, and well-defined optical/unit
  conflicts. It does not judge scientific validity or analysis suitability.
- No file import: models are built in memory (or from `to_dict`/`from_dict`).
- Absolute-zero and other physical range checks on temperature and physico-
  chemical quantities are intentionally **not** enforced, to avoid embedding
  scientific assumptions in the representation layer.

## 12. Unresolved questions

- **Q2 (units), Q4 (optical systems)** — resolved this phase (ADR-0002
  amendment).
- **Heterogeneous per-scan signal units** — whether/how to support multiple
  signal units within one observation set.
- **Q3 — minimum valid-experiment metadata** for *analysis* (vs the structural
  minimum implemented here) remains for Phase 4.
- **Q5 — provenance schema finalisation and checksum computation** remain for
  Phase 6 (SHA-256 format is validated here, but no checksum is computed).
- Whether physical sanity bounds (e.g. temperature ≥ absolute zero, plausible
  radius window) belong in a later *scientific* validation layer.
- mypy numpy-stub handling: revisit if the project later adopts a mypy/numpy
  combination that parses PEP 695 stubs under a 3.11 target.

## 13. Next steps

Phase 3 (tabular ingest): generic long- and wide-format CSV/TSV readers plus
JSON/YAML manifests, mapping parsed inputs onto this canonical model and
populating `ImportProvenance` for real (non-synthetic) sources. The parser
plugin registry (ADR-0004) is introduced there. This model layer is the stable
target those readers build against.
