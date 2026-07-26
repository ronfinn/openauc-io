# Top-level API

Everything on this page is importable directly from `openauc`.

```python
import openauc

openauc.load(...)
openauc.available_formats()
openauc.export_aucx(...)
openauc.inspect_aucx(...)
openauc.validate_aucx(...)
openauc.__version__
```

## Loading

::: openauc.formats.loader.load

## Format discovery

::: openauc.formats.registry.available_formats

## Archives

::: openauc.formats.aucx.export_aucx

::: openauc.formats.aucx.inspect_aucx

::: openauc.formats.aucx.validate_aucx

::: openauc.formats.aucx.read_aucx

## See also

- [Experiments and metadata](experiments.md)
- [AUCX archives](aucx.md)
