# ADR-0004 — Parser plugin registry

- **Status:** Accepted (Phase 3 — implemented; see the Phase 3 amendment below)
- **Date:** 2026-07-23 (proposed); amended 2026-07-23 (Phase 3)
- **Deciders:** Ron Finn
- **Related:** ADR-0001, ADR-0002, ADR-0003; development-log/0001;
  development-log/0003

## Context

The project starts with a small set of first-party readers (generic long-format
CSV/TSV, generic wide-format CSV/TSV, JSON/YAML manifests, and AUCX) but its
stated long-term goal is to support many more AUC formats over time — potentially
including formats contributed by third parties. The library therefore needs a
consistent way to (a) register a format reader, (b) select the right reader for a
given input, and (c) let the CLI and public API enumerate what is supported —
without hard-coding an ever-growing `if/elif` dispatch and without overclaiming
support for formats that are not actually implemented and tested.

Reader selection must be honest: a reader is offered only when it genuinely
handles the input. The registry must never present speculative or untested format
support as available.

## Decision under consideration

Introduce an internal **parser plugin registry** (`src/openauc/registry.py`):

- **First-party registration via a decorator.** Each built-in reader declares
  itself to the registry with a stable format identifier, a human-readable name,
  and a capability/detection hook. This replaces centralised dispatch with local,
  self-describing registration.
- **A uniform reader interface.** Every reader exposes the same contract: a way
  to test whether it can handle a given input, and a way to read that input into
  the canonical model (ADR-0002). Writers (e.g. the AUCX writer, ADR-0003) follow
  an analogous pattern.
- **Explicit selection, no silent guessing beyond declared detection.** Callers
  may name a format explicitly; automatic detection uses only each reader's
  declared capability check. If detection is ambiguous or fails, the library
  raises a clear error rather than guessing.
- **Optional third-party discovery via entry points.** External packages may
  register additional readers through `importlib.metadata` entry points, loaded
  opt-in. This keeps the core lean while allowing an ecosystem, without bundling
  or vendoring third-party format code.
- **Enumerability.** The registry can list registered formats and their
  capabilities so the CLI and `api.py` can report *actually available* support.

## Alternatives considered

- **Hard-coded `if/elif` dispatch in a single function.** Simple initially, but
  scales poorly, centralises knowledge that belongs with each reader, and invites
  overclaiming. Rejected.
- **Entry points only (no internal registry), including for first-party
  readers.** Adds packaging indirection and import-time cost for readers that
  ship in-tree, and makes the core depend on discovery machinery for its own
  formats. Rejected in favour of a decorator for first-party plus *optional*
  entry points for third parties.
- **A plugin framework dependency** (e.g. `pluggy`). Rejected for v0.1: an extra
  dependency and conceptual surface that a small decorator-based registry plus
  stdlib entry points already covers.
- **Class-based subclass auto-registration only.** Workable but couples
  registration to inheritance; a decorator keeps registration explicit and
  greppable and does not force an inheritance hierarchy.

## Consequences

**Positive**

- New formats are added locally by writing a reader and registering it; no
  central dispatch edit.
- Honest capability reporting: the CLI/API can enumerate only tested, registered
  formats.
- A clean extension seam for third-party formats without bundling their code,
  consistent with the licensing/provenance boundaries.
- Symmetry between readers and writers simplifies the AUCX round-trip.

**Negative / costs**

- A registry and a reader interface are more upfront structure than direct
  dispatch for the initial handful of formats.
- Entry-point discovery, once enabled, introduces import-time and trust
  considerations for third-party plugins that must be documented.
- Detection heuristics for ambiguous CSV/TSV inputs need care to avoid both false
  positives and silent misclassification.

## Unresolved questions

- The precise reader/writer interface signatures (method names, how detection
  reports confidence, how streaming vs whole-file reads are expressed) — settled
  during Phase 3 implementation.
- Whether third-party entry-point discovery ships enabled in v0.1 or is deferred
  to a later release once the first-party interface has stabilised.
- How the CLI surfaces the registry (e.g. a `formats`/`list` command) —
  depends on the CLI command surface (development-log Q7).
- Trust and safety policy for loading third-party plugins.

## References

- Python Packaging User Guide — plugin discovery via entry points
  (`importlib.metadata`).
- `importlib.metadata` standard-library documentation.

---

## Amendment — Phase 3 implementation (2026-07-23)

The registry is now implemented in `src/openauc/formats/` and the interface
signatures are settled.

**Decorator registration.** First-party parsers register with the
`@register_parser` class decorator (`openauc.formats.registry`). Each parser is an
ABC subclass exposing `format_id`, `name`, `suffixes`, `layouts`, `limitations`,
`doc_reference`, plus `detect()` and `parse()`.

**Detection contract.** `detect()` returns a `DetectionResult` with
`parser_id`, a `confidence` in `[0.0, 1.0]`, `evidence`, and `warnings`.
`detect_parser()` selects the highest-confidence parser subject to a minimum
confidence (`0.5`) and a tie margin (`0.15`); failures raise
`UnsupportedFormatError` or `AmbiguousFormatError`.

**Selection precedence.** Explicit `format=` override → manifest-declared
`format` → detection (used when the manifest omits a format). A declared or
overridden format goes straight to `parse()`, which yields precise structural
errors on mismatch. Delimiter ambiguity is resolved before parser selection and
raises `AmbiguousFormatError`.

**Enumerability.** `available_formats()` returns `FormatInfo` records for exactly
the registered parsers, so support is never overclaimed.

**Entry points deferred.** Third-party entry-point discovery is **not** enabled in
this phase; only in-tree first-party parsers register. It remains available to add
later once the first-party interface has proven stable, without changing the
decorator contract. This is a scoped narrowing of the original decision, not a
reversal.

**Exceptions.** The ingestion exception vocabulary is `UnsupportedFormatError`,
`AmbiguousFormatError` (both under `FormatError`), `ParseError` (under
`FormatError`), `ManifestError` and `DataConflictError` (under `OpenAUCError`).
