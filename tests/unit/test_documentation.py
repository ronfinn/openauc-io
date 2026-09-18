"""Documentation smoke tests: the site's promises must match the code.

These check structure and resolvability, not prose. They deliberately do not
parse Markdown beyond simple, robust patterns.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
import yaml

import openauc

ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / "docs"
MKDOCS = ROOT / "mkdocs.yml"


def _nav_files(node: object, found: list[str]) -> list[str]:
    """Every Markdown path named anywhere in the nav tree."""
    if isinstance(node, str):
        if node.endswith(".md"):
            found.append(node)
    elif isinstance(node, list):
        for item in node:
            _nav_files(item, found)
    elif isinstance(node, dict):
        for value in node.values():
            _nav_files(value, found)
    return found


@pytest.fixture(scope="module")
def config() -> dict[str, Any]:
    """mkdocs.yml, parsed. It is plain YAML with no custom tags."""
    loaded = yaml.safe_load(MKDOCS.read_text(encoding="utf-8"))
    assert isinstance(loaded, dict)
    return loaded


# --------------------------------------------------------------------------- #
# Configuration and navigation
# --------------------------------------------------------------------------- #


def test_mkdocs_config_is_present_and_coherent(config: dict[str, Any]) -> None:
    assert config["site_name"] == "openauc-io"
    assert config["site_url"] == "https://ronfinn.github.io/openauc-io/"
    assert config["repo_url"] == "https://github.com/ronfinn/openauc-io"
    assert config["repo_name"] == "ronfinn/openauc-io"
    assert config["theme"]["name"] == "material"


def test_mkdocstrings_is_configured_for_src(config: dict[str, Any]) -> None:
    plugins = config["plugins"]
    assert isinstance(plugins, list)
    entry = next(p for p in plugins if isinstance(p, dict) and "mkdocstrings" in p)
    python = entry["mkdocstrings"]["handlers"]["python"]
    assert python["paths"] == ["src"]


def test_every_file_named_in_nav_exists(config: dict[str, Any]) -> None:
    missing = [
        relative
        for relative in _nav_files(config["nav"], [])
        if not (DOCS / relative).is_file()
    ]
    assert missing == [], missing


def test_the_navigation_covers_every_required_section(
    config: dict[str, Any],
) -> None:
    named = set(_nav_files(config["nav"], []))
    for required in (
        "index.md",
        "getting-started/installation.md",
        "getting-started/quickstart.md",
        "tutorials/python-workflow.md",
        "tutorials/cli-workflow.md",
        "how-to/troubleshooting.md",
        "how-to/recipes.md",
        "concepts/validation-tiers.md",
        "concepts/scientific-boundaries.md",
        "concepts/provenance-and-checksums.md",
        "formats/aucx.md",
        "cli/exit-codes.md",
        "api/index.md",
        "project/changelog.md",
    ):
        assert required in named, required


def test_no_markdown_page_is_orphaned(config: dict[str, Any]) -> None:
    """Every page under docs/ is reachable from the navigation."""
    named = set(_nav_files(config["nav"], []))
    on_disk = {str(path.relative_to(DOCS)) for path in DOCS.rglob("*.md")}
    assert on_disk - named == set()


# --------------------------------------------------------------------------- #
# Documented interfaces resolve
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


def test_every_mkdocstrings_target_imports() -> None:
    """`::: some.dotted.path` must resolve to a real object."""
    from importlib import import_module

    pattern = re.compile(r"^:::\s+([A-Za-z_][\w.]*)\s*$", re.MULTILINE)
    targets: set[str] = set()
    for page in DOCS.rglob("*.md"):
        targets.update(pattern.findall(page.read_text(encoding="utf-8")))
    assert targets, "expected mkdocstrings directives in the API pages"

    for dotted in sorted(targets):
        module_path, _, attribute = dotted.rpartition(".")
        try:
            import_module(dotted)
            continue  # the target is itself a module
        except ImportError:
            pass
        module = import_module(module_path)
        assert hasattr(module, attribute), dotted


def test_documented_cli_commands_exist() -> None:
    from openauc.cli import app

    documented = {"version", "formats", "generate", "inspect", "validate", "convert"}
    registered = {
        command.callback.__name__
        for command in app.registered_commands
        if command.callback is not None
    }
    assert documented <= registered, documented - registered
    # And each has its own reference page.
    for name in documented:
        assert (DOCS / "cli" / f"{name}.md").is_file(), name


def test_documented_exit_codes_match_the_implementation() -> None:
    from openauc.cli import ExitCode

    assert (ExitCode.OK, ExitCode.VALIDATION_FAILED) == (0, 1)
    assert (ExitCode.INPUT_ERROR, ExitCode.OUTPUT_EXISTS) == (2, 3)
    page = (DOCS / "cli" / "exit-codes.md").read_text(encoding="utf-8")
    for code in ("`0`", "`1`", "`2`", "`3`"):
        assert code in page


def test_documented_scenarios_match_the_implementation() -> None:
    from openauc.synthetic import Scenario

    page = (DOCS / "cli" / "generate.md").read_text(encoding="utf-8")
    concept = (DOCS / "concepts" / "synthetic-data.md").read_text(encoding="utf-8")
    for scenario in Scenario:
        assert scenario.value in page, scenario.value
        assert scenario.value in concept, scenario.value


def test_documented_formats_match_the_registry() -> None:
    page = (DOCS / "cli" / "formats.md").read_text(encoding="utf-8")
    for info in openauc.available_formats():
        assert info.format_id in page, info.format_id


# --------------------------------------------------------------------------- #
# Documented examples actually work
# --------------------------------------------------------------------------- #


def test_the_readme_end_to_end_example_runs(tmp_path: Path) -> None:
    from openauc.plotting import plot_scans

    experiment = openauc.load(ROOT / "examples" / "data" / "demo_experiment")
    assert experiment.summary()
    assert experiment.validate().is_valid
    axes = plot_scans(experiment)
    assert len(axes.lines) == len(experiment.scans)
    restored = openauc.load(experiment.export(tmp_path / "experiment.aucx"))
    assert restored.to_dict() == experiment.to_dict()


def test_the_documented_manifest_example_loads(tmp_path: Path) -> None:
    """The generic-long manifest and CSV printed in the docs must work."""
    directory = tmp_path / "long-example"
    directory.mkdir()
    (directory / "scans.csv").write_text(
        "scan,radius_cm,signal,elapsed_seconds\n"
        "scan_001,5.90,0.0120,0\n"
        "scan_001,5.92,0.0185,0\n"
        "scan_002,5.90,0.0080,600\n"
        "scan_002,5.92,0.0110,600\n",
        encoding="utf-8",
    )
    (directory / "manifest.json").write_text(
        """{
  "schema_version": "1.0",
  "format": "generic-long",
  "data_file": "scans.csv",
  "experiment": {
    "experiment_id": "long-example-001",
    "name": "Long-format example",
    "experiment_type": "sedimentation_velocity"
  },
  "defaults": {
    "optical_system": "absorbance",
    "signal_unit": "absorbance_unit"
  }
}
""",
        encoding="utf-8",
    )
    experiment = openauc.load(directory)
    assert experiment.metadata.experiment_id == "long-example-001"
    assert len(experiment.scans) == 2
    assert experiment.validate_structure().is_valid


def test_the_documented_wide_manifest_example_loads(tmp_path: Path) -> None:
    directory = tmp_path / "wide-example"
    directory.mkdir()
    (directory / "scans.csv").write_text(
        "radius_cm,scan_001,scan_002\n5.90,0.0120,0.0080\n5.92,0.0185,0.0110\n",
        encoding="utf-8",
    )
    (directory / "manifest.json").write_text(
        """{
  "schema_version": "1.0",
  "format": "generic-wide",
  "data_file": "scans.csv",
  "experiment": {"experiment_id": "wide-example-001"},
  "defaults": {"optical_system": "absorbance", "signal_unit": "absorbance_unit"},
  "columns": {
    "radius": "radius_cm",
    "scans": [
      {"column": "scan_001", "scan_id": "scan_001", "elapsed_seconds": 0},
      {"column": "scan_002", "scan_id": "scan_002", "elapsed_seconds": 600}
    ]
  }
}
""",
        encoding="utf-8",
    )
    experiment = openauc.load(directory)
    assert len(experiment.scans) == 2
    assert experiment.validate_structure().is_valid


def test_the_documented_aucx_round_trip_holds(tmp_path: Path) -> None:
    experiment = openauc.load(ROOT / "examples" / "data" / "demo_experiment")
    archive = experiment.export(tmp_path / "demo.aucx")
    info = openauc.inspect_aucx(archive)
    assert info.aucx_format_version == "1.0"
    assert info.checksum_verified
    assert openauc.validate_aucx(archive).is_valid
    assert openauc.load(archive).to_dict() == experiment.to_dict()


def test_the_documented_hand_built_recipe_works(tmp_path: Path) -> None:
    """Recipe 11 in how-to/recipes.md."""
    from openauc.models import (
        AUCExperiment,
        ExperimentMetadata,
        ExperimentType,
        Observations,
        OpticalSystem,
        Quantity,
        ScanMetadata,
        Unit,
    )

    experiment = AUCExperiment(
        metadata=ExperimentMetadata(
            experiment_id="hand-built-001",
            experiment_type=ExperimentType.SEDIMENTATION_VELOCITY,
        ),
        scans=tuple(
            ScanMetadata(
                scan_id=f"scan_{index + 1:03d}",
                index=index,
                elapsed_time=Quantity.of(index * 600.0, Unit.SECOND),
                optical_system=OpticalSystem.ABSORBANCE,
                rotor_speed=Quantity.of(45000.0, Unit.RPM),
                temperature=Quantity.unknown(),
            )
            for index in range(2)
        ),
        observations=Observations.from_shared_axis(
            radius=[6.00, 6.02, 6.04],
            signal=[[0.10, 0.20, 0.30], [0.08, 0.17, 0.28]],
            scan_ids=["scan_001", "scan_002"],
            signal_unit=Unit.ABSORBANCE_UNIT,
        ),
    )
    assert experiment.validate_structure().is_valid
    assert experiment.export(tmp_path / "hand-built.aucx").is_file()


@pytest.mark.parametrize(
    "script",
    ["01_load_generic.py", "05_aucx_roundtrip.py", "generate_synthetic_experiment.py"],
)
def test_key_example_scripts_execute(script: str) -> None:
    result = subprocess.run(
        [sys.executable, str(ROOT / "examples" / script)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


# --------------------------------------------------------------------------- #
# Claims
# --------------------------------------------------------------------------- #


_NEGATORS = ("not", "never", "no ", "without", "refus", "cannot", "n't", "nothing")


def _affirmative_uses(text: str, phrase: str) -> list[str]:
    """Occurrences of ``phrase`` that are not part of a denial.

    The docs deliberately deny several of these claims, so a bare substring
    search would flag exactly the sentences that make the project honest. Only
    an occurrence with no negator in the preceding clause counts.
    """
    hits: list[str] = []
    start = 0
    while (index := text.find(phrase, start)) != -1:
        preceding = text[max(0, index - 90) : index]
        if not any(negator in preceding for negator in _NEGATORS):
            hits.append(text[max(0, index - 60) : index + len(phrase) + 20])
        start = index + len(phrase)
    return hits


def test_the_documentation_makes_no_forbidden_claim() -> None:
    """Only affirmative claims are forbidden; denials of them are wanted."""
    forbidden = (
        "supports beckman",
        "supports optima",
        "sedfit compatible",
        "is scientifically valid",
        "physically accurate",
        "accurate simulation",
        "automatically converts units",
        "validated simulation of",
    )
    for page in DOCS.rglob("*.md"):
        text = " ".join(page.read_text(encoding="utf-8").lower().split())
        for phrase in forbidden:
            hits = _affirmative_uses(text, phrase)
            assert hits == [], (str(page), phrase, hits)


def test_alpha_installation_guidance_is_explicit() -> None:
    """Alpha installation guidance should be explicit and reproducible.

    A documented command with no version and no ``--pre`` leaves what gets
    installed up to the installer and to whatever is published at the time.
    While the released version is a pre-release, instructions must name the
    version or pass ``--pre``. This is a documentation policy, not a claim
    that a bare install is invalid.
    """
    for page in [*DOCS.rglob("*.md"), ROOT / "README.md"]:
        text = page.read_text(encoding="utf-8").lower()
        for line in text.splitlines():
            stripped = line.strip().lstrip("$ ").strip()
            assert stripped != "pip install openauc", str(page)
            assert stripped != "python -m pip install openauc", str(page)
            assert stripped != "uv pip install openauc", str(page)


def test_the_boundaries_are_stated_where_they_matter() -> None:
    home = " ".join((DOCS / "index.md").read_text(encoding="utf-8").lower().split())
    assert "no scientific analysis" in home
    assert "not_assessed" in home

    install = (DOCS / "getting-started" / "installation.md").read_text(encoding="utf-8")
    assert "pypi" in install.lower()
    assert 'python -m pip install "openauc==0.1.0a1"' in install

    boundaries = (DOCS / "concepts" / "scientific-boundaries.md").read_text(
        encoding="utf-8"
    )
    for topic in ("convection", "aggregation", "meniscus", "unit conversion"):
        assert topic in boundaries.lower(), topic
