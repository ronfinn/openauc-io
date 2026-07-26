# Validation tiers

Validation asks **four independent questions** of an experiment, and refuses to
answer a fifth. Each finding names the tier or tiers it speaks to, so
"structurally valid", "analysis ready" and "scientifically valid" can never
collapse into one another.

| Tier | `ValidationTier` | Question |
|------|------------------|----------|
| A | `ARCHIVAL` | Can the experiment be stored and returned unchanged and unambiguously? |
| B | `STRUCTURAL` | Are metadata, scans and observations internally consistent and inspectable? |
| C | `SV_READINESS` | Is the metadata a future sedimentation-velocity workflow needs present? |
| D | `SE_READINESS` | Is the metadata a future sedimentation-equilibrium workflow needs present? |
| — | **not a tier** | **Is the experiment scientifically valid or suitable?** — never assessed. |

The fifth question is reported permanently as `NOT_ASSESSED`; see
[analysis readiness](analysis-readiness.md).

## Four categories of check

Only the first three exist in `openauc`, and they live in different places:

1. **Construction invariants** — conditions so fundamental that an invalid
   object cannot be built. They **raise** at construction (`ValueError`,
   `ObservationError`), never appearing in a report: non-empty identifiers, a
   non-negative scan index, finite quantity values, elapsed time in seconds or
   unknown, non-negative wavelength and speed, array geometry, mask validity.
2. **Structural validation** — cross-object consistency, reported by
   `validate_structure()` (tiers A and B).
3. **Analysis-readiness assessment** — metadata presence, reported by
   `validate()` and `assess_readiness()` (tiers C and D).
4. **Scientific quality control** — convection, aggregation, meniscus
   estimation, equilibrium assessment. **Out of scope, permanently, by design.**

## The two entry points

```python
report = experiment.validate_structure()  # tiers A+B, ERROR and WARNING only
report = experiment.validate()  # all four tiers, all severities
```

`validate_structure()` is unchanged in meaning: `report.is_valid` is `True` when
there are no `ERROR`-severity findings, and only archival or structural problems
can produce one. `validate()` is the superset, adding readiness findings and
purely informational findings.

## Severity policy

| Severity | May block | Meaning |
|----------|-----------|---------|
| `ERROR` | `ARCHIVAL`, `STRUCTURAL` | The only severity that makes `is_valid` false. |
| `WARNING` | readiness tiers only | Never blocks archival or structural validity. |
| `INFO` | nothing | Descriptive only. |

**Readiness findings never use `ERROR`.** That single rule is what keeps the
tiers independent. A finding carries both `tiers` (what it speaks to) and
`blocks` (what it prevents) — a finding may pertain to a tier without blocking
it, which is the normal case for advisory metadata.

## The minimum for validity (resolves Q3)

The minimum representable object is defined by the construction invariants. On
top of that:

**Tier A blocks on** duplicate scan identifiers, duplicate sample identifiers, a
scan-count mismatch, and a scan-identifier or ordering mismatch between metadata
and observations. All four make observations impossible to attribute
unambiguously.

**Tier B blocks on** no scans, non-positive radial positions, and a well-defined
optical-system/signal-unit contradiction. All three make an inspection
meaningless or self-contradictory.

**That is the complete blocking set.** No metadata field is required. A
historical dataset carrying nothing but an identifier, a radius vector and a
signal vector is archivable and structurally valid; its sparse metadata is
reported explicitly, never inferred and never fatal.

## Every check

Codes are stable. "Blocks" lists the tiers a finding prevents.

### Archival

| Code | Severity | Blocks | Why |
|------|----------|--------|-----|
| `duplicate_scan_id` | ERROR | A, B, C, D | Ambiguous keying; observations cannot be attributed. |
| `duplicate_sample_id` | ERROR | A, B | Ambiguous keying. |
| `scan_count_mismatch` | ERROR | A, B, C, D | Metadata and observations describe different scan sets. |
| `scan_id_mismatch` | ERROR | A, B, C, D | Same identifiers required, in the same order. |
| `provenance_absent` | INFO | — | A hand-built experiment legitimately has none. |
| `source_checksum_absent` | INFO | — | Only fires when provenance exists but records no digest. Since the AUCX phase, imports record source checksums, so this is now rare. Never a warning, never structural. |

### Structural

