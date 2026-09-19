# Development Log 0014 — SEDFIT IgG real-data inspection

- **Date:** 2026-09-19
- **Branch:** `main`
- **Status:** Investigation only. No production code, tests or format
  behaviour changed.
- **Author:** Ron Finn

## 1. Purpose

First trial of openauc with genuine AUC data: the public SEDFIT IgG
sedimentation-velocity example (IgG in PBS, 40,000 rpm, interference
detection; these details come from the tutorial page, not from the files).

## 2. Dataset

- Tutorial: <https://sedfitsedphat.github.io/sedfit_example.htm>
- Archive: <https://sedfitsedphat.github.io/images/IgGdata.zip>
  (2,601,622 bytes; sha256
  `e74fef69316a58e08ce124d17bde718d3c427070827cc8c2775ed6c64937178f`).
- 226 real interference scan files, `00001.IP1` to `00226.IP1`; no other
  files, no documentation, no metadata sidecar.
- Stored locally at `external-data/sedfit-igg/` and deliberately excluded
  from Git (via `.git/info/exclude`). It must not be committed.
- **Redistribution licence has not been established.** The tutorial page states
  none.

## 3. File layout (as observed)

ASCII, CRLF. Line 1 is `cm/pixel:  0.00069667737, Sample`. Line 2 is a
header of eight tokens (e.g. `P 1 20.1 40000 0000536 7.7182E09 675 40`).
Then 1,759 rows of `radius  signal` (whitespace separated; radius 5.9677 to
7.1925 in 0.0007 steps, identical in all files).

Not stored in the files: wavelength, cell/channel, sample, instrument
identity, acquisition timestamps, signal unit, radius unit.

## 4. Result with existing code

- All 226 scans were converted to `generic-long` (values copied verbatim as
  text) and loaded by existing openauc code as a shared radius axis.
- Validation, plotting, AUCX 1.1 export and reload all succeeded without
  production-code changes. The reloaded experiment compared equal, and the
  radius and signal observations matched the source files exactly.
- Direct ingestion is not possible: two header lines, whitespace delimiter,
  one file per scan, per-scan metadata in a header line, no manifest.

## 5. Open issue: header meaning is unverified

The header-token meanings are **not** documented in the files or the
tutorial. Patterns suggest temperature, rotor speed, elapsed seconds and a
ω²t integral (tokens 3–6), but this is inference, and tokens 1, 2, 7, 8 and
the `cm/pixel` value are uninterpreted. Interpretation is not yet
sufficiently verified for production use. A test that mapped tokens 3–5 to
temperature, speed and time made SV readiness "potentially ready"; that result
depends on the unconfirmed mapping.

## 6. Next task

Potential reference: Beckman Coulter ProteomeLab XL-A/XL-I Instructions for
Use, PN LXLAI-IM-10AB, Chapter 3.

1. Verify the documented IP1 field meanings.
2. Decide between a small native interference-file reader and a
   `generic-long` converter (an `examples/` script). A native reader is
   allowed only from a documented specification (see the roadmap "Never" and
   vendor-reader rules).
3. Do not implement other vendor formats.
