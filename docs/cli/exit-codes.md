# Exit codes

Stable, documented, and the reason the CLI is scriptable.

| Code | Name | Meaning |
|------|------|---------|
| `0` | `OK` | Success; where validation ran, structural validation passed |
| `1` | `VALIDATION_FAILED` | Structural validation reported at least one `ERROR` finding |
| `2` | `INPUT_ERROR` | The input could not be read, parsed, verified or configured |
| `3` | `OUTPUT_EXISTS` | The output exists and `--overwrite` was not given |

They are defined as `openauc.cli.ExitCode`, an `IntEnum`.

## Why 1 and 2 are separate

"This file is not an experiment" and "this experiment has a structural problem"
are different outcomes that a script must handle differently. Code `2` means
openauc could not get far enough to judge; code `1` means it judged and found a
structural error.

A **corrupt archive is code 2**, not 1 — a broken container is an input problem.

## Why 3 is separate

So a wrapper can decide whether to retry with `--overwrite`, without parsing
error text.

## Which commands produce which

| Command | 0 | 1 | 2 | 3 |
|---------|---|---|---|---|
| `version` | ✅ | | | |
| `formats` | ✅ | | | |
| `inspect` | ✅ | | ✅ | |
| `validate` | ✅ | ✅ | ✅ | |
| `convert` | ✅ | | ✅ | ✅ |
| `generate` | ✅ | | ✅ | ✅ |

`inspect` never returns 1: it describes, it does not judge.

## Scripting

```bash
#!/usr/bin/env bash
set -euo pipefail

for dir in data/*/; do
    if uv run openauc validate "$dir" >/dev/null 2>&1; then
        uv run openauc convert "$dir" "archives/$(basename "$dir").aucx" --overwrite
    else
        case $? in
            1) echo "structural failure: $dir" >&2 ;;
            2) echo "unreadable:        $dir" >&2 ;;
            *) echo "unexpected:        $dir" >&2 ;;
        esac
    fi
done
```

## What exit 0 does not mean

!!! warning
    Exit `0` from `validate` means the data are **structurally consistent**. It
    is never a claim that the experiment is scientifically valid, that the data
    are good, or that an analysis would be meaningful.

    Readiness findings never affect the exit code. An experiment can exit `0`
    while every readiness tier is `BLOCKED` — that is normal for a dataset with
    sparse metadata.

## Errors never print tracebacks

Expected domain errors produce a single line on stderr:

```text
error: work/demo.aucx already exists; pass --overwrite to replace it
```

Unexpected exceptions are deliberately *not* caught — a genuine bug should still
be loud.
