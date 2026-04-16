# gstack

Use the `/browse` skill from gstack for all web browsing. Never use `mcp__claude-in-chrome__*` tools.

Available gstack skills:
`/office-hours`, `/plan-ceo-review`, `/plan-eng-review`, `/plan-design-review`, `/design-consultation`, `/design-shotgun`, `/design-html`, `/review`, `/ship`, `/land-and-deploy`, `/canary`, `/benchmark`, `/browse`, `/connect-chrome`, `/qa`, `/qa-only`, `/design-review`, `/setup-browser-cookies`, `/setup-deploy`, `/retro`, `/investigate`, `/document-release`, `/codex`, `/cso`, `/autoplan`, `/plan-devex-review`, `/devex-review`, `/careful`, `/freeze`, `/guard`, `/unfreeze`, `/gstack-upgrade`, `/learn`.

# DailyRiff — Claude Code context

## Architecture

Monorepo with three apps and shared packages:

```
apps/api         FastAPI (Python, uv-managed)
apps/web         Next.js 15 (TypeScript)
apps/mobile      Expo (TypeScript, Zustand state)
packages/api-client  Auto-generated TypeScript client (@hey-api/openapi-ts)
tools/check-env.ts   Env var validator — runs at `pnpm dev` startup
```

- **Database:** Supabase Postgres via `supabase start` (localhost:54322). No cloud project yet.
- **Auth:** Supabase Auth JWT validated in FastAPI middleware (`apps/api/src/dailyriff_api/auth.py`). HS256 + `SUPABASE_JWT_SECRET`. `CurrentUser = {id: UUID, email: str|None, role: str|None}`.
- **Notifications:** 3-channel NotificationService (Realtime + Expo Push + Web Push) in `apps/api/src/dailyriff_api/services/notifications.py`.
- **Realtime:** Supabase Realtime for presence and DB change events.
- **Build orchestration:** `pnpm dev` via turbo boots supabase + api + web + codegen watcher in one command.

## Directory layout

```
apps/api/src/dailyriff_api/
  main.py              FastAPI app entrypoint
  auth.py              JWT middleware + CurrentUser dependency
  db.py                asyncpg + Supabase clients
  routers/             health.py, devices.py, preferences.py
  services/            notifications.py (3-channel)
  schemas/             device.py, preferences.py

apps/api/alembic/versions/
  0001_infra_baseline.py   Infra tables + RLS (user_push_subscriptions, notification_preferences)

apps/api/tests/
  conftest.py              make_test_jwt, db fixtures
  unit/                    test_auth_middleware.py, test_notification_service.py
  integration/             test_devices_endpoints.py, test_preferences_endpoints.py, test_rls_isolation.py
  contract/                test_schemathesis.py

apps/web/src/app/          layout.tsx, page.tsx
apps/web/src/lib/          env.ts
apps/web/e2e/              smoke.spec.ts (Playwright static-route smoke)

apps/mobile/src/stores/    sessionStore.ts (Zustand)
apps/mobile/src/App.tsx

packages/api-client/src/   index.ts, types.gen.ts (auto-generated — never edit manually)
```

## Development pipeline

- Ideas → `/office-hours` → `/autoplan` → `/grill-me` → `/write-a-prd` → `/prd-to-issues`
- Implementation → `ralph-once` first, then `afk-ralph`
- Quality → `/review` → `/qa` → `/ship` → `/land-and-deploy` → `/canary`

## TDD rules (enforced by Ralph, enforced by CI)

- Write the failing test before writing any implementation
- One test at a time, one implementation at a time — never write all tests first
- Tests verify behavior through public interfaces, not implementation details
- Mock ONLY at system boundaries (Supabase, external APIs, `httpx.AsyncClient`, `pywebpush.webpush`, time, randomness)
- Never mock your own modules or internal collaborators
- Test names describe WHAT the system does, not HOW
- Never commit with a failing test
- Never refactor while a test is failing

## Coverage gates (CI will block if not met)

| Layer | Gate | Scope |
|---|---|---|
| Python (FastAPI) | 85% minimum | `src/dailyriff_api/{auth,services,routers,schemas}/**` |
| Web (Next.js) | 90% minimum | `src/lib/**` |
| Mobile (Expo) | 90% minimum | `src/stores/**` |

