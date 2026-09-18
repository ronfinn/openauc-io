# Development Log 0013 — First public alpha release

- **Date:** 2026-08-14
- **Branch:** `docs/post-0.1.0a1-release` (from `main` at the release commit)
- **Status:** `openauc 0.1.0a1` is **published**. This entry records the
  release and the post-release documentation update. No version was bumped and
  no scientific scope changed.
- **Author:** Ron Finn

## 1. Release identity

| | |
|---|---|
| Distribution | `openauc` |
| Version | `0.1.0a1` |
| Tag | `v0.1.0a1` (annotated tag object `012e1d253d0178ff3413368c858aa72fa2594444`) |
| Release commit | `84dfe5c3560f21a199dd38afa3c1ad7afcaa830d` |
| GitHub Release | [`v0.1.0a1`](https://github.com/ronfinn/openauc-io/releases/tag/v0.1.0a1), marked **pre-release**, published 2026-08-13T18:54:28Z |
| PyPI | [`openauc 0.1.0a1`](https://pypi.org/project/openauc/0.1.0a1/), publication completed 2026-08-14 |
| Workflow run | [`31733158729`](https://github.com/ronfinn/openauc-io/actions/runs/31733158729), attempt 3, conclusion `success` |

The release followed the documented sequence exactly: a human created and
pushed the tag, created and published the GitHub pre-release, and `publish.yml`
reacted to the `release: published` event. No automation manufactured a tag or
a Release.

## 2. Verification

`build-and-verify` checked out the release commit, ran the full release-check
suite, built from a clean `dist/`, passed `twine check --strict`, confirmed the
tag matched the packaged version, and smoke-tested the real wheel in a fresh
virtualenv before uploading the distributions as the `release-dists` artifact.

Published files and their PyPI SHA-256 digests:

```text
openauc-0.1.0a1-py3-none-any.whl
1f93b160e204197b7485a235516fd31abdc2a800c7756c0ec28a450bd2f52a4d

openauc-0.1.0a1.tar.gz
0fb7a10bdd7b6f6db3f8413bd0432601018d87ab7eebf355a62e1a1a675d1126
```

Checked after publication:

- the `release-dists` artifact downloaded in the publish job matched its
  expected digest, and the artifact's two files hash **identically** to the two
  files PyPI now serves — what was verified is what was published;
- PyPI lists exactly those two files for `0.1.0a1`, neither yanked, and
  `0.1.0a1` is the only release of the project;
- a fresh Python 3.12 virtualenv installed `openauc==0.1.0a1` from PyPI with
  `--no-cache-dir`;
- in that environment, `openauc version` and `import openauc;
  openauc.__version__` both report `0.1.0a1`, and `openauc formats` lists
  `aucx`, `generic-long` and `generic-wide`;
- PyPI's integrity endpoint serves a Sigstore attestation bundle for each file.
  The signing certificate names the workflow
  `https://github.com/ronfinn/openauc-io/.github/workflows/publish.yml@refs/tags/v0.1.0a1`,
  the GitHub Actions OIDC issuer, event `release`, and build config SHA
  `84dfe5c3560f21a199dd38afa3c1ad7afcaa830d`; the in-toto statement subjects
  match the published file digests.

## 3. Publication recovery

The first publication attempt failed. The upload never started: the Trusted
Publishing OIDC exchange was rejected with

```text
invalid-publisher: valid token, but no corresponding publisher
(Publisher with matching claims was not found)
```

which happens before any distribution is offered to PyPI, so nothing was
partially published — PyPI still had no `openauc` project at that point.

The PyPI publisher configuration was corrected to match the workflow's actual
claims:

| Field | Value |
|-------|-------|
| Project | `openauc` |
| Owner | `ronfinn` |
| Repository | `openauc-io` |
| Workflow | `publish.yml` |
| Environment | `pypi` |

The **failed jobs of the same run** were then re-run — `gh run rerun
31733158729 --failed` — which preserves the original `release` event, commit
and tag, so the thing published is the thing that was verified. The rerun
paused at the protected `pypi` environment for human approval, as intended.
Attempt 3 succeeded.

No API token was created, no manual `twine` upload was performed, no second tag
or Release was made, and `skip-existing` was not set: had a file already been
accepted, the run would have failed loudly rather than passing in silence.

## 4. Post-release repository update

The documentation carried a point-in-time claim that the project was not
published. That claim is now false, so the current-facing pages were updated:
the README and the installation guide make PyPI the primary path (pinned to
`openauc==0.1.0a1`, so that an alpha is installed deterministically), and the
documentation landing page, project index, known limitations, licence/citation
note, security policy, release checklist and roadmap now describe a released
first public alpha.

Historical records were left alone. Development logs `0008`, `0010`, `0011` and
`0012` describe the project as unpublished, which was true when they were
written, and `release.yml`'s comment that the dry run cannot publish remains a
statement about that workflow, not about the project.

The release checklist's one-time-setup section was rewritten from "create a
pending publisher" to "verify the active Trusted Publisher", since pending
publishers exist only to create a project that does not yet exist on PyPI.

## 5. What did not change

The version in `src/openauc/__init__.py` remains `0.1.0a1`, `CITATION.cff` is
untouched, and no next version was started — the checklist defers both to the
point where work on the next version begins. No workflow, packaging metadata,
tag or Release was modified, and no source behaviour changed.

Scientific scope is unchanged and unchangeable by this entry. Being installable
from PyPI is a statement about availability, not about maturity: there is still
no sedimentation fitting, molecular-weight estimation, meniscus detection,
convection assessment, scientific quality control, unit conversion or
physically validated simulation; scientific suitability remains
`NOT_ASSESSED`; synthetic curves remain illustrative; and vendor formats remain
unsupported absent a documented, non-reverse-engineered specification.

## 6. Next step

No successor version is committed. The roadmap records the first public alpha
as delivered and keeps its candidates explicitly separate from commitments.
