"""FastAPI app entrypoint.

Boot via: `uv run uvicorn dailyriff_api.main:app --reload --port 8000`
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from dailyriff_api.db import close_pool, init_pool
from dailyriff_api.routers import devices, health, preferences


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_pool()
    yield
    await close_pool()


app = FastAPI(title="DailyRiff API", version="0.0.0", lifespan=lifespan)

app.include_router(health.router)
app.include_router(devices.router)
app.include_router(preferences.router)