## API contracts

- FastAPI auto-generates OpenAPI spec → `apps/api/openapi.snapshot.json`
- CI runs codegen: openapi.json → `packages/api-client/src/`
- Both `apps/mobile` and `apps/web` import from `packages/api-client`
- If the backend breaks a type the frontend uses, `tsc --noEmit` fails in CI

## CI workflow

`.github/workflows/ci.yaml` — 4 jobs:

| Job | What it does |
|---|---|
| `api` | `supabase start` → pytest (85% coverage gate) + Schemathesis contract tests |
| `codegen` | Export OpenAPI → regenerate api-client → `tsc --noEmit` in web + mobile |
| `web` | jest (90% coverage gate on `src/lib/**`) + Playwright smoke |
| `mobile-unit` | jest-expo (90% coverage gate on `src/stores/**`) |

## Key files

- `apps/api/src/dailyriff_api/main.py` — FastAPI app entrypoint
- `apps/api/src/dailyriff_api/auth.py` — JWT middleware + CurrentUser
- `apps/api/src/dailyriff_api/services/notifications.py` — 3-channel NotificationService
- `apps/api/alembic/versions/` — DB migrations (never skip, never hand-edit prod)
- `apps/api/openapi.snapshot.json` — OpenAPI snapshot (codegen source of truth)
- `packages/api-client/src/` — Auto-generated TypeScript client (never edit manually)
- `tools/check-env.ts` — Env var validator
- `supabase/config.toml` — Supabase local config
- `.github/workflows/ci.yaml` — CI pipeline
- `ralph/prompt.md` — Ralph's TDD instructions per iteration
- `ralph/review-prompt.md` — Ralph's per-iteration code review gate
- `docs/prds/stage-0-foundation.md` — Stage 0 Foundation PRD
- `docs/prds/stage-1-foundation.md` — Stage 1 Foundation PRD (MVP)
- `docs/prds/stage-1-deferred-features.md` — Stage 1 scope tracker (Q1–Q29 grill-me output)
- `docs/DESIGN.md` — Design system (typography, colors, spacing, motion, voice)

## Deploy pipeline

`.github/workflows/deploy.yaml` — 2.5-stage pipeline triggered on merge to master:

| Stage | Environment | Gate | What it does |
|---|---|---|---|
| 1 | `staging` | Auto (on merge) | Runs `alembic upgrade head` against staging Supabase |
| 2 | `production` | Manual approval | Runs `alembic upgrade head` against production Supabase |

**Routing rules:**

| Change type | Path |
|---|---|
| Frontend-only | PR preview (Vercel) → merge → Vercel prod auto-deploy |
| API logic (no schema) | PR preview → merge → Vercel prod |
| Alembic migrations | Merge → staging DB → approval → prod DB |
| Stripe/COPPA flows | Merge → staging (test keys) → approval → prod (live keys) |
| Env config changes | Staging → approval → prod |

**GitHub Environment secrets required:**
- `staging`: `STAGING_DATABASE_URL`
- `production`: `PRODUCTION_DATABASE_URL` (requires reviewer approval)

**Vercel setup (manual):**
- Connect `slubby101/DailyRiffV2` to Vercel, root directory `apps/web`, framework preset Next.js
- Per-environment vars: `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`, `NEXT_PUBLIC_SUPABASE_PROJECT_REF`, `NEXT_PUBLIC_API_URL`, `ENVIRONMENT`

**Expo EAS build profiles** (`apps/mobile/eas.json`):
- `development`: local Supabase, dev client
- `preview`: staging Supabase, internal distribution
- `production`: prod Supabase, auto-increment version

Health checks: `GET /api/health` (web) + `GET /health` (API).

## Design System

Always read `docs/DESIGN.md` before making any visual or UI decisions. All font choices (Fraunces display + Geist body + Geist Mono), colors (warm amber brand primary, 12-swatch per-studio Radix palette), spacing, radius (8px), and aesthetic direction (Editorial Warmth) are defined there. Do not deviate without explicit user approval. In QA mode, flag any code that doesn't match `docs/DESIGN.md`.
