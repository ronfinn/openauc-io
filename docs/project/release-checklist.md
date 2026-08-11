# Release checklist

The procedure for cutting a release of openauc-io. It is written down so a
release is a repeatable act rather than a remembered one.

!!! note "Status — nothing has been released yet"

    `0.1.0a1` is prepared but **unpublished**: no PyPI upload, no GitHub
    release, no tag. The machinery below is in place and exercised in dry-run
    form; running it to completion is a separate, deliberate decision.

    This note records a point in time, not a permanent property of the project.
    Update it when a release is made — the "After the release" steps below say
    so, and no test pins it.

## What is automated and what is not

| Step | Automated |
|------|-----------|
| Lint, format, types, tests, strict docs build | `scripts/release_check.py`, and CI on every pull request |
| Coverage floor | `fail_under` in `pyproject.toml`, enforced by every `pytest` run |
| Build, metadata check, artifact verification, clean-environment smoke test | `.github/workflows/release.yml` (**Release dry run**) |
| Tagging | **Manual** |
| GitHub Release creation and publication | **Manual** |
| Rebuild + verification of the tagged source | `.github/workflows/publish.yml`, after the Release is published |
| PyPI upload | `.github/workflows/publish.yml`, after the Release is published |

The dry-run workflow holds `permissions: contents: read` and contains no upload
step, so it cannot publish even if invoked by mistake. It remains publish-free
deliberately, and tests pin that.

## The two release workflows

| | **Release dry run** (`release.yml`) | **Publish to PyPI** (`publish.yml`) |
|---|---|---|
| Trigger | `workflow_dispatch`, `pull_request` | `release: published` only |
| Publishes | Never | Yes, to PyPI |
| OIDC identity | None | `id-token: write`, publish job only |
| GitHub environment | None | `pypi` |

`publish.yml` has two jobs, and the split is the security boundary:

- **`build-and-verify`** checks out the released tag, runs the full release
  check suite, builds from a clean `dist/`, runs `twine check --strict`, runs
  `scripts/verify_artifacts.py` — which on a `release` event also asserts that
  the tag is `v<version>`, derived from the sources rather than hard-coded —
  smoke-tests the real wheel in a fresh virtualenv, and uploads the
  distributions as an Actions artifact. It holds **no** publishing identity.
- **`publish-to-pypi`** downloads that artifact and uploads it with
  `pypa/gh-action-pypi-publish`, pinned to a commit SHA. It does not check out
  the repository, install dependencies or run any project code. Its only
  privilege is `id-token: write`.

There is no `workflow_dispatch` on `publish.yml`: the published GitHub Release
is the only way to reach PyPI. `skip-existing` is not set, so republishing an
already-published version fails loudly.

## One-time setup before the first publication

Both of these are **human configuration steps** performed in GitHub and PyPI
settings. No repository code performs them, and this documentation does not
assert that they have been done.

### 1. The `pypi` GitHub environment

Create an environment named exactly `pypi` under **Settings → Environments**.
Apply the protection rules available for the repository — required reviewers,
and a deployment-branch/tag rule limiting it to release tags — so that
publication has a human gate in addition to the Release gate.

### 2. The PyPI Trusted Publisher

Under **PyPI → Publishing** (a *pending publisher*, since the project does not
exist yet), configure exactly:

| Field | Value |
|-------|-------|
| PyPI project name | `openauc` |
| Owner | `ronfinn` |
| Repository name | `openauc-io` |
| Workflow name | `publish.yml` |
| Environment name | `pypi` |

A pending publisher **creates** the project on its first successful
publication. It does **not** reserve the name beforehand: until the first
upload succeeds, the name `openauc` remains claimable by anyone, and no
guarantee of its availability can be made here.

Trusted Publishing uses a short-lived OIDC token minted per run. There is no
PyPI API token, username or password anywhere in this repository or its
secrets, and none should ever be added.

## Before the release

1. Working tree clean, on a release branch cut from current `main`.
2. Confirm the version in `src/openauc/__init__.py` — hatch reads it from there
   — and that `CITATION.cff` declares the same version. A test enforces this.
3. `CHANGELOG.md` has a section for the version, with its entries written and
   the release date filled in.
4. Run every gate:

   ```console
   $ uv sync --all-groups
   $ uv run python scripts/release_check.py
   ```

5. Build and verify the artifacts:

   ```console
   $ rm -rf dist
   $ uv build
   $ uv run python scripts/verify_artifacts.py
   $ uvx twine check --strict dist/*
   ```

6. Install the wheel alone into a throwaway environment and exercise it:

   ```console
   $ python -m venv /tmp/openauc-smoke
   $ /tmp/openauc-smoke/bin/pip install dist/openauc-*.whl
   $ /tmp/openauc-smoke/bin/openauc version
   $ /tmp/openauc-smoke/bin/openauc formats
   ```

7. Run the **Release dry run** workflow from the Actions tab and confirm it is
   green.
8. Confirm the `pypi` GitHub environment exists and is protected.
9. Confirm the PyPI Trusted Publisher (or pending publisher) is configured
   exactly as tabulated above.

## The release itself

Only once every step above passes.

**Human, in order:**

1. Create the tag `v<version>` on the release commit and push it. Pushing the
   tag publishes nothing — no workflow reacts to it.
2. Create the GitHub Release from that tag, with the `CHANGELOG.md` section as
   its body.
3. Mark it as a **pre-release** for any `aN`/`bN`/`rcN` version — so, for
   `v0.1.0a1`, yes.
4. Publish the Release. A *draft* Release triggers nothing; publishing is the
   act that authorises the upload.

**Automated, and only now:**

5. `publish.yml` rebuilds and re-verifies the tagged source, confirming the tag
   matches the packaged version.
6. It publishes those verified distributions to PyPI over Trusted Publishing
   OIDC, with attestations left at their default.

## After the release

Verify, by hand:

1. The project and version exist on PyPI.
2. `pip install openauc==<version>` succeeds in a fresh environment — for a
   pre-release, with `--pre` or the exact version.
3. The installed version is the expected one, and `openauc version` and
   `openauc formats` work.
4. The publication carries the provenance/attestation information PyPI shows
   for Trusted Publishing uploads.

Then update the repository:

5. Replace `- unreleased` in the `CHANGELOG.md` section heading with the release
   date, and open the next `## [Unreleased]` section.
6. Update the status note at the top of this page, the version line on the
   [project index](index.md), and the README installation instructions, so none
   still says the version is unpublished.
7. Record the release in `docs/project/roadmap.md` and the development log.
8. Bump the version in `src/openauc/__init__.py` and `CITATION.cff`, and update
   `CITATION.cff`'s publication metadata, when work on the next version begins.

None of these are enforced by tests, deliberately: the tests pin what the
*machinery* may do — build, verify, never publish or tag — not which point in
the release cycle the repository currently occupies. A clone that has fetched
`v0.1.0a1` must still pass the whole suite.

## Next step

- [Roadmap](roadmap.md)
- [Changelog](changelog.md)
- [Contributing](contributing.md)
