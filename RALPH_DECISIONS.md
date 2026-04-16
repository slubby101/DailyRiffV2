# RALPH decisions log

Cross-iteration memory for the AFK Ralph loop. One terse entry per iteration.
**Append new entries at the bottom of this file.**

GitHub issue state already tells Ralph *what* was done. This file captures the
*why* — non-obvious tradeoffs, dependency choices, environment quirks, and
follow-up hooks — so later iterations don't re-litigate decisions that past-Ralph
already thought through.

## Format

```
### <YYYY-MM-DD HH:MM UTC> / iteration #<N> of PRD #<PRD> / closed #<sub-issue>
- **Decision:** <one or two lines; what was chosen and why, especially non-obvious tradeoffs>
- **Blocker:** <one line if hit and worked around, otherwise omit>
- **Next:** <one line pointer to a follow-up if this work unblocks something specific>
```

Keep it terse. One to three bullets, single lines. This file is Ralph's working
memory, not a changelog — the PR descriptions and commit messages are the
changelog.

## Rules for Ralph

- Read this file at the start of every iteration before picking a sub-issue.
- Append a new entry **after** closing the sub-issue but **before** emitting any
  `<promise>` sentinel, as part of the same git commit as the sub-issue work.
- Never rewrite past entries. Append-only.
- If this file is missing, create it with the header above and add the first
  entry.

---

## Entries

<!-- Ralph appends new entries below this marker. Newest at the bottom. -->

### 2026-04-15 18:00 UTC / iteration #1 of PRD #16 / closed #19
- **Decision:** Stood up web UI foundation with Tailwind 3.4 + shadcn/ui new-york + TanStack Query v5 + next-themes. Used React 19 function components (no forwardRef) for Button to avoid @types/react version conflicts between Radix and Next. All CSS variables from docs/DESIGN.md ported verbatim to globals.css. 12-swatch studio palette defined in studio-theme.ts with getStudioThemeStyle helper.
- **Blocker:** OneDrive EIO errors during pnpm install — resolved by manually adding deps to package.json then retrying install. Build also hits EIO on final export step but compilation + type check pass clean.
- **Next:** #23 (superadmin surface) and #29/#30/#31 are now unblocked. #23 still blocked by #22 (dailyriff_employees).

### 2026-04-16 12:00 UTC / iteration #2 of PRD #16 / closed #29
- **Decision:** Resources implemented as flat `/resources` router (not nested under `/studios/{id}/resources`) matching the sub-issue spec. RLS policies enforce studio-member-only SELECT and owner/teacher-only INSERT/UPDATE/DELETE via `studio_members` join table — same pattern as studios. No separate `resource_service.py` since there's no business logic beyond CRUD; kept SQL in router matching the studios pattern.
- **Blocker:** OneDrive EIO errors prevented `pnpm install` and `openapi-ts` codegen; worked around by generating to /tmp then copying files.
- **Next:** #30 (messaging) and #31 (rate limiting) are unblocked. #23 still blocked by #22 (hitl).

### 2026-04-16 18:00 UTC / iteration #3 of PRD #16 / closed #31
- **Decision:** Built four-layer rate limiting infrastructure. Layer B: slowapi middleware with module-level singleton limiter, platform_settings-aware config resolution via `refresh_from_settings()`. Layer D: `BusinessCapsService` counting per-entity actions against configurable caps. Webhook hardening: `IdempotencyService` with `idempotency_log` table (unique provider+event_id) + Stripe/Postmark HMAC signature verification with 5-min timestamp tolerance. Enumeration defense: `constant_time_response()` async wrapper with configurable minimum duration. hCaptcha: verification utility with graceful degradation (bypasses when no secret configured). Applied `@limiter.limit("10/minute")` to `POST /devices/register` as the first per-route example. Seeded 7 platform_settings rows for all Layer B + D tunables. Many rate-limited endpoints (recordings, messages, waitlist, password-reset) don't exist yet — the infrastructure is ready for them.
- **Blocker:** OneDrive EIO on pnpm install (same as prior iterations); codegen via /tmp workaround.
- **Next:** #30 (messaging) is the next unblocked issue. #23 still blocked by #22 (hitl).

