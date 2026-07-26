# Choosing Python or the CLI

Both interfaces sit on the same code. Neither can do anything the other cannot
reach, with two exceptions noted below.

## Use the CLI when

- You want to look at a file quickly.
- You are scripting in shell and want [exit codes](../cli/exit-codes.md).
- You are converting data in bulk.
- You do not want to write Python.

```bash
uv run openauc inspect my-experiment
uv run openauc validate my-experiment --readiness --json
uv run openauc convert my-experiment archive.aucx
```

## Use Python when

- You need the data itself — arrays, metadata, individual findings.
- You are building something on top of the model.
- You want to plot. **There is no plotting subcommand.**
- You want to construct an experiment in memory rather than read one.

```python
import openauc

experiment = openauc.load("my-experiment")
radius, signal = experiment.observations.scan_vectors("scan_001")
```

## Side by side

| Task | CLI | Python |
|------|-----|--------|
| Show a summary | `openauc inspect X` | `experiment.summary()` |
| Structured summary | `openauc inspect X --json` | `experiment.summary_data()` |
| Structural validation | `openauc validate X` | `experiment.validate_structure()` |
| All tiers | `openauc validate X --readiness --json` | `experiment.validate()` |
| Readiness | `openauc validate X --readiness` | `experiment.assess_readiness()` |
| Convert to AUCX | `openauc convert X out.aucx` | `experiment.export("out.aucx")` |
| Verify an archive | `openauc validate X.aucx` | `openauc.validate_aucx("X.aucx")` |
| Generate data | `openauc generate out --scenario ...` | `generate_experiment(config)` |
| List formats | `openauc formats` | `openauc.available_formats()` |
| **Plot** | *not available* | `plot_scans(experiment)` |
| **Build an experiment in memory** | *not available* | `AUCExperiment(...)` |

## Composing the two

`--json` makes every informative command machine-readable, so the CLI composes
with `jq` and friends:

```bash
uv run openauc validate my-experiment --json | jq '.structural.counts'
```

```json
{ "error": 0, "info": 2, "warning": 3 }
```

## Next step

- [Complete CLI workflow](../tutorials/cli-workflow.md)
- [Complete Python workflow](../tutorials/python-workflow.md)
