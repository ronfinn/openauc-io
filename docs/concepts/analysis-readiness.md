# Analysis readiness

Readiness answers one narrow question per workflow:

> Is the metadata that a future workflow would need actually present?

It is a **metadata-presence report**. It never inspects the signal, never models
sedimentation, and never concludes that data are correct, of good quality, or
scientifically suitable.

```python
assessment = experiment.assess_readiness()
assessment.sedimentation_velocity.status      # ReadinessStatus
assessment.sedimentation_equilibrium.status
assessment.scientific_suitability.status      # always NOT_ASSESSED
```

## What readiness is not

`openauc` never describes an experiment as *ready*, *scientifically valid*, or
*suitable for analysis*. The strongest statement it can make is
`POTENTIALLY_READY`, and even that is a statement about metadata, not data.

| `ReadinessStatus` | Meaning |
|-------------------|---------|
| `POTENTIALLY_READY` | Every metadata prerequisite is present. Nothing is claimed about the data themselves. |
| `BLOCKED` | At least one prerequisite is absent, or a structural error prevents assessment. |
| `NOT_APPLICABLE` | The declared experiment type says this workflow does not apply. |
| `NOT_ASSESSED` | Not evaluated, and never will be. |

## Routing by experiment type

| `ExperimentType` | SV | SE |
|------------------|----|----|
| `SEDIMENTATION_VELOCITY` | assessed | `NOT_APPLICABLE` |
| `SEDIMENTATION_EQUILIBRIUM` | `NOT_APPLICABLE` | assessed |
| `UNKNOWN` | assessed | assessed |
| `OTHER` | `NOT_APPLICABLE` | `NOT_APPLICABLE` |

`OTHER` and `UNKNOWN` are **not** equivalent. `OTHER` is an explicit statement
that the run is neither a velocity nor an equilibrium experiment, so neither
readiness tier applies. `UNKNOWN` is the *absence* of a statement, so both are
assessed and a non-blocking `experiment_type_unknown` warning is recorded. The
model never guesses which one was meant.

## What blocks a tier

The blocking sets are deliberately minimal. Metadata that a conventional AUC
workflow would merely *prefer* is reported, never required.

**Sedimentation velocity** is blocked by:

- `no_scans`, `no_observations`, `non_physical_radius`, or any archival keying
  error — there is nothing coherent to analyse;
- `elapsed_time_absent` — velocity is inherently a time series;
- `insufficient_scans_for_sv` — fewer than two scans carry observations;
- `rotor_speed_absent` — no per-scan speed and no instrument nominal speed.

**Sedimentation equilibrium** is blocked by the same structural errors and by
`rotor_speed_absent`, but **not** by `elapsed_time_absent`: an equilibrium
distribution is time-independent, so elapsed time is not a prerequisite.

Everything else — temperature, wavelength, optical system, signal unit, sample
records, density, viscosity, partial specific volume, buffer description, cell
and channel — is reported as an **advisory** finding and blocks nothing. Each
appears in `advisory_issues` for the tiers it pertains to.

## Reading an assessment

```python
entry = experiment.assess_readiness().sedimentation_velocity
entry.status            # ReadinessStatus
entry.is_blocked        # bool
entry.blocking_issues   # findings whose `blocks` names this tier
entry.advisory_issues   # findings pertaining to this tier that block nothing
entry.note              # why the status is what it is
entry.to_dict()
```

Blocking is derived directly from each finding's `blocks` metadata, so the
tables in [validation tiers](validation-tiers.md) and the behaviour of this
module cannot drift apart.

## Structural validity and readiness are independent

An experiment can be archivally and structurally valid while every readiness
tier is blocked — that is the normal case for a historical dataset with sparse
metadata, and it is a success, not a failure:

```python
assert experiment.validate_structure().is_valid          # nothing wrong with it
assert experiment.assess_readiness().sedimentation_velocity.is_blocked
```

The converse also holds: a structural `ERROR` blocks both readiness tiers,
because there is no coherent experiment to assess.

## Scientific suitability

`AnalysisKind.SCIENTIFIC_SUITABILITY` is present in **every** assessment with
status `NOT_ASSESSED` and a fixed note. It is a constant: it is never derived
from structural or readiness findings, never scored, and never upgraded.

It exists as a machine-readable entry rather than a prose disclaimer so that any
consumer reading the assessment programmatically encounters the non-assessment
explicitly and cannot omit it.

Judging convection, aggregation, meniscus position, equilibrium attainment or
fit quality is **out of scope for `openauc`, permanently and by design**. Those
belong to established AUC analysis software.
