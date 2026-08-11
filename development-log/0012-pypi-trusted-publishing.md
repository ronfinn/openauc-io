# Development Log 0012 — PyPI Trusted Publishing preparation

- **Date:** 2026-08-11
- **Branch:** `chore/pypi-trusted-publishing` (from `main` after PR #24)
- **Status:** Publication *mechanism* only. **Nothing published, tagged or
  released.** `0.1.0a1` remains prepared and unpublished.
- **Author:** Ron Finn

## 1. Objective

Give the repository a production path to PyPI. Phase 9 built everything up to
the upload and deliberately stopped there; the upload step was the one piece of
release machinery that did not exist. This adds it — and nothing else. No
version changed, no tag was created, no release was made, no upload occurred.

## 2. Why Trusted Publishing

The alternative is a long-lived PyPI API token in repository secrets. That
token is a standing credential: it exists between releases, it is readable by
anything that can inject a step into a privileged workflow, and revoking it is
a manual act taken after the fact.

Trusted Publishing (OIDC) removes the secret entirely. PyPI verifies a
short-lived token minted by GitHub for one specific workflow file, in one
specific repository, in one specific environment, and issues a credential
scoped to that upload. Nothing persists between runs. There is no PyPI
credential anywhere in this repository or its settings, and none should ever be
added.

Attestations are left at the action's default — on for Trusted Publishing — so
uploads carry provenance.

## 3. Why a separate workflow from the Release dry run

`release.yml` runs on pull requests. A workflow that runs on pull requests must
never be able to publish, and the cleanest way to guarantee that is for it to
contain no publishing capability at all, which tests pin. Adding a conditional
upload to it would put the credential path one `if:` expression away from
untrusted input.

So `publish.yml` is a distinct file. That is also a hard requirement of the
security model rather than a matter of taste: PyPI's Trusted Publisher
configuration names the *workflow filename*, so the filename is part of the
credential's scope and must be stable.

## 4. Why a published GitHub Release triggers it, not a pushed tag

Pushing a tag is easy to do by accident and easy to do from a laptop without
review. Publishing a GitHub Release is a deliberate, visible act performed
through the UI, and it can be staged: a *draft* Release fires no event, so the
release notes can be prepared and checked before anything is authorised.

There is deliberately no `workflow_dispatch`, so there is no manual bypass of
that gate. A botched release is corrected by yanking on PyPI and cutting a new
version, not by re-running a publish by hand. `skip-existing` is likewise not
set: re-publishing a version that already exists is a release mistake and must
fail loudly.

## 5. Privilege separation between the two jobs

| | `build-and-verify` | `publish-to-pypi` |
|---|---|---|
| Runs project code | Yes | **No** |
| Checks out the repository | Yes | **No** |
| Permissions | `contents: read` | `id-token: write` |
| Environment | none | `pypi` |

The workflow itself grants `permissions: {}`; each job asks for exactly what it
needs. The consequence is the property worth having: **nothing that executes
this repository's code holds a PyPI credential, and the job that holds the
credential executes none of this repository's code.** The verified
distributions cross that boundary as an Actions artifact and nothing else.

Because a `release` event sets `GITHUB_REF` to the tag, `verify_artifacts.py`
additionally asserts that the release tag is `v<version>` — the tag and the
packaged version cannot silently disagree. The expected version is derived from
the sources; no version is hard-coded in the workflow.

The publishing action is pinned to the commit behind `v1.14.2`
(`dc37677b…`), not to a mutable tag, and a test enforces that the pin is a
40-character SHA.

## 6. How the Phase 9 tests changed

Phase 9 asserted `test_no_workflow_publishes_anywhere`. That was correct when no
workflow was allowed to publish; it is now too blunt. Deleting it would have
lost the boundary it protected, so it became narrower and stronger instead:
*exactly one* workflow may contain the publishing action, and that workflow is
structurally pinned — trigger, absent triggers, environment, per-job
permissions, artifact hand-off, action pinning, absence of credentials, absence
of `skip-existing`, and the absence of any checkout or shell step in the
credential-bearing job.

Every Phase 9 guarantee about the dry run survives unchanged: `release.yml`
still holds read-only permissions, contains no publishing action, requests no
OIDC identity, and cannot tag or create a release. Neither workflow, and no
script, manufactures a tag or a GitHub Release.

One prior test needed a real correction rather than a narrowing:
`docs.yml` legitimately holds `id-token: write` for GitHub Pages deployment, so
the invariant is that no workflow other than the publishing one pairs an OIDC
identity with a PyPI audience — not that no workflow requests OIDC at all.

## 7. What remains manual, and unperformed

These are human acts in GitHub and PyPI settings. **None of them has been
done**, and nothing in this repository claims otherwise:

1. Create the `pypi` GitHub environment and apply protection rules.
2. Configure the PyPI pending publisher: project `openauc`, owner `ronfinn`,
   repository `openauc-io`, workflow `publish.yml`, environment `pypi`.

A pending publisher creates the project on its first successful publication but
does **not** reserve the name beforehand. Until the first upload succeeds, the
name `openauc` is not guaranteed to remain available.

Also deliberately not done here, because they belong to the release commit or
the post-release update: the version is unchanged, the `0.1.0a1` changelog
heading still says `unreleased`, `CITATION.cff` is untouched, the README does
not yet advertise `pip install openauc`, and the project is still documented as
unpublished. This log entry prepares a mechanism; it does not report a release.

## 8. Next step

The release checklist ([`docs/project/release-checklist.md`](../docs/project/release-checklist.md))
now documents the full sequence: before-release gates, the human tag/Release
gate, the automated publication that follows it, and the post-release
verification. Executing it remains a separate, deliberate decision.
