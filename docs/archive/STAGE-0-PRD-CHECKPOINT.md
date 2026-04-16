# Stage 0 PRD — Scoping Checkpoint

> Paused mid-scoping. Resume by re-reading this file, then continuing at **Question 10** below.
> Source docs: `TOOLCHAIN (1).md`, `UNIVERSAL-PLATFORM-DECISIONS.md`, `DAILYRIFF-PLATFORM-ADDENDUM.md`.

---

## Task

Write a **Stage 0 PRD** for DailyRiffV2 that scaffolds the full monorepo foundation per the Universal Platform Decisions and DailyRiff Platform Addendum. Claude authors the PRD directly (not Ralph). Ralph will execute the PRD after it is written and sub-divided.

---

## Locked decisions (Q1–Q9)

| # | Topic | Decision |
|---|---|---|
| Q1 | Stage 0 scope | **Option C — full foundation.** Monorepo + backend + DB + auth + push + testing + observability env slots. |
| Q2 | Accounts split | **Option 2 — 0a vs 0b.** 0a = fully functional local dev (this PRD). 0b = deploy to Vercel/Railway via gstack `/ship` → `/land-and-deploy` → `/canary` (not a PRD, just run gstack when ready). |
| Q3 | Supabase | **Option A — local stack via Supabase CLI (`supabase start`).** Postgres on `localhost:54322`. JWT secret pulled from `supabase status`. No cloud Supabase project in 0a. |
| Q4 | Mobile runtime | **Option C — scaffold + headless tests only.** No simulator in 0a. Visual verification documented via `eas build --profile development --platform android` → QR → Expo Dev Client (optional, not blocking). iOS impossible on Windows. |
| Q5 | Alembic baseline | **A + D — infra tables only + RLS policies on them.** Tables: `user_push_subscriptions`, `notification_preferences`. RLS: users can only read/write their own rows. **No domain tables** (Track/Session/Studio/User deferred to feature PRDs). |
| Q6 | NotificationService | **Option B — full three-channel implementation with boundary mocks.** Realtime + Expo Push + Web Push all real. Tests mock at `httpx.AsyncClient` and `pywebpush.webpush` boundaries. VAPID keypair generated locally (`npx web-push generate-vapid-keys`). Explicit acceptance: Web Push 410-gone response deletes the subscription row. |
| Q7 | Testing frameworks | **Option B — configs + one real test per testable layer, gates active and passing.** pytest + jest-expo + jest (web) + Schemathesis + Playwright smoke. **Maestro deferred** (no simulator). Web coverage gate scoped to `apps/web/src/lib/**` only until feature code exists. |
| Q8 | Monorepo location | **Option A — scaffold in place at repo root.** `apps/`, `packages/`, `tools/`, `pnpm-workspace.yaml` added alongside existing docs. Cleanup: rename `TOOLCHAIN (1).md` → `TOOLCHAIN.md`. `Universal-pipeline-deploy_v2/` left untouched. |
| Q9 | CI workflow | **Option B — 4 jobs in `.github/workflows/ci.yaml`: `api`, `codegen`, `web`, `mobile-unit`.** No EAS build step (0b). Playwright smoke only (static routes, no DB). `api` job runs `supabase start` for integration + Schemathesis. Coverage gates active: 85 / 90 / 90. |

---

## In progress — Question 10 (auth middleware)

**Awaiting user decision.** Claude's recommendation sent but not yet confirmed.

Recommendation:
- **Algorithm**: HS256 + `SUPABASE_JWT_SECRET` (matches universal doc).
- **`CurrentUser` model**: `id: UUID` (from `sub`), `email: str | None`, `role: str | None` (from `app_metadata.role`). Minimal + extensible.
- **Test users**: both strategies — (a) canonical seeded user via `supabase/seed.sql` (id `00000000-0000-0000-0000-000000000001`, email `test@dailyriff.local`), and (b) `make_test_jwt(user_id, role="user")` fixture helper. Seeded user used by RLS integration tests; helper used by fast middleware unit tests.
- **Error behavior**: 401 on missing/invalid/expired token. No 403 in Stage 0 (no business-logic ownership checks yet).
- **Protected endpoints in Stage 0**: `POST /devices/register`, `GET /devices`, `PATCH /notification-preferences`. `GET /health` is public.
- **Explicit acceptance test (critical)**: `test_rls_prevents_reading_other_users_push_subscriptions` — seeds 2 users, authenticates as A, tries to read B's row via Supabase client (bypassing FastAPI), asserts 0 rows. This is the only test that verifies the RLS policy actually does its job. **Must be in Stage 0 — not deferred.**

