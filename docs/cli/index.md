# CLI reference

The `openauc` command mirrors the Python API and adds nothing scientific. It
loads, describes, validates, archives and generates — and makes no claim about
scientific validity, data quality or suitability for analysis.

```bash
uv run openauc --help
```

## Commands

| Command | Purpose |
|---------|---------|
| [`version`](version.md) | Print the installed version |
| [`formats`](formats.md) | List the formats this build can read |
| [`generate`](generate.md) | Write an illustrative synthetic dataset |
| [`inspect`](inspect.md) | Print an experiment's factual structural summary |
| [`validate`](validate.md) | Report archival, structural and readiness findings |
| [`convert`](convert.md) | Write an experiment to an AUCX archive |

## Conventions

**`INPUT`** is uniformly "an experiment directory, a data file, or an `.aucx`
archive" — the same dispatch `openauc.load` performs. You never have to tell the
CLI which kind of input you have.

**`--json`** is available wherever structured output is useful, so the CLI
composes with `jq` and friends.

**[Exit codes](exit-codes.md)** are stable and documented, which is what makes
the CLI scriptable.

**Errors print one line.** Expected domain errors produce a single
`error: ...` message on stderr and a documented exit code — never a traceback.

## Running it

From a clone, with the project environment:

```bash
uv run openauc <command>
```

From an installed wheel, with that environment active:

```bash
openauc <command>
```

Every example in these docs uses the `uv run` form and is run from the
repository root.

## What the CLI does not do

No sedimentation-velocity or equilibrium analysis, no fitting, no quality
scoring, **no plotting subcommand** (plotting stays a Python API), no batch or
glob input, and no AUCX → CSV conversion.
