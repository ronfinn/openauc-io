# Complete CLI workflow

**Goal:** generate, inspect, validate and archive without writing Python.

**Prerequisites:** [Installation](../getting-started/installation.md). Commands
run **from the repository root**. Drop the `uv run` prefix if you have
activated `.venv` or installed the wheel elsewhere.

A runnable version is
[`examples/06_cli_usage.py`](https://github.com/ronfinn/openauc-io/blob/main/examples/06_cli_usage.py).

## 1. Confirm the installation

```bash
uv run openauc version
```

```text
0.1.0a1
```

## 2. See what can be read

```bash
uv run openauc formats
```

```text
aucx  AUCX archive
  suffixes:    .aucx
  layouts:     zip-of-parts (JSON metadata + NumPy .npy arrays)
  limitations: format version 1.0 only; archives are never migrated silently
               every checksum is verified before a model is built
               checksums establish integrity, not authenticity
  docs:        docs/formats/aucx.md
generic-long  Generic long-format delimited
  ...
```

Machine-readable:

```bash
uv run openauc formats --json | jq -r '.formats[].format_id'
```

## 3. Get some data

Either use the repository's demo data at `examples/data/demo_experiment`, or
generate a dataset:

```bash
uv run openauc generate work/demo --scenario moving-boundary --scans 12 --points 200 --seed 7
```

```text
wrote work/demo
  scenario: moving-boundary  seed: 7  scans: 12
  note: illustrative synthetic data; not a physically validated simulation
```

That writes `work/demo/manifest.json` and `work/demo/scans.csv`.

## 4. Inspect

```bash
uv run openauc inspect work/demo
```

Prints the structural summary. For scripting:

```bash
uv run openauc inspect work/demo --json | jq '.n_scans, .total_valid_observations'
```

```json
12
2400
```

## 5. Validate

```bash
uv run openauc validate work/demo
echo "exit code: $?"
```

```text
structural validation: OK (no issues)

note: structural validation only; no claim is made about scientific validity
or data quality.
exit code: 0
```

Add readiness:

```bash
uv run openauc validate work/demo --readiness
```

## 6. Convert to AUCX

```bash
uv run openauc convert work/demo work/demo.aucx
```

```text
wrote work/demo.aucx (18244 bytes)
```

Running it again refuses, with exit code `3`:

```bash
uv run openauc convert work/demo work/demo.aucx
echo "exit code: $?"
```

```text
error: work/demo.aucx already exists; pass --overwrite to replace it
exit code: 3
```

## 7. Verify the archive

```bash
uv run openauc validate work/demo.aucx
```

```text
archive integrity: OK (work/demo.aucx)
structural validation: OK (no issues)
...
```

Integrity is checked **first**. A corrupt container stops the run with exit
code `2` before the experiment is examined.

!!! warning "Integrity is not authenticity"
    A verified archive is one whose bytes are unchanged since it was written.
    AUCX carries no signature and proves nothing about who produced it.

## 8. Script it

Exit codes make the CLI composable:

```bash
#!/usr/bin/env bash
set -euo pipefail

for dir in data/*/; do
    if uv run openauc validate "$dir" >/dev/null 2>&1; then
        uv run openauc convert "$dir" "archives/$(basename "$dir").aucx" --overwrite
        echo "archived $dir"
    else
        echo "SKIPPED (validation failed): $dir" >&2
    fi
done
```

| Code | Meaning |
|------|---------|
| 0 | Success; where validation ran, it passed |
| 1 | Structural validation failed |
| 2 | Input, parsing, archive or configuration error |
| 3 | Output exists and `--overwrite` was not given |

Details: [Exit codes](../cli/exit-codes.md).

## Common failure modes

| Symptom | Cause | Fix |
|---------|-------|-----|
| `command not found: openauc` | Not in the project environment | Use `uv run`, or activate `.venv` |
| `No such command 'generate'` | Stale checkout | `git pull && uv sync --all-groups` |
| exit 2 on a directory | No manifest, or unreadable data | `openauc inspect` for the message |
| exit 3 | Output exists | Add `--overwrite` |

## Next step

- Per-command detail: [CLI reference](../cli/index.md)
- [Recipes](../how-to/recipes.md)
