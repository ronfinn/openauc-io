# Interpret validation findings

**Goal:** know what each finding means, what it blocks, and whether to act.

Full rationale per rule: [Validation tiers](../concepts/validation-tiers.md).

## Anatomy of a finding

```python
issue.code  # stable identifier, e.g. 'rotor_speed_absent'
issue.severity  # ERROR | WARNING | INFO
issue.tiers  # tier(s) it speaks to
issue.blocks  # tier(s) it prevents — may be empty
issue.message  # what was found
issue.observed  # what was actually there
issue.expected  # what would have satisfied the check
issue.remediation  # a concrete suggestion
issue.component  # the model field concerned
issue.location  # the single affected subject, when there is exactly one
issue.scan_ids  # every affected scan, sorted
issue.describe()  # all of the above, rendered
```

One finding covers a condition across many scans — a 200-scan import missing
wavelengths yields **one** finding listing 200 identifiers, not 200 findings.

## Errors — these make `is_valid` false

| Code | Tier | Blocks | Meaning and fix |
|------|------|--------|-----------------|
| `duplicate_scan_id` | ARCHIVAL | A, B, C, D | Two scan records share an identifier; observations cannot be attributed. Give each a distinct id. |
| `duplicate_sample_id` | ARCHIVAL | A, B | Same, for samples. |
| `scan_count_mismatch` | ARCHIVAL | A, B, C, D | Metadata and observations describe different numbers of scans. |
| `scan_id_mismatch` | ARCHIVAL | A, B, C, D | Same count, but different identifiers or a different order. |
| `no_scans` | STRUCTURAL | B, C, D | Nothing to inspect. Not archival-blocking — an empty set is storable. |
| `non_physical_radius` | STRUCTURAL | B, C, D | A radius ≤ 0. Correct the axis or drop the points. |
| `optical_signal_unit_conflict` | STRUCTURAL | B, C, D | e.g. an absorbance scan with a `fringe` signal unit. Correct one of them. |

## Warnings — never block structural validity

| Code | Blocks | Meaning |
|------|--------|---------|
| `empty_scan` | — | A scan carries no points. Legitimate. |
| `no_observations` | C, D | Nothing anywhere to analyse. |
| `radius_not_monotonic` | — | The axis changes direction. **Descending order is not flagged** — inward scans are legitimate. |
| `duplicate_radius_within_scan` | — | Repeated radial positions. |
| `elapsed_time_not_monotonic` | — | Scans out of time order. Legitimate for interleaved exports. |
| `mixed_optical_systems` | — | More than one *declared* system in one set. |
| `mixed_declared_units` | — | One field declaring two units across scans. Never converted. |
| `elapsed_time_absent` | **C** | Velocity is a time series; equilibrium is time-independent. |
| `insufficient_scans_for_sv` | **C** | Fewer than two scans carry observations. |
| `rotor_speed_absent` | **C, D** | Satisfied by a per-scan speed *or* the instrument's nominal speed. |
| `experiment_type_unknown` | — | An undeclared type does not make data unanalysable. |
| `temperature_absent` | — | Enables standard-condition correction, not analysis. |
| `absorbance_wavelength_absent` | — | Needed to interpret absorbance quantitatively, not to obtain *s*. |
| `signal_unit_unknown` | — | Blocks quantitative interpretation, not analysis. |
| `optical_system_unknown` | — | The signal unit may still be declared. |
| `no_samples` | — | Sample metadata is not needed to obtain *s*. |
| `density_absent`, `viscosity_absent` | — | Correction inputs, not prerequisites. |
| `partial_specific_volume_absent` | — | Needed for molar mass, not for the buoyant term. |

## Informational — block nothing

| Code | Meaning |
|------|---------|
| `cell_absent`, `channel_absent` | Organisational metadata only. |
| `buffer_description_absent` | Descriptive. |
| `provenance_absent` | A hand-built experiment legitimately has none. |
| `source_checksum_absent` | Provenance exists but records no digest. Rare since imports compute them. |

## Deciding whether to act

```python
report = experiment.validate()

if report.errors:
    ...  # must fix: the data cannot be stored or inspected unambiguously

for issue in report.warnings:
    if issue.blocks:
        ...  # a future workflow would lack something; add metadata if you have it
    else:
        ...  # informational-in-effect; act only if it surprises you
```

Findings that block nothing are **reports, not demands**. A historical dataset
with sparse metadata is expected to produce several, and is still perfectly
valid.

## Filtering

```python
from openauc.models import ValidationSeverity, ValidationTier

report.by_code("rotor_speed_absent")
report.for_tiers(ValidationTier.SV_READINESS)
report.blocking_for(ValidationTier.SE_READINESS)
report.for_tiers(ValidationTier.ARCHIVAL, severities=(ValidationSeverity.ERROR,))
```

## Two things deliberately *not* checked

- **A missing experiment identifier** cannot occur — `experiment_id` is required
  and rejects blank strings at construction.
- **Differing radius axes** are not a defect. That is
  `RadiusAxisMode.PER_SCAN`, a first-class representation, reported as a summary
  fact.

## Next step

- [Assess analysis readiness](assess-analysis-readiness.md)
