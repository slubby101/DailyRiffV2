# Stage 0 — Foundation PRD

> **Status:** Ready for `/prd-to-issues` slicing and Ralph execution.
> **Author:** Claude (authored directly, not via Ralph).
> **Scope:** Stage 0a — fully functional local dev foundation. Stage 0b (deploy to Vercel/Railway) is a separate gstack workflow: `/ship` → `/land-and-deploy` → `/canary`.
> **Source decisions:** `UNIVERSAL-PLATFORM-DECISIONS.md`, `DAILYRIFF-PLATFORM-ADDENDUM.md`, `TOOLCHAIN.md`, `STAGE-0-PRD-CHECKPOINT.md`.

---

## 1. Goal

Scaffold the complete DailyRiffV2 monorepo foundation — backend, database, auth, notifications, web scaffold, mobile scaffold, codegen pipeline, testing, and CI — such that after Stage 0 lands:

- `pnpm dev` at repo root boots the entire local stack with a single command.
- All testing gates (pytest 85% / jest-expo 90% / jest-web 90% / Schemathesis / Playwright smoke) pass in CI.
- The codebase is ready for the first feature PRD (Track/Session/Studio/User domain) to drop in without touching infrastructure.

**Non-goals for Stage 0:**

- No domain tables (no `tracks`, `sessions`, `studios`, `users` table beyond what Supabase Auth provides).
- No deployed environments (that's Stage 0b).
- No mobile simulator testing (Windows host, no iOS; Android deferred to visual verification via EAS dev client).
- No Maestro E2E mobile tests.
- No Sentry/Logfire live wiring — only empty env slots reserved.

---

## 2. Locked Decisions

| # | Topic | Decision |
|---|---|---|
| Q1 | Stage 0 scope | Option C — full foundation (monorepo + backend + DB + auth + push + testing + observability slots). |
| Q2 | Accounts split | Option 2 — 0a (this PRD) vs 0b (gstack deploy pipeline). |
| Q3 | Supabase | Local stack via Supabase CLI (`supabase start`). Postgres on `localhost:54322`. JWT secret from `supabase status`. No cloud project in 0a. |
| Q4 | Mobile runtime | Scaffold + headless tests only. No simulator. Visual verification optional via `eas build --profile development --platform android`. |
| Q5 | Alembic baseline | Infra tables only + RLS. Tables: `user_push_subscriptions`, `notification_preferences`. RLS: users read/write own rows only. No domain tables. |
| Q6 | NotificationService | Full 3-channel (Realtime + Expo Push + Web Push) with boundary mocks at `httpx.AsyncClient` and `pywebpush.webpush`. VAPID keypair generated locally. Web Push 410-gone → delete subscription row. |
| Q7 | Testing | Configs + one real test per layer, gates active. pytest + jest-expo + jest (web) + Schemathesis + Playwright smoke. Maestro deferred. Web coverage scoped to `apps/web/src/lib/**`. |
| Q8 | Monorepo location | Scaffold in place at repo root. Rename `TOOLCHAIN (1).md` → `TOOLCHAIN.md`. `Universal-pipeline-deploy_v2/` left untouched. |
| Q9 | CI workflow | 4 jobs in `.github/workflows/ci.yaml`: `api`, `codegen`, `web`, `mobile-unit`. No EAS. Playwright smoke is static-route only. `api` job runs `supabase start`. Coverage gates: 85 / 90 / 90. |
| Q10 | Auth middleware | HS256 + `SUPABASE_JWT_SECRET` (matches Supabase local CLI default). Algorithm list accepts `["HS256"]` in Stage 0; Stage 0b will widen to `["HS256", "ES256"]` when moving to cloud (asymmetric keys). `CurrentUser = {id: UUID, email: str\|None, role: str\|None}`. Both test strategies (seeded canonical user + `make_test_jwt()` helper). 401 on missing/invalid/expired. No 403 in Stage 0. Protected: `POST /devices/register`, `GET /devices`, `PATCH /notification-preferences`. `GET /health` public. Must include RLS integration test. |
| Q11 | Dev orchestration | Single `pnpm dev` via turbo. One command boots supabase + api + web + codegen watcher. |
| Q12 | Env vars | Root `.env.example` (shared) + per-app `.env.example` for app-specific vars. `tools/check-env.ts` validates at `pnpm dev` startup. |
| Q13 | CLAUDE.md | Replace wholesale with full template, preserve gstack note at top. |
| Q14 | PRD delivery | Both — markdown file in repo + mirrored GitHub issue in `slubby101/DailyRiffV2`. |
| Q15 | Sub-issue slicing | 9 slices (a–i) with declared dependency graph (see §9). |
| Q16 | Lint/format | ruff (Python), prettier + eslint-config-next (web), prettier + eslint-config-expo (mobile). No pre-commit hook — CI is the gate. |

---

## 3. Final File Tree (Stage 0 end state)

```
DailyRiffV2/
├── .github/
│   └── workflows/
│       └── ci.yaml
├── .env.example                      # shared vars
├── .gitignore
├── .prettierrc
├── CLAUDE.md                         # expanded (Q13)
├── README.md
├── TOOLCHAIN.md                      # renamed from TOOLCHAIN (1).md
├── UNIVERSAL-PLATFORM-DECISIONS.md
├── DAILYRIFF-PLATFORM-ADDENDUM.md
├── STAGE-0-PRD-CHECKPOINT.md         # retained as history
├── package.json                      # root, pnpm workspace + turbo
├── pnpm-workspace.yaml
├── turbo.json
├── tsconfig.base.json
├── Universal-pipeline-deploy_v2/     # untouched
├── ralph/                            # untouched
├── docs/
│   └── prds/
│       └── stage-0-foundation.md     # this file
├── supabase/
│   ├── config.toml
│   └── seed.sql                      # reserved for domain data; users seeded via Admin API in conftest
├── tools/
│   ├── check-env.ts                  # env var validator
│   └── generate-vapid.md             # one-liner docs
├── packages/
│   └── api-client/                   # generated by @hey-api/openapi-ts
│       ├── package.json
│       ├── tsconfig.json
│       └── src/                      # generated — gitignored except index.ts stub
├── apps/
│   ├── api/
│   │   ├── pyproject.toml            # uv-managed
│   │   ├── .env.example
│   │   ├── alembic.ini
│   │   ├── alembic/
│   │   │   ├── env.py
│   │   │   └── versions/
│   │   │       └── 0001_infra_baseline.py
│   │   ├── src/
│   │   │   └── dailyriff_api/
│   │   │       ├── __init__.py
│   │   │       ├── main.py           # FastAPI app
│   │   │       ├── auth.py           # JWT middleware + CurrentUser
│   │   │       ├── db.py             # asyncpg + Supabase clients
│   │   │       ├── routers/
│   │   │       │   ├── health.py
│   │   │       │   ├── devices.py
│   │   │       │   └── preferences.py
│   │   │       ├── services/
│   │   │       │   └── notifications.py   # 3-channel NotificationService
│   │   │       └── schemas/
│   │   │           ├── device.py
│   │   │           └── preferences.py
│   │   └── tests/
│   │       ├── conftest.py           # make_test_jwt, db fixtures
│   │       ├── unit/
│   │       │   ├── test_auth_middleware.py
│   │       │   └── test_notification_service.py
│   │       ├── integration/
│   │       │   ├── test_devices_endpoints.py
│   │       │   ├── test_preferences_endpoints.py
│   │       │   └── test_rls_isolation.py   # CRITICAL — Q10 acceptance test
│   │       └── contract/
│   │           └── test_schemathesis.py
│   ├── web/
│   │   ├── package.json
│   │   ├── .env.example
│   │   ├── next.config.ts
│   │   ├── tsconfig.json
│   │   ├── jest.config.ts
│   │   ├── playwright.config.ts
│   │   ├── src/
│   │   │   ├── app/
│   │   │   │   ├── layout.tsx
│   │   │   │   └── page.tsx          # static hello
│   │   │   └── lib/
│   │   │       └── env.ts            # one real test target
│   │   ├── __tests__/
│   │   │   └── lib/
│   │   │       └── env.test.ts
│   │   └── e2e/
│   │       └── smoke.spec.ts         # Playwright static-route smoke
│   └── mobile/
│       ├── package.json
│       ├── .env.example
│       ├── app.config.ts
│       ├── tsconfig.json
│       ├── jest.config.js            # jest-expo preset
│       ├── src/
│       │   ├── App.tsx
│       │   └── stores/
│       │       └── sessionStore.ts   # one Zustand store
│       └── __tests__/
│           └── stores/
│               └── sessionStore.test.ts
```

---

## 4. Environment Variables

### Shared (`/.env.example`)

```bash
# Supabase (from `supabase status` after `supabase start`)
SUPABASE_URL=http://localhost:54321
SUPABASE_ANON_KEY=
SUPABASE_SERVICE_ROLE=
SUPABASE_JWT_SECRET=

# Postgres (Supabase local Postgres — NOT the cloud pooler port 6543)
DATABASE_URL=postgresql://postgres:postgres@localhost:54322/postgres
# Build-time git SHA injected by CI / `pnpm dev` wrapper; falls back to "dev"
GIT_SHA=dev

# Web Push (generate: `npx web-push generate-vapid-keys`)
VAPID_PUBLIC_KEY=
VAPID_PRIVATE_KEY=
VAPID_EMAIL=mailto:dev@dailyriff.local

# Redis (optional in 0a — used by NotificationService rate limits later)
REDIS_URL=redis://localhost:6379

# --- Empty slots reserved for future stages ---
# LOGFIRE_TOKEN=
# SENTRY_DSN_API=
# SENTRY_DSN_WEB=
# SENTRY_DSN_MOBILE=
# EXPO_PROJECT_ID=
```

### Per-app overrides

- `apps/api/.env.example` — inherits shared; no app-specific additions in Stage 0.
- `apps/web/.env.example` — `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`, `NEXT_PUBLIC_VAPID_PUBLIC_KEY`.
- `apps/mobile/.env.example` — `EXPO_PUBLIC_SUPABASE_URL`, `EXPO_PUBLIC_SUPABASE_ANON_KEY`.

### Validator

`tools/check-env.ts` runs before `turbo dev`, fails fast listing missing required vars.

---

## 5. Database Schema (Alembic `0001_infra_baseline`)

Two tables, both with RLS enabled.

### `user_push_subscriptions`

| column | type | notes |
|---|---|---|
| `id` | `uuid` PK default `gen_random_uuid()` | |
| `user_id` | `uuid` NOT NULL | references `auth.users(id)` ON DELETE CASCADE |
| `channel` | `text` NOT NULL | CHECK in (`'expo'`, `'webpush'`) |
| `token` | `text` NOT NULL | Expo push token or webpush endpoint |
| `keys` | `jsonb` NULL | `{p256dh, auth}` for webpush; null for expo |
| `user_agent` | `text` NULL | |
| `created_at` | `timestamptz` default `now()` | |
| `last_used_at` | `timestamptz` NULL | |

Unique index on `(user_id, channel, token)`.

**RLS policies:**
- `select_own`: `user_id = auth.uid()`
- `insert_own`: `user_id = auth.uid()`
- `update_own`: `user_id = auth.uid()`
- `delete_own`: `user_id = auth.uid()`

### `notification_preferences`

| column | type | notes |
|---|---|---|
| `user_id` | `uuid` PK | references `auth.users(id)` ON DELETE CASCADE |
| `realtime_enabled` | `boolean` default `true` | |
| `expo_push_enabled` | `boolean` default `true` | |
| `web_push_enabled` | `boolean` default `true` | |
| `quiet_hours_start` | `time` NULL | |
| `quiet_hours_end` | `time` NULL | |
| `updated_at` | `timestamptz` default `now()` | |

Same 4 RLS policies keyed on `user_id = auth.uid()`.

### `realtime_outbox`

Included in the baseline unconditionally so that slice `d` never needs to amend migration `0001`. Used as a fallback when the Supabase local Realtime REST broadcast endpoint is unavailable; a future slice may attach a `NOTIFY` trigger.

| column | type | notes |
|---|---|---|
| `id` | `bigserial` PK | |
| `user_id` | `uuid` NOT NULL | references `auth.users(id)` ON DELETE CASCADE |
| `payload` | `jsonb` NOT NULL | |
| `created_at` | `timestamptz` default `now()` | |
| `delivered_at` | `timestamptz` NULL | |

RLS enabled, `select_own` policy on `user_id = auth.uid()`. Writes are service-role only (no insert/update/delete policies for authenticated users).

### Seed data

**Canonical test user:** `id=00000000-0000-0000-0000-000000000001`, `email=test@dailyriff.local`, `password=test-password-do-not-use-in-prod`.

**Seeding approach (not raw SQL into `auth.users`):** `supabase/seed.sql` is reserved for domain data only. User creation happens in `apps/api/tests/conftest.py` via a session-scoped fixture that calls the Supabase Admin API (`POST /auth/v1/admin/users` with service-role key) at the start of the test session. **The Admin API call must pass `email_confirm: true`** — otherwise `sign_in_with_password` fails with "email not confirmed" and the RLS isolation test cannot authenticate. This guarantees `auth.users`, `auth.identities`, and password hashing are all populated correctly. A second fixture seeds user B (`...-0002`) for the RLS isolation test (same `email_confirm: true` requirement).

**Notification preferences row:** created lazily via upsert semantics on `PATCH /notification-preferences` and `GET /notification-preferences` (no DB trigger needed). GET on a user with no row returns the default values without writing; PATCH upserts.

**FK to `auth.users`:** Alembic migration declares the FK but does NOT own the `auth` schema. `alembic/env.py` sets `include_schemas=False` and an `include_object` filter that rejects anything in schema `auth` to prevent autogenerate from touching Supabase-owned tables.

---

## 6. API Surface (Stage 0)

| Method | Path | Auth | Purpose |
|---|---|---|---|
| GET | `/health` | public | `{status: "ok", version, git_sha}` |
| POST | `/devices/register` | required | Register push subscription. Body: `{channel, token, keys?, user_agent?}`. |
| GET | `/devices` | required | List current user's subscriptions. |
| DELETE | `/devices/{id}` | required | Remove subscription (ownership enforced by RLS). |
| PATCH | `/notification-preferences` | required | Partial update. |
| GET | `/notification-preferences` | required | Read current. |

OpenAPI spec auto-served at `/openapi.json`. Schemathesis consumes it in CI.

---

## 7. NotificationService

`apps/api/src/dailyriff_api/services/notifications.py`

Single class `NotificationService` with one public method:

```python
async def send(self, user_id: UUID, payload: NotificationPayload) -> SendResult: ...
```

Internally fans out to three channels in parallel:

1. **Realtime** — broadcast via Supabase Realtime. **Primary path:** `httpx.AsyncClient` POST to `{SUPABASE_URL}/realtime/v1/api/broadcast` with the service-role key. On any non-2xx response or connection failure, falls back to inserting a row into `realtime_outbox` (which already exists in the baseline from slice `b`, so no schema amendment is ever required). Both paths are covered by unit tests with the `httpx.AsyncClient` boundary mocked.
2. **Expo Push** — `POST https://exp.host/--/api/v2/push/send` via `httpx.AsyncClient`.
3. **Web Push** — `pywebpush.webpush()` per subscription.

**Preference gating:** reads `notification_preferences` row before each channel; skips channel if `*_enabled=false`.

**410-gone handling (Web Push):** on `WebPushException` with status 410, deletes the offending row from `user_push_subscriptions`. Tested explicitly.

**Tests (unit):**
- `test_send_all_channels_enabled` — all 3 called.
- `test_realtime_disabled_skips_realtime` — preferences respected.
- `test_expo_http_error_does_not_block_webpush` — isolation.
- `test_webpush_410_deletes_subscription` — **mandatory**.

All external calls mocked at `httpx.AsyncClient` and `pywebpush.webpush` boundaries. No live HTTP in unit tests.

---

## 8. Testing Gates

| Layer | Tool | Gate | Scope |
|---|---|---|---|
| API unit + integration | pytest + pytest-asyncio + coverage | **85%** | `apps/api/src/dailyriff_api/{auth,services,routers,schemas}/**` (excludes `main.py` bootstrap and `db.py` client factories) |
| API contract | Schemathesis | all strategies pass | `/openapi.json` |
| Web | jest | **90%** | `apps/web/src/lib/**` only (until feature code exists) |
| Web E2E smoke | Playwright | 1 test passes | `apps/web/e2e/smoke.spec.ts` — hits `/` (static), asserts title |
| Mobile unit | jest-expo | **90%** | `apps/mobile/src/stores/**` only (one store exists) |
| Mobile E2E | Maestro | **deferred** | — |

**Mandatory tests that must exist in Stage 0:**

1. `apps/api/tests/integration/test_rls_isolation.py::test_rls_prevents_reading_other_users_push_subscriptions` — Q10 acceptance. Seeds users A and B, authenticates Supabase client as A (bypassing FastAPI entirely), selects from `user_push_subscriptions` filtered on B's `user_id`, asserts 0 rows.
2. `apps/api/tests/unit/test_notification_service.py::test_webpush_410_deletes_subscription` — Q6 acceptance.
3. `apps/api/tests/unit/test_auth_middleware.py::test_401_on_missing_token`, `::test_401_on_expired_token`, `::test_200_on_valid_token`.
4. `apps/api/tests/integration/test_devices_endpoints.py::test_user_cannot_delete_other_users_subscription` — authenticates as user A, `DELETE /devices/{id}` where `id` belongs to user B, asserts 404 (RLS hides the row, so it looks like not-found rather than 403). Belt-and-suspenders alongside the bare-RLS test.
5. `apps/web/__tests__/lib/env.test.ts` — one real test to prove jest config works.
6. `apps/mobile/__tests__/stores/sessionStore.test.ts` — one real test to prove jest-expo config works.

The RLS test (#1) uses the Supabase Python client authenticated via `supabase.auth.sign_in_with_password(email="test@dailyriff.local", password="test-password-do-not-use-in-prod")` against the seeded canonical user. This is why the conftest fixture must create users with real passwords via the Admin API with `email_confirm: true` (see §5 Seed data).

---

## 9. Vertical Slices (for `/prd-to-issues` + Ralph)

Nine slices, dependency graph declared. Ralph picks them up in topo order.

| id | Title | Depends on | Deliverable |
|---|---|---|---|
| **a** | Monorepo skeleton + env validator | — | `package.json` (with `"engines": {"node": ">=22 <23"}`, `"packageManager": "pnpm@9"`), `.nvmrc` (`22`), `pnpm-workspace.yaml`, `turbo.json`, `tsconfig.base.json` (`strict: true`, `moduleResolution: "bundler"`, `target: "ES2022"`, `noUncheckedIndexedAccess: true`), `.prettierrc`, `tools/check-env.ts` (env validator, runs at `pnpm dev` start), rename `TOOLCHAIN (1).md` → `TOOLCHAIN.md`, root `.gitignore` updates. `pnpm install` succeeds. |
| **b** | Supabase + Alembic baseline + RLS | a | `supabase/config.toml`, `supabase start` works, `apps/api/alembic/versions/0001_infra_baseline.py` creates `user_push_subscriptions`, `notification_preferences`, **and `realtime_outbox`** (all with RLS). `alembic upgrade head` succeeds. `realtime_outbox` is included unconditionally to eliminate the risk of amending the baseline in slice `d` if the Supabase local Realtime REST endpoint turns out to be unavailable. |
| **c** | FastAPI + auth middleware | b | `apps/api` uv project, `main.py`, `auth.py` with `CurrentUser` + `make_test_jwt` fixture, `GET /health` public, protected endpoint stubs return 401 without token. Auth unit tests pass. |
| **d** | NotificationService + device & preferences endpoints + OpenAPI snapshot | c | `services/notifications.py`, `routers/devices.py` (incl. `DELETE /devices/{id}`), `routers/preferences.py` (upsert semantics on GET/PATCH), **all response schemas set `model_config = ConfigDict(extra="forbid")`** (required for Schemathesis `response_schema_conformance`), all unit + integration tests incl. RLS isolation + 410-gone + **cross-user DELETE denial**. `pnpm --filter api regenerate-openapi` script produces `apps/api/openapi.snapshot.json` (committed). Realtime broadcast: attempt `POST {SUPABASE_URL}/realtime/v1/api/broadcast`; on any non-2xx or connection failure, write to `realtime_outbox` (already in baseline from slice `b`). pytest gate 85% met. |
| **e** | Codegen pipeline | d | `packages/api-client` with `@hey-api/openapi-ts` config consuming committed `apps/api/openapi.snapshot.json` (not a live URL, for deterministic CI). `pnpm --filter api-client generate` produces typed client. Dev-time watcher mode: `openapi-ts --watch http://localhost:8000/openapi.json` wired into `turbo dev`. |
| **f** | `apps/web` Next.js scaffold + Playwright smoke | e | `apps/web` Next 15 app router, static `/`, jest config + one lib test, Playwright config with `webServer: { command: 'next start', port: 3000, reuseExistingServer: !process.env.CI }` to auto-boot the app before smoke test. Gates met. |
| **g** | `apps/mobile` Expo scaffold + store test | e | `apps/mobile` Expo SDK 52+, `app.config.ts`, one Zustand store + jest-expo test. Gate met. |
| **h** | CI workflow | e | `.github/workflows/ci.yaml` with 4 jobs: `api` (runs `supabase start`, pytest, Schemathesis, **and the snapshot-freshness check — diffs `dump_openapi` output against committed `openapi.snapshot.json`**), `codegen` (regenerates TS client from committed snapshot, fails on `git diff` — node-only, no Python), `web` (jest + Playwright static smoke), `mobile-unit` (jest-expo). All jobs green on a clean branch. |
| **i** | `CLAUDE.md` expansion | h, f, g | Replace `CLAUDE.md` wholesale per `TOOLCHAIN.md` template, preserve the gstack header. Pure docs slice — no code. |

**Critical path:** a → b → c → d → e → h. **Parallel after e:** {f, g} run alongside h. **Last:** i (after h, f, g).

---

## 10. `pnpm dev` Behavior

Root `package.json` script: `"dev": "tsx tools/check-env.ts && turbo run dev"`.

`turbo.json` `dev` task runs (persistent, parallel):

- `supabase:start` — `supabase start` (idempotent; skipped if already running)
- `api#dev` — `uv run uvicorn dailyriff_api.main:app --reload --port 8000`
- `api-client#generate:watch` — `openapi-ts --watch` pointed at `http://localhost:8000/openapi.json`
- `web#dev` — `next dev --port 3000`

**Mobile is excluded from `pnpm dev`.** `expo start` owns the terminal for QR display and hotkeys, which breaks when run under turbo `persistent`. Mobile developers run `pnpm --filter mobile dev` in a dedicated terminal. This is a deliberate carve-out from Q11's "single command."

Exit via Ctrl+C cleanly stops all four turbo tasks.

---

## 11. CI (`.github/workflows/ci.yaml`)

Trigger: `push` + `pull_request` on all branches.

### Job: `api`

- ubuntu-latest
- setup-python 3.12
- install `uv`, install `supabase` CLI
- `supabase start`
- `cd apps/api && uv sync`
- `uv run alembic upgrade head`
- `uv run pytest --cov=src/dailyriff_api --cov-fail-under=85`
- `uv run schemathesis run http://localhost:8000/openapi.json --checks all`
- **Snapshot freshness check:** `uv run python -m dailyriff_api.scripts.dump_openapi > /tmp/fresh.json && diff /tmp/fresh.json apps/api/openapi.snapshot.json`. Fails if the committed snapshot is stale. This check lives in the `api` job (not `codegen`) because it needs the Python toolchain.

### Job: `codegen`

- ubuntu-latest, node 22, pnpm. **Node-only — no Python, no cross-job dependency.**
- Reads committed `apps/api/openapi.snapshot.json` (produced by `pnpm --filter api regenerate-openapi` during slice `d` and updated whenever endpoints change).
- `pnpm --filter api-client generate` regenerates TypeScript client from the snapshot.
- Fails if `git diff --exit-code packages/api-client/src` is non-empty (developer forgot to commit regenerated output).
- Snapshot-freshness is verified by the `api` job above, so `codegen` trusts the committed snapshot.

### Job: `web`

- ubuntu-latest, node 22, pnpm
- `pnpm install --frozen-lockfile`
- `pnpm --filter web lint`
- `pnpm --filter web test -- --coverage` (gate 90%, scoped to `src/lib/**`)
- `pnpm --filter web build`
- `pnpm --filter web exec playwright install --with-deps chromium`
- `pnpm --filter web exec playwright test` — Playwright config's `webServer` auto-starts `next start` before the test run; no manual server boot needed.

### Job: `mobile-unit`

- ubuntu-latest, node 22, pnpm
- `pnpm install --frozen-lockfile`
- `pnpm --filter mobile lint`
- `pnpm --filter mobile test -- --coverage` (gate 90%)

No EAS build. No Maestro. No deploy steps.

---

## 12. Acceptance Criteria (Stage 0 DONE when all true)

- [ ] `pnpm install` at repo root succeeds on a clean clone.
- [ ] `supabase start` succeeds; `alembic upgrade head` creates both tables with RLS enabled.
- [ ] `pnpm dev` boots supabase + api + web + codegen watcher with one command. (Mobile is intentionally excluded — see §10.)
- [ ] `curl localhost:8000/health` returns 200 with JSON body.
- [ ] `curl localhost:8000/devices` without token returns 401.
- [ ] `curl -H "Authorization: Bearer <make_test_jwt>" localhost:8000/devices` returns 200 with `[]`.
- [ ] `pnpm --filter web build` succeeds; `localhost:3000` serves static hello page.
- [ ] `pnpm --filter mobile test` passes with ≥90% coverage.
- [ ] `uv run pytest` passes with ≥85% coverage, including all mandatory tests listed in §8.
- [ ] `uv run schemathesis run http://localhost:8000/openapi.json --checks all` passes.
- [ ] `pnpm --filter web exec playwright test` passes the static smoke.
- [ ] `packages/api-client` is generated and importable from `apps/web` and `apps/mobile`.
- [ ] `.github/workflows/ci.yaml` runs all 4 jobs green on a clean PR.
- [ ] `CLAUDE.md` contains the full expanded template (architecture, TDD rules, coverage gates, key files) with the gstack header preserved.
- [ ] `tools/check-env.ts` validates env vars at `pnpm dev` start, fails clearly on missing required vars.
- [ ] `TOOLCHAIN (1).md` renamed to `TOOLCHAIN.md`.

---

## 13. Out of Scope (explicitly)

- Any domain table (`tracks`, `sessions`, `studios`, custom `users`).
- Any deployed environment (staging/prod).
- Sentry, Logfire, PostHog live wiring (env slots only).
- Mobile simulator / Maestro E2E.
- EAS build step in CI.
- Pre-commit hooks (husky/lefthook).
- Cloud Supabase project.
- Auth UI (login screens).
- Background job runner (Celery/Temporal/etc.).
- Rate limiting middleware.

**Seed-user password hygiene:** the canonical test password (`test-password-do-not-use-in-prod`) is checked into this PRD because it exists only inside the ephemeral `supabase start` Postgres instance on developer machines and CI runners. It must never appear in any deployed environment (Stage 0b onward), and the conftest fixture must refuse to run if `SUPABASE_URL` does not point at `localhost`.

---

## 14. Open Risks

1. **Supabase CLI on Windows** — CI runs on ubuntu-latest so unaffected, but local dev requires scoop or npm global. `tools/check-env.ts` can surface this as a hint.
2. **Codegen drift** — committing `openapi.snapshot.json` means developers must run `pnpm --filter api regenerate-openapi` after editing endpoints. The `api` job enforces freshness by diffing a fresh dump against the committed snapshot; the `codegen` job then diffs regenerated TS output against committed. Two-stage check catches "forgot to regenerate the snapshot" and "forgot to commit the TS client" as separate failures with clear error messages.
3. **Playwright on static-only** — smoke test can't exercise auth. That's fine for Stage 0; first feature PRD will expand Playwright to hit a running API + Supabase.
4. **Web Push 410 test** — requires carefully mocked `pywebpush.WebPushException(response=Response(status_code=410))`. Documented in the test file.
5. **HS256 lock-in for Stage 0b migration** — Supabase cloud uses ES256/asymmetric keys (2024+). Stage 0b must widen the JWT algorithm list and swap the verification key source (JWKS URL instead of shared secret). Tracked as a Stage 0b task, not a Stage 0 blocker.
6. **Realtime broadcast endpoint assumption** — unverified against local `supabase start`, but de-risked: `realtime_outbox` is in the baseline from slice `b`, so `NotificationService` falls back to the outbox at runtime with no schema amendment. Worst-case behavior is "events go to outbox instead of realtime," which is still observable by tests.
7. **Schemathesis `--checks all` strictness** — `response_schema_conformance` will fail if any response model accepts extra fields. **All response schemas in Stage 0 must set `model_config = ConfigDict(extra="forbid")`** — this is an explicit acceptance criterion for slice `d`, not just a risk note.
8. **`git_sha` in `/health`** — injected via `GIT_SHA` env var. CI sets `GIT_SHA=${{ github.sha }}`; local dev defaults to `"dev"`. No `git rev-parse` subprocess at startup.

---

## 15. Handoff

After this PRD lands as a markdown file and GitHub issue:

1. Run `/prd-to-issues` against the issue to produce 9 sub-issues matching §9.
2. Ralph picks up sub-issues in topo order: a → b → c → d, then parallel {e, h}, then {f, g}, then i.
3. Each slice has its own PR reviewed via `/review` before merge.
4. After slice `i` merges, run `/ship` → Stage 0 is complete, and Stage 0b (deploy) can begin.
