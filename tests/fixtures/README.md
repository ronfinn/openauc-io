# Test fixtures

Only **synthetic** or **provably redistributable** fixtures belong here.

Do **not** commit real instrument dumps or any file whose licence/provenance is
undocumented. Fixtures should be small, hand-constructed, and self-explanatory so
tests remain fast and the repository stays legally clean.

## `aucx/v1_0_example.aucx`

A small archive written by the unmodified `0.1.0a1` AUCX writer (format version
`1.0`, before scans could carry a `sample_id`). It is a regression fixture: it
must stay readable, unchanged, by every later reader. **Do not regenerate it.**
It holds one declared sample, two scans (one timestamp with a `+01:00` offset,
one with no timezone) and an experiment `acquired_at` with a `+01:00` offset.
