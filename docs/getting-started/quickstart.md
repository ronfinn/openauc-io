# Five-minute quickstart

**Goal:** generate a dataset, inspect it, validate it, plot it and archive it —
without needing any input files of your own.

**Prerequisites:** a working installation
([Installation](installation.md)). All commands run **from the repository
root**.

## The fastest path: the CLI

### 1. Generate a dataset

```bash
uv run openauc generate demo.aucx \
  --format aucx \
  --scenario moving-boundary \
  --scans 20 \
  --points 300 \
  --seed 42
```

Expected output:

```text
wrote demo.aucx
  scenario: moving-boundary  seed: 42  scans: 20
  note: illustrative synthetic data; not a physically validated simulation
```

!!! warning "This data is invented"
    The generated curves are illustrative shapes. They are **not**
    Lamm-equation solutions, not simulations of sedimentation, and carry no
    physical parameters. Nothing scientific may be inferred from them. See
    [Synthetic data](../concepts/synthetic-data.md).

The same `--seed` always produces the same file, so this is reproducible.

### 2. Inspect it

```bash
uv run openauc inspect demo.aucx
```

You get a factual structural summary — identity, counts, units, ranges,
metadata presence:

```text
Experiment: synthetic-001 - Synthetic illustrative dataset
  Type: sedimentation_velocity
  Scans: 20
  Samples: 1
  Optical systems: absorbance
  Radius axis: shared
  Radius unit: cm
  Signal unit: AU
  Radius range: 5.9 to 7.2 cm (observed)
  Elapsed time: 0 to 11400 s (observed)
  Points per scan: 300 (uniform)
  Total observations: 6000
  ...
  Note: structural summary only; no assessment of scientific validity or
  suitability for analysis.
```

### 3. Validate it

```bash
uv run openauc validate demo.aucx --readiness
```

```text
archive integrity: OK (demo.aucx)
structural validation: OK (no issues)

readiness (metadata presence only):
  - sedimentation_velocity: potentially_ready - required metadata is present;
    scientific suitability is not assessed
  - sedimentation_equilibrium: not_applicable - the experiment is declared as
    sedimentation velocity
  - scientific_suitability: not_assessed - openauc does not assess scientific
    validity, data quality or suitability for sedimentation analysis, and never
    will as part of validation.

note: structural validation only; no claim is made about scientific validity
or data quality.
```

Exit code `0` means structural validation passed. It does **not** mean the data
are scientifically sound — see [Exit codes](../cli/exit-codes.md).

## The same thing in Python

```python
import openauc
from openauc.synthetic import SyntheticExperimentConfig, generate_experiment
from openauc.plotting import plot_scans

config = SyntheticExperimentConfig(  # (1)!
    scenario="moving-boundary",
    n_scans=20,
    n_points=300,
    seed=42,
)

experiment = generate_experiment(config)  # (2)!

print(experiment.summary())  # (3)!

report = experiment.validate()  # (4)!
readiness = experiment.assess_readiness()  # (5)!

ax = plot_scans(experiment)  # (6)!
ax.figure.savefig("synthetic-scans.png")  # (7)!

experiment.export("synthetic.aucx")  # (8)!
restored = openauc.load("synthetic.aucx")  # (9)!
assert restored.to_dict() == experiment.to_dict()  # (10)!
```

1. A frozen `SyntheticExperimentConfig`. Invalid combinations (e.g.
   `radius_max <= radius_min`) are rejected here, with a clear message.
2. Returns an `AUCExperiment` — the canonical in-memory model. Deterministic
   for a given config and seed.
3. Returns `str`: a human-readable structural summary. Prints counts, ranges
   and units, and ends with an explicit no-scientific-claim note.
4. Returns a `ValidationReport` across all four tiers. It never raises.
5. Returns a `ReadinessAssessment` — metadata presence per workflow, plus a
   permanent `scientific_suitability: NOT_ASSESSED` entry.
6. Returns a `matplotlib.axes.Axes` with one line per scan. No pyplot is used,
   so this works headless.
7. The figure is reachable as `ax.figure`. Writing a PNG needs no display.
8. Writes an AUCX archive: atomic, deterministic, checksummed.
9. `openauc.load` dispatches on the `.aucx` suffix and verifies every checksum
   before building a model.
10. AUCX round-trips the canonical model exactly, so the dicts are equal.

Run it, and you get:

```text
Experiment: synthetic-001 - Synthetic illustrative dataset
...
```

plus `synthetic-scans.png` and `synthetic.aucx` in the current directory.

## What just happened

| Step | Concept |
|------|---------|
| `generate_experiment` | [Synthetic data](../concepts/synthetic-data.md) |
| `summary()` | Structural facts only, never a verdict |
| `validate()` | [Validation tiers](../concepts/validation-tiers.md) |
| `assess_readiness()` | [Analysis readiness](../concepts/analysis-readiness.md) |
| `plot_scans()` | [Plotting](../concepts/plotting.md) — no interpolation |
| `export()` / `load()` | [AUCX](../formats/aucx.md) |

## Common failure modes

| Symptom | Fix |
|---------|-----|
| `error: ... already exists; pass --overwrite` (exit 3) | Add `--overwrite`, or choose a new filename |
| `No such command 'generate'` | Update your checkout: `git pull && uv sync --all-groups` |
| Plot window never appears | Expected — `plot_scans` never opens a window. Save the figure, or pass your own pyplot axes |

## Next step

- With your own data: [Your first experiment](first-experiment.md)
- Deeper: [Complete Python workflow](../tutorials/python-workflow.md)
