# Stage 1 — Foundation PRD (MVP)

**Status:** Ready for `/prd-to-issues`
**Created:** 2026-04-15
**Owner:** Rollin
**Companion doc:** [`docs/prds/stage-1-deferred-features.md`](./stage-1-deferred-features.md) — authoritative scope tracker from grill-me Q1–Q29. This PRD summarizes; the tracker is the source of truth for per-feature deferral rationale.
**Predecessor:** [`docs/prds/stage-0-foundation.md`](./stage-0-foundation.md) (shipped — infra/auth/notifications skeleton on master).

---

## Problem Statement

Music teachers running private studios have no single tool that closes the loop between *"I assigned this piece"* and *"the student actually practiced it."* Today, teachers patchwork Google Calendar for lessons, group texts for assignments, Venmo for payments, and unverifiable student self-reports for practice. Parents (especially parents of under-13 students, where COPPA makes the data question legally charged) have no visibility into what their kid is supposed to be practicing, whether it happened, or how much they still owe the studio. Students — the ones who benefit most when practice is visible and rewarded — get none of the feedback loops that make practice feel like progress.

The existing Polymet scaffold (`slubby101/daily-riff-platform`) sketches the product but only wires one sliver end-to-end: practice-recording → assignment-acknowledgement. Everything else (teachers, parents, payments, messaging, lessons, onboarding, superadmin, compliance) is TypeScript classes and mock data with no persistence. DailyRiffV2 Stage 0 shipped the infra backbone (Supabase + FastAPI + Expo + codegen + CI); Stage 1 is the first stage that produces a working, legally shippable, end-user product.

## Solution

Stage 1 ships the full MVP: the complete studio-operations product a real music studio can adopt in a controlled beta, covering teacher, parent, student-web (13+), student-mobile, and DailyRiff superadmin personas. It is the first stage where non-employee users touch production.

From the user's perspective:

- **A studio owner** signs up via a waitlist, is approved by DailyRiff, invites teachers and students, schedules lessons, hands out assignments, reviews practice recordings, tracks attendance and payments, and messages parents — all in one web app with light studio branding.
- **A parent** receives a studio invite, completes COPPA verifiable parental consent (for under-13 children), sees their kid's schedule, assignments, practice streak, and outstanding balance, and can message the teacher — on web.
- **A student 13+** logs in to a web dashboard, sees their assignments, records 5–60 minutes of practice, watches it auto-acknowledge the assignment, and sees their streak and messages.
- **A student (any age)** on the mobile Expo app has a focused 5-screen experience: dashboard, lessons, assignments, messages, profile. Recording is the primary action.
- **A DailyRiff superadmin** (Rollin, Stage 1) runs the platform from an 8-page operator surface: studios list, user list, verification queue, waitlist, employees, platform settings, impersonation, dashboard.

The product loop preserved verbatim from Polymet is: **teacher assigns → student records 5–60 min practice → Postgres trigger auto-acknowledges the assignment → teacher adds feedback in a pending-reviews queue.** That trigger is the whole product's pivot; everything else is scaffolding around it.

Stage 1 ships to a **controlled beta of 3–5 hand-picked studios** with white-glove support and explicit graduation criteria (see Launch Criteria below). There is NO studio SaaS subscription billing — DailyRiff's business model is pure marketplace, monetizing only via platform fees on tuition in Stage 2+ via Stripe Connect.

## User Stories

### Onboarding — studio/DailyRiff (Q14a)
1. As a **prospective studio owner**, I want to join a waitlist from the DailyRiff marketing homepage, so that I can request access before the product is GA.
2. As a **prospective studio owner invited directly**, I want to bypass the waitlist via an invite link, so that personal-network beta studios can skip the queue.
3. As a **DailyRiff superadmin**, I want to review and approve waitlist entries, so that I can pace studio onboarding to my support capacity.
4. As a **DailyRiff superadmin**, I want a post-signup verification queue, so that I can vet new studios after they're signed up without blocking their initial access.
5. As a **newly approved studio owner**, I want a dedicated onboarding page that walks me through studio profile setup, so that my first session ends with a functional studio.
6. As a **studio owner**, I want to upload a logo, pick a primary color from a 12-swatch palette, and set a display name, so that the studio-facing UI and emails feel branded.

### Onboarding — student↔studio (Q14b)
7. As a **teacher**, I want to invite a student directly by email, so that the common case (teacher adds a student they already teach) is frictionless.
8. As a **parent**, I want to self-serve enroll my child into a studio using a studio code, so that I don't have to wait for the teacher to initiate.
9. As a **teacher**, I want to toggle auto-approve on parent self-enrollment, so that I can choose between gatekeeping and convenience.
10. As a **parent of a child under 13**, I want to be the one invited (not my child), so that COPPA verifiable parental consent fires at the right moment.
11. As a **parent inviting multiple children at once**, I want one email and one signup to enroll all my kids, so that I don't sign up three times.
12. As a **student or parent**, I want invitation tokens to be 14-day single-use and regenerable, so that a stale or lost link doesn't lock me out.
13. As a **newly signed-up user**, I want to land on my dashboard immediately, so that there's no blocking walkthrough between me and the product.

### Account conversion (Q13)
14. As a **minor student turning 13**, I want my account to be manually convertible into a teen account (with parent consent), so that I get age-appropriate autonomy.
15. As a **teen student turning 18**, I want my account to be manually convertible into an adult account (requires email), so that my parent no longer has ambient control.

### Teacher — studio operations
16. As a **teacher**, I want a dashboard showing today's lessons, pending reviews, and overdue payments, so that I can start my day knowing what to do.
17. As a **teacher**, I want a students list with search and single-dimension filters, so that I can find a student fast.
18. As a **teacher**, I want a student detail page with lesson history, assignments, recordings, parents, and loan tracking, so that I have one place for everything about one kid.
19. As a **teacher**, I want to create assignments with pieces and techniques and a due date, so that students have specific practice targets.
20. As a **teacher**, I want a pending-reviews queue that updates in realtime when new recordings arrive, so that I can keep feedback latency low.
21. As a **teacher**, I want to play back a student's recording inside the app, so that I can review practice without downloading files.
22. As a **teacher**, I want to attach text feedback and a 1–5 rating to a recording, so that the student knows what to fix.
23. As a **teacher**, I want to schedule recurring lessons in my studio's local timezone, so that DST and travel don't break the calendar.
24. As a **teacher**, I want to mark attendance and optionally schedule a makeup, so that absences are tracked explicitly.
25. As a **teacher**, I want to add payments manually, record refunds, see outstanding balances and payment history, so that I can run my studio's finances without a separate spreadsheet.
26. As a **teacher**, I want a resources page with external links scoped to my studio, so that I have one place to share supplemental materials.
27. As a **teacher**, I want my own profile settings page (distinct from the studio-level profile), so that my personal info and the studio's info are separated.

### Parent
28. As a **parent**, I want to complete COPPA verifiable parental consent via a Stripe micro-charge (with a signed-form escape hatch), so that under-13 data collection is compliant.
29. As a **parent**, I want a dashboard showing each of my children's next lesson, latest assignment, and practice streak, so that I can see the state of all my kids at once.
30. As a **parent with multiple children**, I want per-child permission flags (payments, progress, teacher communication), so that my access matches real-family custody/payer dynamics.
31. As a **parent**, I want to report my child absent and optionally request a makeup, so that sick days don't create awkward payment conversations.
32. As a **parent**, I want to pay outstanding balances and see payment history (Stage 1 = display of teacher-entered ledger; Stripe Connect payments in Stage 2+), so that I know what I owe.
33. As a **parent**, I want to message my child's teacher, so that coordination doesn't sprawl across SMS threads.
34. As a **parent**, I want to schedule the permanent deletion of my child's data with a 15-day grace period and cancellation window, so that COPPA deletion rights are real and safe.

### Student — web (13+)
35. As a **student 13+**, I want to see my assignments and due dates on a dashboard, so that I know what to practice next.
36. As a **student 13+**, I want to record 5–60 minutes of practice in the browser, so that my practice counts as proof.
37. As a **student 13+**, I want my recording to automatically acknowledge the assignment, so that I don't have a second step to prove I did my homework.
38. As a **student 13+**, I want to see my recording history, so that I can replay past sessions.
39. As a **student 13+**, I want to see a practice streak and weekly minutes, so that consistency is visible and rewarding.
40. As a **student 13+**, I want to message my teacher, so that I can ask questions between lessons.

### Student — mobile (Expo, all ages where permitted)
41. As a **student on mobile**, I want a focused 5-screen app (dashboard, lessons, assignments, messages, profile), so that I'm not distracted.
42. As a **student on mobile**, I want chunked resumable recording upload, so that a dropped connection doesn't cost me a practice session.
43. As a **student on mobile**, I want push notifications for new assignments, due-soon reminders, and lesson reminders, so that I don't rely on memory.
44. As a **student on mobile**, I want my session to stay signed in across cold launches, so that opening the app doesn't require typing a password.

### Messaging + notifications
45. As a **user of any persona**, I want realtime in-app messages via Supabase Realtime subscriptions, so that conversations feel immediate.
46. As a **user**, I want unread messages to fall back to email after 15 minutes, so that I don't miss important messages while offline.
47. As a **user**, I want per-category and per-channel notification preferences, so that I can mute channels that annoy me without going dark on everything.
48. As a **user**, I want push notifications on both web (Web Push) and mobile (Expo Push), so that I get notified on whichever device I'm using.

### Superadmin (DailyRiff operator)
49. As a **superadmin**, I want a dashboard with platform-level metrics, so that I can see health at a glance.
50. As a **superadmin**, I want to list all studios and drill into a studio detail page, so that I can support any studio on request.
51. As a **superadmin**, I want to suspend or verify a studio, so that I can handle bad actors and approval follow-ups.
52. As a **superadmin**, I want to impersonate any user (with a mandatory reason, silent or live-mode-banner option, and delayed email notification to the target), so that I can debug issues without full password resets — and so that every impersonation leaves a trail.
53. As a **superadmin**, I want a waitlist management page with single-recipient messaging, so that I can ramp studio onboarding manually.
54. As a **superadmin**, I want an employees page with owner/support/verifier roles, so that I can share operator duties later without re-plumbing auth.
55. As a **superadmin**, I want a platform-settings page with category-grouped editable knobs (rate limits, business-rule caps, notification delays, COPPA grace windows) and a read-only mirror of vendor-side settings, so that I can tune the running platform without redeploying.
56. As a **superadmin**, I want TOTP hard-required on login, with a break-glass runbook and printed offsite recovery codes, so that the highest-blast-radius account class is the hardest to compromise.

### Recording playback authorization (Q18)
57. As a **student, parent, or assigned teacher**, I want to play a recording via a 5-minute signed URL, so that the audio is protected but fast to stream.
58. As a **non-authorized user**, I want to be denied playback with a clear error, so that misconfigured access shows up loud instead of silently leaking.
59. As a **target user of an impersonation session**, I want to see every impersonation playback in my Account Access Log, so that I can audit what admin support looked at.

### Marketing + legal (public)
60. As a **visitor**, I want to browse a marketing homepage, about page, contact page, privacy policy, terms of service, and accessibility statement, so that the product is credible and legally compliant.
61. As a **California/Colorado/Connecticut user**, I want a "Your Privacy Choices" footer link, auto-respected Global Privacy Control, and a cookie table, so that CCPA/CPRA requirements are met without a blocking consent banner.

