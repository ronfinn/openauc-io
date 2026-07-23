"""The committed JSON Schema must stay consistent with the Pydantic model.

If this test fails after a manifest-model change, regenerate the schema with the
same metadata overrides applied below and commit the result.
"""

from __future__ import annotations

import json
from pathlib import Path

from openauc.formats.manifest import GenericManifest

_SCHEMA_PATH = (
    Path(__file__).resolve().parents[2] / "schemas" / "generic-manifest-v1.schema.json"
)

_SCHEMA_META = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "https://openauc.io/schemas/generic-manifest-v1.schema.json",
    "title": "openauc generic experiment manifest (v1)",
}


def _expected_schema() -> dict[str, object]:
    schema = GenericManifest.model_json_schema()
    schema.update(_SCHEMA_META)
    return schema


def test_committed_schema_matches_model() -> None:
    committed = json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))
    assert committed == _expected_schema()
