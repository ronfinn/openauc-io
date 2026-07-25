# Concepts

Domain and data-model background: what an AUC experiment, scan, scan set, cell,
optical system and radial axis mean in this library, and how the canonical model
(`docs/decisions/ADR-0002`) represents them.

- [data model](data-model.md) — the two-layer canonical representation.
- [units](units.md) — declared units, retained and never converted.
- [missing & unknown values](missing-and-unknown-values.md) — the explicit
  present/missing/unknown/not-applicable distinction.
- [optical systems](optical-systems.md) — what is represented, and what is not.
- [validation tiers](validation-tiers.md) — the four questions validation
  answers, and the fifth it refuses to.
- [analysis readiness](analysis-readiness.md) — metadata presence reporting, and
  why scientific suitability is never assessed.
- [plotting](plotting.md) — basic scan plots that render what is stored and
  interpolate nothing.
