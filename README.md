# openauc-io

Open-source Python library for importing, validating, standardising, visualising
and archiving analytical ultracentrifugation (AUC) data.

**📖 Full documentation: <https://ronfinn.github.io/openauc-io/>**

> **Status: pre-alpha (`0.1.0a1`), not published.** APIs may change without
> notice. Implemented: the canonical in-memory data model, generic CSV/TSV
> ingestion, tiered structural validation, analysis-readiness reporting,
> structured summaries, basic scan plotting, the AUCX archival container,
> deterministic synthetic data generation, and a command-line interface.
>
> **No scientific AUC analysis is implemented** — no sedimentation-velocity or
> equilibrium analysis, no quality control, no unit conversion — and none is
> planned. Vendor and instrument formats are not supported.

## Installation

Not on PyPI. From a clone:

```bash
git clone https://github.com/ronfinn/openauc-io.git
cd openauc-io
uv sync --all-groups
uv run openauc version          # 0.1.0a1
```

Or install a locally built wheel:

```bash
uv build
uv pip install dist/openauc-0.1.0a1-py3-none-any.whl
```

Requires Python 3.11, 3.12 or 3.13. Full detail:
[Installation](https://ronfinn.github.io/openauc-io/getting-started/installation/).

## End-to-end example

```python
import openauc
from openauc.plotting import plot_scans

experiment = openauc.load("examples/data/demo_experiment")
print(experiment.summary())

report = experiment.validate()
ax = plot_scans(experiment)

experiment.export("experiment.aucx")
restored = openauc.load("experiment.aucx")
assert restored.to_dict() == experiment.to_dict()
```

## CLI quickstart

```bash
uv run openauc generate demo.aucx --format aucx --scenario moving-boundary \
  --scans 20 --points 300 --seed 42
uv run openauc inspect  demo.aucx
uv run openauc validate demo.aucx --readiness
uv run openauc convert  examples/data/demo_experiment archive.aucx
```

Exit codes: `0` success, `1` structural validation failed, `2` input error,
`3` output exists. See the
[CLI reference](https://ronfinn.github.io/openauc-io/cli/).

## Scope

The first alpha provides generic long/wide CSV/TSV import, JSON/YAML manifests,
a canonical experiment model, structural validation, scan summaries, basic
plotting, the versioned `.aucx` archive with checksums and provenance, synthetic
data generation, a CLI, and documentation.

**This project is not a replacement for SEDFIT, SEDPHAT, UltraScan, GUSSI or
other established AUC analysis software.** It performs no sedimentation
modelling or fitting. It is an independent, clean-room implementation and does
not copy code or interfaces from those tools.

Four ideas are kept deliberately distinct: **representation**, **structural
validation**, **analysis readiness**, and **scientific suitability** — the last
of which is always reported as `NOT_ASSESSED`. See
[Scientific boundaries](https://ronfinn.github.io/openauc-io/concepts/scientific-boundaries/).

## Documentation

| | |
|---|---|
| [Five-minute quickstart](https://ronfinn.github.io/openauc-io/getting-started/quickstart/) | Try it with generated data |
| [Tutorials](https://ronfinn.github.io/openauc-io/tutorials/) | Complete Python and CLI workflows |
| [How-to guides](https://ronfinn.github.io/openauc-io/how-to/) | Task-shaped recipes and troubleshooting |
| [Concepts](https://ronfinn.github.io/openauc-io/concepts/README/) | Data model, validation tiers, readiness |
| [Formats](https://ronfinn.github.io/openauc-io/formats/README/) | Generic delimited, manifest v1, AUCX |
| [Python API](https://ronfinn.github.io/openauc-io/api/) | Curated reference |
| [Known limitations](https://ronfinn.github.io/openauc-io/project/limitations/) | What is missing or bounded |

Build the site locally:

```bash
uv run mkdocs serve      # http://127.0.0.1:8000/
```

## Development

```bash
uv sync --all-groups
uv run ruff check .        # lint
uv run ruff format .       # format
uv run mypy                # type-check (strict)
uv run pytest              # tests
uv run mkdocs build --strict
```

See [CONTRIBUTING.md](CONTRIBUTING.md) and the Architecture Decision Records
under [`docs/decisions/`](docs/decisions/).

## Licence

Apache License 2.0. Copyright 2026 Ron Finn. See [LICENSE](LICENSE) and
[NOTICE](NOTICE).

## Citation

If you use `openauc-io`, please cite it using the metadata in
[CITATION.cff](CITATION.cff).
