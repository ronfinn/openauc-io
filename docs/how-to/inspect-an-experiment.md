# Inspect an experiment

**Goal:** find out what is in a dataset, without judging it.

## CLI

```bash
uv run openauc inspect examples/data/demo_experiment
uv run openauc inspect demo.aucx
uv run openauc inspect examples/data/demo_experiment --json
```

`--json` emits exactly `experiment.summary_data().to_dict()`.

## Python

```python
import openauc

experiment = openauc.load("examples/data/demo_experiment")
print(experiment.summary())            # human-readable text
summary = experiment.summary_data()    # structured, frozen, JSON-friendly
```

## What the summary carries

| Group | Fields |
|-------|--------|
| Identity | `experiment_id`, `name`, `experiment_type`, `acquired_at`, `operator` |
| Size | `n_scans`, `n_samples`, `points_per_scan`, `total_valid_observations` |
| Axes and units | `radius_axis_mode`, `radius_unit`, `signal_unit`, `signal_unit_declared` |
| Categories | `optical_systems`, `wavelengths_nm`, `cells`, `channels` and their unknown counts |
| Ranges | `radius`, `elapsed_time`, `rotor_speed`, `temperature` as `ValueRange` |
| Presence | `metadata_presence` — per field, per component |
| Origin | `provenance_available`, `parser_name`, `checksum_available` |
| Findings | `validation` counts |

## Ranges

```python
summary.radius.minimum        # float | None
summary.radius.maximum
summary.radius.unit           # declared unit, never converted
summary.radius.n_present, summary.radius.n_absent
summary.radius.render()       # '5.9 to 7.2 cm (observed)' or 'unknown'
summary.radius.is_observed    # bool
```

## Counting absence honestly

```python
for entry in summary.metadata_presence:
    print(
        entry.component, entry.field,
        "present", entry.present,
        "missing", entry.missing,
        "unknown", entry.unknown,
        "not_applicable", entry.not_applicable,
        "absent", entry.absent,
    )
```

All five kinds stay distinct. `entry.unrecorded` is the total carrying no usable
value.

## Serialising

```python
import json
print(json.dumps(summary.to_dict(), indent=2))
```

The summary is a frozen pydantic model — every collection is a tuple and no
field can be reassigned.

## What it never contains

No sedimentation or diffusion coefficient, no molecular weight, no quality
score, no inferred value. Every field is read from the model or counted. The
text form ends with an explicit statement that no scientific claim is made.

## Next step

- [Interpret validation findings](interpret-validation-findings.md)
