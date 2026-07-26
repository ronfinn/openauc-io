# Troubleshoot common errors

Organised by what you actually see. Each entry gives the likely cause, how to
confirm it, the fix, and whether data is at risk.

## Installation and environment

### `command not found: openauc`

**Cause:** the console script is not on your `PATH` — you are outside the
project environment.

**Confirm:** `which openauc` prints nothing.

**Fix:** prefix commands with `uv run`, from the repository root:

```bash
uv run openauc version
```

Or activate the environment: `source .venv/bin/activate`.

**Data at risk:** none.

### `No such command 'generate'` (or another missing command)

**Cause:** an older checkout that predates the command.

**Confirm:**

```bash
uv run openauc --help          # does the command appear?
uv run openauc version         # expect 0.1.0a1
```

**Fix:**

```bash
git pull
uv sync --all-groups
```

**Data at risk:** none.

### `ModuleNotFoundError: No module named 'openauc'`

**Cause:** running a bare `python` outside the project environment.

**Confirm:** `which python` is not the project `.venv`.

**Fix:** `uv run python your_script.py`, or install the wheel into the
environment you are using ([Installation](../getting-started/installation.md)).

**Data at risk:** none.

## Loading delimited data

### `ManifestError: no manifest found in ...`

**Cause:** the directory has no `manifest.json`, `manifest.yaml` or
`manifest.yml`.

**Confirm:** `ls my-experiment/`.

**Fix:** add one — [Create a manifest](create-a-manifest.md). `openauc` does
not search recursively; the manifest must sit beside the data file.

**Data at risk:** none.

### `AmbiguousFormatError: ... contains both a JSON and a YAML manifest`

**Cause:** two manifests, and openauc will not pick one for you.

**Fix:** remove one, or name the one you want:

```python
openauc.load("my-experiment", manifest="my-experiment/manifest.json")
```

**Data at risk:** none.

### `ManifestError: data_file '...' resolves outside the experiment directory`

**Cause:** `data_file` uses an absolute path, `..`, or a drive letter. This is
refused deliberately — a manifest must not reach outside its own directory.

**Fix:** put the data file beside the manifest and use a plain relative name:

```json
{ "data_file": "scans.csv" }
```

**Data at risk:** none.

### `UnsupportedFormatError` / `AmbiguousFormatError` on detection

**Cause:** no parser is confident enough, or two are within the tie margin.

**Fix:** declare the format explicitly:

```json
{ "format": "generic-long" }
```

or `openauc.load(path, format="generic-long")`.

**Data at risk:** none.

### `ParseError: ... missing required column`

**Cause:** generic-long needs `scan`, `radius_cm`, `signal`. Generic-wide needs
the `columns` mapping.

**Confirm:** `head -1 my-experiment/scans.csv`.

**Fix:** rename your columns to the documented names, or map them in the
manifest for wide format. See
[Load generic-long data](../tutorials/load-generic-long.md).

**Data at risk:** none.

### `DataConflictError: signal_unit is 'AU' in the data but 'fringe' in the manifest defaults`

**Cause:** the table and the manifest both declare a value and they differ.
`defaults` are **not** overrides.

**Fix:** remove one of the two declarations. openauc never silently picks.

**Data at risk:** none — nothing was loaded.

### `ParseError: ... non-numeric` or `non-finite`

**Cause:** a `radius_cm`/`signal` cell is text, blank, `NaN` or `inf`.

**Confirm:** the message names the row and column.

**Fix:** correct the source file. openauc will not substitute a value.

**Data at risk:** none.

### `DataConflictError: duplicate (scan, radius_cm)`

**Cause:** two rows describe the same radial position in the same scan, which
is ambiguous.

**Fix:** deduplicate at source; decide deliberately which reading is correct.

**Data at risk:** none.

### `AmbiguousFormatError: delimiter is ambiguous between comma and tab`

**Cause:** the file parses consistently either way.

**Fix:** declare it: `{ "delimiter": "tab" }`.

**Data at risk:** none.

## Writing

### `SyntheticWriteError: wide layout needs one shared radius axis`

**Cause:** you are writing per-scan-axis data to generic-wide, which has a
single radius column. Writing it wide would need resampling, which openauc
never does.

**Confirm:** `experiment.observations.mode`.

**Fix:** use `write_generic_long` or `write_aucx`. See
[Per-scan radius axes](per-scan-radius-axes.md).

**Data at risk:** none — nothing was written.

### `ArchiveError: refusing to overwrite existing file` (exit 3)

**Cause:** the destination exists.

**Fix:** `--overwrite` on the CLI, or `overwrite=True` in Python. Check first
that you do not need the existing file.

**Data at risk:** the existing file, once you pass `--overwrite`.

## Archives

### `ArchiveIntegrityError: checksum mismatch for 'experiment.json'`

**Cause:** the archive was modified or is corrupt since it was written.

**Confirm:** `uv run openauc validate the.aucx` — the message names the member.

**Fix:** recover from another copy or regenerate. **Do not** trust the contents.

**Data at risk:** **yes** — treat the archive as unreliable.

!!! note
    A checksum failure means the bytes changed. It says nothing about *who*
    changed them: AUCX provides integrity, not authenticity.

### `ArchiveVersionError: unsupported AUCX format version '2.0'`

**Cause:** written by a newer openauc. Archives are never migrated silently.

**Fix:** upgrade openauc.

**Data at risk:** none — the archive is fine, this build just will not read it.

### `ArchiveError: ... is not a readable ZIP archive`

**Cause:** truncated, or not an archive.

**Confirm:** `unzip -l the.aucx`.

**Fix:** recover from another copy.

**Data at risk:** yes.

## Plotting

### Nothing appears; no window opens

**Cause:** not a bug. `openauc.plotting` never uses pyplot, so it never opens a
window.

**Fix:** save the figure, or supply your own axes:

```python
ax = plot_scans(experiment)
ax.figure.savefig("scans.png")
```

```python
import matplotlib.pyplot as plt

fig, ax = plt.subplots()
plot_scans(experiment, ax=ax)
plt.show()
```

**Data at risk:** none.

### `PlottingError: no scan in the selection carries any observation to plot`

**Cause:** every selected scan is empty.

**Confirm:** `experiment.observations.points_per_scan()`.

**Fix:** select scans that carry data.

**Data at risk:** none.

## Validation

### Readiness is `BLOCKED` although structural validation passed

**Cause:** working as designed. Structural validity and analysis readiness are
independent questions.

**Confirm:**

```python
[i.code for i in experiment.assess_readiness().sedimentation_velocity.blocking_issues]
```

**Fix:** if you have the metadata, add it to the manifest. If you do not, the
experiment is still perfectly valid to store and inspect —
[Assess analysis readiness](assess-analysis-readiness.md).

**Data at risk:** none.

### Validation reports warnings I did not expect

**Cause:** absent optional metadata is *reported*, never required.

**Fix:** check whether the finding blocks anything:

```python
for issue in experiment.validate().warnings:
    print(issue.code, "blocks:", issue.blocks or "nothing")
```

**Data at risk:** none.

## Synthetic data

### Generated data is not reproducing

**Cause:** almost always a changed `seed` or another config field.

**Confirm:** diff the two configs —
`config.model_dump()` vs the one you recorded.

**Fix:** record the whole config, not just the seed. For byte-identical
archives, pin `exported_at` too. See
[Reproduce synthetic datasets](reproduce-synthetic-datasets.md).

**Data at risk:** none.

## Still stuck?

Every error carries a specific message naming the file, member or column
involved. If it does not, that is a bug worth
[reporting](../project/contributing.md).
