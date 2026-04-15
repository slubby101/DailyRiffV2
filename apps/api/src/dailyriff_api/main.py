"""FastAPI app entrypoint.

Boot via: `uv run uvicorn dailyriff_api.main:app --reload --port 8000`
"""

from __future__ import annotations

from contextlib import asynccontextmanager

import asyncpg
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from dailyriff_api.db import close_pool, init_pool
from dailyriff_api.routers import devices, health, preferences, studios


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_pool()
    yield
    await close_pool()


app = FastAPI(title="DailyRiff API", version="0.0.0", lifespan=lifespan)


@app.exception_handler(asyncpg.exceptions.DataError)
async def _asyncpg_data_error_handler(
    request: Request, exc: asyncpg.exceptions.DataError
) -> JSONResponse:
    """Translate asyncpg DataError subclasses into 400 Bad Request.

    Covers UntranslatableCharacterError (null bytes), surrogate-pair
    encoding rejections, and other DataError subclasses that indicate
    the client sent input Postgres can't store. Without this handler
    the unhandled exception bubbles to a 500, which schemathesis
    correctly flags as a server error on random-string fuzz input.
    """
    return JSONResponse(
        status_code=400,
        content={"detail": "Input contains values that cannot be stored"},
    )


app.include_router(health.router)
app.include_router(devices.router)
app.include_router(preferences.router)
app.include_router(studios.router)
