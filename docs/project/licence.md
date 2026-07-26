# Licence and citation

## Licence

**Apache License 2.0.** Copyright 2026 Ron Finn.

The full text is in
[`LICENSE`](https://github.com/ronfinn/openauc-io/blob/main/LICENSE), with
attribution notices in
[`NOTICE`](https://github.com/ronfinn/openauc-io/blob/main/NOTICE).

You may use, modify and redistribute the software, including commercially,
subject to the licence terms — retain the notices and state significant
changes.

## Provenance of the implementation

`openauc` is an **independent, clean-room implementation**. No source code,
format-parsing logic or interface design is copied from SEDFIT, SEDPHAT,
UltraScan, GUSSI or any other AUC software.

AUCX is a **new format defined by this project**, so specifying its rules is
original authorship rather than reverse-engineering of anyone else's format.

All test and example data is synthetic and redistributable. No bundled
third-party binaries.

## Citation

Citation metadata is in
[`CITATION.cff`](https://github.com/ronfinn/openauc-io/blob/main/CITATION.cff),
which GitHub renders as a "Cite this repository" panel.

```yaml
--8<-- "CITATION.cff"
```

!!! warning "Cite the version you used"
    The current version is `0.1.0a1`, a **pre-alpha that has not been
    released**. APIs and behaviour may change. Record the exact commit if
    reproducibility matters.

    Citing `openauc` documents how data were **imported, validated and
    archived**. It is not a citation for any scientific analysis, because
    openauc performs none.

## Dependencies

Runtime: `pydantic`, `numpy`, `xarray`, `pandas`, `PyYAML`, `matplotlib`,
`typer` — all permissively licensed (BSD/MIT/PSF-family or Apache-2.0). Their
own terms apply to their code.
