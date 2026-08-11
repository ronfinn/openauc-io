"""Release mechanics: the coverage gate, the release scripts and the dry run.

These tests pin the *boundaries* of the release machinery as much as its
existence: the dry-run workflow must not be able to publish, and the checklist
must not claim that anything has been published.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import tomllib
import zipfile
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
WORKFLOWS = ROOT / ".github" / "workflows"
RELEASE_WORKFLOW = WORKFLOWS / "release.yml"
PUBLISH_WORKFLOW = WORKFLOWS / "publish.yml"
EXPECTED_VERSION = "0.1.0a1"

#: The one workflow permitted to hold a PyPI publishing identity. Every other
#: workflow in the repository must be incapable of publishing.
PUBLISHING_ACTION = "pypa/gh-action-pypi-publish"


def _load(path: Path) -> dict[object, object]:
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(loaded, dict)
    return loaded


def _workflow() -> dict[object, object]:
    return _load(RELEASE_WORKFLOW)


def _triggers_of(workflow: dict[object, object]) -> dict[object, object]:
    """YAML 1.1 parses a bare ``on:`` key as the boolean ``True``."""
    triggers = workflow["on"] if "on" in workflow else workflow[True]
    assert isinstance(triggers, dict)
    return triggers


def _triggers() -> dict[object, object]:
    return _triggers_of(_workflow())


def _publish_workflow() -> dict[object, object]:
    return _load(PUBLISH_WORKFLOW)


def _publish_jobs() -> dict[str, dict[object, object]]:
    jobs = _publish_workflow()["jobs"]
    assert isinstance(jobs, dict)
    return {str(name): job for name, job in jobs.items()}


def _publish_steps(job: str) -> list[dict[str, object]]:
    steps = _publish_jobs()[job]["steps"]
    assert isinstance(steps, list)
    assert all(isinstance(step, dict) for step in steps)
    return list(steps)


def _uses(step: dict[str, object]) -> str:
    return str(step.get("uses", ""))


def _with(step: dict[str, object]) -> dict[str, object]:
    options = step.get("with") or {}
    assert isinstance(options, dict)
    return options


def _pull_request_paths() -> list[str]:
    pull_request = _triggers()["pull_request"]
    assert isinstance(pull_request, dict)
    paths = pull_request["paths"]
    assert isinstance(paths, list)
    return [str(path) for path in paths]


def _scripts_executed_by_the_workflow() -> set[str]:
    text = RELEASE_WORKFLOW.read_text(encoding="utf-8")
    return set(re.findall(r"scripts/[\w./-]+\.py", text))


# --------------------------------------------------------------------------- #
# A deterministic artifact fixture
#
# The verifier's positive path must run on every test run without depending on
# whatever happens to sit in the repository's `dist/`. Both the version and the
# required wheel entries are read from the sources the verifier itself reads, so
# the fixture cannot drift away from what is being verified.
# --------------------------------------------------------------------------- #


def _declared_version() -> str:
    source = (ROOT / "src" / "openauc" / "__init__.py").read_text(encoding="utf-8")
    match = re.search(r'^__version__\s*=\s*"([^"]+)"', source, flags=re.MULTILINE)
    assert match is not None, "no __version__ in src/openauc/__init__.py"
    return match.group(1)


def _required_wheel_entries() -> tuple[str, ...]:
    source = (SCRIPTS / "verify_artifacts.py").read_text(encoding="utf-8")
    block = re.search(
        r"REQUIRED_WHEEL_ENTRIES\s*=\s*\((.*?)\)", source, flags=re.DOTALL
    )
    assert block is not None, "verify_artifacts.py no longer declares required entries"
    entries = tuple(re.findall(r'"([^"]+)"', block.group(1)))
    assert entries
    return entries


def _fabricate_dist(directory: Path, *, omit: str | None = None) -> Path:
    """Write the minimal wheel/sdist pair the verifier accepts."""
    version = _declared_version()
    wheel = directory / f"openauc-{version}-py3-none-any.whl"
    with zipfile.ZipFile(wheel, "w") as archive:
        for entry in _required_wheel_entries():
            if entry == omit:
                continue
            archive.writestr(entry, b"")
        archive.writestr(f"openauc-{version}.dist-info/METADATA", "")
    (directory / f"openauc-{version}.tar.gz").write_bytes(b"")
    return directory


def _run_verifier(dist: Path) -> subprocess.CompletedProcess[str]:
    env = {key: value for key, value in os.environ.items() if key != "GITHUB_REF"}
    return subprocess.run(
        [sys.executable, str(SCRIPTS / "verify_artifacts.py"), str(dist)],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )


# --------------------------------------------------------------------------- #
# Coverage gate
# --------------------------------------------------------------------------- #


def test_coverage_gate_is_configured() -> None:
    config = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    report = config["tool"]["coverage"]["report"]
    assert isinstance(report["fail_under"], int | float)
    assert report["fail_under"] >= 90, "the gate must be meaningful"
    assert config["tool"]["coverage"]["run"]["branch"] is True


def test_every_pytest_run_measures_coverage() -> None:
    config = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    addopts = config["tool"]["pytest"]["ini_options"]["addopts"]
    assert "--cov=openauc" in addopts


# --------------------------------------------------------------------------- #
# Release scripts
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("name", ["release_check.py", "verify_artifacts.py"])
def test_release_scripts_exist_and_import_cleanly(name: str) -> None:
    path = SCRIPTS / name
    assert path.is_file(), path
    compile(path.read_text(encoding="utf-8"), str(path), "exec")


def test_release_check_runs_every_gate() -> None:
    source = (SCRIPTS / "release_check.py").read_text(encoding="utf-8")
    for fragment in ("ruff", "check", "format", "mypy", "pytest", "mkdocs"):
        assert fragment in source, fragment


def test_release_scripts_do_not_publish() -> None:
    for path in SCRIPTS.glob("*.py"):
        source = path.read_text(encoding="utf-8").lower()
        for forbidden in ("twine upload", "pypi.org/legacy", "gh release create"):
            assert forbidden not in source, f"{path.name} contains {forbidden!r}"


def test_verify_artifacts_reports_a_version_mismatch(tmp_path: Path) -> None:
    """A dist directory holding the wrong artifacts must fail, not pass."""
    (tmp_path / "openauc-9.9.9-py3-none-any.whl").write_bytes(b"")
    (tmp_path / "openauc-9.9.9.tar.gz").write_bytes(b"")
    result = _run_verifier(tmp_path)
    assert result.returncode == 1
    assert "expected openauc-" in result.stdout or "FAIL" in result.stdout


def test_verify_artifacts_accepts_a_well_formed_dist(tmp_path: Path) -> None:
    """The positive path, on a fixture: never on the developer's own ``dist/``.

    A repository-local ``dist/`` is mutable developer state — stale artifacts
    from an earlier version make it hold two wheels and two sdists, which the
    verifier is right to reject. The real build is integration-tested by the
    release dry-run workflow; here we assert the verifier's contract against a
    minimal, deterministic artifact pair.
    """
    dist = _fabricate_dist(tmp_path)
    result = _run_verifier(dist)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "PASS" in result.stdout


def test_verify_artifacts_rejects_a_wheel_missing_py_typed(tmp_path: Path) -> None:
    dist = _fabricate_dist(tmp_path, omit="openauc/py.typed")
    result = _run_verifier(dist)
    assert result.returncode == 1
    assert "missing openauc/py.typed" in result.stdout


def test_verify_artifacts_rejects_a_corrupt_wheel(tmp_path: Path) -> None:
    (tmp_path / f"openauc-{_declared_version()}-py3-none-any.whl").write_bytes(
        b"not a zip"
    )
    (tmp_path / f"openauc-{_declared_version()}.tar.gz").write_bytes(b"")
    result = _run_verifier(tmp_path)
    assert result.returncode == 1
    assert "not a readable wheel" in result.stdout


def test_verify_artifacts_rejects_stale_artifacts_alongside_current_ones(
    tmp_path: Path,
) -> None:
    """The defect that motivated the fixture: a dist holding two versions."""
    dist = _fabricate_dist(tmp_path)
    (dist / "openauc-0.0.1.dev0-py3-none-any.whl").write_bytes(b"")
    (dist / "openauc-0.0.1.dev0.tar.gz").write_bytes(b"")
    result = _run_verifier(dist)
    assert result.returncode == 1
    assert "expected exactly one wheel" in result.stdout


# --------------------------------------------------------------------------- #
# The dry-run workflow cannot publish
# --------------------------------------------------------------------------- #


def test_release_workflow_exists() -> None:
    assert RELEASE_WORKFLOW.is_file()


def test_release_workflow_has_read_only_permissions() -> None:
    workflow = _workflow()
    assert workflow["permissions"] == {"contents": "read"}


def test_release_workflow_has_no_publishing_step() -> None:
    text = RELEASE_WORKFLOW.read_text(encoding="utf-8").lower()
    for forbidden in (
        "twine upload",
        "pypa/gh-action-pypi-publish",
        "gh release create",
        "softprops/action-gh-release",
        "actions/create-release",
        "pypi_api_token",
        "id-token: write",
    ):
        assert forbidden not in text, f"release workflow contains {forbidden!r}"


def test_release_workflow_builds_verifies_and_smoke_tests() -> None:
    text = RELEASE_WORKFLOW.read_text(encoding="utf-8")
    assert "uv build" in text
    assert "twine check" in text
    assert "scripts/verify_artifacts.py" in text
    assert "scripts/release_check.py" in text
    assert "openauc version" in text


def test_release_workflow_runs_on_dispatch_and_pull_requests() -> None:
    triggers = _triggers()
    assert "workflow_dispatch" in triggers
    assert "pull_request" in triggers


def test_every_script_the_workflow_runs_is_a_trigger_path() -> None:
    """Derived from the workflow's own commands, so it cannot drift."""
    executed = _scripts_executed_by_the_workflow()
    assert executed, "expected the workflow to run at least one script"
    paths = set(_pull_request_paths())
    for script in executed:
        assert script in paths, f"{script} is executed but does not trigger the run"


