"""FastAPI app entrypoint.

Boot via: `uv run uvicorn dailyriff_api.main:app --reload --port 8000`
"""

from __future__ import annotations

from fastapi import FastAPI

from dailyriff_api.routers import devices, health, preferences

app = FastAPI(title="DailyRiff API", version="0.0.0")

app.include_router(health.router)
app.include_router(devices.router)
app.include_router(preferences.router)
