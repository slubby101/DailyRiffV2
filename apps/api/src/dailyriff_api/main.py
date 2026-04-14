"""FastAPI app entrypoint.

Boot via: `uv run uvicorn dailyriff_api.main:app --reload --port 8000`
"""

from __future__ import annotations

from contextlib import asynccontextmanager

import asyncpg
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from dailyriff_api.db import close_pool, init_pool
from dailyriff_api.routers import devices, health, preferences


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_pool()
    yield
    await close_pool()


app = FastAPI(title="DailyRiff API", version="0.0.0", lifespan=lifespan)


@app.exception_handler(asyncpg.exceptions.UntranslatableCharacterError)
async def _untranslatable_character_handler(
    request: Request, exc: asyncpg.exceptions.UntranslatableCharacterError
) -> JSONResponse:
    """Translate asyncpg's null-byte rejection into a 400 Bad Request.

    Postgres text columns can't store certain Unicode escape sequences
    (most commonly \\u0000). Without this handler, the unhandled
    asyncpg exception bubbles to a 500, which schemathesis correctly
    flags as a server error on random-string fuzz input.
    """
    return JSONResponse(
        status_code=400,
        content={"detail": "Input contains characters that cannot be stored"},
    )


app.include_router(health.router)
app.include_router(devices.router)
app.include_router(preferences.router)