@pytest.mark.parametrize(
    "path",
    [
        "pyproject.toml",
        "uv.lock",
        "src/openauc/__init__.py",
        "CITATION.cff",
        ".github/workflows/release.yml",
    ],
)
def test_build_inputs_trigger_the_release_dry_run(path: str) -> None:
    """The lock file is included: resolution changes the environment built in."""
    assert path in _pull_request_paths(), path


def test_every_trigger_path_exists() -> None:
    for path in _pull_request_paths():
        assert (ROOT / path).exists(), path


def test_no_workflow_uploads_with_twine() -> None:
    """``twine upload`` is never the publication mechanism, anywhere.

    Publication goes through the PyPA action under Trusted Publishing, which
    needs no credential of ours; a `twine upload` would imply one exists.
    """
    for workflow in WORKFLOWS.glob("*.yml"):
        text = workflow.read_text(encoding="utf-8").lower()
        assert "twine upload" not in text, workflow.name


def test_only_the_publish_workflow_may_publish_to_pypi() -> None:
    """Narrower than "nothing publishes": exactly one workflow is allowed to.

    Phase 9 could assert that no workflow published at all. Now that a
    dedicated production workflow exists, the durable property is that the
    publishing capability is confined to that one file.
    """
    holders = {
        workflow.name
        for workflow in WORKFLOWS.glob("*.yml")
        if PUBLISHING_ACTION in workflow.read_text(encoding="utf-8").lower()
    }
    assert holders == {PUBLISH_WORKFLOW.name}


