# Assess analysis readiness

**Goal:** find out whether the metadata a future workflow would need is present
— and understand exactly how little that claims.

## Run it

```python
import openauc

experiment = openauc.load("examples/data/demo_experiment")
assessment = experiment.assess_readiness()
print(assessment)
```

```bash
uv run openauc validate examples/data/demo_experiment --readiness
```

## What it is

A **metadata-presence report**. It never inspects the signal, never models
sedimentation, and never concludes that data are correct, of good quality, or
scientifically suitable.

| Status | Meaning |
|--------|---------|
| `POTENTIALLY_READY` | Every metadata prerequisite is **present**. Nothing is claimed about the data themselves. |
| `BLOCKED` | A prerequisite is absent, or a structural error prevents assessment. |
| `NOT_APPLICABLE` | The declared experiment type says this workflow does not apply. |
| `NOT_ASSESSED` | Not evaluated, and never will be. |

!!! danger "`POTENTIALLY_READY` is not a verdict"
    It says the fields were found. It says nothing about whether the run was
    well executed, whether the sample behaved, or whether any analysis would be
    meaningful. `openauc` never describes an experiment as *ready*,
    *scientifically valid* or *suitable for analysis*.

## Routing by experiment type

| `ExperimentType` | SV | SE |
|------------------|----|----|
| `sedimentation_velocity` | assessed | `NOT_APPLICABLE` |
| `sedimentation_equilibrium` | `NOT_APPLICABLE` | assessed |
| `unknown` | assessed | assessed |
| `other` | `NOT_APPLICABLE` | `NOT_APPLICABLE` |

`other` and `unknown` are **not** equivalent. `other` is an explicit statement
that the run is neither; `unknown` is the *absence* of a statement, so both are
assessed and a non-blocking `experiment_type_unknown` warning is recorded.

## What blocks a tier

**Sedimentation velocity:** `no_scans`, `no_observations`, `non_physical_radius`
or any archival keying error; `elapsed_time_absent`;
`insufficient_scans_for_sv`; `rotor_speed_absent`.

**Sedimentation equilibrium:** the same structural errors and
`rotor_speed_absent`, but **not** `elapsed_time_absent` — an equilibrium
distribution is time-independent.

Everything else — temperature, wavelength, optical system, signal unit, samples,
density, viscosity, partial specific volume, cell, channel — is **advisory** and
blocks nothing.

## Reading an entry

```python
sv = assessment.sedimentation_velocity
sv.status
sv.is_blocked
sv.note
for issue in sv.blocking_issues:
    print("BLOCKING", issue.code, "-", issue.remediation)
for issue in sv.advisory_issues:
    print("advisory", issue.code)
```

## The permanent non-assessment

```python
assessment.scientific_suitability.status  # always NOT_ASSESSED
```

Present in **every** assessment, as a machine-readable entry rather than a prose
disclaimer, so a programmatic consumer cannot omit it. It is a constant, never
derived from any finding, never scored, never upgraded.

## Independence from structural validity

Both directions occur, and both are correct:

```python
# Valid, but blocked — the normal case for a sparse historical dataset
assert experiment.validate_structure().is_valid
assert assessment.sedimentation_velocity.is_blocked
```

A structural `ERROR` blocks both readiness tiers, because there is no coherent
experiment to assess.

## Next step

- [Analysis readiness concepts](../concepts/analysis-readiness.md)
- [Scientific boundaries](../concepts/scientific-boundaries.md)