---

## Still-open questions (after Q10)

Questions I had queued but hadn't reached yet. Order may shift based on user priorities.

1. **Dev orchestration** — should there be a single `pnpm dev` / `just dev` / `make dev` command that starts `supabase start` + `uvicorn` + `pnpm --filter web dev` + codegen watcher together? Or keep them as separate terminals? Recommend: one top-level command via `turbo` or a root `dev` script.
2. **Env var management** — `.env.example` files per app, which vars, how secrets get shared. Stage 0 needs: `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE`, `SUPABASE_JWT_SECRET`, `DATABASE_URL` (pooler :6543), `VAPID_PRIVATE_KEY`, `VAPID_PUBLIC_KEY`, `VAPID_EMAIL`, `REDIS_URL`. Empty slots for `LOGFIRE_TOKEN`, `SENTRY_DSN_*`, `EXPO_PROJECT_ID`.
3. **CLAUDE.md expansion** — the project CLAUDE.md is currently minimal (just gstack note). Stage 0 should expand it to match the template in `TOOLCHAIN (1).md` lines 384–429 (architecture, TDD rules, coverage gates, key files). Open question: replace wholesale, or append?
4. **PRD delivery format** — does the PRD live as a local markdown file (`docs/prds/stage-0-foundation.md`), as a GitHub issue filed via `gh issue create`, or both? If GitHub issue, which repo — `slubby101/DailyRiffV2` (confirmed as remote in memory). Recommend: markdown file in repo AND mirrored as GitHub issue so `/prd-to-issues` can slice it.
5. **Sub-issue breakdown strategy** — Stage 0 is large; how does it slice into Ralph-ready vertical slices? Candidate slices: (a) pnpm workspace + tsconfig skeleton, (b) Supabase local stack + Alembic baseline + RLS, (c) FastAPI health + auth middleware, (d) NotificationService + device endpoints, (e) codegen pipeline, (f) `apps/web` scaffold + smoke test, (g) `apps/mobile` scaffold + one store test, (h) CI workflow, (i) CLAUDE.md expansion. Dependencies: a→b→c→d→e→{f,g}; h can run parallel to e+; i last.
6. **Lint / format / pre-commit** — ruff + prettier + eslint configs. Husky or lefthook pre-commit hooks? The universal doc doesn't specify. Recommend: ruff (Python), prettier + eslint-config-next (web), eslint-config-expo (mobile), no pre-commit hook in Stage 0 (lint runs in CI, add hook later if churn demands).
7. **`superpowers` tool** — user said "ignore superpowers, don't need it." Resolved: author PRD directly as markdown.

---

## Infrastructure already verified (prior review)

✅ Installed: Claude Code, gstack (all skills), Matt Pocock skills (grill-me, write-a-prd, prd-to-issues), Ralph + ralph/ scripts, agent-browser, Docker Desktop, GitHub CLI (authed as `slubby101`), Node 24 / npm 11.

⚠️ Missing (not blockers for PRD authoring, but needed before Ralph executes):
- `eas-cli` (`npm i -g eas-cli`) — optional, only for mobile visual verification
- `pnpm` (`npm i -g pnpm`) — Stage 0 prerequisite
- `supabase` CLI (`scoop install supabase` or `npm i -g supabase`) — Stage 0 prerequisite
- `ruff`, `@hey-api/openapi-ts`, `playwright` — will be added as dev deps by the PRD, not pre-installed
- `.github/workflows/` directory does not yet exist

---

## Resume instructions for next session

1. Re-read this file first.
2. Re-read `UNIVERSAL-PLATFORM-DECISIONS.md` + `DAILYRIFF-PLATFORM-ADDENDUM.md` if context was lost.
3. Ask the user to confirm or modify **Question 10 (auth middleware)**.
4. Continue one-at-a-time through the still-open questions list.
5. After all questions resolved, write the Stage 0 PRD as `docs/prds/stage-0-foundation.md` (pending Q4 confirmation on format).
6. Do NOT hand off to Ralph yet — writing the PRD is the deliverable, not executing it.