def test_no_other_workflow_can_authenticate_to_pypi() -> None:
    """`docs.yml` legitimately holds an OIDC identity — for GitHub Pages.

    So the property is not "no workflow requests `id-token`" but: no workflow
    other than the publishing one pairs an OIDC identity with a PyPI audience.
    """
    for workflow in WORKFLOWS.glob("*.yml"):
        if workflow.name == PUBLISH_WORKFLOW.name:
            continue
        text = workflow.read_text(encoding="utf-8").lower()
        if "id-token" in text:
            assert "pypi" not in text, workflow.name
            assert PUBLISHING_ACTION not in text, workflow.name


def test_the_release_dry_run_requests_no_oidc_identity() -> None:
    assert "id-token" not in RELEASE_WORKFLOW.read_text(encoding="utf-8").lower()


# --------------------------------------------------------------------------- #
# The production publishing workflow is pinned to its security model
# --------------------------------------------------------------------------- #


def test_publish_workflow_exists_and_is_parseable() -> None:
    assert PUBLISH_WORKFLOW.is_file()
    assert _publish_jobs()


def test_publish_workflow_triggers_only_on_a_published_release() -> None:
    """A pushed tag must not publish; a *draft* release must not publish."""
    triggers = _triggers_of(_publish_workflow())
    assert set(triggers) == {"release"}
    release = triggers["release"]
    assert isinstance(release, dict)
    assert release["types"] == ["published"]


