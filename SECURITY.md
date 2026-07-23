# Security Policy

## Supported versions

`openauc-io` is in **pre-alpha** development. No release has been made and there
is no supported release line yet. Security fixes are applied to the `main`
branch. This section will be updated when the first alpha is published.

## Reporting a vulnerability

Please report suspected vulnerabilities **privately**. Do not open a public
issue for a security problem.

- Preferred: open a private advisory via GitHub Security Advisories
  ("Report a vulnerability") at
  https://github.com/ronfinn/openauc-io/security/advisories/new.

Please include a description, reproduction steps, affected version/commit, and
any relevant environment details. We will acknowledge your report and keep you
informed of progress toward a fix.

## Scope note

`openauc` reads external data files (CSV/TSV, manifests, and `.aucx` archives).
Reports about parsing untrusted input — for example resource exhaustion or
unsafe deserialization — are in scope and welcome.
