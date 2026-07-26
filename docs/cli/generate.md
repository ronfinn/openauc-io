# `openauc generate`

Write an **illustrative synthetic dataset** for testing and demonstration.

!!! danger "The output is invented data"
    It is **not** a physically validated simulation of an analytical
    ultracentrifugation experiment, **not** a Lamm-equation solution, and
    carries no sedimentation coefficient, molar mass or any other physical
    parameter. Nothing scientific may be inferred from it.

## Syntax

```bash
openauc generate OUTPUT [--scenario S] [--scans N] [--points N] [--seed N]
                        [--noise X] [--format F] [--overwrite] [--json]
```

## Arguments

| Argument | Meaning |
|----------|---------|
| `OUTPUT` | A **directory** for CSV output, or an `.aucx` **file** |

## Options

| Option | Default | Meaning |
|--------|---------|---------|
| `--scenario` | `moving-boundary` | Which scenario to generate (below) |
| `--scans` | `10` | Number of scans |
| `--points` | `100` | Radial points per scan |
| `--seed` | `0` | Seed; the same seed always produces the same dataset |
| `--noise` | `0.0` | Deterministic noise level; `0` disables |
| `--format` | `generic-long` | `generic-long`, `generic-wide` or `aucx` |
| `--overwrite` | off | Replace existing output |
| `--json` | off | Emit structured JSON |

## Scenarios

| Scenario | Demonstrates | Axis mode | Structural result |
|----------|--------------|-----------|-------------------|
| `moving-boundary` | A step advancing outward between scans | shared | valid |
| `equilibrium-profile` | A stationary curved profile | shared | valid |
| `static-profile` | Identical scans | shared | valid |
| `per-scan-radius` | Distinct radius vectors per scan | per-scan | valid |
| `sparse-metadata` | Explicit missing/unknown/not-applicable | shared | valid |
| `mixed-optics` | Several declared optical systems | shared | valid |
| `empty-scans` | Scans with no observations | per-scan | valid |
| `invalid-structure` | Cross-object inconsistency | shared | **invalid** |

## Examples

Generate an archive:

```bash
uv run openauc generate demo.aucx --format aucx \
  --scenario moving-boundary --scans 20 --points 300 --seed 42
```

```text
wrote demo.aucx
  scenario: moving-boundary  seed: 42  scans: 20
  note: illustrative synthetic data; not a physically validated simulation
```

Generate CSV plus manifest:

```bash
uv run openauc generate work/demo --format generic-long --scenario sparse-metadata
```

That writes `work/demo/manifest.json` and `work/demo/scans.csv`.

With noise, as JSON:

```bash
uv run openauc generate demo.aucx --format aucx --noise 0.01 --overwrite --json
```

```json
{
  "output": "demo.aucx",
  "scenario": "moving-boundary",
  "format": "aucx",
  "seed": 0,
  "n_scans": 10,
  "synthetic": true,
  "note": "illustrative synthetic data; not a physically validated simulation"
}
```

## Reproducibility

The same options always produce the same experiment. Noise comes from a local
`numpy.random.Generator` seeded from `--seed`; **NumPy's global random state is
never touched**.

## Exit codes

| Code | When |
|------|------|
| 0 | The dataset was written |
| 2 | Unknown scenario or format, or an invalid configuration |
| 3 | The output exists and `--overwrite` was not given |

## Common errors

| Message | Exit | Cause |
|---------|------|-------|
| `unknown scenario 'x'; choose one of [...]` | 2 | Typo — the message lists the valid names |
| `unknown format 'parquet'; choose one of [...]` | 2 | Only three formats exist |
| `invalid configuration: ...` | 2 | e.g. `--scans 1` with `invalid-structure` |
| `wide layout needs one shared radius axis ...` | 2 | `--format generic-wide` with a per-scan scenario |
| `refusing to overwrite existing file` | 3 | Add `--overwrite` |

## Notes

`--format generic-wide` **fails** for `per-scan-radius` and `empty-scans` rather
than resampling onto a common grid — openauc never does that. Use
`generic-long` or `aucx` for those scenarios.

See [Generate synthetic data](../tutorials/generate-synthetic-data.md) and
[Synthetic data](../concepts/synthetic-data.md).
