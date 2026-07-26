# Validate an experiment

**Goal:** read a `ValidationReport` correctly, and understand what each tier
does and does not claim.

**Prerequisites:** [Installation](../getting-started/installation.md).

## The two entry points

```python
import openauc

experiment = openauc.load("examples/data/demo_experiment")

structural = experiment.validate_structure()  # ARCHIVAL + STRUCTURAL, ERROR/WARNING
everything = experiment.validate()            # all four tiers, all severities
```

Neither raises. `validate_structure()` is the narrower, historical view;
`validate()` is the superset that also carries readiness and informational
findings.

## The verdict

```python
structural.is_valid          # True when there are no ERROR-severity findings
structural.counts()          # (errors, warnings, infos)
print(structural)            # 'structural validation: OK (no issues)'
```

!!! warning "`is_valid` is a statement about structure only"
    It means the scans and observations correspond unambiguously and are
    internally consistent. It is **never** a claim that the experiment is
    scientifically valid, of good quality, or suitable for analysis.

## The four tiers

| Tier | Question |
|------|----------|
| `ARCHIVAL` | Can it be stored and returned unchanged and unambiguously? |
| `STRUCTURAL` | Are metadata, scans and observations internally consistent? |
| `SV_READINESS` | Is the metadata a future velocity workflow needs present? |
| `SE_READINESS` | Is the metadata a future equilibrium workflow needs present? |

A fifth question — scientific suitability — is **not a tier and is never
answered**.

Before all of them sit **construction invariants**: conditions so fundamental
that an invalid object cannot be built at all. Those *raise* at construction and
never appear in a report — a blank `scan_id`, a negative elapsed time, a
non-finite radius, a mask inconsistent with its data.

## Severity

| Severity | May block | Meaning |
|----------|-----------|---------|
| `ERROR` | `ARCHIVAL`, `STRUCTURAL` | The only severity that makes `is_valid` false |
| `WARNING` | readiness tiers only | Never blocks archival or structural validity |
| `INFO` | nothing | Descriptive only |

**Readiness findings never use `ERROR`.** That single rule is what keeps
structural validity and analysis readiness independent.

## Reading a finding

```python
for issue in experiment.validate().issues:
    print(issue.describe())
```

```text
WARNING rotor_speed_absent: 4 scan(s) carry no rotor speed
    tiers: sv_readiness, se_readiness
    blocks: sv_readiness, se_readiness
    component: scan.rotor_speed
    observed: 4 of 4 scan(s), and no instrument nominal speed
    expected: a per-scan rotor speed, or an instrument nominal speed
    remediation: record rotor_speed_rpm per scan or nominal_speed_rpm
    scans: scan_001, scan_002, scan_003, scan_004
```

`tiers` is what the finding *speaks to*; `blocks` is what it *prevents*. A
finding can pertain to a tier without blocking it — the normal case for
advisory metadata.

## Worked example: structurally valid, readiness blocked

The commonest situation for a historical dataset. It is a success, not a
failure.

```python
from openauc.synthetic import SyntheticExperimentConfig, generate_experiment

sparse = generate_experiment(
    SyntheticExperimentConfig(
        scenario="sparse-metadata", n_scans=6, metadata_completeness="minimal"
    )
)

assert sparse.validate_structure().is_valid          # nothing wrong with it
assessment = sparse.assess_readiness()
print(assessment.sedimentation_velocity.status)      # BLOCKED
for issue in assessment.sedimentation_velocity.blocking_issues:
    print(" blocked by:", issue.code)
```

Absent metadata is **reported, never required**. A dataset carrying only an
identifier, a radius vector and a signal vector remains archivable and
structurally valid.

## Worked example: archival but structurally invalid

```python
broken = generate_experiment(
    SyntheticExperimentConfig(scenario="invalid-structure", n_scans=4)
)
report = broken.validate_structure()
print(report.is_valid)                # False
print(sorted(set(report.codes())))    # ['duplicate_scan_id', 'scan_id_mismatch']
```

## Worked example: UNKNOWN vs OTHER experiment type

These are **not** equivalent, and the distinction drives readiness routing:

```python
from openauc.models import ExperimentType

unknown = generate_experiment(
    SyntheticExperimentConfig(experiment_type=ExperimentType.UNKNOWN, n_scans=4)
)
a = unknown.assess_readiness()
# both assessed; a non-blocking experiment_type_unknown warning is recorded

other = generate_experiment(
    SyntheticExperimentConfig(experiment_type=ExperimentType.OTHER, n_scans=4)
)
b = other.assess_readiness()
print(b.sedimentation_velocity.status)      # NOT_APPLICABLE
print(b.sedimentation_equilibrium.status)   # NOT_APPLICABLE
```

`OTHER` is an explicit statement that the run is neither velocity nor
equilibrium. `UNKNOWN` is the *absence* of a statement, so both are assessed.

## Worked example: missing provenance and optional metadata

```python
from openauc.models import (
    AUCExperiment, ExperimentMetadata, Observations, Quantity, ScanMetadata, Unit,
)

hand_built = AUCExperiment(
    metadata=ExperimentMetadata(experiment_id="bare"),
    scans=(ScanMetadata(scan_id="s1", index=0, elapsed_time=Quantity.missing()),),
    observations=Observations.from_shared_axis(
        radius=[6.0, 6.1], signal=[[0.1, 0.2]], scan_ids=["s1"]
    ),
)
report = hand_built.validate()
print(report.is_valid)                       # True — still perfectly valid
print("provenance_absent" in report.codes()) # True, but INFO only
```

`provenance_absent` is informational: a hand-built experiment legitimately has
none.

## What is never checked

No convection, aggregation or sample-quality assessment. No equilibrium or
meniscus detection. No molecular weight or sedimentation coefficient. No
physical plausibility bounds — not even absolute zero — because that would
embed scientific assumptions in a representation layer.

## Next step

- [Interpret validation findings](../how-to/interpret-validation-findings.md) —
  every code, with severity and blocked tiers
- [Assess analysis readiness](../how-to/assess-analysis-readiness.md)
