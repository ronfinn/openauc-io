# Generate synthetic data

**Goal:** produce reproducible datasets for tests, demos and experimentation.

**Prerequisites:** [Installation](../getting-started/installation.md).

!!! danger "Illustrative data only"
    Generated curves are closed-form shapes chosen for being smooth, cheap and
    reproducible. They are **not** Lamm-equation solutions, **not** simulations
    of sedimentation, **not** instrument noise models, and **not**
    scientifically validated. No physical parameter is used to produce them and
    none may be inferred from them.

    Every generated experiment records this in `metadata.notes` and in its
    provenance, so it cannot later be mistaken for a measurement.

## Python

```python
from openauc.synthetic import SyntheticExperimentConfig, generate_experiment

config = SyntheticExperimentConfig(
    scenario="moving-boundary",
    experiment_id="demo-001",
    n_scans=20,
    n_points=300,
    seed=42,
)
experiment = generate_experiment(config)
```

`generate_experiment` returns an ordinary `AUCExperiment` — everything in the
[Python workflow](python-workflow.md) applies to it.

## CLI

```bash
uv run openauc generate demo.aucx --format aucx --scenario moving-boundary \
  --scans 20 --points 300 --seed 42
```

```bash
uv run openauc generate work/demo --format generic-long --scenario sparse-metadata
```

## The eight scenarios

| Scenario | Demonstrates | Axis mode | Structural result | Notable findings |
|----------|--------------|-----------|-------------------|------------------|
| `moving-boundary` | A step advancing outward between scans | shared | valid | — |
| `equilibrium-profile` | A stationary curved profile | shared | valid | — |
| `static-profile` | Identical scans; archive/plot tests | shared | valid | — |
| `per-scan-radius` | Distinct radius vectors per scan | **per-scan** | valid | — |
| `sparse-metadata` | Explicit missing/unknown/not-applicable | shared | valid | absence warnings |
| `mixed-optics` | Several declared optical systems | shared | valid | `mixed_optical_systems` |
| `empty-scans` | Scans with no observations | **per-scan** | valid | `empty_scan` |
| `invalid-structure` | Cross-object inconsistency | shared | **invalid** | `duplicate_scan_id`, `scan_id_mismatch` |

Two scenarios override the configured axis mode because they cannot be
expressed otherwise, exposed as `config.effective_radius_axis_mode`.

`mixed-optics` deliberately uses `Unit.UNKNOWN` as the signal unit: an
observation set carries one unit, so any concrete unit would contradict a
declared optical system and raise a structural error, which is not what that
scenario is for.

`invalid-structure` builds only objects the model permits — the second metadata
record repeats the first identifier. **No construction invariant is bypassed.**

## Reproducibility

```python
a = generate_experiment(config)
b = generate_experiment(config)
assert a.to_dict() == b.to_dict()  # identical
```

Noise is drawn from `numpy.random.default_rng(config.seed)`. **NumPy's global
random state is never read or written**, so generating data cannot perturb
anything else in your process.

With `noise_level=0` the seed does not affect the data at all — the curves are
deterministic functions of the configuration. The seed is still recorded in
provenance, so two such experiments have identical observations and different
provenance.

## Configuration reference

| Field | Type | Default | Meaning |
|-------|------|---------|---------|
| `scenario` | `Scenario` | `moving-boundary` | Which shape to build |
| `experiment_id` | `str` | `"synthetic-001"` | Identity |
| `name` | `str \| None` | set | Display name |
| `n_scans` | `int` ≥ 1 | 10 | Number of scans |
| `n_points` | `int` ≥ 1 | 100 | Radial points per scan |
| `radius_min` / `radius_max` | `float` > 0 | 5.9 / 7.2 | Radial domain; max must exceed min |
| `elapsed_seconds_step` | `float` ≥ 0 | 600.0 | Spacing between scan times |
| `signal_scale` | `float` > 0 | 1.0 | Curve amplitude |
| `noise_level` | `float` ≥ 0 | 0.0 | Noise standard deviation; 0 disables |
| `seed` | `int` ≥ 0 | 0 | Seed for the local generator |
| `radius_axis_mode` | `RadiusAxisMode` | `shared` | Some scenarios override this |
| `optical_system` | `OpticalSystem` | `absorbance` | Declared per scan |
| `signal_unit` | `Unit` | `AU` | Declared for the set |
| `experiment_type` | `ExperimentType` | `sedimentation_velocity` | Drives readiness routing |
| `metadata_completeness` | `MetadataCompleteness` | `typical` | `minimal`, `typical` or `complete` |

The config is frozen with `extra="forbid"`, so typos and impossible domains are
rejected at construction:

```python
SyntheticExperimentConfig(radius_min=7.0, radius_max=6.0)
# ValidationError: radius_max (6.0) must be greater than radius_min (7.0)
```

## Exporting

```python
from openauc.synthetic import write_generic_long, write_generic_wide, write_aucx

write_generic_long(experiment, "out/long")  # manifest.json + scans.csv
write_generic_wide(experiment, "out/wide")  # shared-axis only
write_aucx(experiment, "out/demo.aucx")
```

`write_generic_wide` **refuses** a per-scan-axis experiment rather than
resampling it. All three refuse to overwrite unless `overwrite=True`.

## Limitations

- Curves are one-dimensional in radius with no diffusive broadening: the
  boundary shifts, nothing spreads.
- Noise is independent Gaussian per point.
- One sample and one cell/channel per generated experiment.
- `invalid-structure` produces one specific finding pair, not a sweep.

## Next step

- [Reproduce synthetic datasets](../how-to/reproduce-synthetic-datasets.md)
- [Synthetic data concepts](../concepts/synthetic-data.md)
