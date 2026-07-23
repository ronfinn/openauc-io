# openauc-io

Open-source Python library for importing, validating, standardising, visualising
and archiving analytical ultracentrifugation (AUC) data.

> **Status: pre-alpha (Phase 1 foundation).** Nothing is released yet and no
> scientific functionality is implemented. The current tree is packaging,
> tooling and documentation scaffolding only. APIs will change without notice.

## Scope

`openauc` aims to support historical and modern AUC formats over time. The
**first alpha release** is intentionally narrow and will provide:

1. Generic long-format CSV/TSV import.
2. Generic wide-format CSV/TSV import.
3. JSON/YAML experiment manifests (JSON canonical; YAML for authoring).
4. A canonical in-memory AUC experiment model.
5. Structural validation.
6. Scan summaries.
7. Basic scan plotting.
8. Export to a versioned `.aucx` archive.
9. Reloading `.aucx` archives.
10. Checksums and provenance.
11. A command-line interface.
12. User and developer documentation.

**This project is not a replacement for SEDFIT, SEDPHAT, UltraScan, GUSSI or
other established AUC analysis software.** It performs no sedimentation
modelling or fitting. It is an independent, clean-room implementation and does
not copy code or interfaces from those tools.

## Requirements

- Python 3.11, 3.12 or 3.13
- [uv](https://docs.astral.sh/uv/) for development

## Install (from source)

Not yet published to PyPI. For development:

```bash
git clone https://github.com/ronfinn/openauc-io
cd openauc-io
uv sync
```

## Quickstart

Only version reporting is wired up so far:

```bash
uv run openauc version
```

Import and scientific features arrive in later phases — see the roadmap in
[`development-log/0001-project-foundation.md`](development-log/0001-project-foundation.md).

## Development

```bash
uv sync              # create the environment
uv run ruff check .  # lint
uv run ruff format . # format
uv run mypy          # type-check
uv run pytest        # tests
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for the full workflow and the Architecture
Decision Records under [`docs/decisions/`](docs/decisions/).

## Documentation

- Architecture Decision Records: [`docs/decisions/`](docs/decisions/)
- Development log: [`development-log/`](development-log/)
- Format specifications: [`docs/formats/`](docs/formats/)
- Concepts: [`docs/concepts/`](docs/concepts/)

## Licence

Apache License 2.0. Copyright 2026 Ron Finn. See [LICENSE](LICENSE) and
[NOTICE](NOTICE).

## Citation

If you use `openauc-io`, please cite it using the metadata in
[CITATION.cff](CITATION.cff).
