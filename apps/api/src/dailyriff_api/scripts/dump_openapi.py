"""Dump the OpenAPI schema to stdout as formatted JSON.

Usage: `uv run python -m dailyriff_api.scripts.dump_openapi`

CI uses this to verify the committed snapshot is fresh.
"""

from __future__ import annotations

import json

from dailyriff_api.main import app


def main() -> None:
    schema = app.openapi()
    print(json.dumps(schema, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
