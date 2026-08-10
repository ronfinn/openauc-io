# Release checklist

The procedure for cutting a release of openauc-io. It is written down so a
release is a repeatable act rather than a remembered one.

!!! note "Nothing has been released yet"

    `0.1.0a1` is prepared but **unpublished**: no PyPI upload, no GitHub
    release, no tag. The machinery below is in place and exercised in dry-run
    form; running it to completion is a separate, deliberate decision.

## What is automated and what is not

| Step | Automated |
|------|-----------|
| Lint, format, types, tests, strict docs build | `scripts/release_check.py`, and CI on every pull request |
| Coverage floor | `fail_under` in `pyproject.toml`, enforced by every `pytest` run |
| Build, metadata check, artifact verification, clean-environment smoke test | `.github/workflows/release.yml` (**Release dry run**) |
| Tagging | Manual |
| GitHub release | Manual |
| PyPI upload | Manual, and no workflow has credentials for it |

The dry-run workflow holds `permissions: contents: read` and contains no upload
step, so it cannot publish even if invoked by mistake.

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

## The release itself

Only once every step above passes:

1. Tag `v<version>` on the release commit and push the tag.
2. Create the GitHub release from that tag, with the `CHANGELOG.md` section as
   its body, marked as a pre-release for any `aN`/`bN`/`rcN` version.
3. Upload `dist/` to PyPI.
4. Verify the published package installs from PyPI into a clean environment.

## After the release

1. Open the next `## [Unreleased]` section in `CHANGELOG.md`.
2. Record the release in `docs/project/roadmap.md` and the development log.
3. Bump the version in `src/openauc/__init__.py` and `CITATION.cff` when work on
   the next version begins.

## Next step

- [Roadmap](roadmap.md)
- [Changelog](changelog.md)
- [Contributing](contributing.md)