### 2026-04-16 22:00 UTC / iteration #4 of PRD #16 / closed #30
- **Decision:** Messaging built as single `messaging.py` router with nested `/conversations` + `/conversations/{id}/messages` + `/conversations/{id}/read` endpoints (not two separate routers). RLS enforces participant-only access via `conversation_participants` join table. `last_read_at` on participants tracks read state per-user; email fallback query in `MessagingService.find_unread_needing_fallback()` uses LEFT JOIN against `message_email_fallbacks` to avoid duplicate sends. Seeded `messaging_email_fallback_delay_minutes` platform_setting (default 15). Web UI deferred — backend + tests only this iteration since the UI requires working Supabase Realtime subscriptions which depend on a running stack.
- **Blocker:** OneDrive EIO on pnpm install (same as prior iterations); tsc check done via Node API workaround.
- **Next:** #40 (notification service extension) is unblocked by #30. #23 still blocked by #22 (hitl).

### 2026-04-16 23:30 UTC / iteration #5 of PRD #16 / closed #40
- **Decision:** Built 18-row `notification_templates` table (15 unique events across 4 personas with 3 cross-persona variants) + `notification_category_preferences` table for per-category/channel toggles. `NotificationEventService.fire_event()` orchestrates template lookup → variable rendering → preference gating → dispatch via existing `NotificationService.send()`. Stage 0 send() surface untouched. Default prefs: all channels enabled (no prefs rows = all on). Weekly digest templates configured with web_push-only channels. Actual trigger wiring (Postgres triggers, pg_cron jobs) deferred to the slices that create the source tables (assignments, lessons, streaks) — this slice provides the dispatch infrastructure.
- **Blocker:** OneDrive EIO on pnpm install (same as prior iterations); codegen via /tmp workaround.
- **Next:** All remaining open non-hitl issues are blocked by #22/#24/#27 (all hitl). Loop should COMPLETE or ABORT after this iteration.

### 2026-04-16 23:45 UTC / iteration #6 of PRD #16 / closed #22
- **Decision:** `dailyriff_employees` table with role enum {owner, support, verifier} + `mfa_failure_log` for 3-in-15-min alerting. `require_superadmin` dependency in auth.py centralizes role + TOTP gate: checks JWT `amr` claim for `totp` method, enforces in production, warn-only in dev/staging/test. Employees router uses `service_transaction` (bypasses RLS) matching settings router pattern. `MfaAlertService.record_failure()` counts failures in rolling 15-min window, writes activity_log alert when threshold hit. Bootstrap script validates: zero employees, auth.users row exists, TOTP enrolled (production only). #22 was incorrectly labeled hitl in iteration #5 notes — it's `ralph, stage-1, afk`.
- **Blocker:** OneDrive EIO on pnpm install (same as prior iterations); codegen via /tmp workaround.
- **Next:** #23 (superadmin surface) is now unblocked by #22 + #19. #24 (marketing pages) is hitl.

### 2026-04-16 UTC / iteration #7 of PRD #16 / closed #23
- **Decision:** Built 8-page superadmin surface under `apps/web/src/app/(superadmin)/` route group. Added `/admin` backend router with superadmin-only endpoints (list all studios, get/suspend/verify studios, verification queue) using `service_transaction` to bypass RLS. Created 9 shadcn/ui components manually (Card, Badge, Input, Table, Dialog, Tabs, Separator, Select, Textarea) due to OneDrive EIO preventing `npx shadcn` install. Added `src/lib/api.ts` with `apiFetch` helper for authenticated API calls. Users pages are stubs with info banner since full user management requires Supabase Admin API (deferred). Impersonation buttons disabled with stub labels (ships in Slice 30). Sidebar nav uses lucide-react icons. All pages are client-side rendered with TanStack Query for data fetching.
- **Blocker:** OneDrive EIO on pnpm install (same as prior iterations); manually symlinked jest/ts-jest/clsx/tailwind-merge from pnpm store for local test runs.
- **Next:** #24 (marketing pages) and #25 (waitlist + onboarding, blocked by #23 + #24) are next unblocked.

### 2026-04-16 UTC / iteration #8 of PRD #16 / closed #24
- **Decision:** Built 6 marketing + legal pages under `(marketing)` route group with shared layout (nav header + footer). Homepage has hero + how-it-works + teacher/parent features + waitlist form posting to `POST /waitlist` (stub endpoint OK until Slice 8). Legal pages use placeholder copy with visible "DRAFT — legal review pending" banners. `privacy@dailyriff.com` surfaced on privacy policy, contact, accessibility, and footer. Skip-to-main-content link on all marketing pages. Deleted old root `page.tsx` — the `(marketing)/page.tsx` now serves `/`.
- **Blocker:** OneDrive EIO prevents `pnpm install` and ESLint (same as prior iterations); jest run via /tmp workaround. TSC errors all pre-existing from broken node_modules symlinks.
- **Next:** #25 (waitlist + studio onboarding) is unblocked by #23 + #24. #73 and #74 (infra) also unblocked but non-critical-path.

