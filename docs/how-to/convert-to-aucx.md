# Convert CSV/TSV to AUCX

**Goal:** turn a delimited experiment into a checksummed archive.

## CLI

```bash
uv run openauc convert examples/data/demo_experiment demo.aucx
```

```text
wrote demo.aucx (18244 bytes)
```

The output must end in `.aucx`. An existing file is refused with exit code `3`
unless `--overwrite` is given:

```bash
uv run openauc convert examples/data/demo_experiment demo.aucx --overwrite
uv run openauc convert examples/data/demo_experiment demo.aucx --json
```

## Python

```python
import openauc

experiment = openauc.load("examples/data/demo_experiment")
experiment.export("demo.aucx")
```

## Archive in, archive out

`convert` also accepts an archive, which is how you verify and rewrite one:

```bash
uv run openauc convert old.aucx new.aucx
```

The input is fully verified on read, so a successful rewrite proves the original
was intact.

## What is preserved

Everything the canonical model holds: both radius modes, masks, dtypes, array
shapes, scan order, declared units, provenance, and all four value statuses.

```python
restored = openauc.load("demo.aucx")
assert restored.to_dict() == experiment.to_dict()
```

Nothing is interpolated, resampled, sorted or unit-converted.

!!! note "Going the other way"
    There is no AUCX → CSV command. It would need a documented lossiness policy,
    since a delimited file cannot carry per-scan axes or the unknown/missing
    distinction.

## Batch conversion

```bash
#!/usr/bin/env bash
set -euo pipefail
mkdir -p archives
for dir in data/*/; do
    name=$(basename "$dir")
    if uv run openauc validate "$dir" >/dev/null 2>&1; then
        uv run openauc convert "$dir" "archives/${name}.aucx" --overwrite
        echo "ok: $name"
    else
        echo "SKIPPED (validation failed): $name" >&2
    fi
done
```

## Common failure modes

| Symptom | Exit | Fix |
|---------|------|-----|
| `output must be an .aucx archive` | 2 | Give the output a `.aucx` suffix |
| `already exists; pass --overwrite` | 3 | Add `--overwrite` |
| Input error before writing | 2 | `openauc inspect` the input for the message |

## Next step

- [Verify an AUCX archive](verify-an-aucx-archive.md)
