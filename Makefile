# DailyRiff development Makefile
#
# Prerequisites:
#   - `supabase start` running (localhost:54321/54322)
#   - `uv` installed for Python package management
#   - SUPABASE_SERVICE_ROLE env var set (from `supabase status`)

API_DIR := apps/api

# ---------------------------------------------------------------------------
# Database seeds
# ---------------------------------------------------------------------------

.PHONY: seed-polymet-only seed-edge-cases seed-rich migrate

## Run Alembic migrations to head
migrate:
	cd $(API_DIR) && uv run alembic upgrade head

## Seed Polymet's Mitchell Music Studio (idempotent)
seed-polymet-only: migrate
	cd $(API_DIR) && uv run python -m dailyriff_api.scripts.seed_polymet

## Seed synthetic edge cases on top of Polymet data (idempotent)
seed-edge-cases: seed-polymet-only
	cd $(API_DIR) && uv run python -m dailyriff_api.scripts.seed_edge_cases

## Seed everything: Polymet baseline + edge cases (idempotent)
seed-rich: seed-polymet-only seed-edge-cases

# ---------------------------------------------------------------------------
# Testing
# ---------------------------------------------------------------------------

.PHONY: test test-api test-web test-mobile

## Run API tests
test-api:
	cd $(API_DIR) && uv run pytest tests/ -v

## Run all tests
test: test-api
