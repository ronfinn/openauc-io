# `openauc inspect`

Load an input and print its factual structural summary.

## Syntax

```bash
openauc inspect INPUT [--json]
```

## Arguments

| Argument | Meaning |
|----------|---------|
| `INPUT` | Experiment directory, data file, or `.aucx` archive |

## Options

| Option | Meaning |
|--------|---------|
| `--json` | Emit `summary_data().to_dict()` as JSON |

## Example

```bash
uv run openauc inspect examples/data/demo_experiment
```

```text
Experiment: demo-sv-001 - Demonstration velocity run
  Type: sedimentation_velocity
  Acquired: unknown
  Operator: example
  Scans: 4
  Samples: 1
  Optical systems: absorbance
  Radius axis: shared
  Radius unit: cm
  Signal unit: AU
  Radius range: 5.9 to 6.12 cm (observed)
  Elapsed time: 0 to 2700 s (observed)
  Points per scan: 12 (uniform)
  Total observations: 48
  Wavelengths: 280 nm
  Cells: 1
  Channels: A
  Rotor speed: 45000 to 45000 rpm (observed)
  Temperature: 20 to 20 degC (observed)
  Provenance: recorded (generic-long)
  Source checksum: recorded
  Validation: 0 error(s), 0 warning(s), 0 info
  Note: structural summary only; no assessment of scientific validity or suitability for analysis.
```

## JSON output

```bash
uv run openauc inspect examples/data/demo_experiment --json | jq '.n_scans, .signal_unit'
```

```json
4
"AU"
```

The JSON is exactly `experiment.summary_data().to_dict()`, so anything
documented for [`ExperimentSummary`](../api/summaries.md) appears here.

## Archives

```bash
uv run openauc inspect demo.aucx
```

Checksums are verified as part of loading.

## Exit codes

| Code | When |
|------|------|
| 0 | The input loaded and the summary printed |
| 2 | The input could not be read, parsed or verified |

`inspect` never fails on validation findings — use
[`validate`](validate.md) for that.

## Common errors

| Message | Cause |
|---------|-------|
| `error: ...: path does not exist` | Wrong path |
| `error: ...: no manifest found in ...` | The directory has no manifest |
| `error: ...: checksum mismatch` | Corrupt archive |

## Notes

The summary describes structure and metadata only. It makes **no** scientific
claim, and says so in its final line.
