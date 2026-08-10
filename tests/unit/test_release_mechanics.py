"""Release mechanics: the coverage gate, the release scripts and the dry run.

These tests pin the *boundaries* of the release machinery as much as its
existence: the dry-run workflow must not be able to publish, and the checklist
must not claim that anything has been published.
"""

from __future__ import annotations

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


def _workflow() -> dict[str, object]:
    loaded = yaml.safe_load(RELEASE_WORKFLOW.read_text(encoding="utf-8"))
    assert isinstance(loaded, dict)
    return loaded


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


def test_no_workflow_publishes_anywhere() -> None:
    for workflow in WORKFLOWS.glob("*.yml"):
        text = workflow.read_text(encoding="utf-8").lower()
        assert "twine upload" not in text, workflow.name
        assert "gh-action-pypi-publish" not in text, workflow.name


# --------------------------------------------------------------------------- #
# The checklist is documented and honest
# --------------------------------------------------------------------------- #


def test_release_checklist_is_documented_and_navigable() -> None:
    checklist = ROOT / "docs" / "project" / "release-checklist.md"
    assert checklist.is_file()
    nav = (ROOT / "mkdocs.yml").read_text(encoding="utf-8")
    assert "project/release-checklist.md" in nav


def test_release_checklist_does_not_claim_a_release_happened() -> None:
    text = (ROOT / "docs" / "project" / "release-checklist.md").read_text(
        encoding="utf-8"
    )
    lowered = text.lower()
    assert "unpublished" in lowered
    assert "no pypi upload, no github release, no tag" in " ".join(lowered.split())
    # Affirmative claims only: the page's *denials* ("nothing has been released
    # yet") must not be mistaken for the claim they deny.
    for claim in (
        "is available on pypi",
        "was published to pypi",
        "0.1.0a1 has been released",
    ):
        assert claim not in lowered, claim


def test_changelog_still_marks_the_alpha_unreleased() -> None:
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    assert "## [0.1.0a1] - unreleased" in changelog
    assert "Phase 9" in changelog


def test_no_release_tag_was_created() -> None:
    tags = subprocess.run(
        ["git", "tag", "--list", "v*"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.split()
    assert tags == [], f"unexpected release tags: {tags}"
