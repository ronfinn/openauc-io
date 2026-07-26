# `openauc convert`

Write an experiment to an AUCX archive.

## Syntax

```bash
openauc convert INPUT OUTPUT [--overwrite] [--json]
```

## Arguments

| Argument | Meaning |
|----------|---------|
| `INPUT` | Experiment directory, data file, or `.aucx` archive |
| `OUTPUT` | Destination archive. **Must end in `.aucx`** |

## Options

| Option | Meaning |
|--------|---------|
| `--overwrite` | Replace the output if it exists |
| `--json` | Emit structured JSON about what was written |

## Example

```bash
uv run openauc convert examples/data/demo_experiment demo.aucx
```

```text
wrote demo.aucx (18244 bytes)
```

## JSON output

```bash
uv run openauc convert examples/data/demo_experiment demo.aucx --overwrite --json
```

```json
{
  "input": "examples/data/demo_experiment",
  "output": "demo.aucx",
  "n_scans": 4,
  "bytes": 18244
}
```

## Archive in, archive out

```bash
uv run openauc convert old.aucx new.aucx
```

The input is fully verified on read, so a successful rewrite proves the original
was intact. This is the intended way to verify and re-write an archive.

## Overwrite protection

```bash
uv run openauc convert examples/data/demo_experiment demo.aucx
echo "exit: $?"
```

```text
error: demo.aucx already exists; pass --overwrite to replace it
exit: 3
```

Writes are atomic: a temporary sibling file is written, verified in full, and
only then moved into place. A failure never leaves a partial archive.

## What is preserved

Everything the canonical model holds — both radius modes, masks, dtypes, array
shapes, scan order, declared units, provenance, and all four value statuses.
Nothing is interpolated, resampled, sorted or unit-converted.

## Exit codes

| Code | When |
|------|------|
| 0 | The archive was written |
| 2 | The input could not be read, or `OUTPUT` does not end in `.aucx` |
| 3 | `OUTPUT` exists and `--overwrite` was not given |

## Common errors

| Message | Exit | Fix |
|---------|------|-----|
| `output must be an .aucx archive, got 'out.csv'` | 2 | Use a `.aucx` suffix |
| `already exists; pass --overwrite to replace it` | 3 | Add `--overwrite` |
| `path does not exist` | 2 | Check the input path |

## Notes

There is **no AUCX → CSV** direction. It would need a documented lossiness
policy, since a delimited file cannot carry per-scan axes or the
unknown/missing distinction.