### Accessibility
62. As a **keyboard-only user**, I want every interactive element reachable via Tab and operable via Enter/Space, so that I can use the entire product without a mouse.
63. As a **screen-reader user**, I want proper landmarks, heading order, ARIA labels, and live-region announcements for state changes, so that I can use NVDA or VoiceOver productively.
64. As a **low-vision user**, I want 200% zoom + reflow support and AA contrast ratios, so that I can read the UI.
65. As a **user with vestibular sensitivity**, I want `prefers-reduced-motion` respected, so that transitions don't make me sick.

### Beta (Q29)
66. As a **beta studio**, I want a private beta landing page behind a URL token, so that I can onboard before GA.
67. As a **beta studio**, I want a `/beta/feedback` form (scoped to my studio), so that I can submit structured bug reports and feature requests.
68. As a **DailyRiff operator during beta**, I want each beta studio flagged forever via `studios.beta_cohort`, so that I can run post-mortems on the founding cohort.

---

## Implementation Decisions

Every Stage 1 scoping question was resolved in the companion tracker `docs/prds/stage-1-deferred-features.md` (grill-me Q1–Q29). The tracker is the authoritative source for per-decision rationale. The summary below captures the decisions that shape the implementation plan.

### Architecture

- **Three-environment split**: dev (local `supabase start`), staging (Supabase project + Railway service + R2 `dailyriff-staging` + Stripe test), prod (Supabase Pro + Railway prod + R2 `dailyriff-prod` + Stripe live). Staging doubles as the demo environment. Auto-deploy master → staging; tag-gated deploy to prod with manual approval.
- **Services**:
  - **Supabase Pro** (prod, $25/mo) for Postgres + GoTrue + PostgREST + Realtime + Studio + small-asset Storage. Free tier acceptable for staging (re-seedable).
  - **FastAPI on Railway** for business logic: Stripe, COPPA VPC, recording upload-confirm, orchestration, notifications.
  - **Cloudflare R2** for recordings via presigned URLs (direct upload, CDN playback, free egress).
  - **Cloudflare** in front of Railway (WAF, Bot Fight Mode, rate-limit rule, public status page).
