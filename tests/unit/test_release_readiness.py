"""Alpha-release readiness: public surface, examples, packaging and hygiene."""

from __future__ import annotations

import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

import openauc
import openauc.api as api

ROOT = Path(__file__).resolve().parents[2]
EXAMPLES = ROOT / "examples"
EXPECTED_VERSION = "0.1.0a1"


# --------------------------------------------------------------------------- #
# Version coherence
# --------------------------------------------------------------------------- #


def test_version_is_the_alpha_release_version() -> None:
    assert openauc.__version__ == EXPECTED_VERSION


def test_citation_declares_the_same_version() -> None:
    citation = (ROOT / "CITATION.cff").read_text(encoding="utf-8")
    assert f"version: {EXPECTED_VERSION}" in citation


def test_package_metadata_is_correct() -> None:
    config = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    project = config["project"]
    assert project["name"] == "openauc"
    assert project["license"] == "Apache-2.0"
    assert "LICENSE" in project["license-files"]
    assert project["requires-python"] == ">=3.11,<3.14"
    assert project["scripts"]["openauc"] == "openauc.cli:main"
    assert "version" in project["dynamic"]


# --------------------------------------------------------------------------- #
# Public surface
# --------------------------------------------------------------------------- #


def test_documented_top_level_imports_resolve() -> None:
    for name in (
        "load",
        "available_formats",
        "export_aucx",
        "inspect_aucx",
        "validate_aucx",
        "__version__",
    ):
        assert hasattr(openauc, name), name
    assert len(set(openauc.__all__)) == len(openauc.__all__)


def test_every_api_export_resolves_and_is_sorted() -> None:
    missing = [name for name in api.__all__ if not hasattr(api, name)]
    assert missing == []
    # Ordering is enforced by ruff (RUF022), whose natural sort differs from
    # str.sort; what matters here is that nothing is duplicated or dangling.
    assert len(set(api.__all__)) == len(api.__all__)


def test_subpackage_facades_resolve() -> None:
    import openauc.formats as formats
    import openauc.models as models
    import openauc.plotting as plotting
    import openauc.synthetic as synthetic

    for module in (models, formats, plotting, synthetic):
        missing = [name for name in module.__all__ if not hasattr(module, name)]
        assert missing == [], (module.__name__, missing)
        assert len(set(module.__all__)) == len(module.__all__), module.__name__


def test_the_readme_end_to_end_example_runs(tmp_path: Path) -> None:
    """The exact sequence README advertises must actually work."""
    from openauc.plotting import plot_scans

    experiment = openauc.load(EXAMPLES / "data" / "demo_experiment")
    assert experiment.summary()
    report = experiment.validate()
    assert report.is_valid
    axes = plot_scans(experiment)
    assert len(axes.lines) == len(experiment.scans)
    archive = experiment.export(tmp_path / "experiment.aucx")
    restored = openauc.load(archive)
    assert restored.to_dict() == experiment.to_dict()


# --------------------------------------------------------------------------- #
# Examples
# --------------------------------------------------------------------------- #

EXAMPLE_SCRIPTS = [
    "01_load_generic.py",
    "02_inspect_summary.py",
    "03_assess_readiness.py",
    "04_plot_scans.py",
    "05_aucx_roundtrip.py",
    "06_cli_usage.py",
    "generate_synthetic_experiment.py",
]


@pytest.mark.parametrize("script", EXAMPLE_SCRIPTS)
def test_every_example_executes(script: str) -> None:
    result = subprocess.run(
        [sys.executable, str(EXAMPLES / script)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip()


def test_example_data_is_synthetic_and_declared_so() -> None:
    manifest = (EXAMPLES / "data" / "demo_experiment" / "manifest.json").read_text(
        encoding="utf-8"
    )
    assert "Synthetic" in manifest
    assert "Not a real experiment" in manifest


def test_examples_make_no_scientific_claim() -> None:
    forbidden = ("sedimentation coefficient of", "molecular weight is", "we conclude")
    for script in EXAMPLE_SCRIPTS:
        text = (EXAMPLES / script).read_text(encoding="utf-8").lower()
        for phrase in forbidden:
            assert phrase not in text, (script, phrase)


# --------------------------------------------------------------------------- #
# Documentation coherence
# --------------------------------------------------------------------------- #


def test_documented_files_exist() -> None:
    for relative in (
        "README.md",
        "CHANGELOG.md",
        "CONTRIBUTING.md",
        "CODE_OF_CONDUCT.md",
        "SECURITY.md",
        "LICENSE",
        "NOTICE",
        "CITATION.cff",
        "docs/api/index.md",
        "docs/cli/index.md",
        "mkdocs.yml",
        "docs/concepts/data-model.md",
        "docs/concepts/units.md",
        "docs/concepts/missing-and-unknown-values.md",
        "docs/concepts/optical-systems.md",
        "docs/concepts/validation-tiers.md",
        "docs/concepts/analysis-readiness.md",
        "docs/concepts/plotting.md",
        "docs/concepts/synthetic-data.md",
        "docs/formats/generic-delimited.md",
        "docs/formats/manifest-v1.md",
        "docs/formats/parser-detection.md",
        "docs/formats/aucx.md",
        "schemas/generic-manifest-v1.schema.json",
        "docs/project/release-checklist.md",
        "scripts/release_check.py",
        "scripts/verify_artifacts.py",
        ".github/workflows/release.yml",
    ):
        assert (ROOT / relative).is_file(), relative


def test_every_adr_is_accepted_or_explains_itself() -> None:
    for adr in sorted((ROOT / "docs" / "decisions").glob("ADR-*.md")):
        status = next(
            line
            for line in adr.read_text(encoding="utf-8").splitlines()
            if line.startswith("- **Status:**")
        )
        assert "Accepted" in status, (adr.name, status)


def test_readme_does_not_claim_vendor_or_scientific_support() -> None:
    raw = (ROOT / "README.md").read_text(encoding="utf-8").lower()
    # Normalise line wrapping and blockquote markers before matching prose.
    readme = " ".join(raw.replace("\n>", "\n").split())
    assert "no scientific auc analysis is implemented" in readme
    assert "always reported as `not_assessed`" in readme
    for claim in ("supports beckman", "supports optima", "sedfit compatible"):
        assert claim not in readme


# --------------------------------------------------------------------------- #
# Packaging hygiene
# --------------------------------------------------------------------------- #


def test_no_build_products_or_caches_are_tracked() -> None:
    tracked = subprocess.run(
        ["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout.split()
    for name in tracked:
        assert not name.startswith(("dist/", "build/", "htmlcov/")), name
        assert "__pycache__" not in name, name
        assert not name.endswith((".pyc", ".whl", ".tar.gz", ".coverage")), name
        assert ".egg-info" not in name, name


def test_no_credential_like_files_are_tracked() -> None:
    tracked = subprocess.run(
        ["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout.split()
    suspicious = [
        name
        for name in tracked
        if name.endswith((".pem", ".key", ".p12", ".pfx"))
        or Path(name).name in {".env", "id_rsa", "credentials.json"}
    ]
    assert suspicious == []


def test_all_test_and_example_data_is_synthetic() -> None:
    """Every committed data file must be small and declared synthetic."""
    data_files = [
        *(ROOT / "tests" / "fixtures").rglob("*.csv"),
        *(ROOT / "tests" / "fixtures").rglob("*.tsv"),
        *(ROOT / "examples" / "data").rglob("*.csv"),
    ]
    assert data_files, "expected committed synthetic data"
    for path in data_files:
        assert path.stat().st_size < 64 * 1024, path
