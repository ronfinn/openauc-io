# Synthetic data

`openauc.synthetic` generates reproducible, repository-safe AUC-*like* datasets
for examples, integration tests, demonstrations and performance work.

```python
from openauc.synthetic import SyntheticExperimentConfig, generate_experiment

experiment = generate_experiment(
    SyntheticExperimentConfig(
        scenario="moving-boundary",
        n_scans=20,
        n_points=300,
        seed=42,
    )
)
```

## What this is, and is not

> **Illustrative synthetic data.** The curves are closed-form shapes chosen
> because they are smooth, cheap and reproducible. They are **not** solutions of
> the Lamm equation, **not** simulations of sedimentation, and **not** a
> physically validated model of anything. No sedimentation or diffusion
> coefficient, molar mass, buoyancy term or fitted parameter is used to produce
> them, and none may be inferred from them.

A generated experiment is *structurally* valid data — useful for exercising
ingestion, validation, summaries, plotting and archiving. It is never
scientifically meaningful data. Every generated experiment carries this
statement in `metadata.notes` and in its provenance `assumptions`, so it cannot
be mistaken for a real measurement after the fact.

## Intended uses

- Fixtures for integration tests that need more than a handful of rows.
- Demonstrations and documentation examples.
- Exercising both radius-axis modes, all four value statuses and the validation
  tiers without hand-writing CSV.
- Rough performance work: generating a few hundred thousand points is fast.

**Not** intended for: benchmarking scientific algorithms, validating analysis
software, or standing in for real instrument output.

## Scenarios

| Scenario | Produces |
|----------|----------|
| `moving-boundary` | A logistic step whose midpoint advances outward with scan index. Illustrative only. |
| `equilibrium-profile` | A stationary curved profile, identical in every scan (plus optional noise). No equilibrium condition is modelled. |
| `static-profile` | A fixed ramp repeated in every scan; handy for archive and plotting tests. |
| `per-scan-radius` | Scans with distinct radius vectors of differing length, in `PER_SCAN` mode. |
| `sparse-metadata` | A valid experiment carrying explicit `MISSING`, `UNKNOWN` and `NOT_APPLICABLE` values. |
| `mixed-optics` | Several declared optical systems across scans. |
| `empty-scans` | Some scans carrying no observations at all. |
| `invalid-structure` | A deliberate cross-object inconsistency, for exercising `ValidationReport`. |

Two scenarios override the configured axis mode because they cannot be expressed
otherwise: `per-scan-radius` by definition, and `empty-scans` because the
canonical model can only represent an empty scan when each scan owns its axis.

`mixed-optics` uses `Unit.UNKNOWN` as the signal unit. An observation set
carries **one** signal unit, so any concrete unit would contradict at least one
declared optical system and raise a structural error — which is not what that
scenario exists to test. It produces a `mixed_optical_systems` warning and stays
structurally valid.

`invalid-structure` builds only objects the model permits: the second scan
metadata record repeats the first identifier, so the metadata no longer matches
the observations. It yields exactly `duplicate_scan_id` and `scan_id_mismatch`,
both archival errors. **No construction invariant is bypassed** and no
impossible object is created.

## Reproducibility

The same configuration and seed always produce the same experiment, byte for
byte through AUCX. Noise is drawn from a `numpy.random.Generator` created from
the configured seed alone:

```python
rng = np.random.default_rng(config.seed)
```

**NumPy's global random state is never read or written**, so generating data
cannot perturb anything else in your process. A test asserts this.

With `noise_level=0` the seed does not affect the data at all — the curves are
deterministic functions of the configuration. The seed is still recorded in
provenance, so two such experiments differ in their provenance while their
observations are identical.

## Configuration

| Field | Meaning |
|-------|---------|
| `scenario` | Which dataset shape to build |
| `experiment_id`, `name` | Identity of the generated experiment |
| `n_scans`, `n_points` | Size |
| `radius_min`, `radius_max` | Radial domain (`max` must exceed `min`, both positive) |
| `elapsed_seconds_step` | Spacing between scan elapsed times |
| `signal_scale` | Amplitude of the generated curve |
| `noise_level` | Standard deviation of deterministic noise; `0` disables |
| `seed` | Seed for the local generator |
| `radius_axis_mode` | `shared` or `per_scan` (some scenarios override it) |
| `optical_system`, `signal_unit`, `experiment_type` | Declared metadata |
| `metadata_completeness` | `minimal`, `typical` or `complete` |

The config is a frozen pydantic model with `extra="forbid"`, so typos and
impossible domains are rejected at construction with a clear message.

## Exporting and reloading

```python
from openauc.synthetic import write_generic_long, write_generic_wide, write_aucx

write_generic_long(experiment, "out/long")        # manifest.json + scans.csv
write_generic_wide(experiment, "out/wide")        # shared-axis only
write_aucx(experiment, "out/experiment.aucx")

restored = openauc.load("out/experiment.aucx")
assert restored.to_dict() == experiment.to_dict()
```

Manifests are built with the real `GenericManifest` models and archives with the
real AUCX writer, so the writers cannot drift away from what the readers expect.

`write_generic_wide` **refuses** a per-scan-axis experiment rather than
resampling it onto a common grid — openauc never does that. Directory writers
refuse to overwrite an existing `manifest.json` or `scans.csv` unless
`overwrite=True`.

## Limitations

- **Delimited output cannot carry the `UNKNOWN` / `MISSING` distinction.** A
  generic CSV has no way to say "explicitly unknown", so an optional column is
  written only when *every* scan has that value `PRESENT`; otherwise the column
  is omitted and reloads as absent. **AUCX preserves all four statuses exactly**,
  so use it whenever the distinction matters. Exact `to_dict()` round-trip
  equality is expected for AUCX only.
- Curves are one-dimensional in radius with no time-dependent broadening beyond
  the boundary shift; nothing diffuses.
- One sample and one cell/channel per generated experiment.
- Noise is independent Gaussian per point — not an instrument noise model.
- `invalid-structure` produces one specific pair of findings, not an exhaustive
  sweep of every possible inconsistency.

## Command line

```bash
openauc generate out/demo --scenario moving-boundary --scans 20 --points 300 --seed 42
openauc generate demo.aucx --format aucx --scenario per-scan-radius
openauc generate out/demo --overwrite --noise 0.01
```

See [the CLI reference](../cli.md). The command's help text states prominently
that its output is illustrative synthetic data and not a physically validated
simulation.
