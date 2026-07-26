# `openauc validate`

Report archival and structural findings for an input, optionally including
analysis readiness.

## Syntax

```bash
openauc validate INPUT [--readiness] [--json]
```

## Arguments

| Argument | Meaning |
|----------|---------|
| `INPUT` | Experiment directory, data file, or `.aucx` archive |

## Options

| Option | Meaning |
|--------|---------|
| `--readiness` | Also report readiness findings and per-workflow status |
| `--json` | Emit structured JSON |

## Example: passing

```bash
uv run openauc validate examples/data/demo_experiment
echo "exit: $?"
```

```text
structural validation: OK (no issues)

note: structural validation only; no claim is made about scientific validity
or data quality.
exit: 0
```

## Example: with readiness

```bash
uv run openauc validate examples/data/demo_experiment --readiness
```

```text
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

## Example: failing

```bash
uv run openauc validate broken-experiment
echo "exit: $?"
```

```text
structural validation: FAILED (1 error(s), 0 warning(s))
  - ERROR non_physical_radius: radius values must be positive; found values <= 0
...
exit: 1
```

## Archives

For an `.aucx` input, **integrity is verified first**:

```bash
uv run openauc validate demo.aucx
```

```text
archive integrity: OK (demo.aucx)
structural validation: OK (no issues)
```

A broken container exits `2` without pretending to have examined the
experiment — a corrupt archive is an *input* problem, not a validation failure.

## JSON output

```bash
uv run openauc validate examples/data/demo_experiment --readiness --json
```

```json
{
  "path": "examples/data/demo_experiment",
  "structural": {
    "is_valid": true,
    "counts": {"error": 0, "warning": 0, "info": 0},
    "issues": []
  },
  "all_tiers": { "...": "every tier, every severity" },
  "readiness": {
    "entries": [
      {"analysis": "sedimentation_velocity", "status": "potentially_ready", "...": "..."},
      {"analysis": "sedimentation_equilibrium", "status": "not_applicable", "...": "..."},
      {"analysis": "scientific_suitability", "status": "not_assessed", "...": "..."}
    ]
  }
}
```

`all_tiers` and `readiness` appear only with `--readiness`.

Useful queries:

```bash
uv run openauc validate my-experiment --json | jq '.structural.counts'
uv run openauc validate my-experiment --json \
  | jq -r '.structural.issues[] | select(.severity=="error") | .code'
```

## Exit codes

| Code | When |
|------|------|
| 0 | Structural validation passed |
| 1 | Structural validation reported at least one `ERROR` |
| 2 | The input could not be read, parsed or verified |

Separating 1 from 2 matters: "this file is not an experiment" and "this
experiment has a structural problem" need different handling.

```bash
if uv run openauc validate my-experiment >/dev/null; then
    uv run openauc convert my-experiment archive.aucx
fi
```

## What exit 0 does and does not mean

!!! warning
    Exit `0` means the data are **structurally consistent** — scans and
    observations correspond unambiguously and nothing contradicts itself.

    It is **never** a statement that the experiment is scientifically sound,
    that the data are good, or that any analysis is appropriate. Readiness
    findings do not affect the exit code at all.

## Notes

Warnings never change the exit code. Absent metadata is reported, not required —
see [Interpret validation findings](../how-to/interpret-validation-findings.md).