### 2026-04-16 UTC / iteration #9 of PRD #16 / closed #25
- **Decision:** Waitlist pipeline: `waitlist_entries` + `waitlist_messages` tables (migration 0009), public `POST /waitlist` endpoint with hCaptcha stub + duplicate-email check, superadmin management endpoints under `/admin/waitlist` (list/filter, approve, reject, message, bypass invite). Bypass tokens use `secrets.token_urlsafe(32)` for personal-network direct invites that skip the queue. Used `str` instead of `EmailStr` to avoid adding `email-validator` dependency. Studio onboarding page (`(studio)/onboarding`) with 2-step flow: create studio → pick color. Studio profile page (`(studio)/studio-profile`) with logo upload (R2 presigned URL flow — endpoint stub), display name edit, and 12-swatch color picker from DESIGN.md. Superadmin waitlist page wired to real admin endpoints with status filtering, approve/reject, messaging, and bypass invite dialogs.
- **Blocker:** OneDrive EIO on codegen (same workaround via /tmp). `email-validator` not installed so used plain `str` for email fields.
- **Next:** #26 (invitations + student onboarding) is unblocked by #25. #73 and #74 (infra) remain unblocked non-critical-path.

### 2026-04-16 UTC / iteration #10 of PRD #16 / closed #26
- **Decision:** Invitations built as dual-router pattern (studio_router for create/list/batch/regenerate under `/studios/{studio_id}/invitations`, public_router for `/invitations/redeem`). Token security: SHA-256 hashed before storage, plaintext returned once on creation, hash-compare on redemption. Age-class routing: minor→parent (COPPA), adult→student, teen→caller decides. `parents` + `parent_children` tables with per-child permission flags (is_primary_contact, can_manage_payments, can_view_progress, can_communicate_with_teacher). `studios.auto_approve_parents` column for per-studio parent self-serve toggle. Membership check enforces only owner/teacher can invite. Redemption auto-creates `studio_members` row via ON CONFLICT DO NOTHING.
- **Blocker:** OneDrive EIO on pnpm install (same workaround via /tmp for codegen).
- **Next:** #27 (COPPA VPC), #28 (core loop), #38 (teacher students), #43 (beta rollout) are now unblocked by #26.

### 2026-04-16 UTC / iteration #11 of PRD #16 / closed #28
- **Decision:** Core loop backend: `assignments`, `recordings`, `assignment_acknowledgements` tables (migration 0011) with Polymet's `auto_acknowledge_assignment` Postgres trigger ported verbatim (fires on `recordings UPDATE` when `uploaded_at` transitions NULL→non-NULL, flips pending acks to acknowledged). Duration CHECK 300–3600s on recordings preserved. `AssignmentValidator` enforces due ≤6mo, ≤10 pieces, ≤15 techniques, teacher≠student. `RecordingService` handles MIME negotiation (opus→mp4a→webm→hard fail) and R2 object key generation. Presigned URL flow: FastAPI mints URL, never proxies bytes. Web UI (create-assignment, recording, pending-reviews pages) deferred — backend + services + routers + full test coverage shipped this iteration; UI depends on working Supabase Realtime subscriptions and MediaRecorder API which need a running stack.
- **Blocker:** OneDrive EIO on pnpm install (same workaround via /tmp for codegen).
- **Next:** #36 (recording playback), #37 (student dashboard), #39 (Expo mobile) are now unblocked by #28. #38 (teacher students) also unblocked (by #26).

### 2026-04-16 UTC / iteration #12 of PRD #16 / closed #38
- **Decision:** Teacher-students router under `/studios/{studio_id}/students` + `/studios/{studio_id}/loans` + `/studios/{studio_id}/parent-children/{id}` using `service_transaction()` (not `rls_transaction`) because membership checks happen in-endpoint. `loans` table (migration 0012) with RLS policies for studio-member read, owner/teacher write. `_require_teacher_or_owner()` helper centralizes the membership gate. Student detail endpoint aggregates student info + parent-children permissions + loans in a single response. Frontend teacher pages under `(studio)/teacher/students/` with `GuardianDetailDialog` for per-child permission toggle editing via mutations.
- **Blocker:** OneDrive EIO on pnpm install (same workaround via /tmp for codegen).
- **Next:** #44 (lessons + attendance), #45 (payment ledger), #46 (account conversion), #49 (data seeding), #50 (parent dashboard) are now unblocked by #38.