- **Stage 0b is subsumed by Stage 1.** There is no standalone Stage 0b deploy stage. Cloud Supabase migration, Railway deploys, staging environment, CI deploy pipelines, and the HS256→ES256 auth widening that was originally scoped as Stage 0b all ship inside Stage 1.
- **Auth widening (not rewrite)**: Stage 0's `apps/api/src/dailyriff_api/auth.py` middleware is **widened**, not replaced. Stage 0 shipped HS256 validation via `SUPABASE_JWT_SECRET` for the local `supabase start` instance. Stage 1 adds ES256 validation via a Supabase JWKS URL for cloud-hosted Supabase, keeping HS256 as a local-dev fallback. The `CurrentUser` contract, the middleware surface, and every Stage 0 test stay intact; only the verification-key source and algorithm list change. Preserves working code, working tests, and the Stage 0 PRD Q10 / Open Risk #5 intent.
- **`realtime_outbox` is preserved, not retired.** Stage 0 deliberately shipped `realtime_outbox` as a belt-and-suspenders fallback for transient Supabase Realtime REST broadcast failures (Stage 0 PRD Open Risk #6). The primary Realtime path is already `NotificationService.send()` → `httpx.AsyncClient` POST to `{SUPABASE_URL}/realtime/v1/api/broadcast`; on non-2xx or connection failure, a row is written to `realtime_outbox`. Stage 1 builds on top of this existing service — no retirement, no schema change. Stage 0's `user_push_subscriptions`, `notification_preferences`, device/preferences routers, and 3-channel `NotificationService` are all preserved.
- **Multi-tenancy**: `studio_id` on every tenant-scoped row + Supabase RLS policies (DB-enforced isolation).
- **Core-loop invariant**: Polymet's `auto_acknowledge_assignment` Postgres trigger is **preserved verbatim**. Recording upload → `recordings.uploaded_at` transitions null → non-null → trigger flips matching `assignment_acknowledgements` rows from pending → acknowledged. This is the whole product's pivot.
- **Recording duration hard-gate**: 300–3600 seconds (5–60 min), enforced by DB CHECK constraint. Preserved from Polymet as the product's opinion on what counts as a real practice session.
- **Recording format**: client negotiates `audio/webm;codecs=opus` → `audio/mp4;codecs=mp4a.40.2` → `audio/webm` generic → hard fail. No server-side transcoding. Server stores whichever MIME the client uploaded.

### Modules to build or modify

Grouped by bounded context. Each is designed to be a deep module (simple interface, rich behavior, unit-testable in isolation).

- **`auth` (widened from Stage 0)** — the existing `apps/api/src/dailyriff_api/auth.py` middleware, widened in place to accept both HS256 (local `supabase start`, `SUPABASE_JWT_SECRET`) and ES256 (cloud Supabase, JWKS URL fetched and cached from `{SUPABASE_URL}/auth/v1/.well-known/jwks.json`). `CurrentUser` extended with `studio_id`, `impersonation_session_id`. All Stage 0 tests preserved; new ES256 tests added. No new module — same file, same import path.
- **`rls_policies`** — Alembic-managed RLS definitions for every tenant-scoped table. Tested via the RLS isolation test suite (Stage 0 pattern extended).
- **`studio_service`** — studio lifecycle (create, update, suspend, verify, set branding, set timezone). Owns `studios.logo_url`, `studios.primary_color`, `studios.display_name`, `studios.timezone`, `studios.beta_cohort`.
- **`onboarding_service`** — the two pipelines (Q14a studio↔DailyRiff, Q14b student↔studio). Token generation (14-day, single-use, hashed), regeneration, verification, post-signup routing. Multi-child batch invite. Handles the COPPA VPC trigger on parent signup for under-13 children.
- **`account_conversion_service`** — manual-trigger 13→teen, 18→adult. Ports Polymet's `AccountConversionService` domain rules. Birthday-automation is deferred.
- **`assignment_service`** — create, acknowledge, complete, list, pending-acknowledgements, send-assignment-reminders. Validates teacher↔student studio match, due date ≤6 months, ≤10 pieces / ≤15 techniques.
- **`recording_service`** — upload-URL minting (presigned R2), upload-confirm (writes `uploaded_at`, triggers ack via DB trigger), teacher feedback, pending-reviews query. Duration gate enforced both at the schema and service layer.
- **`playback_authorization`** — `can_play_recording(user, recording)` policy function, single source of truth for Q18's default-deny allow-list. Unit-tested across the full persona × relationship × state matrix. Mints 5-minute signed R2 URLs. Writes `impersonation_playback_log` when the session is an impersonation.
- **`lesson_service`** — create, mark-attendance, complete, list. Recurring lessons stored as rules against studio-local TZ (not UTC offset), DST-safe.
- **`attendance_service`** — status transitions, makeup request/schedule, absence reporting. Q15 `absences`, `absenceNotifications`, `studioAbsencePolicy` data shapes inform the schema.
- **`messaging_service`** — send-message, get-conversation, mark-read. Supabase Realtime subscription for live updates. Email fallback after 15 min unread.
- **`notification_service`** — extends Stage 0's 3-channel service (Realtime + Expo Push + Web Push) with the 15 event types from Q16.1. `notification_templates` table drives copy + channels + target persona. Trigger sources: Postgres triggers (DB state), `pg_cron` (time-based), FastAPI handlers (cross-service).
- **`notification_preferences_service`** — per-category + per-channel toggles. Defaults all on except weekly digests (email only).
- **`payment_service`** — teacher-entered ledger (add, refund, outstanding balance, payment history). NO Stripe Connect in Stage 1 (Stage 2+). NO studio SaaS subscription billing.
- **`coppa_service`** — VPC via Stripe micro-charge Setup Intent + signed-form escape hatch. 15-day grace-period deletion with cancellation window. VPC revocation as a separate pause-new-collection flow with 30-day auto-delete if not re-consented.
- **`streak_service`** — ports Polymet's `PracticeStreakCalculator`. One practice recording per day counts. Current and longest streaks. Streak milestones drive notification events.
- **`resources_service`** — studio-scoped list of external links.
- **`impersonation_service`** — start session (requires reason), end session, silent vs live-mode, delayed email notification to target, write `impersonation_sessions` row. Scope restrictions: cannot change password / delete account / change email / authorize OAuth / delete recordings/messages/child data.
- **`platform_settings_service`** (Q24) — `platform_settings` table reader/writer with 30-second in-process TTL cache + write invalidation. Every tunable knob in the app (rate limits, business-rule caps, notification delays, COPPA grace windows) is stored here and edited from the superadmin platform-settings page. Exception: vendor-side settings (Cloudflare WAF, GoTrue limits) are read-only mirrors.
- **`rate_limit_middleware`** — FastAPI `slowapi` middleware. Global defaults + per-route overrides, all tunable live via `platform_settings`. Specific routes per Q24 Layer B.
- **`idempotency_log`** — `(provider, event_id)` uniqueness for webhook replay defense (Stripe, Postmark).
- **`waitlist_service`** — join, approve, single-recipient message, basic reminder cron. Waitlist polish (A/B, bulk messaging, template manager) deferred.
- **`employees_service`** — DailyRiff staff roles (owner, support, verifier). TOTP-required login. First-owner bootstrap via `apps/api/scripts/bootstrap_first_owner.py` (one-shot, sanity-checked, staging-parity).
- **`activity_logs`** — append-only audit log (impersonations, verifications, payment events, platform-settings edits, MFA events, R2 deletes). Table exists in Stage 1; UI viewer deferred to Stage 2. Supabase Studio is the Stage 1 viewer.
- **`secret_rotation_schedule`** — table + superadmin UI + daily `pg_cron` warn-on-due-soon + "mark rotated" action. Seeded pre-launch with all Q28 secrets.
- **`operational_alerts`** — `pg_cron` self-check heartbeat table + FastAPI endpoint for BetterStack to heartbeat against. Defense against silent cron failure.
- **`beta_feedback_service`** — `beta_feedback` table + `/beta/feedback` form behind auth, beta-studios only. Superadmin view reuses existing surfaces.
- **`api_client` (codegen)** — Stage 0 codegen pipeline extended to cover every new router. Mobile and web both consume `packages/api-client`.

### Schema changes (summary — full DDL lives in Alembic)

New tables (additive to Stage 0's `user_push_subscriptions` + `notification_preferences`):

- `studios` — studio-level record, including `logo_url`, `primary_color`, `display_name`, `timezone`, `beta_cohort`, waitlist/verification state.
- `dailyriff_employees` — superadmin staff with role (owner/support/verifier).
- `waitlist_entries` + `waitlist_messages`.
- `invitations` — hashed tokens, 14-day expiry, single-use, regenerable, persona-typed (studio-owner, teacher, parent, student).
- `students` — id = auth.users.id, studio_id, teacher_id, name, email, phone, instrument, level, avatar_url, age-class (MINOR/TEEN/ADULT/COLLEGE), deletion_scheduled_at, pending_deletion flag, parent linkage table.
- `parents` + `parent_children` — per-child permission flags (`is_primary_contact`, `can_manage_payments`, `can_view_progress`, `can_communicate_with_teacher`).
- `teachers` — studio_id, profile fields, hourly_rate, availability (recurrent rule format), qualifications[], preferences jsonb.
- `lessons` — schedule (date, start/end, duration, is_recurring, cadence), attendance, recording id, notes, cost, is_paid, is_trial. Recurrence against studio-local TZ.
- `absences` + `absence_notifications` + `studio_absence_policy`.
- `assignments` — teacher_id, student_id, title, description, pieces[], techniques[], due_date, status (active/completed/overdue).
- `recordings` — student_id, assignment_id, **duration CHECK (300, 3600)**, file_size, quality, format, recorded_at, uploaded_at, device_info, app_version, waveform_data jsonb, notes, tags[], storage_url, mime_type.
- `assignment_acknowledgements` — assignment_id, student_id, recording_id, status (pending/acknowledged/failed), attempt_count, teacher_feedback, acknowledged_at. UNIQUE (assignment_id, student_id, recording_id). **`auto_acknowledge_assignment` trigger preserved verbatim from Polymet.**
- `messages` + `conversations` — realtime-subscribed.
- `notifications` + `notification_templates` + `notifications_pending`.
- `payments` — studio-scoped manual ledger. Amount, currency=USD, payer, status, method, memo.
- `loans` — instrument loan tracking, embedded in student detail.
- `resources` — studio_id-scoped external link list.
- `coppa_consents` — Stripe Setup Intent id, consent form, status, revoked_at.
- `coppa_deletion_log` — no-PII audit trail `{deleted_at, studio_id, deleted_by, r2_objects_count, db_rows_count}`.
- `impersonation_sessions` + `impersonation_playback_log`.
- `activity_logs` — append-only event log (schema reserved; UI deferred).
- `secret_rotation_schedule`.
- `platform_settings` — `{key, value_json, description, category, updated_at, updated_by}`.
- `operational_alerts`.
- `beta_feedback`.
- `idempotency_log` — `(provider, event_id)` unique.

### API contracts

- FastAPI OpenAPI snapshot remains the codegen source of truth (`apps/api/openapi.snapshot.json`).
- Codegen produces `@hey-api/openapi-ts` TypeScript client in `packages/api-client/`, consumed by both `apps/web` and `apps/mobile`.
- Schemathesis contract tests move from **informational → blocking** (upgrade tracked in #15).
- Routes grouped under logical prefixes: `/auth/*`, `/studios/*`, `/students/*`, `/parents/*`, `/teachers/*`, `/lessons/*`, `/assignments/*`, `/recordings/*`, `/messages/*`, `/notifications/*`, `/payments/*`, `/coppa/*`, `/resources/*`, `/admin/*` (superadmin), `/waitlist/*`, `/beta/*`, `/health`, `/health/deep`.

### Frontend stack (web)

`apps/web` is **Next.js 15 App Router** (committed in Stage 0, preserved in Stage 1 — no Vite migration). Stage 1 adds the full UI foundation on top:

- **TailwindCSS 3.4+** with `tailwindcss-animate` and `tailwind-merge`.
- **shadcn/ui** in the `"new-york"` style, base color `zinc`, CSS variables on — matching Polymet's configuration so component ports are near-literal copies. Components live under `apps/web/src/components/ui/`.
- **Radix UI primitives** (dependencies of shadcn) — provide ~70% of WCAG 2.1 AA coverage for free (per the accessibility section).
- **lucide-react** for icons (Polymet parity).
- **react-hook-form** + **zod** for form state and validation.
- **next-themes** for dark-mode toggle (Q13 committed to dark mode).
- **TanStack Query (React Query) v5** for server-state caching, consuming `packages/api-client`. Invalidation on mutation; Supabase Realtime subscriptions push targeted invalidations for the pending-reviews queue and messaging.
- **CSS custom property `--primary`** honored across student/parent layouts for the per-studio `studios.primary_color` (Q15). The 12-swatch palette is defined as CSS variables at the root level, each pre-vetted to AA contrast (4.5:1 normal, 3:1 large) against both white and black text.
- **`jsx-a11y` ESLint plugin at error level** blocks the build on violations (tracked alongside #14).

Polymet's React+Vite+Tailwind+shadcn components port to Next App Router with minimal friction: shadcn components are framework-agnostic, Tailwind classes transfer verbatim, routing moves from `react-router-dom` to App Router file-based routes, and data fetching moves from direct Supabase client calls to `@/lib/api` wrappers around the codegen'd `packages/api-client`.

### Frontend stack (mobile)

`apps/mobile` is **Expo SDK 52+** (committed in Stage 0, preserved in Stage 1). Polymet has no Expo app, so the 5-screen Stage 1 mobile UI is new construction — but kept deliberately minimal.

- **Zustand** for client state (already committed in Stage 0 via `sessionStore.ts`).
- **TanStack Query v5** for server state (consumes the same `packages/api-client`).
- **React Native core components + Expo primitives** as the baseline — no heavyweight UI library in Stage 1. Five screens is few enough that a dedicated component library is overkill.
- **NativeWind / Tamagui / react-native-paper**: **explicitly deferred.** Revisit when the mobile surface grows beyond 5 screens. Stage 1 uses plain StyleSheet + small local component primitives.
- **Expo Router** for navigation.
- **Expo AV** for recording (chunked resumable uploads to R2 via presigned URLs).

### Information hierarchy per persona

For each persona's primary screen, the top-3 content priorities are committed here. This is NOT a wireframe — it's a content-priority decision. Implementation (Slices 6, 18, 20, 21, 22, 33) reads this to know what goes above the fold, what goes in the hero position, and what the user's first action should be. Every deviation from this hierarchy during implementation requires explicit approval.

The rationale for each hierarchy is the real product loop — the user's actual question when they open the app — not Polymet's mocked layout (which was designed as a scaffold, not optimized for DailyRiff's pivot).

#### Teacher dashboard (Slice 6 consumer via superadmin, but primarily Slice 21 / #38 for studio teacher)

Opens in the morning before first lesson. Question: *"what do I need to do today, and is there anything I'm behind on?"*

| Priority | Content | Why |
|---|---|---|
| **1st (hero)** | **Pending reviews queue** — realtime list of recordings awaiting feedback, with the oldest at top. Count badge in hero position. Primary CTA: "Review oldest." | This is the product's pivot. Auto-ack fires on upload; the teacher's whole value-add is the feedback step. If pending reviews isn't first, teachers forget to review and the loop collapses. Polymet leads with "upcoming lessons this week" — wrong for DailyRiff's model. |
| **2nd** | **Today's lessons** — scheduled lessons for today in studio-local TZ, with attendance status + next lesson time. Inline "mark attendance" action. | Second because it's logistically urgent but doesn't define the product. A teacher who misses one day of review is fine; a teacher who misses a lesson is in trouble with a parent. |
| **3rd** | **Overdue / outstanding payments summary** — count of students with balance >0 and oldest unpaid invoice age. Drill-in to full ledger. | Third because money matters but can wait till end of day. Teachers need to see it exists, not interrupt their morning with it. |

Secondary (below fold, always visible on larger screens): streak summary across all students, upcoming assignments due this week, unread messages count.

#### Parent dashboard (Slice 33 / #50)

Opens in the evening after school. Question: *"did my kid practice today, and what do they need to do next?"*

| Priority | Content | Why |
|---|---|---|
| **1st (hero)** | **Per-child streak + today's practice status** — for each child, a large streak count with "practiced today ✓" or "not yet today." If multi-child, a row per child. | The parent's core anxiety/joy is "are my kids keeping up." Making this the hero turns the dashboard into a reassurance device instead of a chore list. |
| **2nd** | **Next assignment due** — per child, the soonest-due assignment with due date and a "view assignment" link. | Second because parents use it to nudge ("have you done this yet?"). Not first because the streak already answered the core question. |
| **3rd** | **Next lesson reminder** — per child, date/time in studio-local TZ with "add to my calendar" link (.ics export). | Third because scheduling is logistical, not emotional. Always the same question ("when's the next one?"). |

Secondary: outstanding balance (display-only in Stage 1, Stripe Connect in Stage 2+), unread messages from teacher, COPPA consent status + deletion schedule for under-13 children.

#### Student web (13+) dashboard (Slice 20 / #37)

Teen opens after school from homework break. Question: *"what do I need to practice, and can I just start?"*

| Priority | Content | Why |
|---|---|---|
| **1st (hero)** | **Today's assignment + one-tap "Start recording" button** — the currently active assignment with pieces/techniques list and a large amber primary CTA that opens the recording flow directly. | The whole product reduces to "practice and hit record." Every other dashboard element is noise compared to the button. Teen friction tolerance is zero. |
| **2nd** | **Streak + weekly minutes** — large display-xl streak count from `streak_service`, this week's total minutes in Fraunces display font. | Second because identity/motivation. A 14-year-old with a 47-day streak is a different person than a 14-year-old without one. The scale (`display-xl 64px` per DESIGN.md) matches the emotional weight. |
| **3rd** | **Latest teacher feedback on a prior recording** — the most recent ack row with teacher feedback text, starred if rating ≥4. | Third because the loop closes here — the student did a thing, the teacher noticed, here's what the teacher said. Without this, the feedback loop is invisible to the student. |

Secondary: assignments due this week (list), recording history (last 5), unread messages from teacher.

**Explicit non-goal:** no payment info, no schedule-mgmt, no multi-child UI. Student sees their own data only.

#### Student mobile (5-screen Expo — Slice 22 / #39)

Kid opens on phone, often during practice setup. Question: *"start recording, now."* The whole dashboard screen is a launchpad for the record button.

| Priority | Content | Why |
|---|---|---|
| **1st (hero)** | **Giant "Start recording" button** — fills the top ~40% of the screen, amber primary, keyboard-style tap target. Below it in small caption: the current assignment title. | On mobile, the record button IS the product. Every tap that isn't starting a recording is a tap the kid might give up on. Lead with action. |
| **2nd** | **Streak count + day-of-week grid** — 7-day practice grid showing this week, today highlighted. Small display size (Fraunces display-md, ~40px). | Second because motivation. The 7-day grid is the most common "motivation at a glance" pattern for practice apps (Duolingo, Noom, etc.) — evidence-based and kids understand it instantly. |
| **3rd** | **Next lesson reminder** — "Next lesson: Tue 4pm" compact row. | Third because it's the only logistical info the kid actually needs on mobile. Teachers and parents handle everything else. |

The other 4 screens (`lessons`, `assignments`, `messages`, `profile`) are secondary surfaces. The dashboard is the launchpad; everything else is reference.

#### DailyRiff superadmin dashboard (Slice 6 / #23)

Rollin opens each morning. Question: *"is anything broken, and what needs my attention today?"*

| Priority | Content | Why |
|---|---|---|
| **1st (hero)** | **Operational health strip** — green/yellow/red status for each pg_cron heartbeat and each `operational_alerts` row in the last 24h. BetterStack status mirror for web + api + deep health. | Silent system failures are the biggest risk to a solo-operator platform. The dashboard's first job is answering "did anything break overnight?" before anything else. |
| **2nd** | **Waitlist + verification queue counts** — count of waitlist entries needing review + count of signups in verification queue >24h old. Both link to their queues. | Second because these are the daily operational tasks that pace studio growth. Q29 beta graduation gates depend on keeping this queue flowing. |
| **3rd** | **Platform metrics strip** — 4 headline numbers: active studios (beta cohort flagged separately), total students, recordings uploaded in last 7d, new signups in last 7d. | Third because trend data isn't urgent but sets the "how are we doing overall" context. |

Secondary: recent impersonation sessions log, recent `activity_logs` entries (expand to full page via deferred Slice), open `beta_feedback` entries.

**Non-goals:** no billing metrics (no SaaS billing in Stage 1), no per-studio deep analytics (deferred), no real-time user map.

#### Constraint: Fraunces display sizes where it matters

All 5 dashboard heroes use `display-md` (40px) or `display-lg` (48px) Fraunces per DESIGN.md for the primary metric (pending review count, streak, kid's name, health status, studios count). This is deliberate — the PRD's generous type scale decision lives or dies at these five screens. If implementation defaults to 18px body for these numbers, the whole "editorial warmth" aesthetic collapses into generic SaaS.

### Interaction state matrix

For each of the five highest-stakes flows, every state the user can see is specified here. Empty states are features (per DESIGN.md § Aesthetic Direction). Error states name the problem, the consequence, and the action. Copy is illustrative — Slice 7 / #24 owns final voice review.

#### Flow 1 — Student recording (Slice 11 / #28 web, Slice 22 / #39 mobile)

The product pivot. Every state has to be intentional because this is where students spend their attention.

| State | Trigger | What the user sees | Primary action | Copy example |
|---|---|---|---|---|
| **Idle** | Dashboard, no recording in progress | Large amber primary button, assignment title + due date above | Tap button to request mic | "Start practicing — Bach Invention 13" |
| **Mic permission prompt** | First-ever tap on "start" | Browser/OS native permission dialog + in-app explainer card | Grant permission | "DailyRiff needs your mic to record practice. Nothing leaves your device until you're done." |
| **Mic permission denied** | User clicks "Block" | Card with explainer + link to browser/OS settings + "Try again" button | Fix settings, retry | "Mic access is off. Open your browser settings → site permissions → microphone → allow dailyriff.com." |
| **MIME negotiation failed** | Browser can't produce opus/mp4a/webm | Full-screen blocker | Upgrade browser | "Your browser can't record audio. Please use Chrome, Safari, or Firefox." |
| **Recording** | Mic granted, recording started | Waveform + elapsed time counter (tabular-nums Geist) + pause/stop controls. Duration gate min marker at 5:00. | Pause or stop | "Recording — 03:42 / min 5:00" |
| **Paused** | User pauses | Frozen waveform + resume/stop | Resume or stop | "Paused at 03:42" |
| **Duration too short** | Stop tapped before 300s | Modal: "This practice was short" + "save anyway" / "keep practicing" buttons. Save anyway marks as draft, doesn't count as assignment completion. | Keep practicing (recommended) | "You practiced 03:42. DailyRiff counts sessions of 5 min or more. Keep going?" |
| **Duration too long** | 60:00 hit | Auto-stop with modal: "60 min limit reached" + upload automatically starts | Watch upload | "You practiced the full 60 min. Uploading now." |
| **Uploading** | Valid recording, upload started | Progress bar (chunked, resumable) + elapsed upload time + chunk count | Wait or cancel | "Uploading 1 of 8 chunks..." |
| **Upload failed (retry)** | Network error mid-upload | Inline error card + auto-retry counter (5 attempts per PRD) | Wait or manual retry | "Upload paused — retrying in 12s (attempt 2 of 5). Your recording is safe on this device." |
| **Upload failed (final)** | All 5 retries exhausted | Error card + "Save to device and retry later" button. Recording stays in mobile local cache (10-recording limit). | Retry later | "Upload failed after 5 tries. Your recording is saved on this device and will retry when you reconnect." |
| **Upload offline** | `navigator.onLine === false` at stop | Card: "You're offline. We'll upload when you reconnect." + recording queued in local cache | Continue practicing | "Offline — your practice is saved and will sync when you're back online." |
| **Uploaded, pending ack** | Upload complete, auto-ack trigger not yet fired (usually <1s) | Brief spinner with "Almost done..." | Wait | "Almost done..." |
| **Acknowledged** | Trigger fired, ack row flipped | Success confirmation + celebration micro-animation (spring ease per DESIGN.md § Motion) + assignment marked done | Return to dashboard | "Practice submitted. Your teacher will review it." |
| **Acknowledged with prior feedback** | Ack complete + teacher already left feedback on a recent recording | Same success + "See what your teacher said about Tuesday's practice" link | View feedback or return | "Nice work. Your teacher left a note on Tuesday's recording." |

**Implementation note:** All transitions use DESIGN.md § Motion durations (short 150–250ms for state changes, medium 250–400ms for modals, long 400–700ms for the spring celebration on acknowledged). Waveform rendering is `<canvas>`; no library needed for the amplitude bars.

#### Flow 2 — Teacher pending-reviews queue (Slice 11 / #28)

The teacher side of the product pivot. Realtime subscription drives live updates; states reflect both queue volume and teacher action.

| State | Trigger | What the teacher sees | Primary action | Copy example |
|---|---|---|---|---|
| **Zero pending (caught up)** | No unreviewed recordings | Empty state with warmth: Fraunces display-md "You're caught up" + illustration (subtle, no emoji, no confetti) + count of reviews completed this week | Browse students, check schedule | "You're caught up. 23 reviews this week — nice work." |
| **1–10 pending (normal)** | Ack rows with status=acknowledged, teacher_feedback is null | Ordered list (oldest first), each row = student name + assignment title + recording duration + time since upload + waveform thumbnail + "Review" button | Click "Review" on oldest | (standard list rendering) |
| **11+ pending (grouped)** | Large queue | Same list with a filter bar at top: by student, by assignment, by age. Default view still oldest-first. Filter persists in URL. | Filter or grind through | "12 pending — showing oldest first. Filter by student." |
| **Stale pending (>48h)** | Ack row older than 48h without feedback | Row rendered with amber primary warning border (the one exception to "no colored borders" per DESIGN.md § sidebar nav note, explicitly extended here) + "2 days old" badge | Review urgently | "Bach Invention — Sarah — 2 days old" |
| **New arrival (realtime)** | Supabase Realtime emits a new ack row event | New row slides in from top with amber glow per DESIGN.md § Motion ("the ONE moment the interface celebrates itself"). Toast optional: "New practice from Sarah." | Continue reviewing | "New practice from Sarah — 4:32" |
| **Reviewing (in-progress)** | Teacher clicks "Review" on a row | Modal/split-pane with full waveform player + text feedback textarea + 1–5 rating selector. Side-nav previews next 3 in queue. | Submit feedback | (form UX) |
| **Review submitted** | Feedback saved | Row removed from pending list with exit animation (ease-exit 250ms) + toast "Feedback sent to Sarah" | Auto-advance to next | "Feedback sent. 11 left." |
| **Loading failure** | API error fetching queue | Inline error card + retry button + offline-mode indicator | Retry | "Couldn't load the queue. Check your connection and retry." |

**Empty state is THE critical moment** — it's the teacher's reward for being on top of their studio. If we show "No results" SaaS slop, the teacher feels like they're using a CRM. If we show "You're caught up — 23 reviews this week," the teacher feels like they're doing their job well. Do NOT let implementation default to "No items found."

#### Flow 3 — Student streak (Slice 20 / #37 web, Slice 22 / #39 mobile)

Gamification lives or dies on specificity. `streak_service` port from Polymet's `PracticeStreakCalculator`.

| State | Trigger | What the student sees | Primary action | Copy example |
|---|---|---|---|---|
| **Zero streak (first-time)** | No recordings ever uploaded | Large display-xl "0" in muted color + "Start your first streak today" prompt → record button | Start recording | "Ready for day 1?" |
| **Active streak** | Practiced today | display-xl streak number in `--primary` (the studio's brand amber by default) + "days" label + today's tick in the 7-day grid (mobile) | See details, keep going | "47 days" |
| **At-risk (practiced yesterday, not today)** | Last practice was yesterday, today is not yet recorded, local time after 6pm | display-xl number in `--primary` + amber warning row: "Don't lose your streak" + record CTA | Record before midnight | "Don't lose your 47-day streak — practice before midnight." |
| **Grace window (streak-alive-if-practice-now)** | Same as at-risk, after 9pm | Same + urgency nudge | Record now | "1 hour left to save your streak." |
| **Broken (48h+ since last practice)** | `streak_active === false` | display-xl current=0 + muted "Longest: 47 days" below in body-sm + "Start a new streak today" prompt | Record to restart | "New day 1 starts whenever you're ready." |
| **Milestone (7d / 30d / 100d / 365d)** | Day count hit on today's recording | Celebration moment with spring motion per DESIGN.md § Motion + share-worthy visual (just a screenshot, no actual social share in Stage 1). Fires notification via Slice 23 / #40. | Continue | "30 days in a row. You're committing." |
| **Streak frozen (pending-deletion child)** | Child is in COPPA 15-day grace | Streak displayed read-only, muted color, with banner above explaining | Parent cancels deletion | "Streak paused while account is pending deletion." |

**Milestone copy rules:** Never "AMAZING!!!" Never emoji. Never "You rocked it!" Warm, specific, respectful of the student's actual effort. Fraunces display font for the number makes it feel weighty.

#### Flow 4 — COPPA 15-day grace deletion (Slice 31 / #48)

Legally fraught. Every state must be crystal clear and every action reversible until T-0.

| State | Trigger | What the parent sees | Primary action | Copy example |
|---|---|---|---|---|
| **Normal** | Child account active, no deletion scheduled | Standard parent dashboard, no deletion UI surfaced | — | — |
| **Delete-requested (confirmation)** | Parent clicks "delete my child's data" in child settings | Modal with full disclosure: what will be deleted, when (T+15 days), how to cancel. Typing "DELETE" to confirm. | Type "DELETE" to schedule, or cancel | "Permanently delete Sarah's account on 2026-04-30? This will remove all practice recordings, assignment history, and messages. You can cancel anytime before that date. Type DELETE to schedule." |
| **Scheduled (grace period)** | `child.deletion_scheduled_at` is set | Top banner (not modal) on every parent + child page: "Sarah's data will be deleted on [date]. [Cancel deletion]" in destructive-tinted background at low opacity | Cancel anytime | "Sarah's data will be deleted on April 30. Cancel deletion" |
| **T-7 reminder** | 7 days before deletion | Same banner + email sent via Postmark. Banner text updates with countdown. | Cancel or let expire | "Sarah's data will be deleted in 7 days. Cancel deletion" |
| **T-1 final reminder** | 24 hours before deletion | Banner text: "Final notice — deletion happens in 24 hours" + email. Banner turns destructive color (not just tinted). | Cancel or let expire | "Final notice: Sarah's data will be deleted in 24 hours. Cancel now" |
| **T-0 processing** | pg_cron fires | Brief banner: "Deleting..." + spinner. Usually <30s. | Wait | "Deleting Sarah's account..." |
| **Deleted** | Hard-delete complete | Parent redirected to "account removed" confirmation page. Email sent. Audit row written to `coppa_deletion_log` with no PII. No way to see the child's old data — even in superadmin impersonation. | Navigate away | "Sarah's account has been permanently deleted. You will no longer see their data in DailyRiff. If you believe this was an error, email privacy@dailyriff.com." |
| **Cancelled** | Parent clicks "cancel deletion" anytime T-15 → T-0 | Banner removed, `deletion_scheduled_at` cleared, toast confirmation | Resume normal use | "Deletion cancelled. Sarah's account is active." |
| **Teacher view (pending-deletion badge)** | Teacher opens student with `pending_deletion=true` | Student row shows "pending deletion" badge (amber/destructive, not shouting) + date. Recording playback still allowed during grace per PRD § Q18. | Note and continue | "Pending deletion — April 30" |

**Never**: no toast-only feedback on scheduling (too easy to misclick and miss), no hidden "are you sure" flows, no way to bypass the typed "DELETE" confirmation. The type-to-confirm is a deliberate speed bump because the action is irreversible after T-0.

#### Flow 5 — Per-studio branding runtime (Slice 8 / #25 setup, affects every studio-tenant page)

Every student and parent surface renders with the studio's chosen `--primary` color. First paint must not flash the default amber then swap to the studio's color.

| State | Trigger | What the user sees | Implementation detail |
|---|---|---|---|
| **SSR render** | Any page load under `/studio/[slug]/*` route group | Server-side layout reads `studios.primary_color` + `studios.display_name` + `studios.logo_url` and injects `<style>` with the override BEFORE any HTML body. No flash. | `apps/web/src/app/(studio)/[slug]/layout.tsx` reads from cache via server component, injects `<style>:root { --primary: ${hsl}; --ring: ${hsl}; }</style>` in the `<head>`. |
| **Logo loading** | `studios.logo_url` is set | `next/image` with `priority` flag on the studio layout header + placeholder color matching the studio primary | Shadcn `Skeleton` with primary background at 10% opacity while loading |
| **Logo missing / broken** | `studios.logo_url` is null, or R2 returns 404 | Fallback: display_name in Fraunces display-sm (32px) as a text-logo | No broken-image icon ever |
| **Color update (live)** | Studio owner changes color in settings | Optimistic update + `router.refresh()` + toast. Student/parent layouts re-render on next navigation. No WebSocket push — color changes are rare enough that next-nav is fine. | — |
| **DailyRiff default** | Non-studio routes (marketing, superadmin, onboarding pre-signup) | Default amber `hsl(30 85% 48%)` per DESIGN.md | — |
| **Contrast violation (theoretical)** | Studio picked a color outside the 12-swatch palette (shouldn't happen, but defend) | Server-side validation rejects; admin alert | `platform_settings` contains the allowlist of 12 Radix hex values; any other value fails validation at the API layer |

**The 12-swatch allowlist is enforced at the database + API layer, not the UI.** Even if a malicious client bypasses the picker, the backend rejects any `primary_color` not in the allowlist. This is the defense against both mistakes and contrast-regression attacks.

#### Superadmin distinct color

The superadmin surface does NOT use the default DailyRiff amber. It uses **deep teal `hsl(180 60% 35%)`** (`--chart-2` from DESIGN.md). Rationale: during impersonation, Rollin needs instant visual confirmation of "I'm in operator mode" vs "I'm inside Studio X's branded mode." The distinct color also builds muscle memory that superadmin surfaces are high-stakes (impersonation, platform settings, secret rotation) and not the studio-facing product.

Implementation: superadmin route group at `apps/web/src/app/(superadmin)/layout.tsx` injects `<style>:root { --primary: 180 60% 35%; --ring: 180 60% 35%; }</style>` server-side, overriding the default. Superadmin pages never inherit a studio's `--primary` (no per-tenant theming on operator surfaces).

#### Marketing homepage visual policy

**No hero image in Stage 1.** The marketing homepage hero is pure Fraunces typography + warm neutrals + a single well-placed primary CTA. No stock photos (blacklist). No custom illustration (budget). No abstract blobs (slop). The brand voice IS the image.

Rationale: the three alternatives each fail. Stock photos scream generic edtech and hit the DESIGN.md blacklist. Custom illustration is $1–3k + lead time + risk of generic-edtech-illustrator output. Abstract composition via AI risks the same slop we codified against.

The deliberate quiet is also a differentiation signal. Every competitor uses a cheerful stock photo of a smiling child at a piano. DailyRiff doesn't. That alone sets a tone.

Revisit post-launch once real studios are using the product and we can use actual (permissioned) studio photography with real teachers and students. Stage 2 decision, not Stage 1.

#### Dark mode defaults per persona

Dark mode is user-toggleable everywhere via `next-themes` (web) and Expo's appearance API (mobile). But the default at first login differs by persona:

| Persona | Default | Rationale |
|---|---|---|
| **Student web (13+)** | Light | Web users are sometimes parents of under-13 looking at their kid's dashboard during the day. Light is safer default. Toggleable. |
| **Student mobile (Expo)** | **Dark** | Teens practice in evenings and at night. Mobile screens at night in light mode are harsh. Toggleable. |
| **Parent web** | Light | Daytime schedule/admin context. Toggleable. |
| **Teacher web** | Light | Dashboards are data-dense; light is easier for table scanning. Toggleable. |
| **Superadmin web** | Light | Operator surface; parity with teacher. Toggleable. |
| **Marketing + legal** | Light | First impression is brand-defining; warm neutrals + amber read best on light. Respects `prefers-color-scheme` though — if visitor's OS is dark, marketing loads dark. |

Dark mode toggle persists per-user in the user settings row (new column `users.theme_preference` enum {'light','dark','system'} default 'system' for non-student-mobile, default 'dark' for student-mobile).

### Emotional moments

Five moments where design weight matters more than feature completeness. Implementation must preserve these, not flatten them into generic UI. Each is a named product moment — not decoration, not polish, part of the functional spec.

| # | Moment | Persona | What they feel | What implementation must preserve |
|---|---|---|---|---|
| 1 | **First record button tap** | Student (mobile especially) | Scary + excited. First time producing visible evidence of practice. | The "Start recording" button is the largest single UI element on the dashboard, in `--primary`, with keyboard-scale tap target. Mic-permission dialog has a plain-language explainer card, not just the browser default. The transition from permission-granted to recording-started is immediate — no interstitial, no toast, straight to the waveform. |
| 2 | **"You're caught up"** | Teacher | Pride + relief. The reward for keeping up with the studio. | Empty state uses Fraunces display-md, warm language ("You're caught up. 23 reviews this week — nice work."), never "No items found." Review count is real and tabular-nums. This is the moment the PRD most strongly refuses generic SaaS defaults. |
| 3 | **First 7-day streak milestone** | Student | "I'm actually doing this." The first concrete proof of commitment. | Spring ease motion (DESIGN.md § Motion) fires once, then never again until the 30-day milestone. Notification sent via Slice 23 / #40. Copy respects the achievement ("7 days in a row. You're committing.") — never cartoonish, never emoji, never exclamation marks. Fraunces display-xl on the streak number is non-negotiable. |
| 4 | **COPPA delete confirmation** | Parent | Gravity. Final decision about their child's data. | Type-to-confirm speed bump (must type "DELETE") is non-negotiable even if it adds a step. Copy names the exact date, what will be deleted, and the cancel window. No toast-only feedback, no "one-click undo," no A/B test of removing the typed confirmation. The friction is the feature. |
| 5 | **Studio color flows through** | Studio owner | "My studio. My product." Proof DailyRiff isn't generic. | During onboarding (Slice 8 / #25), after the studio owner picks a color from the 12-swatch palette, the **next screen renders in that color** — not a preview, not a modal confirmation, the actual next step of onboarding uses the studio's `--primary`. Server-side SSR injection so there's no flash. This is the single moment that differentiates DailyRiff from generic edtech SaaS in the first 5 minutes of use. |

These are **functional requirements**, not design polish. A slice that ships with the interaction working but the emotional moment flattened (generic empty state, no spring ease, toast-only confirmation, preview-instead-of-live color) has not met acceptance criteria.

### Responsive commitments per persona

Per-persona responsive policy. Breakpoints match DESIGN.md § Layout (sm 640, md 768, lg 1024, xl 1280, 2xl 1536). "Desktop-first" in the PRD never means "broken on mobile" — it means what's committed below.

| Persona | Mobile (<lg) policy | Rationale |
|---|---|---|
| **Teacher** | **Pending-reviews queue must work fully on mobile.** Audio playback, feedback textarea, 1–5 rating selector, realtime updates, and the "review oldest" CTA are first-class on mobile. Everything else (payment ledger, lesson editor, student detail tables, studio profile) renders as single-column stacks that are *usable* (no clipping, scroll works, forms submit) but not *optimized*. No mobile-specific layouts or gestures for non-pivot surfaces. | Teachers will review recordings on phones during evenings and weekends. The product pivot has to work there. Everything else can wait for desktop because teachers do their business ops at a desk. |
| **Superadmin** | **Operational health strip must work on mobile.** The "is anything broken overnight" view (Slice 6 / #23 hero) is reachable and readable on a phone. Every other superadmin page (studios list, user detail, impersonation, platform settings, verification queue, waitlist, employees) is desktop-required — mobile shows a banner: "This page needs a larger screen. Switch to desktop to continue." | Rollin will check health from phone (possibly at 2am, woken by BetterStack). All other ops work is deliberate and belongs at a desk. Not every page needs to be responsive. |
| **Parent** | **Mobile-first.** Every parent page fully responsive through all breakpoints. | Parents check throughout the day from phones. The dashboard, schedule view, messages, and COPPA delete flow are all equally important on mobile. |
| **Student web (13+)** | **Mobile-first.** Record flow, streak display, assignments, messages all fully responsive. | Teens open on phones and laptops roughly equally. Record flow especially needs mobile-web parity because the Expo app is the preferred path but web must work if mic permission grants. |
| **Student mobile (Expo)** | **Phone-only.** Tablet rendering is acceptable but untested in Stage 1. | The 5-screen Expo app is a focused mobile experience by definition. |
| **Marketing / legal / public** | **Mobile-first.** Marketing homepage, about, contact, privacy, ToS, accessibility all fully responsive. Hero composition may change at breakpoints but brand+headline+CTA must be legible and actionable at every size. | Visitor traffic is >50% mobile; conversion depends on mobile-first design. |
| **Studio onboarding (Q14a)** | **Desktop-first, tolerant mobile.** Primary flow designed for desktop; mobile renders single-column stacks that complete the flow but don't fight it. Logo upload allowed on mobile via `capture="environment"` file input. | Studio owners sign up deliberately at a desk. Mobile fallback exists for the rare phone-only signup. |

**Enforcement:** Slice 18 / #35 Playwright smoke matrix runs Chromium+Firefox+WebKit at a mobile viewport (iPhone 14 Pro, 393×852) AND a desktop viewport (1440×900) for every persona's primary flow. A failure at either viewport blocks merge.

### Engineering commitments (from `/plan-eng-review`)

#### Recording upload — R2 multipart semantics (F2)

"Chunked resumable upload" means **R2 S3-compatible multipart upload**, not one presigned PUT. Three-step flow:

1. `POST /recordings/upload-initiate` — client sends `{assignment_id, duration_seconds_estimate, mime_type}`. Server mints a multipart upload_id via R2, returns `{upload_id, part_urls: [presigned for parts 1..N], chunk_size_bytes}`. Creates a row in new `recordings_uploading` table tracking upload state.
2. Client uploads parts in parallel (up to 3 concurrent), each to its presigned part URL. On any failure, `POST /recordings/upload-part-retry {upload_id, part_number}` mints a new presigned URL for that specific part. Max 5 retries per part before hard failure.
3. `POST /recordings/upload-complete {upload_id, parts: [{number, etag}]}` — server finalizes the multipart upload against R2, writes the final row to `recordings` with `uploaded_at = now()`, deletes the row from `recordings_uploading`. The `auto_acknowledge_assignment` trigger fires at this point.

**Constants:** chunk size 10 MB, max 60 parts (600 MB absolute ceiling, well above 60-min AAC), 5-min TTL per part URL. Concurrency 3 parts in flight at once.

**New table `recordings_uploading`:** `{upload_id, student_id, assignment_id, mime_type, started_at, last_activity_at, parts_uploaded int, parts_total int, status enum(in_progress, failed, completed)}`. Garbage-collected by `pg_cron` after 24h of inactivity; R2 multipart aborted via `AbortMultipartUpload` API.

**Mobile offline cache:** when `navigator.onLine === false` or first part upload fails, recording stays in the Expo mobile local cache (10-recording limit per Polymet constraint). On reconnect, the mobile client resumes by calling `upload-initiate` fresh (existing upload_ids are allowed to be abandoned — R2 multipart cleanup handles the orphaned parts).

#### `auto_acknowledge_assignment` trigger — disambiguation (F1)

Polymet's trigger assumed one active assignment per student. Stage 1 supports multiple concurrent active assignments. Resolution: **the recording row carries an explicit `assignment_id` FK set at `upload-initiate` time**. The student picks which assignment this practice is for BEFORE recording starts (default = soonest-due active assignment). The trigger flips **only the one ack row** matching `(assignment_id, student_id, recording_id)`.

UI implication for Slice 11 / #28: student-facing record button is always scoped to an explicit assignment. If a student has multiple active assignments, the dashboard shows them a picker before the mic-permission step. Default selection: soonest due. Override affordance: "Practicing something else? Pick an assignment." Only 1 click to start recording the default case.

Trigger idempotency: if the trigger fires twice for the same `recording_id` (e.g., a fast retry write), the second call is a no-op because the ack row is already `acknowledged`. No concurrency hazard.

#### Notification fan-out — queue pattern (F3)

`NotificationService.send()` has two entry paths:

- **Synchronous path** (direct FastAPI handlers) — when a notification is a direct consequence of a user action (teacher sends a message, student submits a recording). Sends immediately via `httpx.AsyncClient` fan-out. Existing Stage 0 pattern preserved.
- **Queue path** (pg_cron-originated events) — when a notification is triggered by a time-based event (lesson reminder, streak milestone fired by cron, weekly digest). Inserts a row into `notifications_pending`. A new `notifications_drain` pg_cron job runs every 10 seconds, selects up to `platform_settings.notifications_drain_batch_size` (default 20) rows in `notifications_pending` with `status=pending`, dispatches via `NotificationService.send()`, marks rows `status=sent` or `status=failed` with retry count.

Max retries on the queue path: 3 per notification (exponential backoff — 1min, 5min, 30min). After 3 failures, row marked `status=failed` and written to `activity_logs` with the error. No silent drops.

New table **`notifications_pending`:** `{id bigserial, user_id, event_type, payload jsonb, scheduled_for timestamptz, status enum(pending, sending, sent, failed), attempt_count int default 0, last_attempt_at, last_error text, created_at}`. Indexed on `(status, scheduled_for)` for drain efficiency.

#### Supabase Realtime subscription quota + fallback (F4)

Supabase Pro tier Realtime quota: 200 concurrent connections. At beta scale (5 studios × 20 students × 2 devices × teacher + parent) this could exceed quota. Mitigation:

- **Subscription consolidation:** one Realtime channel per user (`user:{user_id}`), not per resource. All events for a user (messages, pending-review updates, notification pushes) multiplexed via a `type` field in the payload. `realtime_service.py` on the backend fans out internally.
- **Quota monitoring:** Supabase built-in alert at 80% of connection quota → P1 alert per Q27 observability. Also exposed on the superadmin platform-settings page as a read-only metric.
- **Polling fallback:** if a client's Realtime subscription fails (`realtime.connect()` returns error or `channel.state === 'closed'` for >30s), the client falls back to polling via TanStack Query with a 30-second `refetchInterval`. This preserves functionality at the cost of latency. The fallback is automatic and transparent to the user.

This adds a new `realtime_service.py` module (server-side multiplexing) and a `useRealtimeWithPollingFallback` hook (client-side).

#### Alembic migration ordering across parallel slices (F5)

Linear Alembic revision IDs cause guaranteed merge conflicts when 25+ slices add migrations in parallel. Resolution:

- **Timestamp-prefixed filenames:** `alembic/versions/20260415_1432_studios.py` instead of `0002_studios.py`. Alembic supports any filename as long as the `revision` / `down_revision` IDs inside link correctly.
- **`down_revision` always points to `head` at branch-cut time.** The first slice to merge after `head` moves rebases its migration against the new head. The second slice does the same. If two slices merge in parallel, git marks a conflict on `alembic/versions/` — the second-to-merge PR rebases.
- **`alembic merge` for genuine branching:** if two migrations genuinely must coexist (unusual), use `alembic merge -m "merge_slices_X_Y"` to produce a merge migration. This is the Alembic-sanctioned pattern.
- **CI check:** pre-merge, CI runs `alembic check` which fails if there are multiple heads. Forces the second-to-merge PR to produce a merge migration or rebase. New CI step in the `api` job.

This is a Stage 0 infrastructure concern Stage 1 exposes at scale. Rollin owns this — don't let a slice author miss it.

#### `packages/api-client` codegen conflict resolution (F6)

Same problem as F5 for `openapi.snapshot.json`. Resolution:

- Developers **never** hand-edit `openapi.snapshot.json` or `packages/api-client/src/types.gen.ts`.
- CI `api` job regenerates the snapshot on every PR. If `git diff --exit-code apps/api/openapi.snapshot.json` fails, CI commits the regenerated snapshot via bot and re-runs codegen job.
- Merge conflicts on the snapshot: the second-to-merge PR rebases and regenerates in one step (`pnpm --filter api regenerate-openapi && pnpm --filter api-client generate && git add apps/api/openapi.snapshot.json packages/api-client/src/`).
- CI fails if `packages/api-client/src/types.gen.ts` is hand-edited (diff-detectable since it's auto-generated).

Applies to Slice 18 / #35 CI upgrades.

#### RLS regression testing meta-coverage (F7)

Stage 1 adds 15+ tenant-scoped tables. A new table can ship without RLS coverage. Resolution:

- New meta-test `apps/api/tests/integration/test_rls_coverage.py` runs two introspections:
  1. `SELECT table_name FROM information_schema.columns WHERE column_name = 'studio_id'` → list of tenant-scoped tables
  2. `SELECT tablename FROM pg_policies` → list of tables with at least one RLS policy
- Asserts every tenant-scoped table has an RLS policy AND a corresponding test function in `test_rls_isolation.py` (detected via test name pattern `test_rls_isolation_{table_name}`).
- Fails CI if any tenant-scoped table is missing either.
- New tables that should NOT be tenant-scoped (platform-level tables like `waitlist_entries`, `dailyriff_employees`, `platform_settings`) are explicitly listed in an `RLS_EXEMPT_TABLES` constant in the meta-test.

This is the Stage 1 analog of Stage 0's single `test_rls_isolation.py`. Applies to Slice 3 / #20 (studios — first tenant-scoped table, sets the pattern).

#### COPPA deletion cascade (F8)

When a child account hard-deletes at T-0, `ack.teacher_feedback` referencing the deleted `recording_id` must cascade. Schema constraint:

- `assignment_acknowledgements.recording_id` FK: `ON DELETE CASCADE`
- `recordings.student_id` FK: `ON DELETE CASCADE`
- `parents.children[]` junction: `ON DELETE CASCADE`
- `messages.sender_id` / `messages.recipient_id` FK: `ON DELETE CASCADE` (when sender or recipient is the deleted child)

Feedback text is lost at T-0. This is correct under COPPA — the feedback is derived child data and must be deleted. Audit row in `coppa_deletion_log` records counts of all cascade-deleted rows for forensic purposes (no PII, just `{db_rows_count, r2_objects_count}`).

Applies to Slice 31 / #48.

#### Impersonation idle timeout (F9)

Superadmin sessions: 8h max / 1h idle. Impersonation sessions within a superadmin session: **15min idle timeout**, independent of the outer session. After 15 min idle, the impersonation session ends automatically via `pg_cron` sweep + client-side ping check; the outer superadmin session continues.

Rationale: impersonation is the highest-stakes operator action (temporary god-mode against another user's data). Lower idle timeout is friction Rollin should welcome.

Applies to Slice 30 / #47.

#### Expo push token rotation (F10)

Same pattern as WebPush 410-gone but for Expo push:
- When Expo Push Service returns `DeviceNotRegistered` in the receipts API, `NotificationService` deletes the row from `user_push_subscriptions` (matching `channel='expo'` and `token=<rotated token>`)
- Tested explicitly with a mocked Expo response in `test_notification_service.py`

Applies to Slices 13 / #30 (messaging wires notifications) and 23 / #40 (notification extension).

#### Graceful degradation policy per dependency (F11)

When a dependency is down, the product must fail in a predictable, user-visible way — not hang, not silently drop data, not succeed-but-lose-state. Committed policy per dependency:

| Dependency | Failure mode | User-facing behavior | Retry strategy | Alerting |
|---|---|---|---|---|
| **Supabase GoTrue** (auth) | Slow / down | Login form shows "Sign-in is taking longer than usual — retrying..." after 3s; hard fail after 15s with "Sign-in service is unavailable. Try again in a minute." | 3 retries with exponential backoff | Sentry error rate alert per Q27 |
| **Supabase Postgres** | Slow / down | API returns 503 with `Retry-After: 30`; web UI shows "DailyRiff is temporarily unavailable. We're on it." banner | No client retry (the DB is authoritative) | BetterStack P0 |
| **Supabase Realtime** | Slow / down | Client falls back to polling (F4 above) automatically, no user-visible degradation | 30s poll interval | Supabase quota + subscription failure alerts |
| **R2 (presign)** | Slow / down | Recording upload flow shows "Upload service is unavailable. Your recording is saved locally and will upload when service returns." Local cache preserved on mobile. | 5 retries over 5 minutes | Cloudflare dashboard + Sentry |
| **R2 (playback)** | Slow / down | Recording playback shows "Playback unavailable — try again." No fallback (no local cached playback). | 3 retries automatic + manual retry button | Cloudflare dashboard |
| **Postmark** | Slow / down | Email dispatch rows marked `status=failed` with error, retried via notifications_pending queue. User-facing flows (onboarding, COPPA) proceed and show a banner: "We couldn't email [X]. Check your inbox or contact support." | 3 retries over 30 minutes | Postmark webhook + P0 on bounce rate >5% |
| **Expo Push** | Slow / down | Push notification rows marked failed in queue. In-app banner surfaces at next login. Non-critical — user experience degraded but loop continues. | 3 retries | Queue drain rate monitoring |
| **Stripe** (COPPA VPC) | Slow / down | VPC charge flow shows "Payment service is unavailable — please use the signed-form escape hatch." The escape hatch is the fallback. | No retry | Stripe webhook delivery monitoring |
| **Stripe webhook** | Replay / duplicate | `idempotency_log` catches duplicates silently. User sees no effect. | — | Stripe dashboard alerts |
| **hCaptcha** | Slow / down | Public forms (waitlist, signup) show "Verification is unavailable — please try again in a moment." Hard-block signup attempts. | Manual retry only | Sentry error rate |
| **pg_cron** (silent failure) | Scheduler broken | Heartbeat (`operational_alerts`) detects missing writes and alerts via BetterStack P1 after 20 min | — | BetterStack heartbeat uplink |

**Rule:** every user-facing error message names the problem, the consequence, and the action (matches DESIGN.md voice rule). Never "Something went wrong."

### Cross-cutting Stage 1 principles

- **Design system enforcement**: every UI slice's acceptance criteria implicitly include `docs/DESIGN.md` § Aesthetic Direction / Anti-slop rules. Reviewers reject PRs that ship any blacklist pattern. The 10 hard-reject patterns are: (1) purple/violet/indigo gradients, (2) 3-column icon-in-colored-circle feature grids, (3) centered-everything with uniform spacing, (4) uniform bubbly border-radius on every element, (5) decorative blobs / floating SVG confetti / wavy dividers, (6) emoji as design elements, (7) colored left-border on cards (exception: active sidebar nav items only), (8) generic hero copy patterns ("Welcome to DailyRiff," "Unlock the power of," "Your all-in-one"), (9) cookie-cutter section rhythm (hero → 3 features → testimonials → pricing → CTA), (10) stock photos of smiling children at pianos. Slice 7 / #24 (marketing homepage) is the highest-risk surface because shadcn homepage starters default to pattern #2 — extra review scrutiny there.
- **Platform-settings principle (Q24)**: every tunable knob is in `platform_settings`, editable from the superadmin UI with 30-sec TTL cache. Exception: vendor-owned values are read-only mirrors.
- **Expand-then-contract migrations (Q19.2)**: every migration must be safe to run *before* the new API code deploys. Forward-fix only; no `alembic downgrade` in prod.
- **Audit trail first**: impersonation, platform-settings edits, secret rotations, COPPA deletions, R2 deletes, MFA events all write to `activity_logs` before anything else.
- **Default-deny authorization**: `can_play_recording` is the template. Every sensitive op has a single centralized policy function, unit-tested across the persona × relationship × state matrix.
- **Two tools, two scopes for DB**: Alembic owns app tables; `supabase db push` with `supabase/migrations/*.sql` owns Supabase-native objects (RLS, auth schema, `supabase_functions` triggers).
- **R2 credential scoping (Q25)**: FastAPI credential has read/write/presign ONLY. Delete permission lives only with the `pg_cron` hard-delete worker. Two credentials, two rotations, two audit trails.
- **Soft-delete everywhere that touches user content**: all deletes set `deleted_at` first; `pg_cron` hard-deletes after grace window.
- **Timezone canon (Q22)**: all timestamps `timestamptz`; display resolves against `studios.timezone` with TZ abbreviation always visible. `en-US` only — no i18n framework.

### Rate limiting, abuse prevention, compliance

- **Layer A (Cloudflare)**: Bot Fight Mode, WAF OWASP ruleset, 50 req/10s per IP on `/api/*`, Under Attack Mode as break-glass.
- **Layer B (FastAPI `slowapi`)**: global defaults 100/min authenticated, 30/min anonymous; per-route overrides for `/auth/*`, `/recordings/upload-url`, `/messages`, `/waitlist`, `/coppa/vpc-charge`, `/auth/password-reset`. All tunable live.
- **Layer C (Supabase GoTrue)**: signup 10/hr/IP, signin 10/5min/IP, password reset 5/hr/email, magic link disabled. Mirrored read-only in superadmin settings.
- **Layer D (business-rule caps)**: 50 recordings/student/day, 200 messages/user/day, 1 waitlist/email + 3/IP lifetime, 20 push/user/day, 3 COPPA VPC/parent/24h.
- **Webhook hardening**: Stripe signature + 5-min timestamp tolerance, Postmark signature, `idempotency_log` dedupes.
- **Enumeration defense**: password reset returns 200 with constant latency regardless of email existence; signup emails the existing user instead of disclosing.
- **hCaptcha** on waitlist + public signup forms.
- **Stripe Radar** enabled by default.

### Security, secrets, 2FA, impersonation

- **Superadmin TOTP required** (Q20). Hard-block login without enrolled TOTP. No SMS. 8h max session + 1h idle. Failed-auth alerting: 3 failures in 15 min emails all owners. Every MFA event writes to `activity_logs`. Break-glass runbook is a launch prerequisite.
- **Studio-side TOTP optional but nagged**. Parent/student: no 2FA in Stage 1.
- **Superadmin bootstrap (Q23)**: one-shot `apps/api/scripts/bootstrap_first_owner.py` with sanity checks (employees count zero, referenced auth user exists, TOTP already enrolled via GoTrue's native flow). No middleware backdoors, no Alembic data migrations, no undocumented SQL.
- **Secret rotation (Q28)**: 1Password is the canonical store; Railway env + GH secrets are derived copies. `secret_rotation_schedule` table tracks cadence; daily `pg_cron` warns on due-soon. Full Stage 1 secret inventory in the tracker.
- **Impersonation (Q17.4)**: silent default with delayed email notification; required `reason`; live-mode override shows red banner; target's Account Access Log is read-only visible in settings. Scope-restricted — cannot change password, delete account, change email/2FA, authorize OAuth, delete child content.
- **Recording playback auth (Q18)**: 5-min signed URLs, FastAPI never proxies bytes, single policy function, impersonation playbacks audited.

### Observability + incident response (Q27)

- **BetterStack free tier** as uptime backbone: 10 HTTP monitors @ 30s, flap protection, phone call + mobile push + email for P0, public status page at `status.dailyriff.com`.
- **Sentry free tier** with error replay masked by default (`maskAllText: true`, `maskAllInputs: true`, `blockAllMedia: true`), `replaysSessionSampleRate: 0`, `replaysOnErrorSampleRate: 1.0`. Parent/student route groups have replay disabled entirely.
- **PostHog** event tracking only (`disable_session_recording: true`). Event properties carry only IDs/timestamps/enums — never names, emails, or user-generated text.
- **Supabase built-in alerts** for DB disk/CPU/quota.
- **Application heartbeat**: `pg_cron` self-check every 10 min + FastAPI endpoint BetterStack heartbeats every 5 min. Defense against silent cron failure.
- **Incident SLA**: P0 15 min waking / 30 min overnight; P1 2 hrs waking; P2 weekly review. Vacation coverage explicit and disclosed in ToS.
- **Stage 1 observability cost: $0** on top of the $25/mo Supabase Pro.

### Environments + CI/CD

- **`ci.yaml`**: 4 jobs (api, codegen, web, mobile-unit) preserved from Stage 0. Schemathesis upgraded to blocking per #15. New Stage 1 jobs: contract tests per router, Playwright cross-engine smoke (Chromium + Firefox + WebKit), axe-core a11y on every critical page, Lighthouse CI a11y ≥95 per page.
- **Staging auto-deploys** on merge to master: `alembic upgrade head` → `supabase db push` → Railway deploy → smoke test → re-seed Polymet + edge-cases.
- **Prod deploys** gated on `api-v*` tag → DDL preview artifact → GitHub environment approval → apply → deploy.
- **Mobile CI/CD (Q19.1)**: `mobile-v*` tag → `eas build --platform all --profile production` → `eas submit` to TestFlight + Play Internal. `mobile-hotfix-*` tag → `eas update` OTA. Per-PR validation stays light (existing `mobile-unit` + `codegen` only).
- **Supabase migration split**: Alembic for FastAPI app tables; `supabase db push` for Supabase-native objects (RLS, auth schema, triggers).

### Email + transactional delivery (Q17.2)

- **Postmark** for transactional delivery (best-in-class deliverability, transactional-only shared IP pool).
- **React Email** for template authoring.
- Stage 1 volume estimate ~1k/month.
- Marketing email (weekly digest, waitlist nurture) uses a separate provider in Stage 2–3 — NOT sent through Postmark.
- Emails go out as `"{Studio Name} via DailyRiff" <hello@dailyriff.com>`.
- DNS SPF/DKIM/DMARC configured; Mail-Tester ≥9/10 required pre-launch.

### Data seeding (Q17.1)

- `apps/api/scripts/seed_polymet.py` — verbatim Mitchell Music Studio mock data.
- `apps/api/scripts/seed_edge_cases.py` — synthetic generator for pending-deletion children, mid-conversion teens, divorced-family multi-parent students, recording-upload-failed states.
- Makefile toggles: `make seed-polymet-only`, `make seed-rich`.

### Browser + device support (Q26)

- **Desktop**: Chrome, Edge, Firefox, Safari — last 2 stable majors (rolling window).
- **Mobile web**: iOS Safari 15+, Android Chrome last 2 stable.
- **Expo mobile**: iOS 15.1+, Android 7.0 / API 24+.
- **Recording capture**: MIME negotiation with hard-fail error message.
- **Playwright**: Chromium + Firefox + WebKit smoke; full functional suite on Chromium only.
- **Manual release gate**: real Safari + real Mobile Safari + real Android Chrome before every release.
- **Explicitly NOT supported**: IE, Opera Mini, Samsung Internet (untested), Firefox ESR (unless inside window), headless user contexts.

### Accessibility (WCAG 2.1 AA)

- `jsx-a11y` at error level (blocks build).
- axe-core via Playwright on every critical page.
- Lighthouse CI ≥95 per page.
- 12-color palette AA-vetted (4.5:1 normal, 3:1 large) against both white and black.
- Semantic HTML, keyboard nav, form accessibility, live-region announcements, alt text, 200% zoom/reflow, `prefers-reduced-motion`, audio-player keyboard controls + ARIA.
- Pre-launch manual audit: keyboard + NVDA + VoiceOver per persona (~4–6 hrs each).
- Every Stage 1 GH issue has the acceptance criterion: *"axe-core AA passes, keyboard-only nav verified."*

### Cookie / tracking compliance

- **NO blocking consent banner** in Stage 1. US-only, zero advertising cookies → GDPR does not apply.
- **CCPA/CPRA safeguards**: "Your Privacy Choices" footer link → `/legal/privacy-choices` page with cookie table, opt-out toggles, disclosure, contact; `navigator.globalPrivacyControl` auto-respected on mount; full cookie table in privacy policy.
- **Upgrade path** documented for when EU users come into scope.

### R2 backup + DR (Q25)

- **Tier 1**: R2 object versioning with 30-day retention lifecycle. Cost ~$0.75/mo.
- **Tier 2**: application-level soft delete everywhere (`recordings.deleted_at` + `pg_cron` hard-delete after grace).
- **Tier 3 (cross-cloud to S3 Glacier Deep Archive)**: deferred to Stage 2.
- **COPPA carve-out**: privacy policy documents the 30-day versioning window as a recoverable-deletion safety-net. Legal review required; fallback is 1-day versioning retention for COPPA-flagged objects if legal says no.

### Beta rollout (Q29)

- 3–5 studios hard cap, personal network + warm intros, 6–12 week window.
- White-glove support: 30–60 min Zoom onboarding (recorded), Slack Connect per studio, weekly 15-min check-ins for 4 weeks, manual data entry via Supabase Studio, zero-friction bug reporting, public status page.
- Graduation criteria: ≥3/5 retained at week 6, ≥70% of enrolled students uploaded ≥3 recordings in prior 2 weeks, zero P0 in prior 2 weeks, ≥2 Sean Ellis "disappointed" signals. Failing any extends beta.
- Post-beta: weeks 1–8 gradual GA (~5–10 approvals/week, manual approval stays on); week 9+ re-evaluate auto-approve.
- Schema additions: `studios.beta_cohort`, `beta_feedback` table, `/beta/feedback` form, superadmin view.

---

## Testing Decisions

### What makes a good test

- **Test behavior through public interfaces, not implementation details.** If a test breaks when a private function is renamed, it was testing the wrong thing.
- **Mock only at system boundaries.** The approved list: Supabase (GoTrue, PostgREST, Storage, Realtime), Stripe, Postmark, R2, `httpx.AsyncClient`, `pywebpush.webpush`, time, randomness. Never mock internal collaborators.
- **One test, one behavior.** Avoid "kitchen sink" tests.
- **Test names describe WHAT, not HOW.** `test_recording_upload_auto_acknowledges_assignment`, not `test_recording_trigger_fires_update_statement`.
- **TDD is enforced by Ralph and by CI.** Failing test first, single implementation, never commit with a failing test, never refactor while red.
- **Coverage gates**: Python 85% on `src/dailyriff_api/{auth,services,routers,schemas}/**`; web 90% on `src/lib/**`; mobile 90% on `src/stores/**`.

### Modules tested in isolation

Every `*_service` module listed in Implementation Decisions gets a unit test suite. Highest-value targets (where isolated unit tests pay off most):

- **`playback_authorization.can_play_recording`** — the persona × relationship × state matrix. This is the security-critical module where exhaustive unit testing is the entire point.
- **`account_conversion_service`** — age-gated rules, parent-consent requirement at 13, email requirement at 18, conversion messages.
- **`streak_service`** — day-boundary edge cases, DST, multi-recording-same-day, longest-streak tracking.
- **`coppa_service`** — 15-day grace deletion, cancellation, VPC revoke-vs-delete distinction, T-7 and T-1 reminder emission.
- **`platform_settings_service`** — TTL cache behavior, write invalidation, JSON value coercion, vendor-side mirror read-only.
- **`rate_limit_middleware`** — per-route override resolution, live reload from `platform_settings`.
- **`impersonation_service`** — scope restrictions, silent vs live-mode, delayed notification timing, audit writes.
- **`onboarding_service`** — token hashing, expiry, regeneration, single-use enforcement, multi-child batch, under-13 parent-invite routing.
- **`notification_service`** — channel selection per user preference, template rendering, Postmark/Expo/Web Push boundary mocking.
- **`assignment_service`** — validator rules (teacher-student studio match, due-date window, piece/technique counts).

### Integration tests

- **RLS isolation** — extend Stage 0's `test_rls_isolation.py`. Every tenant-scoped table gets a "studio A cannot see studio B" test.
- **Recording upload end-to-end** — presigned URL mint → client upload → upload-confirm → `uploaded_at` set → `auto_acknowledge_assignment` trigger fires → ack row flips → Supabase Realtime emits event → teacher pending-reviews sees it. This is the product loop; it gets the most thorough integration coverage.
- **COPPA grace-period deletion** — schedule → cancel → schedule again → T-0 fires → hard-delete completes → R2 objects removed → audit row written.
- **Impersonation session lifecycle** — start with reason → playback URL minted → `impersonation_playback_log` written → notification emailed to target → session ends → target sees entries in Account Access Log.
- **Waitlist → approval → invited signup → dashboard landing** — full Q14a pipeline.
- **Parent self-serve enrollment with studio code** — under-13 path triggers COPPA VPC; 13–17 path lets teacher pick; 18+ path signs up directly.

### Contract tests

- **Schemathesis** — upgraded from informational to blocking (#15). Property-based fuzzing on every route, with authentication stubs.
- **OpenAPI snapshot diff** — PRs that change `openapi.snapshot.json` must show the regenerated `packages/api-client/` changes.

### End-to-end / smoke

- **Playwright** — cross-engine smoke (Chromium + Firefox + WebKit) on public routes and the auth loop; full functional suite on Chromium only.
- **Playwright + axe-core** — AA pass on every critical page.
- **Lighthouse CI** — accessibility score ≥95 per page.
- **Manual release gate** — real Safari / real Mobile Safari / real Android Chrome walkthrough of each persona's primary flow before every release.

### Prior art in the codebase

- `apps/api/tests/unit/test_auth_middleware.py` — pattern for `CurrentUser` dependency unit tests.
- `apps/api/tests/unit/test_notification_service.py` — pattern for boundary-mocked service tests.
- `apps/api/tests/unit/test_device_router.py` / `test_preferences_router.py` — pattern for router-layer *unit* tests (tight, FastAPI dependency overrides, no DB). Stage 1 reuses this shape for every new router.
- `apps/api/tests/integration/test_rls_isolation.py` — pattern for tenant isolation.
- `apps/api/tests/integration/test_devices_endpoints.py` / `test_preferences_endpoints.py` — router integration test pattern (real DB, RLS-aware).
- `apps/api/tests/contract/test_schemathesis.py` — contract test scaffold to upgrade to blocking (#15).
- `apps/web/e2e/smoke.spec.ts` — Playwright baseline.

---

## Out of Scope

Everything in the "Deferred" sections of [`docs/prds/stage-1-deferred-features.md`](./stage-1-deferred-features.md) is explicitly out of scope for Stage 1. The tracker is the single authoritative source — read it before any Stage 2 scoping. Categories:

- **Entire personas deferred**: teacher mobile app, parent mobile app.
- **Superadmin polish deferred**: `superadmin-billing-page` (no SaaS billing in marketplace model), `superadmin-analytics-page`, `superadmin-logs-page` (table exists, UI deferred), `superadmin-notifications-page` (bulk blast), `superadmin-invitations-page`, `superadmin-integrations-page`, `superadmin-system-page`, superadmin ⌘K search.
- **Waitlist polish deferred**: A/B testing, email-template manager, SMS templates, reminder scheduler UI, analytics dashboard, bulk messaging.
- **Payments**: **NO Stripe Connect, NO platform-fee collection, NO SaaS subscription billing in Stage 1.** Teacher-entered ledger only. Parent payment display only. Actual money movement is Stage 2+.
- **SMS**: deferred entirely (Stage 2+ pending 10DLC registration and Twilio).
- **Stage 1 business features deferred**: student/lesson cross-studio transfers, teacher reviews/ratings, public teacher discovery/map, referral program, student demographics dashboard, group lessons/message groups, dashboard preview dialogs, college enrollment verification, help center, security-page public marketing, parent-documents page, dashboard draggable grid, export/print menus, advanced filters panels, undo/redo.
- **i18n/l10n**: `en-US` only, no framework, no translation files, no RTL. Deferred indefinitely.
- **Mobile a11y formal audit**: +3–5 days added when mobile testing starts; deferred out of Stage 1 a11y budget.
- **WebAuthn/passkey**: deferred to Stage 2 pending GoTrue support.
- **Mandatory 2FA on studio staff**: deferred to Stage 2.
- **Account conversion birthday-automation**: deferred — Stage 1 is manual-trigger only.
- **Real-time log viewer in-app**: deferred — Supabase Studio is the Stage 1 viewer.
- **Cross-cloud R2 replication (Tier 3)**: deferred to Stage 2.
- **Per-PR EAS preview builds**: deferred — eats free tier.
- **Mobile Sentry + source-map upload**: deferred.
- **Stage 0 is preserved, not retired.** Earlier drafts of this PRD said HS256 `auth.py` and `realtime_outbox` would be retired; that was incorrect. `auth.py` is widened in place to add ES256/JWKS alongside HS256 local-dev; `realtime_outbox` stays as the Realtime broadcast fallback (see Architecture section). No Stage 0 code is removed.

---

## Stage 1 Launch Criteria (from Q21)

**Launch definition**: Stage 1 is "done" when the first full end-to-end loop completes successfully on production with non-employee users — one real studio, one real parent, one real student, one real practice recording — observed for 48 hours with zero new P0/P1 bugs.

### Pre-launch gates (all must pass)

**Legal gate**
- Terms of Service written + reviewed by edtech-experienced counsel
- Privacy Policy written + reviewed
- Sentry replay masking legal review complete (Q17.3)
- Impersonation policy legal review complete (Q17.4)
- COPPA privacy contact (`privacy@dailyriff.com`) live and monitored
- Accessibility statement published
- R2 30-day versioning disclosure reviewed under COPPA (Q25.d)

**Security gate**
- Superadmin TOTP break-glass runbook written; recovery codes in 1Password + printed offsite
- DNS SPF/DKIM/DMARC configured; Mail-Tester ≥9/10
- Stripe account in live mode; COPPA VPC Setup Intent flow tested end-to-end
- Supabase Pro active on prod; PITR verified with test restore drill
- All secrets rotated from any dev/staging values; `.env.prod` reviewed line-by-line
- Security scans clean: `pnpm audit --prod`, `uv pip audit`, Semgrep OSS
- `secret_rotation_schedule` seeded
- Dev laptop encrypted at rest

**Quality gate**
- CI green on master for 7 consecutive days
- Coverage gates met: API 85%, web 90% on `src/lib/**`, mobile 90% on `src/stores/**`
- Playwright smoke passing in staging across all three engines
- Schemathesis contract tests passing as **blocking**
- Lighthouse a11y ≥95 on every persona's primary flow
- axe-core AA passing on every persona's primary flow
- Manual a11y audit complete (keyboard + NVDA + VoiceOver per persona)

**Operational gate**
- Staging running a full copy of prod for 7 days with no schema/config drift
- Incident response plan written
- Runbooks: JWT rotation, PITR restore, superadmin MFA clear, COPPA hard-delete, R2 object recovery, break-glass
- Every persona's primary flow end-to-end tested in staging on iPhone, Android, desktop Chrome, desktop Safari, desktop Firefox
- Postmark warmed via 10–20 test sends before any real-user email
- Canary monitoring configured to page Rollin on post-deploy anomalies
- BetterStack monitors + status page live
- `pg_cron` heartbeat + operational alerts verified

### Bug severity rubric

- **P0 — launch blocker (hard stop)**: data loss, child data exposure, any COPPA/CCPA violation, superadmin lockout, payment errors, auth bypass, RLS bypass, cross-tenant data leak.
- **P1 — launch blocker unless documented workaround**: core flow broken, AA a11y failure on a primary flow, email delivery failure, notification failure, performance regression >2× baseline.
- **P2 — ship with it, fix in week 1**: secondary flow broken, cosmetic regressions, refresh-recoverable states.
- **P3 — backlog**.

### Ship decision

Objective only: **all gates pass + zero open P0/P1 + 48h staging soak with zero new P0/P1 + first real end-to-end loop completes.** No judgment tiebreaker.

### Post-launch posture

No formal Stage 1.5 canary phase. Ship → immediately resume Stage 2 planning. Sentry + PostHog + Supabase health alerts handle passive monitoring; Rollin is informal pager first week.

---

## Further Notes

- **Relationship to the tracker**: `docs/prds/stage-1-deferred-features.md` is a living companion doc. This PRD is a synthesis snapshot; the tracker is authoritative for per-feature rationale, deferral reasoning, Polymet source file pointers, and propagation across stages. Always read both. The tracker is Q1–Q29 closed; if a later change reopens any question, update the tracker first, then regenerate this PRD.
- **Relationship to Stage 0**: Stage 0 shipped the infra baseline. Stage 1 retires two Stage 0 pieces (`auth.py` HS256 middleware, `realtime_outbox`) and preserves the rest (`user_push_subscriptions`, `notification_preferences`, device/preferences routers, 3-channel notification service).
- **Relationship to Polymet**: Stage 1 ports the 5-step Polymet loop (teacher assigns → student records → auto-ack → teacher reviews) verbatim. The `auto_acknowledge_assignment` trigger is copied byte-for-byte. Everything else is re-implemented natively; the Polymet clean-architecture migration is NOT the plan — Polymet's domain classes are reference-only.
- **Development pipeline for this PRD**: `/prd-to-issues` produces independently-grabbable GitHub issues using tracer-bullet vertical slices. `ralph-once` first, then `afk-ralph`. `/review` → `/qa` → `/ship` → `/land-and-deploy` → `/canary`.
- **Estimated duration**: not committed here. The tracker's beta window is 6–12 weeks post-launch; implementation itself depends on Ralph throughput and will be estimated per-issue during `/prd-to-issues`.
- **This PRD is the input to `/prd-to-issues`.** Issues exclude everything in the deferred sections of the tracker; deferred items are tagged with future-stage labels for longitudinal tracking.