@pytest.mark.parametrize("trigger", ["push", "pull_request", "workflow_dispatch"])
def test_publish_workflow_has_no_bypass_trigger(trigger: str) -> None:
    """No branch, no untrusted pull request and no manual run reaches PyPI."""
    assert trigger not in _triggers_of(_publish_workflow())


def test_publish_workflow_grants_no_workflow_scoped_permissions() -> None:
    """OIDC is granted per job, never at workflow scope."""
    assert _publish_workflow()["permissions"] == {}


def test_publish_workflow_separates_build_from_publication() -> None:
    jobs = _publish_jobs()
    assert set(jobs) == {"build-and-verify", "publish-to-pypi"}
    needs = jobs["publish-to-pypi"]["needs"]
    assert needs == ["build-and-verify"] or needs == "build-and-verify"


def test_publish_workflow_build_job_has_no_publishing_identity() -> None:
    build = _publish_jobs()["build-and-verify"]
    assert build["permissions"] == {"contents": "read"}
    assert "environment" not in build
    for step in _publish_steps("build-and-verify"):
        assert PUBLISHING_ACTION not in _uses(step)


def test_publish_job_holds_the_oidc_identity_and_nothing_else() -> None:
    publish = _publish_jobs()["publish-to-pypi"]
    assert publish["permissions"] == {"id-token": "write"}


def test_publish_job_uses_the_pypi_environment() -> None:
    environment = _publish_jobs()["publish-to-pypi"]["environment"]
    name = environment["name"] if isinstance(environment, dict) else environment
    assert name == "pypi"


def test_publish_job_neither_checks_out_source_nor_runs_project_code() -> None:
    """The OIDC-bearing job must execute none of this repository's code."""
    for step in _publish_steps("publish-to-pypi"):
        assert "run" not in step, f"publish job runs a shell step: {step}"
        uses = _uses(step)
        assert not uses.startswith("actions/checkout"), uses
        assert not uses.startswith("astral-sh/setup-uv"), uses


def test_distributions_cross_the_job_boundary_as_an_artifact() -> None:
    """The published files are the ones the verified build produced."""
    uploads = [
        step
        for step in _publish_steps("build-and-verify")
        if _uses(step).startswith("actions/upload-artifact")
    ]
    downloads = [
        step
        for step in _publish_steps("publish-to-pypi")
        if _uses(step).startswith("actions/download-artifact")
    ]
    assert len(uploads) == 1 and len(downloads) == 1
    assert _with(uploads[0])["name"] == _with(downloads[0])["name"]


def test_publish_step_is_pinned_to_a_commit_sha() -> None:
    """A mutable tag on a credential-bearing action is a supply-chain risk."""
    pinned = [
        _uses(step)
        for step in _publish_steps("publish-to-pypi")
        if PUBLISHING_ACTION in _uses(step)
    ]
    assert len(pinned) == 1
    _, _, ref = pinned[0].partition("@")
    assert re.fullmatch(r"[0-9a-f]{40}", ref), f"not a commit SHA: {ref!r}"


