"""Public health endpoint."""

from __future__ import annotations

import os

from fastapi import APIRouter

from dailyriff_api import __version__

router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "version": __version__,
        "git_sha": os.environ.get("GIT_SHA", "dev"),
    }
