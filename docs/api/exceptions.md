# Exceptions

A single, shallow hierarchy, so callers can catch `OpenAUCError` broadly or an
individual subclass narrowly.

```text
OpenAUCError
├── ValidationError
│   └── StructuralValidationError
├── ObservationError
├── FormatError
│   ├── UnsupportedFormatError
│   ├── AmbiguousFormatError
│   └── ParseError
├── ManifestError
├── DataConflictError
├── ArchiveError
│   ├── ArchiveIntegrityError
│   └── ArchiveVersionError
├── PlottingError
└── SyntheticWriteError
```

```python
from openauc.exceptions import OpenAUCError, ManifestError, ParseError

try:
    experiment = openauc.load("my-experiment")
except ManifestError as exc:
    ...
except OpenAUCError as exc:
    ...
```

::: openauc.exceptions

::: openauc.synthetic.writers.SyntheticWriteError