def test_every_action_in_the_publish_workflow_is_pinned_to_a_commit_sha() -> None:
    """Not just the PyPI action: every step of the production release path.

    `checkout` decides what source is built, `setup-uv` decides the build
    environment, `upload-artifact` decides what crosses the trust boundary, and
    `download-artifact` runs inside the job holding `id-token: write`. A
    mutable `@v4`/`@v5`/`@main` on any of them reopens the hole this workflow
    closes, so reverting a pin must fail the suite.

    Deliberately scoped to `publish.yml`: the dry run and ordinary CI are not
    on the production publication path and keep the repository's usual pins.
    """
    steps = [
        step for job in _publish_jobs() for step in _publish_steps(job) if _uses(step)
    ]
    assert len(steps) >= 5, "expected the workflow to use several actions"
    for step in steps:
        action, _, ref = _uses(step).partition("@")
        assert re.fullmatch(r"[0-9a-f]{40}", ref), f"{action} is pinned to {ref!r}"


def test_downloaded_artifact_digest_mismatch_fails_the_publication() -> None:
    """Integrity is checked, not assumed, before the PyPI step ever runs.

    The upload records the artifact's digest; `download-artifact` v8 validates
    the download against it. `digest-mismatch: error` is v8's default, but a
    production policy must not rest on an upstream default, so it is stated
    explicitly — and pinned here.
    """
    steps = _publish_steps("publish-to-pypi")
    downloads = [
        step for step in steps if _uses(step).startswith("actions/download-artifact@")
    ]
    assert len(downloads) == 1
    action, _, ref = _uses(downloads[0]).partition("@")
    assert re.fullmatch(r"[0-9a-f]{40}", ref), f"{action} is pinned to {ref!r}"
    assert _with(downloads[0])["digest-mismatch"] == "error"

    # The digest check is a v8 capability: a downgrade would silently remove it.
    line = next(
        line
        for line in PUBLISH_WORKFLOW.read_text(encoding="utf-8").splitlines()
        if "actions/download-artifact@" in line
    )
    assert re.search(r"#\s*v8\.\d+", line), line

    # And it must run before publication: the download is the first step.
    assert steps.index(downloads[0]) < min(
        index for index, step in enumerate(steps) if PUBLISHING_ACTION in _uses(step)
    )


def test_publish_workflow_pins_carry_a_readable_version_comment() -> None:
    """A bare SHA is unreviewable; each pin names the release it is."""
    for line in PUBLISH_WORKFLOW.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped.startswith("uses:"):
            continue
        assert re.search(r"#\s*v\d+\.\d+", stripped), stripped


def test_build_job_checks_out_the_immutable_release_commit() -> None:
    """`github.sha` is the released commit; the tag *name* is re-resolvable.

    Checking out `github.sha` means a tag moved between publishing the Release
    and this run cannot change what is built. `GITHUB_REF` is still the tag
    ref, so `verify_artifacts.py` keeps checking tag against version.
    """
    checkouts = [
        step
        for step in _publish_steps("build-and-verify")
        if _uses(step).startswith("actions/checkout@")
    ]
    assert len(checkouts) == 1
    options = _with(checkouts[0])
    assert options["ref"] == "${{ github.sha }}"
    assert options["persist-credentials"] is False


def test_publish_step_supplies_no_credentials() -> None:
    """Trusted Publishing means no username, no password, no API token."""
    for step in _publish_steps("publish-to-pypi"):
        options = _with(step)
        assert "user" not in options
        assert "password" not in options
    text = PUBLISH_WORKFLOW.read_text(encoding="utf-8").lower()
    for forbidden in ("pypi_api_token", "pypi_token", "secrets.pypi", "twine upload"):
        assert forbidden not in text, forbidden


def test_publish_step_does_not_skip_existing_distributions() -> None:
    """Republishing a version must fail loudly, not be silently tolerated."""
    for step in _publish_steps("publish-to-pypi"):
        assert "skip-existing" not in _with(step)


