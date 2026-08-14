# Installation

**Goal:** get a working `openauc` and confirm it runs.

## Prerequisites

- **Python 3.11, 3.12 or 3.13.** These are the versions declared in
  `pyproject.toml` (`requires-python = ">=3.11,<3.14"`) and the three legs of
  the CI matrix.
- **[uv](https://docs.astral.sh/uv/)** for the development workflow.

!!! warning "Alpha release"
    `openauc 0.1.0a1` is published on PyPI as a **pre-release**. APIs and
    behaviour may change without notice. Ask for the version explicitly, as
    below, so that what you get is the version you meant.

## 1. Installation from PyPI (recommended for users)

```bash
python -m pip install "openauc==0.1.0a1"
```

That is the project's recommended command. Naming the exact version is
deterministic: `0.1.0a1` is a pre-release, and how a request without a version
resolves depends on the installer, its configuration, and what is published at
the time. Pinning removes all of that.

To opt in to whatever the newest pre-release is, rather than naming one:

```bash
python -m pip install --pre openauc
```

Confirm:

```bash
openauc version
```

Expected output:

```text
0.1.0a1
```

That installs the published wheel — `openauc-0.1.0a1-py3-none-any.whl` — from
[the PyPI project page](https://pypi.org/project/openauc/0.1.0a1/), together
with the runtime dependencies listed below. The sdist,
`openauc-0.1.0a1.tar.gz`, is published alongside it.

## 2. Development installation from a clone

Run these from wherever you keep source checkouts:

```bash
git clone https://github.com/ronfinn/openauc-io.git
cd openauc-io
uv sync --all-groups
```

`uv sync --all-groups` creates `.venv/` and installs the runtime dependencies
plus the `dev` and `docs` groups. Confirm it worked — run this **from the
repository root**:

```bash
uv run openauc version
```

Expected output:

```text
0.1.0a1
```

This is an editable installation: edits to `src/openauc/` take effect
immediately, with no reinstall.

## 3. Installation from a locally built wheel

Use this to install into an environment that is not the repository's own — for
a notebook, a separate project, or to check what a real user would get.

From the repository root:

```bash
uv build
```

That writes two files into `dist/`:

```text
dist/openauc-0.1.0a1-py3-none-any.whl
dist/openauc-0.1.0a1.tar.gz
```

Then, from wherever you want the environment:

```bash
uv venv
uv pip install /path/to/openauc-io/dist/openauc-0.1.0a1-py3-none-any.whl
```

For example, if the clone is at `~/src/openauc-io`:

```bash
uv pip install ~/src/openauc-io/dist/openauc-0.1.0a1-py3-none-any.whl
```

Confirm:

```bash
.venv/bin/openauc version
```

## 4. Editable installation into an existing environment

If you already have a virtual environment and want to develop against the
source tree:

```bash
uv pip install --python /path/to/existing/.venv/bin/python \
  --editable /path/to/openauc-io
```

## What gets installed

Runtime dependencies: `pydantic`, `numpy`, `xarray`, `pandas`, `PyYAML`,
`matplotlib`, `typer`. The package ships a `py.typed` marker, so type checkers
see its annotations.

The `openauc` console script is installed with the package.

## Verifying the installation

```bash
uv run openauc version      # prints 0.1.0a1
uv run openauc formats      # lists aucx, generic-long, generic-wide
```

```python
import openauc
print(openauc.__version__)          # '0.1.0a1'
print([f.format_id for f in openauc.available_formats()])
# ['aucx', 'generic-long', 'generic-wide']
```

## Common failure modes

| Symptom | Cause | Fix |
|---------|-------|-----|
| `command not found: openauc` | Not using the project environment | Prefix with `uv run`, or activate `.venv` |
| `No such command 'generate'` | Older checkout without the synthetic generator | `git pull` then `uv sync --all-groups` |
| `ModuleNotFoundError: openauc` | Wheel not installed in the active environment | Re-run the wheel install, check `which python` |

More in [Troubleshooting](../how-to/troubleshooting.md).

## Next step

[Five-minute quickstart](quickstart.md) — a full workflow with no input files.
