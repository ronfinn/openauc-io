# Examples

Runnable examples of importing, validating, summarising, plotting and archiving
AUC data. **All example data is synthetic and invented** — `data/demo_experiment`
is not a real measurement and no scientific meaning should be read into it.

Each script runs standalone and is executed by the test suite:

```bash
uv run python examples/01_load_generic.py
```

| Script | Shows |
|--------|-------|
| `01_load_generic.py` | Loading a generic delimited experiment and reading stored vectors |
| `02_inspect_summary.py` | The structured summary and validation findings |
| `03_assess_readiness.py` | Analysis readiness, without claiming scientific suitability |
| `04_plot_scans.py` | Plotting scans and saving a figure headlessly |
| `05_aucx_roundtrip.py` | Exporting to AUCX, verifying it, and reading it back |
| `06_cli_usage.py` | The same workflow through the command line, with exit codes |

`data/demo_experiment/` holds a four-scan long-format CSV and its manifest.