# --------------------------------------------------------------------------- #
# Nothing in the automation manufactures a release tag
#
# These assert a property of the machinery, not the current absence of tags: a
# clone that has fetched `v0.1.0a1` must still pass the whole suite.
# --------------------------------------------------------------------------- #

TAG_CREATING_COMMANDS = (
    "git tag",
    "git push --tags",
    "git push --follow-tags",
    "gh release create",
    "actions/create-release",
    "softprops/action-gh-release",
    "rickstaa/action-create-tag",
    "create-git-tag",
    "refs/tags/{",
)


def _automation_sources() -> list[Path]:
    sources = [*WORKFLOWS.glob("*.yml"), *SCRIPTS.glob("*.py")]
    assert sources
    return sources


@pytest.mark.parametrize("forbidden", TAG_CREATING_COMMANDS)
def test_no_automation_creates_or_pushes_a_release_tag(forbidden: str) -> None:
    for path in _automation_sources():
        text = path.read_text(encoding="utf-8").lower()
        assert forbidden not in text, f"{path.name} contains {forbidden!r}"


def test_release_scripts_never_write_to_git_or_the_network() -> None:
    for path in SCRIPTS.glob("*.py"):
        source = path.read_text(encoding="utf-8").lower()
        for forbidden in ("git push", "git commit", "urllib.request", "requests."):
            assert forbidden not in source, f"{path.name} contains {forbidden!r}"


def test_verify_artifacts_only_reads_the_tag_it_is_given() -> None:
    """The tag check must observe `GITHUB_REF`, never produce a tag."""
    source = (SCRIPTS / "verify_artifacts.py").read_text(encoding="utf-8")
    assert 'os.environ.get("GITHUB_REF"' in source
    assert "subprocess" not in source


# --------------------------------------------------------------------------- #
# The checklist is documented and honest
# --------------------------------------------------------------------------- #


def test_release_checklist_is_documented_and_navigable() -> None:
    checklist = ROOT / "docs" / "project" / "release-checklist.md"
    assert checklist.is_file()
    nav = (ROOT / "mkdocs.yml").read_text(encoding="utf-8")
    assert "project/release-checklist.md" in nav


def _checklist() -> str:
    text = (ROOT / "docs" / "project" / "release-checklist.md").read_text(
        encoding="utf-8"
    )
    return " ".join(text.lower().split())


def test_release_checklist_keeps_the_human_gates_manual() -> None:
    """Durable: tagging and the GitHub Release are never automated.

    Publication itself is now automated — but only downstream of a Release a
    human published. What must stay documented as manual is that gate.
    """
    normalised = _checklist()
    for step in ("tagging", "github release", "pypi"):
        assert step in normalised, step
    assert "manual" in normalised
    for claim in (
        "the workflow creates the tag",
        "tagging is automated",
        "automatically creates the github release",
    ):
        assert claim not in normalised, claim


def test_release_checklist_documents_the_trusted_publisher_setup() -> None:
    """The manual PyPI/GitHub configuration must be written down, exactly."""
    normalised = _checklist()
    for fragment in (
        "trusted publish",
        "publish.yml",
        "pypi",
        "environment",
        "openauc",
        "ronfinn",
        "openauc-io",
    ):
        assert fragment in normalised, fragment


def test_changelog_documents_the_declared_version() -> None:
    """Durable: the section exists and is either unreleased or dated."""
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    heading = next(
        (
            line
            for line in changelog.splitlines()
            if line.startswith(f"## [{EXPECTED_VERSION}]")
        ),
        None,
    )
    assert heading is not None, f"no changelog section for {EXPECTED_VERSION}"
    remainder = heading.split("]", 1)[1].strip(" -")
    assert remainder == "unreleased" or re.fullmatch(r"\d{4}-\d{2}-\d{2}", remainder), (
        f"changelog heading must be 'unreleased' or an ISO date, got {remainder!r}"
    )
    assert "Phase 9" in changelog
