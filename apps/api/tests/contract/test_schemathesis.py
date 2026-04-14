"""Schemathesis contract test.

Runs against a live server; skipped when the API is not reachable.
CI runs this after `uv run uvicorn` is started.
"""

from __future__ import annotations

import os

import pytest

pytestmark = pytest.mark.skipif(
    not os.environ.get("RUN_CONTRACT_TESTS"),
    reason="Set RUN_CONTRACT_TESTS=1 to run Schemathesis (requires live server)",
)


def test_schemathesis_placeholder() -> None:
    pytest.skip(
        "Schemathesis is run via CLI in CI: "
        "`schemathesis run http://localhost:8000/openapi.json --checks all`"
    )
