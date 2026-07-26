# Scientific boundaries

These boundaries are **binding on all work in this project** and are recorded in
the founding development log. They are not a roadmap of things not yet done.

## What openauc will not do

### No scientific analysis

No sedimentation-velocity or equilibrium analysis, no fitting, no modelling. No
sedimentation coefficient, diffusion coefficient or molecular weight is ever
computed, stored or inferred.

`openauc` is **not a replacement** for SEDFIT, SEDPHAT, UltraScan, GUSSI or any
other established AUC analysis software, and it is an independent, clean-room
implementation that copies no code or interfaces from them.

### No scientific quality control

No convection, aggregation, meniscus or equilibrium detection. No sample-quality
assessment. No data-quality score.

Scientific suitability is reported as `NOT_ASSESSED` — permanently, as a
machine-readable constant, never derived from any finding.

### No silent inference of missing metadata

Absent metadata is **reported explicitly**, never filled in. Missing, unknown
and not-applicable are kept distinct and never collapsed into a default.

### No silent interpolation or resampling

Radial observations are preserved as acquired. Order is never changed. Per-scan
radius axes stay distinct; nothing is placed onto a common grid. Any future
operation that *does* regrid must be explicit, opt-in and recorded in
provenance — no such operation exists today.

### No unit conversion

Declared units are retained. openauc checks representational consistency (a
rotor speed must be `rpm` or unknown) but never converts, and never infers a
unit from a value.

### No fabricated format rules

Only *generic* CSV/TSV and this project's own AUCX are parsed. No vendor or
instrument format is reverse-engineered. If a format is not documented publicly,
openauc does not guess at it.

### No unverified claims

Documentation states only what has been verified. No vendor compatibility, no
scientific validation, no PyPI availability are claimed unless true.

## The four questions, kept apart

Conflating these is the likeliest way to misuse this library.

| Question | Answered by | Answer means |
|----------|-------------|--------------|
| **Representation** — can the data be held faithfully? | Construction invariants | An invalid object cannot be built |
| **Structural validation** — is it internally consistent? | `validate_structure()`, `validate()` | Scans and observations correspond; nothing contradicts itself |
| **Analysis readiness** — is the needed metadata present? | `assess_readiness()` | Fields were **found**. Nothing about the data themselves |
| **Scientific suitability** — is the experiment sound? | **nothing** | Never assessed |

`is_valid == True` means the third column, and only the third column.
`POTENTIALLY_READY` means the fourth, and only the fourth.

## Why permissive validation is the correct choice

A historical dataset carrying nothing but an identifier, a radius vector and a
signal vector is a legitimate archival subject. Refusing to represent it would
defeat the purpose of an archival tool.

So the blocking rules are minimal: unambiguous keying, internal consistency, and
nothing more. Everything a conventional workflow would merely *prefer* is
reported, never required. See
[Validation tiers](validation-tiers.md).

## Licensing and provenance of the implementation

- Apache License 2.0.
- No code, format-parsing logic or GUI design copied from established AUC
  software.
- Public literature and public format specifications may be cited as references;
  implementation provenance stays clear.
- All test and example data is synthetic and redistributable. **No real or
  confidential instrument data is committed.**
- No bundled third-party binaries.

## If you need analysis

Use established AUC analysis software. openauc's job is to get your data into a
faithful, validated, archivable form — and then get out of the way.

## Next step

- [Validation tiers](validation-tiers.md)
- [Analysis readiness](analysis-readiness.md)
- [Architecture decisions](../project/decisions.md)
