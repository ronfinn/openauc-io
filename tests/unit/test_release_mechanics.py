"""Release mechanics: the coverage gate, the release scripts and the dry run.

These tests pin the *boundaries* of the release machinery as much as its
existence: the dry-run workflow must not be able to publish, and the checklist
must not claim that anything has been published.
"""

from __future__ import annotations

import re
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
WORKFLOWS = ROOT / ".github" / "workflows"
RELEASE_WORKFLOW = WORKFLOWS / "release.yml"
EXPECTED_VERSION = "0.1.0a1"


def _workflow() -> dict[object, object]:
    loaded = yaml.safe_load(RELEASE_WORKFLOW.read_text(encoding="utf-8"))
    assert isinstance(loaded, dict)
    return loaded


def _triggers() -> dict[object, object]:
    """YAML parses a bare ``on:`` key as the boolean ``True``."""
    workflow = _workflow()
    triggers = workflow["on"] if "on" in workflow else workflow[True]
    assert isinstance(triggers, dict)
    return triggers


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
    result = subprocess.run(
        [sys.executable, str(SCRIPTS / "verify_artifacts.py"), str(tmp_path)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 1
    assert "expected openauc-" in result.stdout or "FAIL" in result.stdout


def test_verify_artifacts_accepts_a_built_dist() -> None:
    # Building is environment-dependent; only assert when a dist is present.
    dist = ROOT / "dist"
    if not dist.is_dir() or not list(dist.glob("*.whl")):
        pytest.skip("no built distributions present")
    result = subprocess.run(
        [sys.executable, str(SCRIPTS / "verify_artifacts.py"), str(dist)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


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


def test_no_workflow_publishes_anywhere() -> None:
    for workflow in WORKFLOWS.glob("*.yml"):
        text = workflow.read_text(encoding="utf-8").lower()
        assert "twine upload" not in text, workflow.name
        assert "gh-action-pypi-publish" not in text, workflow.name


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


def test_release_checklist_keeps_publishing_manual() -> None:
    """Durable: whatever the release status, publishing is never automated."""
    text = (ROOT / "docs" / "project" / "release-checklist.md").read_text(
        encoding="utf-8"
    )
    normalised = " ".join(text.lower().split())
    for step in ("tagging", "github release", "pypi upload"):
        assert step in normalised, step
    assert "manual" in normalised
    for claim in (
        "the workflow publishes",
        "publishing is automated",
        "automatically uploads to pypi",
    ):
        assert claim not in normalised, claim


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
