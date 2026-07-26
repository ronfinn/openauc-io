# Recipes

Short, copyable, using only implemented APIs and options. Run from the
repository root unless stated.

## 1. Generate data and save it as AUCX

```bash
uv run openauc generate demo.aucx --format aucx \
  --scenario moving-boundary --scans 20 --points 300 --seed 42
```

```python
from openauc.synthetic import SyntheticExperimentConfig, generate_experiment

experiment = generate_experiment(
    SyntheticExperimentConfig(scenario="moving-boundary", n_scans=20,
                              n_points=300, seed=42)
)
experiment.export("demo.aucx")
```

## 2. Generate generic-long data

```bash
uv run openauc generate work/demo --format generic-long --scenario static-profile --seed 1
```

```python
from openauc.synthetic import write_generic_long
write_generic_long(experiment, "work/demo")     # manifest.json + scans.csv
```

## 3. Inspect a CSV experiment

```bash
uv run openauc inspect examples/data/demo_experiment
uv run openauc inspect examples/data/demo_experiment --json | jq '.n_scans'
```

## 4. Convert CSV/TSV to AUCX

```bash
uv run openauc convert examples/data/demo_experiment demo.aucx --overwrite
```

## 5. Validate every AUCX file in a directory

```python
from pathlib import Path
import openauc

for path in sorted(Path("archives").glob("*.aucx")):
    report = openauc.validate_aucx(path)
    status = "OK  " if report.is_valid else "FAIL"
    print(f"{status} {path.name}")
    for issue in report.issues:
        print("      ", issue.code, "-", issue.message)
```

```bash
for f in archives/*.aucx; do
    uv run openauc validate "$f" >/dev/null 2>&1 \
      && echo "OK   $f" || echo "FAIL $f"
done
```

## 6. Save plots for a batch of experiments

```python
from pathlib import Path
import openauc
from openauc.plotting import plot_scans

Path("figures").mkdir(exist_ok=True)
for directory in sorted(Path("data").iterdir()):
    if not directory.is_dir():
        continue
    experiment = openauc.load(directory)
    ax = plot_scans(experiment, title=experiment.metadata.experiment_id)
    ax.figure.savefig(f"figures/{directory.name}.png", dpi=150, bbox_inches="tight")
    ax.figure.clf()      # release the figure between iterations
```

No display is required; pyplot is never used.

## 7. Produce JSON validation output

```bash
uv run openauc validate examples/data/demo_experiment --readiness --json > report.json
jq '.structural.counts' report.json
```

```python
import json
print(json.dumps(experiment.validate().to_dict(), indent=2))
```

## 8. Find all ERROR findings

```python
report = experiment.validate()
for issue in report.errors:
    print(issue.code, "|", issue.message)
    print("   fix:", issue.remediation)
```

```bash
uv run openauc validate my-experiment --json \
  | jq -r '.structural.issues[] | select(.severity=="error") | .code'
```

## 9. Find all readiness blockers

```python
from openauc.models import ValidationTier

report = experiment.validate()
for tier in (ValidationTier.SV_READINESS, ValidationTier.SE_READINESS):
    print(tier.value)
    for issue in report.blocking_for(tier):
        print("   ", issue.code, "-", issue.remediation)
```

```python
assessment = experiment.assess_readiness()
for entry in assessment.entries:
    print(entry.analysis.value, entry.status.value)
    for issue in entry.blocking_issues:
        print("    blocked by", issue.code)
```

## 10. Compare an experiment before and after an AUCX round-trip

```python
import openauc

original = openauc.load("examples/data/demo_experiment")
restored = openauc.load(original.export("check.aucx", overwrite=True))
assert restored.to_dict() == original.to_dict()
print("round trip is exact")
```

To compare only the data, ignoring provenance timestamps:

```python
for key in ("metadata", "instrument", "samples", "scans", "observations"):
    assert restored.to_dict()[key] == original.to_dict()[key]
```

## 11. Create an experiment programmatically

```python
from openauc.models import (
    AUCExperiment, ExperimentMetadata, ExperimentType, Observations,
    OpticalSystem, Quantity, ScanMetadata, Unit,
)

experiment = AUCExperiment(
    metadata=ExperimentMetadata(
        experiment_id="hand-built-001",
        experiment_type=ExperimentType.SEDIMENTATION_VELOCITY,
    ),
    scans=(
        ScanMetadata(
            scan_id="scan_001", index=0,
            elapsed_time=Quantity.of(0.0, Unit.SECOND),
            optical_system=OpticalSystem.ABSORBANCE,
            rotor_speed=Quantity.of(45000.0, Unit.RPM),
            temperature=Quantity.unknown(),      # explicitly unknown
        ),
        ScanMetadata(
            scan_id="scan_002", index=1,
            elapsed_time=Quantity.of(600.0, Unit.SECOND),
            optical_system=OpticalSystem.ABSORBANCE,
            rotor_speed=Quantity.of(45000.0, Unit.RPM),
            temperature=Quantity.unknown(),
        ),
    ),
    observations=Observations.from_shared_axis(
        radius=[6.00, 6.02, 6.04],
        signal=[[0.10, 0.20, 0.30], [0.08, 0.17, 0.28]],
        scan_ids=["scan_001", "scan_002"],
        signal_unit=Unit.ABSORBANCE_UNIT,
    ),
)
print(experiment.validate_structure())
experiment.export("hand-built.aucx")
```

## 12. Work with per-scan radius vectors

```python
from openauc.models import Observations, RadiusAxisMode, Unit

observations = Observations.from_per_scan(
    radii=[[6.00, 6.02, 6.04], [6.00, 6.02]],     # differing lengths
    signals=[[0.1, 0.2, 0.3], [0.4, 0.5]],
    scan_ids=["a", "b"],
    signal_unit=Unit.FRINGE,
)
assert observations.mode is RadiusAxisMode.PER_SCAN
observations.points_per_scan()          # (3, 2)

radius, signal = observations.scan_vectors("b")   # padding removed
for scan_id, radius, signal in observations.iter_scan_vectors():
    print(scan_id, radius.tolist())
```

## Next step

- [Troubleshooting](troubleshooting.md)
- [Python API reference](../api/index.md)