| Code | Severity | Blocks | Why |
|------|----------|--------|-----|
| `no_scans` | ERROR | B, C, D | Nothing to inspect. Not archival-blocking: an empty set is storable. |
| `non_physical_radius` | ERROR | B, C, D | A radius ≤ 0 is not a representable radial position. |
| `optical_signal_unit_conflict` | ERROR | B, C, D | A defined contradiction, e.g. absorbance with fringes. |
| `empty_scan` | WARNING | — | A scan may legitimately carry no points. |
| `no_observations` | WARNING | C, D | Nothing anywhere to analyse. |
| `radius_not_monotonic` | WARNING | — | The axis changes direction. Descending order is **not** flagged. |
| `duplicate_radius_within_scan` | WARNING | — | Repeated radial positions are ambiguous but storable. |
| `elapsed_time_not_monotonic` | WARNING | — | Legitimate for interleaved or re-ordered exports. |
| `mixed_optical_systems` | WARNING | — | An observation set carries one signal unit, so a genuine mix is notable. |
| `mixed_declared_units` | WARNING | — | One field declaring two units across scans. Never converted. |
| `cell_absent` / `channel_absent` | INFO | — | Organisational metadata only. |

### Readiness

None of these is ever an error.

| Code | Severity | Tiers | Blocks | Why |
|------|----------|-------|--------|-----|
| `elapsed_time_absent` | WARNING | C | **C** | Velocity is inherently a time series; equilibrium is time-independent. |
| `insufficient_scans_for_sv` | WARNING | C | **C** | Fewer than two scans carry observations. |
| `rotor_speed_absent` | WARNING | C, D | **C, D** | Unavoidable in both. Satisfied by a per-scan speed or the instrument's nominal speed. |
| `experiment_type_unknown` | WARNING | C, D | — | An undeclared type does not make data unanalysable. |
| `temperature_absent` | WARNING | C, D | — | Enables standard-condition correction, not analysis itself. |
| `absorbance_wavelength_absent` | WARNING | C, D | — | Needed to interpret absorbance quantitatively, not to obtain *s*. |
| `signal_unit_unknown` | WARNING | C, D | — | Blocks quantitative interpretation, not analysis. |
| `optical_system_unknown` | WARNING | C, D | — | The signal unit may still be declared. |
| `no_samples` | WARNING | C, D | — | Sample metadata is not needed to obtain *s*. |
| `density_absent` / `viscosity_absent` | WARNING | C, D | — | Correction inputs, not prerequisites. |
| `partial_specific_volume_absent` | WARNING | D | — | Needed for molar mass, not for the buoyant term. |
| `buffer_description_absent` | INFO | D | — | Descriptive. |

### Deliberately *not* checks

- **A missing experiment identifier** cannot occur — `experiment_id` is required
  and rejects blank strings at construction. It is a construction invariant.
- **Differing radius axes** are not a defect. They are `RadiusAxisMode.PER_SCAN`,
  a first-class representation. It is reported as a summary fact, never as a
  finding.
- **Physical plausibility bounds** (absolute zero, a "reasonable" radius window)
  are not enforced anywhere, to keep scientific assumptions out of the
  representation layer.

## Determinism and aggregation

Validation is deterministic and explainable. No machine learning, no heuristics,
no scientific interpretation.

- Checks run in the fixed order of the `CHECKS` registry, so report order is
  fully determined by the experiment's content.
- A condition affecting many scans produces **one** finding carrying every
  affected identifier in `scan_ids`, sorted — not one finding per scan.
- `location` is set only when exactly one subject is affected.
- Equivalent experiments produce equal reports, including `to_dict()` output.

## Finding structure

```python
issue.code  # stable identifier, e.g. "rotor_speed_absent"
issue.severity  # ERROR | WARNING | INFO
issue.tiers  # tiers this finding speaks to (never empty)
issue.tier  # the primary (first) tier
issue.blocks  # tiers this finding prevents
issue.message  # what was found
issue.observed  # what was actually there
issue.expected  # the condition that would satisfy the check
issue.remediation  # a concrete suggestion
issue.component  # the model field concerned
issue.location  # the single affected subject, when there is exactly one
issue.scan_ids  # every affected scan, sorted
issue.blocks_structural_validity
issue.blocks_tier(tier)
issue.describe()  # multi-line rendering with the detail above
issue.to_dict()
```

Reports offer `is_valid`, `errors`, `warnings`, `infos`, `counts()`, `codes()`,
`by_code()`, `for_tiers()`, `blocking_for()`, `raise_if_invalid()` and
`to_dict()`.
