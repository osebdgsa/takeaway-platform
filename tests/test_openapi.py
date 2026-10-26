"""The committed OpenAPI spec must match the schema generated from the app."""

import json
from pathlib import Path

from app.main import app

SPEC_PATH = Path(__file__).resolve().parent.parent / "openapi.json"


def test_committed_openapi_spec_exists() -> None:
    assert SPEC_PATH.exists(), "openapi.json is missing; run `make openapi`"


def test_committed_openapi_spec_is_current() -> None:
    committed = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
    assert (
        committed == app.openapi()
    ), "openapi.json is stale; run `make openapi` and commit the result"
