# Command-line interface

The `openauc` command mirrors the Python API. It adds nothing scientific: it
loads, describes, validates and archives, and makes no claim about scientific
validity, data quality or suitability for analysis.

```bash
uv run openauc --help
```

## Commands

### `openauc version`

Prints the installed version.

### `openauc formats`

Lists every format this build can read, with its stable format id, suffixes,
layouts and limitations.

```bash
openauc formats
openauc formats --json
```

### `openauc inspect INPUT`

Loads an experiment directory, data file or `.aucx` archive and prints the
factual structural summary — counts, ranges, units, metadata presence. `--json`
emits the same facts as `experiment.summary_data().to_dict()`.

```bash
openauc inspect path/to/experiment
openauc inspect experiment.aucx --json
```

### `openauc validate INPUT`

Reports archival and structural findings. For an `.aucx` input, **archive
integrity is verified first** — a broken container stops the run before the
model is examined.

```bash
openauc validate path/to/experiment
openauc validate path/to/experiment --readiness
openauc validate experiment.aucx --readiness --json
```

`--readiness` adds analysis-readiness findings and the per-workflow status,
including the permanent `scientific_suitability: not_assessed` entry.

### `openauc convert INPUT OUTPUT`

Writes an experiment to an AUCX archive. Accepts generic delimited input or an
existing archive — archive-in/archive-out is useful for verifying and rewriting
one. The output must end in `.aucx`.

```bash
openauc convert path/to/experiment experiment.aucx
openauc convert old.aucx new.aucx --overwrite
openauc convert path/to/experiment experiment.aucx --json
```

Model data is preserved exactly: nothing is interpolated, resampled, sorted or
unit-converted. An existing output is refused unless `--overwrite` is supplied.

## Exit codes

| Code | Meaning |
|------|---------|
| `0` | Success; where validation ran, structural validation passed. |
| `1` | Structural validation reported at least one `ERROR` finding. |
| `2` | The input could not be read, parsed or verified. |
| `3` | The output already exists and `--overwrite` was not given. |

Codes are stable and scriptable:

```bash
if openauc validate path/to/experiment >/dev/null; then
    openauc convert path/to/experiment experiment.aucx
fi
```

Expected domain errors print one clear `error: ...` line to stderr and exit with
the code above — **never a traceback**.

## What the CLI does not do

No sedimentation-velocity or equilibrium analysis, no fitting, no quality
scoring, no plotting subcommand, and no vendor format conversion. Exit code `0`
from `validate` means the data is structurally consistent; it is never a
statement that the experiment is scientifically sound.
