# Stage 1 — Feature Inventory (In Scope + Explicitly Deferred)

**Created:** 2026-04-14
**Source:** grill-me session on Polymet → DailyRiffV2 Stage 1 scoping
**Status:** Living doc — update as grill-me continues and across every stage thereafter
**Owner:** Rollin
**Last updated:** 2026-04-14 (grill-me Q18-Q29 closed; all Stage 1 scoping questions resolved; doc is complete pending PRD synthesis)

---

## Purpose

Canonical record of DailyRiffV2 Stage 1 scope. Two categories:

1. **In Stage 1 Scope** — everything confirmed to ship as part of Stage 1, grouped by cluster
2. **Deferred** — everything that is part of full Polymet parity but explicitly NOT in Stage 1, with target stage and rationale

This file is the authoritative answer to both *"is feature X in Stage 1?"* and *"where did feature X go?"* for the entire life of the project. No feature should be lost between grill-me and shipping.

---

## Entry schema

Each deferred item has:
- **Name** — feature cluster name
- **Polymet source** — file(s) in `slubby101/daily-riff-platform` that spec this feature
- **Target stage** — Stage 2, Stage 3, Stage N, or "indefinite"
- **Reason deferred** — why it's not in Stage 1
- **Dependencies** — what must ship before this can land
- **Risk notes** — liability, compliance, UX, or other non-obvious considerations

---

## In Stage 1 Scope

The following clusters are confirmed to ship in Stage 1. Grouped by area. Page counts are approximate.

### Personas shipping in Stage 1
- **Teacher (studio owner)** — full desktop-first web experience
- **Parent** — full desktop-first web experience; required by COPPA for under-13 children
- **Student 13+** — web experience (self-serve login)
- **Student under-13** — parent-mediated (no direct login); recording flow accessible via parent account
- **Student mobile (Expo)** — 5 screens: dashboard, lessons, assignments, messages, profile
- **DailyRiff superadmin (YOU + future staff)** — core platform operator surface, 8 pages

### Marketing / public-facing static pages (IN Stage 1 — added during gap-analysis pass)
- `home-page.tsx` — marketing homepage, waitlist entry point (840 lines in Polymet, substantial content)
- `about-page.tsx` — minimal "About DailyRiff" static page
- `contact-page.tsx` — minimal contact page with form or info (required for COPPA privacy contact disclosure)
- `privacy-policy-page.tsx` — renders the privacy policy content (content authored in compliance checklist)
- `terms-of-service-page.tsx` — renders the ToS content (content authored in compliance checklist)
- `accessibility-statement-page.tsx` — minimal WCAG/ADA statement for legal prudence

### Clusters shipping in Stage 1 (studio-facing)
- **Added during gap-analysis pass:**
  - `student-practice-sessions-page.tsx` — student's active practice management (record new + recent sessions + filter/search). Distinct from `student-recording-history-page.tsx` (audit log). Both ship in Stage 1.
  - `report-absence-dialog.tsx` + supporting absence flow — parent reports child sick, attendance marked, optional makeup-lesson trigger. Daily-use feature. `absences`, `absenceNotifications`, `studioAbsencePolicy` mock data inform the schema.
  - `lesson-recording-player.tsx` — in-app audio player component for recording playback (used in pending-reviews, recording-history)
  - `breadcrumb-navigation.tsx` — basic UI primitive, copy from Polymet
  - `dashboard-alert-banner.tsx` — dismissable alert banner primitive (used for "pending deletion" banner, system messages)
  - `invite-studio-dialog.tsx` — already covered by superadmin waitlist/invite flow but flagged explicitly
  - `parent-search-dialog.tsx` — already covered by student-detail / roster but flagged
  - `teacher-profile-dialog.tsx` — quick-view popup of teacher info for student/parent pages
  - `parent-notifications-dialog.tsx` — already covered by Q16 notification preferences

- **Added during gap-analysis pass 2 (rigorous audit agent findings) 2026-04-14:**
  - `studio-onboarding-page.tsx` — studio signup continuation page after waitlist approval (implicit in Q14a, now named)
  - `teacher-profile-settings-page.tsx` — teacher's own profile settings (distinct from studio-profile-page)
  - `studio-profile-page.tsx` — studio branding + contact info page (Q15's feature surface)
  - `theme-toggle.tsx` — dark mode toggle component (Q13 committed to dark mode, now named)
  - `guardian-detail-dialog.tsx` — guardian contact popup from student-detail page
  - `lesson-history-card.tsx` — lesson history widget (used in lesson-detail and student-detail pages)
  - `account-conversion-dialog.tsx` — MANUAL-TRIGGER age-based account conversion flow (13→teen, 18→adult). Manual version is IN Stage 1; birthday-automation is DEFERRED per earlier Q13 note.

- Auth + onboarding — two distinct pipelines locked in Q14a/Q14b:
  - **Studio↔DailyRiff** (Q14a): marketing homepage → waitlist (6 fields, bypassable via direct invite) → superadmin approval → invited signup → email verify → auto-active on signup → superadmin verification-queue is post-signup review (non-blocking) → no SaaS billing (free in Stage 1)
  - **Student↔Studio** (Q14b): teacher-initiated (primary) OR parent self-serve via studio code (secondary, manual-approve default, per-studio auto-approve toggle). Under-13 → always parent invited (COPPA VPC triggers on parent signup). 13-17 → teacher picks parent or student. 18+ → student directly. Multi-child batch invite (one email, one signup, multiple kids). Tokens: 14-day expiry, single-use, regenerable, hashed. Post-signup lands on dashboard (no blocking walkthrough).
- Teacher dashboard + students list/detail + lessons + assignments + pending reviews
- Teacher-side ledger finances (add-payment, refund, outstanding balance, payment history)
- Parent dashboard + children management + schedule view + progress view + payments view + messages
- Student-web dashboard (13+) + assignments + recording flow + recording history + profile
- Student Expo app (5 screens)
- Messaging (in-app realtime via Supabase subscription + email fallback after 15 min unread)
- Notifications panel + push notifications (Expo + Web Push infra from Stage 0)
- Per-persona profile + settings (minimal — change password, email prefs, logout, delete account, notification toggles)
- Theme toggle (dark mode)
- COPPA VPC flow (Stripe micro-charge + signed-form escape hatch)
- Resources library (minimal: studio_id-scoped list of external links)
- **Light-touch per-studio branding (Q15)**: logo upload + primary color from constrained 12-swatch palette + display name for emails/headers. `studios.logo_url`, `studios.primary_color`, `studios.display_name`. CSS custom property `--primary` honored across student/parent layouts. Emails use `"{Studio Name} via DailyRiff" <hello@dailyriff.com>` display name. R2 `studio-assets` bucket for logos.

- **Push notification triggers (Q16.1)**: 15 notification events across teacher/parent/student-13+/superadmin. Teacher: new recording submitted, new message, pending code-join student, attendance needing mark, weekly overdue-payment digest. Parent: teacher message, assignment due 24h, assignment acknowledged, lesson reminders (24h + 1h), streak milestones. Student-13+: teacher message, new assignment, due 24h, acknowledged, lesson 1h before, streak milestones. Superadmin: daily waitlist digest, verification-queue > 48h nudge. Preferences model: per-category + per-channel toggles, defaults all on except weekly digests (email only). Trigger sources: Postgres triggers (DB state), `pg_cron` (time-based), FastAPI handlers (cross-service). `notification_templates` table drives copy + channels + target persona.

- **Environments (Q16.2)**: three-environment split — dev (local via `supabase start`), staging (hosted copy with own Supabase project + Railway service + R2 bucket `dailyriff-staging` + Stripe test mode), prod (Supabase prod project + Railway prod + R2 `dailyriff-prod` + Stripe live mode). Secrets segmented per env. CI auto-deploys main → staging, tags → prod. Staging doubles as demo environment for prospect walkthroughs.

- **Data seeding for dev (Q17.1, hybrid)**: Polymet mock data verbatim as the base (Mitchell Music Studio + all students/assignments/lessons/recordings/messages/payments), plus a synthetic edge-case generator layered on top for coverage cases Polymet doesn't model (pending-deletion children, mid-conversion teens, divorced-family multi-parent students, recording-upload-failed states). Two scripts: `apps/api/scripts/seed_polymet.py` (verbatim) + `apps/api/scripts/seed_edge_cases.py` (generator). `make seed-polymet-only` and `make seed-rich` as Makefile toggles.

- **Email provider (Q17.2, Postmark + React Email)**: Postmark for transactional delivery (best-in-class deliverability, transactional-only shared IP pool kept clean by customer vetting). React Email for template authoring (JSX components rendered to HTML, sent via Postmark API). Stage 1 email volume ~1k/month fits well within low-tier pricing. All transactional emails go through this pipeline: invitations, waitlist confirmations, verification reminders, notification fallbacks, COPPA deletion-scheduled + reminders, impersonation notifications. Marketing email (weekly digest, waitlist nurture) handled by a separate provider in Stage 2-3 — NOT sent through Postmark.

- **Analytics + session replay (Q17.3, PostHog events + Sentry masked error replay)**: PostHog JS SDK with `disable_session_recording: true` globally — event tracking only, no session replay. Event properties contain only IDs, timestamps, enums — never names, emails, or user-generated text. Sentry SDK with `replaysSessionSampleRate: 0, replaysOnErrorSampleRate: 1.0` — replay captured only on errors. Sentry `replayIntegration({ maskAllText: true, maskAllInputs: true, blockAllMedia: true })` — nuclear masking by default. Parent/student route groups have Sentry replay disabled entirely as belt-and-suspenders. Teacher-side pages can selectively `data-sentry-unmask` non-sensitive elements (studio name in header, etc.). **Legal review of masking approach required before launch.**

- **Impersonation UX (Q17.4, delayed notification with live-mode override)**: Default mode is silent impersonation with email notification to the target user within minutes of session start ("DailyRiff support accessed your account on [date] at [time] for: {reason}"). Admin must enter a required `reason` field before starting any impersonation. Live-mode override: admin checks "collaborative session" box → red banner shows on every page while impersonation is active. Target user's settings page has read-only "Account Access Log" showing every admin access. `impersonation_sessions` table: `{id, impersonator_user_id, target_user_id, studio_id, started_at, ended_at, reason, ip, user_agent, mode, notification_sent_at}`, 3-year retention. Impersonation scope restrictions: cannot change password, cannot delete account, cannot change email/2FA, cannot authorize OAuth, cannot delete recordings/messages/child data. **Impersonation policy must be documented in Terms of Service.**

- **Beta rollout plan (Q29, added 2026-04-14)**: Controlled beta with 3-5 hand-picked studios, white-glove support, explicit graduation criteria, and gradual GA ramp.

  **Cohort size: 3-5 studios, hard cap at 5.** Enough diversity to surface real patterns; few enough for solo white-glove support. Below 3 = insufficient signal; above 5 = support load exceeds solo-operator capacity.

  **Sourcing: personal network + warm intros only.** Target teachers Rollin knows directly who have already expressed interest in a tool like this. Cold outreach is for Stage 1.5 post-beta. Friendly critics bias is acceptable at this stage — the goal is fast feedback loops, not conversion-funnel optimization.

  **White-glove support definition (concrete commitments per studio):**
  - 30-60 min Zoom onboarding call walking the teacher through studio signup, student invite flow, and the recording+review loop. Recorded (with permission) for later playback.
  - Shared Slack Connect channel (or private Discord) per studio — Rollin + teacher + parents, async support during business hours, phone escalation for urgent issues.
  - Weekly 15-min check-in with each teacher for the first 4 weeks, biweekly after.
  - Manual data entry assistance for migration (direct DB via Supabase Studio, logged in `activity_logs` per Q20) — do NOT force the teacher to wait on an in-app bulk-import feature that doesn't exist.
  - Zero-friction bug reporting: teacher texts a screenshot, Rollin files the GH issue.
  - Public status page (Q27) visible to teachers for self-service health checks.
  - Feature-request fast track: small asks can ship mid-beta; large asks go on the Stage 2 list with explicit yes/no/when.

  **Beta graduation criteria (all four must pass to flip to GA):**
  1. **Retention:** ≥3 of 5 studios still actively using the platform at week 6 (60% floor)
  2. **Engagement:** within active studios, ≥70% of enrolled students have uploaded ≥3 recordings in the prior 2 weeks (core loop working)
  3. **Zero P0 bugs in the 2 weeks prior to graduation**
  4. **PMF signal:** ≥2 teachers independently say "I would be disappointed if this went away" (Sean Ellis PMF test), asked directly during a 1:1

  Failing any criterion → extend beta, root-cause the failure, re-measure. No fixed ship date — the criteria are the gate.

  **Beta duration: 6 weeks minimum, 12 weeks maximum.** 6 weeks covers 4 natural weekly cycles of lessons and recordings (enough to observe real usage patterns). Beyond 12 weeks, beta fatigue sets in and "beta" becomes procrastination on GA.

  **Post-beta ramp: gradual GA.**
  - Weeks 1-8 post-graduation: waitlist open to public, ~5-10 approved studios per week, manual approval gate stays ON
  - Week 9+: re-evaluate auto-approve based on support load and verification automation maturity (Q14a)
  - Full auto-approve only after ops feel stable AND the verification queue has clear automated rules

  **Stage 1 scope additions for beta:**
  - Private beta landing page (variant of marketing homepage, URL-token gated)
  - Beta-specific onboarding email sequence (distinct from GA waitlist flow)
  - `studios.beta_cohort` boolean column — identifies beta studios forever, useful for post-mortem analysis and a potential "founding studio" badge later
  - `beta_feedback` table — `{studio_id, submitted_by, category, severity, body, submitted_at, resolved_at}` for structured capture during beta
  - `/beta/feedback` form behind auth, beta-studios only, writes to `beta_feedback`
  - Superadmin view of `beta_feedback` (reuses existing superadmin notification + messaging surfaces)

- **Secret inventory + rotation (Q28, added 2026-04-14)**: Explicit Stage 1 secret catalog, canonical storage in a password manager, tracked rotation cadence, and a runbook for each class.

  **Canonical store: password manager (1Password).** Every Stage 1 secret lives in 1Password as the single source of truth. Railway env vars and GitHub encrypted secrets are *derived copies* — on rotation, 1Password is updated first, then the copies. TOTP recovery codes (Q20) are the only secret also stored offsite (printed). Local dev uses `.env.local` files with dev-only values; no copies of prod secrets ever land on a dev laptop.

  **Stage 1 secret inventory (full list, blast radius, storage location):**
  | Secret | Blast radius | Location | Cadence |
  |---|---|---|---|
  | Supabase `service_role` | Full DB + RLS bypass | Railway env | 90 days |
  | Supabase JWT signing | Auth forgery all users | Supabase dash | 365 days / compromise-only |
  | Supabase `anon` | Low (RLS applies) | Public bundle | Public by design |
  | Supabase DB connection string | Full DB | Railway env + runbook | 90 days |
  | FastAPI app secret | Session/CSRF | Railway env | 90 days |
  | Stripe live secret key | $-loss, API access | Railway env | 180 days |
  | Stripe webhook signing | Webhook spoofing | Railway env | 180 days |
  | Postmark server token | Email send + logs | Railway env | 180 days |
  | R2 read+write+presign key | Recording read/write | Railway env | 90 days |
  | R2 delete-only key | Recording delete | pg_cron env | 90 days |
  | Cloudflare API token (DNS+WAF) | DNS hijack, WAF bypass | 1Password + GH secrets | 90 days |
  | Sentry DSN | Low (public ingest) | Public bundle | Public by design |
  | PostHog project key | Low (write-only) | Public bundle | Public by design |
  | hCaptcha secret | Captcha bypass | Railway env | 180 days |
  | BetterStack API | Alert spoof, status tamper | 1Password | 180 days |
  | Apple ASC API key (.p8) | App Store submission | GH secrets (mobile workflow) | Vendor interval (~1yr) |
  | Google Play service account JSON | Play Store submission | GH secrets (mobile workflow) | 365 days |
  | TOTP recovery codes (Rollin) | Superadmin takeover | 1Password + printed offsite | Regenerated after use, annually regardless |

  **Immediate-rotation triggers (any secret):** suspected Railway compromise, dev laptop loss, any unfamiliar IP on DNS/WAF/DB access logs, vendor breach disclosure, any activity in `activity_logs` flagged as suspicious.

  **Rotation tracking (lives in the platform):**
  - `secret_rotation_schedule` table — `{secret_name, last_rotated_at, rotation_interval_days, next_due_at, notes}`
  - Editable from the superadmin platform-settings page (Q24 cross-cutting principle)
  - Daily `pg_cron` job: if any row's `next_due_at < now() + 7 days`, email Rollin
  - "Mark rotated" action on the page writes to `activity_logs` and recomputes due date
  - Seeded pre-launch with all Stage 1 secrets and initial due dates

  **Canonical rotation procedure (one per secret class, documented in runbook):**
  1. Generate new value at vendor (Stripe dashboard, Supabase dashboard, etc.)
  2. Update 1Password (source of truth) *first*
  3. Update Railway env vars or GH secrets (derived copies)
  4. Verify new value works in staging
  5. Deploy to prod
  6. Revoke old value at vendor
  7. Mark rotated in `secret_rotation_schedule`
  8. Auto-writes to `activity_logs`

  **Decisions on the hazardous rotations:**
  - **Supabase `service_role` every 90 days:** accepted despite requiring a Railway redeploy each time. Rationale: blast radius is catastrophic; 90-day rotation enforces muscle memory and limits any undetected compromise to a 90-day window.
  - **Supabase JWT signing secret:** 365-day baseline *plus* compromise-only trigger. Rotating this nukes all active sessions (users get logged out). Annual rotation is a scheduled "practice the procedure" event during a known low-traffic window; unscheduled rotation is reserved for actual compromise.

  **Pre-launch blockers (added to compliance checklist):**
  - 1Password vault set up with all Stage 1 secrets organized by category
  - Secret rotation runbook written (one canonical procedure + class-specific deviations)
  - `secret_rotation_schedule` table seeded with all Stage 1 secrets and initial due dates
  - Dev laptop encrypted at rest (FileVault / BitLocker) — holds `.env.local` values

- **Observability alerting / on-call (Q27, added 2026-04-14)**: Solo-operator paging stack, $0 incremental cost, tiered severity with honest "vacation = delayed P0" disclosure.

  **Uptime backbone: BetterStack free tier.**
  - 10 HTTP monitors at 30s interval
  - Monitored endpoints: `GET dailyriff.com/`, `GET api.dailyriff.com/health` (shallow), `GET api.dailyriff.com/health/deep` (Supabase + R2 + Postmark + Stripe connectivity check behind auth)
  - Alert flap protection: "down for 2 consecutive checks"
  - P0 channels: phone call (10/mo free) + BetterStack mobile push + email
  - Public status page at `status.dailyriff.com` (free BetterStack perk) — builds studio trust

  **Sentry alerting (free tier):**
  - **P0 (phone push):** uncaught exceptions in `/auth/*`; any error tagged `coppa`, `payment`, or `pii_leak`; error rate >10/min sustained 5 min
  - **P1 (email):** new error types first-seen in 24h (daily digest); error rate 2× baseline for 15 min
  - **P2 (weekly email):** error volume summary

  **PostHog alerting (free tier):**
  - **P1:** recording upload success rate <90% for 1 hour; new signup rate = 0 for 4+ business hours
  - **P2:** practice completion rate = 0 for 24h (silent-breakage indicator)

  **Supabase built-in alerts:**
  - **P0:** DB disk >90% (phone push via BetterStack uplink)
  - **P1:** DB CPU >80%, disk >75%, realtime subscription count >90% quota

  **Cloudflare alerts:**
  - R2 storage/egress cost thresholds (tunable via `platform_settings` per Q24 principle)
  - WAF block rate spike (>100× baseline)

  **Stripe alerts:**
  - Webhook delivery failure after internal retries → Stripe account email
  - Radar block rate spike → email
  - Any dispute/chargeback → phone push

  **Postmark alerts:**
  - Bounce rate >5% → email
  - Spam complaint rate >0.1% → phone push (reputation critical)
  - Hard bounce to active user email → FastAPI marks invalid, surfaces in user settings

  **Application-level heartbeat (`pg_cron` self-check):**
  - Self-check job every 10 min verifies other `pg_cron` jobs via `cron.job_run_details`, counts unprocessed rows in queue-like tables (`notifications_pending`, `recordings_uploading`), and writes to an `operational_alerts` table.
  - FastAPI exposes an endpoint that BetterStack heartbeats against every 5 min. Missing heartbeat → P1 alert.
  - **Rationale:** silent `pg_cron` failure is a real production hazard — without an explicit heartbeat, broken reminders / deletions / digests go undetected for days. The cost is one self-check job + one endpoint; the payoff is not discovering "our reminders stopped firing 11 days ago" from a user complaint.

  **Incident response SLA (internal):**
  - P0: 15 min during waking hours, 30 min overnight
  - P1: within 2 hours during waking hours
  - P2: weekly review
  - No formal on-call rotation (sole operator). **Vacation coverage is explicit: automated retries + public status page + ETA communication. P0 may wait until Rollin is back.** This is disclosed in ToS / Acceptable Use to set realistic expectations.

  **Incident break-glass runbook (pre-launch blocker, bundled with existing runbooks):**
  - How to flip maintenance-mode banner
  - How to roll back last Railway deploy
  - How to restore from Supabase PITR
  - How to communicate via `status.dailyriff.com`

  **Stage 1 observability cost: $0** (rolls up into the $25/mo Supabase Pro from Q19.2). All tools on free tiers. Upgrade triggers documented: BetterStack paid ($18/mo) when phone call allowance exhausted; Sentry paid ($26/mo) when error volume exceeds 5k/mo; PostHog paid ($0 + usage) when events exceed 1M/mo.

- **Browser / device support matrix (Q26, added 2026-04-14)**: Explicit commitment so WCAG testing, recording codec choices, Playwright scope, and bug-triage decisions have a clear line.

  **Desktop browsers — last 2 stable major versions of each:**
  - Chrome, Edge, Firefox, Safari. Rolling window — at any point in time, the current and one-previous major versions are supported. Browsers auto-update, so this covers >95% of desktop users in practice. Safari is the laggard and therefore the binding constraint on web API availability.

  **Mobile web (responsive experience on phones):**
  - iOS Safari 15+ (Apple's floor for ongoing Safari updates; drops stale WebKit variants with broken MediaRecorder)
  - Android Chrome, last 2 stable versions (Chrome auto-updates independently of Android OS version, so OS version is not the binding constraint)

  **Expo mobile app OS targets (Stage 1):**
  - iOS 15.1+ (Expo SDK 52 floor; covers iPhone 6s and later)
  - Android 7.0 / API 24+ (covers ~95% of active Android devices; Expo SDK 52 floor)
  - Below these, Expo compatibility breaks — hard floor.

  **Recording capture — MIME negotiation with hard fail:**
  `MediaRecorder.isTypeSupported()` tried in preference order:
  1. `audio/webm;codecs=opus` (Chrome, Edge, Firefox, Android Chrome — best compression)
  2. `audio/mp4;codecs=mp4a.40.2` (Safari iOS/macOS, some Android — AAC in MP4)
  3. `audio/webm` (generic fallback)
  4. Hard fail with user-facing error: "Your browser can't record audio. Please use Chrome, Safari, or Firefox."
  Server stores whichever MIME the client uploaded. No server-side transcoding (all supported browsers produce clean Opus or AAC natively). Playback uses `<audio>` element which handles both natively on all target browsers. Preserves the Stage 0 "no AAC transcoding" decision.

  **CI test matrix:**
  - Playwright runs smoke tests against Chromium + Firefox + WebKit engines (catches engine-level regressions at reasonable CI cost)
  - Full functional test suite runs only against Chromium (speed)
  - **Manual cross-browser testing before every release:** real Safari on a physical Mac + real Mobile Safari on a physical iPhone (Playwright WebKit diverges from real Safari enough that it alone is insufficient for release gating)
  - Manual testing on real Android Chrome on a physical Android device before every release

  **Explicitly NOT supported (closed as won't-fix):**
  - Internet Explorer (all versions) — EOL, blocked with hard banner
  - Opera Mini — proxy browser, JS model incompatible
  - Samsung Internet — not tested (Android Chrome is the commitment; Samsung usually works but untested)
  - Firefox ESR — supported only if it happens to fall within the "last 2 stable" window
  - Headless browsers in user contexts — blocked at Cloudflare Bot Fight Mode layer (Q24)
  - Anything older than the stated support window — hard banner: "DailyRiff requires a modern browser. Please update to continue."

  **Support-window statement goes on:**
  - Accessibility statement page
  - Help center FAQ (when it exists — Stage 2)
  - Error page shown to unsupported browsers
  - README + CLAUDE.md for dev context

- **R2 backup + DR for recordings (Q25, added 2026-04-14)**: Tiered protection — R2 object versioning + application-level soft delete in Stage 1; cross-cloud replication deferred to Stage 2.

  **Tier 1 — R2 object versioning with 30-day retention.** Enable versioning on `dailyriff-prod-recordings`. Lifecycle policy: delete versions older than 30 days. Every "delete" creates a delete marker, original bytes retained for 30 days. Restore via `rclone` or Cloudflare CLI (documented in runbook). Cost: ~$0.75/mo at Stage 1 volume. Covers accidental bulk deletion, wrong-target COPPA delete bugs, and most credential-compromise scenarios. Retention window stored in `platform_settings` (Q24 principle) so it's tunable live.

  **Tier 2 — Application-level soft delete.** All recording deletes from the app path set `recordings.deleted_at` rather than issuing an immediate R2 delete. A `pg_cron` job hard-deletes from R2 only after the grace window expires. Q16.3's 15-day COPPA grace period uses this pattern; extend it to *every* delete path (teacher removing a recording, student self-delete, admin cleanup). Double-layer defense for COPPA-critical operations.

  **Tier 3 — Cross-cloud replication to S3 Glacier Deep Archive.** Deferred to Stage 2. Rationale: vendor-side R2 failures are rare, and engineering time is better spent on Stage 1 features. Re-evaluate when recording volume exceeds 1000 active students or compliance pressure lands.

  **R2 credential scoping (defense against credential compromise):**
  - Primary API credential (held by FastAPI) has `read + write + presign` only — NO delete permission. A compromised FastAPI environment cannot bulk-wipe recordings even with full shell access.
  - Dedicated deletion-worker credential (held only by the `pg_cron` hard-delete job's execution environment) has `delete` permission.
  - Two credentials, two rotation schedules, two audit trails.

  **Audit:** every R2 delete action (regardless of layer) writes to `activity_logs` with `{recording_id, deletion_reason, delete_layer, actor}`. Supabase Studio is the forensics tool in Stage 1.

  **Runbook items (pre-launch):**
  - "How to restore R2 objects from versioning"
  - "How to identify unauthorized R2 deletes"
  - "How to hard-delete a COPPA-requested recording (bypassing Tier 1 versioning)" — see Q25.d COPPA carve-out below

  **Q25.d — COPPA carve-out (legal review required):**
  COPPA's "delete on parent request" mandate is in tension with the 30-day R2 versioning window: after the 15-day grace period expires and hard-delete runs, the R2 object still exists as a delete-marked version for 30 more days, technically recoverable. Two paths:
  1. **Set R2 versioning retention to 1 day for hard-deleted COPPA objects** — effectively permanent deletion within 24h at the cost of weaker accidental-delete protection for those specific objects
  2. **Document the 30-day versioning window in the privacy policy as a "recoverable deletion period"** and get legal sign-off that this is acceptable under COPPA

  **Stage 1 decision: path (2).** Privacy policy will explicitly describe the 30-day versioning window as a safety-net recovery period during which data is delete-marked and inaccessible to all users but technically restorable by DailyRiff operators in case of accidental deletion. Legal review of this disclosure bundles with the existing Q17.3 / Q17.4 privacy counsel engagement — added as a specific reviewable item to the pre-launch legal review checklist. **If legal says no, fall back to path (1).**

- **Rate limiting + abuse prevention (Q24, added 2026-04-14)**: Four-layer defense-in-depth, with app-owned values tunable live via a new superadmin settings page.

  **Cross-cutting platform-settings principle (introduced Q24):** every tunable knob in the DailyRiff application stack is stored in a `platform_settings` table and editable from a new superadmin page (`superadmin-platform-settings-page`) — not hardcoded, not env-var-only. The FastAPI side caches settings in-process with a short TTL (30 sec) and invalidates on write. This applies to rate limits, business-rule caps, notification delays, COPPA grace windows, session timeouts where the app controls them, and any future tunable. Exception: values owned by third-party vendors (Supabase GoTrue limits, Cloudflare WAF rules, Supabase Auth session timeouts) are configured at the vendor dashboard and documented in the prod deploy runbook — the superadmin page displays their *current* values as read-only for visibility but cannot write them.

  **Layer A — Cloudflare in front of Railway (vendor-side, runbook-managed):**
  - Proxy `dailyriff.com` + `api.dailyriff.com` through Cloudflare (free tier).
  - Bot Fight Mode enabled.
  - WAF managed OWASP ruleset enabled.
  - Rate limit rule: 50 req/10sec per IP on `/api/*` (1 free-tier rule).
  - "Under Attack Mode" documented as break-glass for active DoS incidents.

  **Layer B — FastAPI `slowapi` middleware (app-owned, tunable via `platform_settings`):**
  - Global defaults: 100 req/min/authenticated user; 30 req/min/anonymous IP.
  - Per-route overrides (all editable live):
    - `POST /auth/*` — 5 req/min/IP
    - `POST /recordings/upload-url` — 20 req/hour/user
    - `POST /messages` — 30 req/min/user
    - `POST /waitlist` — 3 req/hour/IP
    - `POST /coppa/vpc-charge` — 3 req/hour/parent
    - `POST /auth/password-reset` — 3 req/hour/email
  - Storage: in-memory on single Railway instance in Stage 1 (horizontal scaling not expected). Documented upgrade path to Redis-backed when a second instance is added.

  **Layer C — Supabase GoTrue built-ins (vendor-side, runbook-managed):**
  - Signup: 10/hour/IP
  - Signin: 10/5min/IP
  - Password reset: 5/hour/email
  - Token refresh: 150/hour (default)
  - Magic link: **disabled** (Stage 1 = password + TOTP only)
  - Values configured in Supabase dashboard and documented in the prod deploy runbook. Read-only mirror in superadmin platform-settings page.

  **Layer D — Business-rule caps (app-owned, tunable via `platform_settings`):**
  - Recordings: max 50/student/day (R2 cost protection; 10× real-use headroom)
  - Messages: max 200/user/day (compromised-account spam defense)
  - Waitlist: max 1/email + max 3/IP lifetime (unique constraint + IP count)
  - Push notifications: max 20/user/day (Expo credit burn protection)
  - COPPA VPC: max 3 attempts/parent/24h (Stripe cost protection)

  **Additional hardening:**
  - **Webhook replay defense:** Stripe webhooks verified via `stripe.Webhook.construct_event` (signature + 5-min timestamp tolerance). Postmark webhooks via Postmark's signature check. All webhook events stored in `idempotency_log` with unique `(provider, event_id)` — duplicates are no-ops.
  - **Enumeration defense:** password reset returns 200 with constant latency regardless of email existence. Signup does not disclose "already registered" — emails the existing user instead ("someone tried to sign up with your email").
  - **hCaptcha** on waitlist + public signup forms (free tier, privacy-respecting).
  - **Stripe Radar** enabled default on all charges.
  - **R2 cost alerts:** Cloudflare dashboard alerts at $10 / $20 / $40 monthly thresholds. Expected Stage 1 steady-state: well under $5/mo (~24 GB storage + ~50 GB egress at R2 rates).

  **New Stage 1 scope surface:**
  - `platform_settings` table (`{key, value_json, description, category, updated_at, updated_by}`)
  - `superadmin-platform-settings-page` — category-grouped editable settings with audit trail (every edit writes to `activity_logs`)
  - FastAPI `settings_service.py` with 30-sec in-process TTL cache + write invalidation
  - Read-only vendor-side mirror showing current Cloudflare/GoTrue values for operator situational awareness

- **Superadmin bootstrap (Q23, added 2026-04-14)**: One-shot Python script — no migration-seeded data, no env-var middleware backdoors, no undocumented SQL.
  - **Script:** `apps/api/scripts/bootstrap_first_owner.py`. Reads `SUPABASE_AUTH_USER_ID` and `SUPABASE_AUTH_EMAIL` from env. Inserts a single row into `dailyriff_employees` with `{role: 'owner', created_by: null, notes: 'bootstrap'}` so the genesis account is discoverable forever.
  - **Hard sanity checks (all must pass or script aborts):** (1) `dailyriff_employees` row count must be zero — script is first-owner-only forever, re-running is a no-op by design; (2) referenced `auth.users` row must exist; (3) target auth user must already have TOTP enrolled via Supabase Auth's native flow.
  - **TOTP sequencing:** user enrolls TOTP via Supabase Auth's own battle-tested enrollment flow *before* running the script. The script never handles TOTP itself — each tool does one thing, no reimplementation of MFA primitives.
  - **Staging parity:** same script runs against staging DB first, creating Rollin's dev account as staging's first owner. This validates the prod bootstrap path end-to-end before it ever touches prod. Staging is not bootstrapped differently (despite being re-seedable) because the whole point is exercising the exact prod procedure.
  - **No break-glass twin script.** Destructive ops like "wipe all employees" live in the Q20 break-glass runbook as documented SQL executed via Supabase Studio — never as a runnable script that could fire accidentally.
  - **Rejected alternatives:** (A) Alembic data migrations couple schema history to a one-time operational event; (C) env-var middleware backdoors are silent full-platform holes waiting to be forgotten; (D) undocumented SQL becomes institutional knowledge only one person has.

- **Timezone + locale (Q22, added 2026-04-14)**: Studio-local TZ is canonical; en-US only; no i18n framework.
  - **Storage:** all timestamps are `timestamptz` in Postgres, always UTC under the hood.
  - **Canonical TZ for scheduling:** `studios.timezone` column (IANA name, e.g. `America/Los_Angeles`) set at studio creation. All lesson times, assignment due dates, reminder schedules, and recital times resolve against studio-local TZ. A music studio is a physical place and the teacher effectively *is* the studio — lesson scheduling follows studio time, not viewer time.
  - **Display:** every time rendered as studio-local with TZ abbreviation always visible ("Tue 4:00 PM PST"). No viewer-local conversion. Calendar export (`.ics`) uses studio-local with proper `TZID=` for external calendar interop. Global footer reminder: "All times shown in {Studio Name}'s timezone ({IANA abbr})."
  - **Reminder semantics:** "1h before lesson" and "due in 24h" tick against studio-local TZ. `pg_cron` runs in UTC; target times computed via `AT TIME ZONE studios.timezone`. DST handled automatically by IANA TZ data in Postgres.
  - **DST edge case:** recurring lesson series crossing a spring-forward/fall-back boundary is covered by storing the recurrence rule against studio-local TZ (not UTC offset). Test case required before launch.
  - **Studio TZ change:** allowed but does NOT auto-migrate existing scheduled events. Teacher sees a warning: "existing lessons will keep their current UTC instants; review your schedule." Auto-rebase deferred to Stage 2.
  - **Locale:** `en-US` only. All UI strings in English. No i18n framework, no translation files, no RTL, no MessageFormat. Date = MM/DD/YYYY, time = 12-hour with AM/PM, currency = USD `$`. i18n/l10n deferred indefinitely — revisit only when international expansion is a deliberate product decision.
  - **Traveling parent:** sees studio-local time unchanged regardless of device TZ. This is the correct answer — the parent is delivering their kid to a physical studio, not teaching remotely.

- **Superadmin account security / 2FA (Q20, added 2026-04-14)**: Tight-on-superadmin, optional-on-studio-side posture.
  - **Superadmin (DailyRiff employees): TOTP REQUIRED.** Hard-block login without a registered TOTP factor. No SMS as a factor (SIM-swap risk on the highest-value account class). First-login flow: email/password → forced TOTP enrollment → recovery codes displayed + stored → session starts. No grace period, no "remind me later."
  - **WebAuthn/passkey deferred to Stage 2** (Supabase GoTrue does not natively support WebAuthn as of 2026-04; revisit when GoTrue ships it or implement via custom auth hook).
  - **Studio-side (owner/teacher): TOTP optional but nagged.** Settings toggle, dashboard banner if disabled, login works without. Blast radius is bounded to one studio. Mandatory 2FA for studio staff deferred to Stage 2 when support capacity exists.
  - **Parent/student: no 2FA in Stage 1.** Friction cost is high (under-13 flows already complex), blast radius is single-user. Defer.
  - **Session policy:** superadmin = 8h max session + 1h idle timeout (re-auth forced). Studio-side = Supabase Auth defaults (~1 week). Parent/student = Supabase Auth defaults.
  - **Recovery (solo-operator reality):** Stage 1 has a single owner (Rollin). No second-owner-resets-first-owner path exists. Recovery mechanism: TOTP recovery codes stored in password manager + printed offsite backup (safe deposit box / fireproof home safe). Break-glass procedure: direct Supabase Studio SQL access to clear the MFA requirement on the owner row, documented in a runbook only Rollin can access. **This break-glass runbook is a launch prerequisite.**
  - **Failed-auth alerting:** 3 failed MFA attempts on a superadmin account within 15 min → email alert to all owner-role employees (Stage 1 = Rollin's personal email). Writes to `activity_logs`.
  - **Audit log:** every MFA event (enrollment, successful challenge, failed challenge, recovery code used, admin-initiated reset) writes to `activity_logs` with actor, target, timestamp, IP, user agent.
  - **Launch blocker:** cannot grant impersonation powers (Q17.4) to any account protected only by a password. Adds to pre-launch compliance checklist below.

- **Mobile CI/CD via EAS (Q19.1, added 2026-04-14)**: Minimal tag-triggered Stage 1 pipeline.
  - **Triggers:** `mobile-v*` tag → `eas build --platform all --profile production --non-interactive` → `eas submit` to TestFlight + Play Internal Testing. `mobile-hotfix-*` tag → `eas update --branch production` for JS-only OTA hotfixes (no native rebuild). `workflow_dispatch` enabled for ad-hoc manual builds from any branch.
  - **Per-PR validation stays light:** existing `mobile-unit` (jest-expo) + `codegen` (`tsc --noEmit`) jobs cover PR-level checks. No per-PR EAS builds — burns the free tier (30 builds/mo) too fast for Stage 1 volume.
  - **One build profile: `production`.** Staging is handled by pointing the local dev client at the staging API via env var, not a separate `preview` EAS profile. Dev client is built locally once per machine via `expo start --dev-client`.
  - **Credentials:** Apple ASC API key (.p8) + Google Play service account JSON as GitHub encrypted secrets scoped to mobile workflows only. EAS manages signing certs via `eas credentials`. Rollin owns Apple Developer + Play Console accounts in Stage 1 (no delegation).
  - **Deferred:** per-PR EAS preview builds, automated `app.json` version bumping, fastlane, mobile Sentry source-map upload (deferred with mobile Sentry wiring itself).

- **Supabase migration deploys (Q19.2, added 2026-04-14)**: Alembic stays as schema source of truth; auto-apply to staging, manual gate to prod.
  - **Two-tool split:** Alembic (`apps/api/alembic/versions/`) owns all FastAPI app tables + infra tables. `supabase db push` with `supabase/migrations/*.sql` owns Supabase-native objects (RLS policies, auth schema customizations, `supabase_functions` triggers). Clearly separated scopes to prevent version-history conflicts.
  - **Staging deploy (fully automatic):** on merge to master — `alembic upgrade head` against staging DB → `supabase db push --db-url $STAGING_DB_URL` → deploy FastAPI to Railway staging → smoke test. Any failure halts the deploy; schema is NOT auto-rolled-back (forward-fix only). After successful migration, CI re-runs `seed_polymet.py` + edge-case generator against staging so demo data stays current.
  - **Prod deploy (manual approval gate):** `api-v*` tag triggers a workflow that (1) runs `alembic upgrade head --sql > migration.sql` to preview the DDL, (2) posts it as a workflow artifact + PR comment, (3) waits on a GitHub environment protection approval, (4) applies migration on approval, (5) deploys API to Railway prod. Rollin eyeballs every prod schema change in Stage 1.
  - **Expand-then-contract rule:** every migration must be safe to run *before* the new API code deploys — new columns nullable, dropped columns deprecated-then-dropped across two deploys. Enforced by PR checklist in Stage 1 (tooling-enforced later).
  - **Rollback:** forward-fix only for schema (`0042_fix_0041.py`, never `alembic downgrade` in prod). Data rollback is Supabase Point-in-Time Recovery.
  - **Pre-flight:** every prod migration has already run against staging (same schema, smaller data) before the prod approval gate fires.
  - **Supabase tier (Q19.2 Decision):** **Pro tier for prod ($25/mo)**, Free tier acceptable for staging. Pro is non-negotiable for prod — Free-tier auto-pause after 7 days of inactivity is fatal for a real app; PITR + 7-day daily backups are the safety net that makes "forward-fix only" a real strategy. Staging is re-seedable from Polymet mocks + edge-case generator (Q17.1), so losing it is acceptable. Total Stage 1 Supabase cost: **$25/mo**. Upgrading staging to Pro deferred until PITR drills become routine.

- **Recording playback authorization (Q18, added 2026-04-14)**: Default-deny allow-list enforced by FastAPI-minted short-lived signed R2 URLs.
  - **Allow-list:** the student themselves, their parents/guardians, the teacher(s) assigned to that student, and the studio owner. Superadmin playback is permitted **only** inside an active impersonation session (no direct-from-admin-UI playback path).
  - **Deny in Stage 1:** peer students, non-assigned teachers, external share links ("send to grandma"), any public URL. Co-teacher / substitute access deferred to Stage 2.
  - **Enforcement:** client requests `GET /recordings/{id}/playback-url` → FastAPI runs `can_play_recording(user, recording)` (single centralized policy function, unit-tested across the full persona × relationship × state matrix) → mints a presigned R2 URL with **5-minute TTL** → client plays directly from R2 via CDN. FastAPI never proxies bytes (preserves R2 free egress).
  - **Impersonation audit:** when `CurrentUser.impersonation_session_id is not None`, URL-minting writes a row to `impersonation_playback_log {session_id, recording_id, minted_at}`. Target user sees these in their "Account Access Log" alongside the Q17.4 impersonation session record.
  - **Revocation:** deletion or authorization change fails the next `can_play_recording` check. Already-minted URLs expire within the 5-min TTL window; hard per-byte revocation is not a Stage 1 goal.
  - **Download resistance is an explicit non-goal:** `<audio controlsList="nodownload">` is used as soft deterrent only. The privacy policy documents that authorized users can technically extract audio from their browser; the threat model defends against *unauthorized* access, not *authorized re-distribution*. Hard DRM / Cloudflare Worker edge-enforcement deferred to Stage 2-3 pending a concrete leak incident or compliance pressure.
  - **No normal-playback audit log:** only impersonation playbacks are logged. Per-user per-recording play events are not an auditable concern in Stage 1 (revisit if COPPA counsel requires it during privacy policy review).
  - **Pending-deletion students:** playback remains available to authorized users during the 15-day grace period (Q16.3); access revokes atomically at hard-delete.

- **WCAG 2.1 AA accessibility compliance (added 2026-04-14)**: Target is WCAG 2.1 Level AA on every shipped page/flow. Leverages Radix UI primitives (baked into shadcn) for ~70% free coverage. Stage 1 commitments:
  - `jsx-a11y` ESLint plugin at error level blocks build on violations
  - axe-core via Playwright test on every critical page; build fails on new AA violations
  - Lighthouse CI accessibility score ≥95 per page
  - pa11y-ci as optional second-opinion scanner
  - 12-color brand palette (Q15) vetted against AA contrast ratios (4.5:1 normal text, 3:1 large text) against both white and black text before palette finalization
  - Semantic HTML: proper landmarks, heading outline order, buttons-not-divs, lists as ul/ol
  - Keyboard navigation: every interactive element reachable via Tab, operable via Enter/Space, skip-to-main-content link
  - Form accessibility: visible labels, aria-describedby for errors, aria-required, role=alert for errors
  - Dynamic announcements: role=status/alert for toasts, real-time message announcements, recording state transitions
  - Alt text on all images (avatars, logos); alt="" for decorative
  - 200% zoom + reflow support (covered by mobile-responsive layouts)
  - prefers-reduced-motion respected for all transitions
  - Audio player (lesson-recording-player) has standard keyboard controls + ARIA labels
  - Pre-launch manual audit: full keyboard walkthrough + NVDA + VoiceOver testing on each persona's primary flows (~4-6 hrs per persona)
  - Color-blindness simulator check on dashboard-heavy pages
  - Acceptance criterion on every Stage 1 GH issue: "axe-core AA passes, keyboard-only nav verified"
  - Budget: ~1 week of dedicated a11y polish on top of normal feature dev
  - Deferred: VPAT (Stage 3+ enterprise sales enabler), WCAG AAA, i18n/RTL, Expo mobile a11y testing (adds +3-5 days when mobile testing starts)

- **Cookie / tracking compliance (added 2026-04-14)**: NO blocking cookie consent banner in Stage 1. DailyRiff uses zero advertising cookies, is US-only in Stage 1, so GDPR does not apply. CCPA/CPRA compliance via three safeguards instead:
  1. **"Your Privacy Choices" footer link** on every page (CCPA-mandated language) pointing to `/legal/privacy-choices` page with: cookie table (name, purpose, duration, category), toggle to opt-out of PostHog analytics (writes localStorage + calls `posthog.opt_out_capturing()`), disclosure that DailyRiff does not sell or share data for advertising, contact link to privacy@dailyriff.com
  2. **Global Privacy Control (GPC) auto-respect**: on app mount, check `navigator.globalPrivacyControl`; if true, auto-opt-out of PostHog without user action. California AG has confirmed GPC respect is required for CCPA compliance. Colorado + Connecticut also recognize it.
  3. **Cookie documentation in privacy policy**: full table of every cookie with name, purpose, duration, first-party vs third-party, category (essential/functional/analytics)
  - Cookies used: Supabase auth session (strictly necessary), PostHog analytics (functional, opt-out-able), Sentry error replay (masked, opt-out-able), Stripe during VPC (strictly necessary). No advertising, no social, no retargeting.
  - Implementation cost: ~2-3 days in Stage 1
  - **Upgrade path when EU users ever in scope**: add Osano/Cookiebot/self-hosted consent banner with EU geo-detection; banner defaults to "essential only" for EU, auto-dismisses for US with GPC respect. Privacy-choices page content becomes banner content. ~2-3 days additional work at that time.

- **COPPA deletion mechanics (Q16.3, revised)**: 15-day grace period deletion, not immediate.
  - Parent clicks "delete my child's data" → confirmation ("permanent deletion on [date]") → `child.deletion_scheduled_at = now() + interval '15 days'`, child marked `pending_deletion`
  - Child can still use the platform normally during grace period (top banner: "Data will be deleted on [date] — cancel?")
  - Teacher sees "pending deletion" badge on student record
  - Email cadence: immediate scheduling confirmation, T-7 reminder, T-1 final reminder
  - `pg_cron` job at T-0: hard-delete student row, R2 objects (audio recordings), related acks/messages/progress/assignment completions; write audit row to `coppa_deletion_log` with no PII (just `{deleted_at, studio_id, deleted_by, r2_objects_count, db_rows_count}`)
  - Parent cancellation anytime before T-0 clears `deletion_scheduled_at` and resumes normal state
  - VPC revocation is a separate flow (pauses new data collection without scheduling deletion; 30-day auto-delete if not re-consented)
  - Confirmation UI requires typing "DELETE" to prevent accidental clicks
- Loan tracking (embedded in student detail page)
- Practice streak + weekly minutes + assignment completion rate (basic gamification)
- Google + Apple OAuth (no Facebook)

### Clusters shipping in Stage 1 (superadmin / platform-operator)
- `superadmin-dashboard-home` — platform overview + metrics
- `superadmin-studios-page` — list all studios
- `superadmin-studio-detail-page` — drill into studio, suspend, verify, impersonate
- `superadmin-users-page` — list all platform users, search, drill in
- `superadmin-user-detail-page` — impersonate, password reset, disable
- `superadmin-verification-queue-page` — review and approve pending studio signups
- `superadmin-employees-page` + `EmployeePermissions` — DailyRiff staff roles in Stage 1: **owner, support, verifier** (billing role deferred with billing page)
- `superadmin-platform-settings-page` — category-grouped editable settings for every app-owned tunable knob (rate limits, business-rule caps, notification delays, COPPA grace windows); read-only mirror of vendor-side settings (Cloudflare WAF, GoTrue limits) for situational awareness. Added Q24 as cross-cutting platform-settings principle.
- `superadmin-waitlist-page` + `approve-waitlist-dialog` + `send-waitlist-message-dialog` (single-recipient, no A/B) — waitlist management for controlled studio scaling
- `waitlist-invite-signup-page` + `waitlist-confirmation-page` — public-facing waitlist signup flow
- DailyRiff employee auth (separate from studio-side users) with role-based permissions
- Impersonation flow with audit logging
- **NO studio SaaS subscription billing** — DailyRiff business model is pure marketplace: studios use the platform free, DailyRiff monetizes only via platform fee on tuition (Stage 2+ via Stripe Connect)

### Infrastructure shipping in Stage 1
- Supabase Cloud (Postgres + GoTrue auth + PostgREST + Realtime + Studio + small-asset Storage)
- FastAPI on Railway (business logic: Stripe, COPPA VPC, recording upload-confirm, platform-billing, orchestration)
- Cloudflare R2 for recordings (direct signed-URL upload, CDN playback, free egress)
- Multi-tenant via `studio_id` on every row + Supabase RLS policies (DB-enforced tenant isolation)
- `auto_acknowledge_assignment` Postgres trigger (preserved verbatim from Polymet)
- Supabase Realtime subscription on `assignment_acknowledgements` for teacher pending-reviews live updates
- Stage 0 infra kept: `user_push_subscriptions`, `notification_preferences`, device/preferences routers, push notifications service
- Stage 0 infra retired: `realtime_outbox` table (replaced by Supabase Realtime), `auth.py` HS256 (replaced by GoTrue)

---

## Stage 1 launch criteria (Q21, added 2026-04-14)

**Launch definition:** Stage 1 is "done" when the first full end-to-end loop completes successfully on production with non-employee users — one real studio, one real parent, one real student, one real practice recording — observed for 48 hours with zero new P0/P1 bugs. No subjective "feels ready" — objective gates only.

### Pre-launch gates (all must pass)

**Legal gate**
- Terms of Service written + reviewed by edtech-experienced counsel
- Privacy Policy written + reviewed
- Sentry replay masking legal review complete (Q17.3)
- Impersonation policy legal review complete (Q17.4)
- COPPA privacy contact email (`privacy@dailyriff.com`) live and monitored
- Accessibility statement published

**Security gate**
- Superadmin TOTP break-glass runbook written; recovery codes stored in password manager + printed offsite backup (Q20)
- DNS SPF/DKIM/DMARC configured; Mail-Tester score ≥9/10
- Stripe account in live mode with COPPA VPC Setup Intent flow tested end-to-end
- Supabase Pro tier active on prod; PITR verified with a test restore drill
- All secrets rotated from any dev/staging values; `.env.prod` reviewed line-by-line
- Third-party security scans run clean: `pnpm audit --prod`, `uv pip audit`, Semgrep OSS on both codebases

**Quality gate**
- CI green on master for 7 consecutive days
- Coverage gates met: API 85%, web 90% on `src/lib/**`, mobile 90% on `src/stores/**`
- Playwright smoke suite passing in staging
- Schemathesis contract tests passing as **blocking** (upgrade from informational, currently tracked in #15)
- Lighthouse accessibility score ≥95 on every persona's primary flow
- axe-core AA passing on every persona's primary flow
- Manual a11y audit complete (keyboard + NVDA + VoiceOver per persona, per Q WCAG commitments)

**Operational gate**
- Staging environment running a full copy of prod for 7 days with no schema or config drift
- Incident response plan written (rough acceptable, refined post-launch)
- Runbooks: JWT secret rotation, PITR restore procedure, superadmin MFA clear, COPPA hard-delete, R2 object recovery
- Rollin has personally tested every persona's primary flow end-to-end in staging on real devices: iPhone, Android, desktop Chrome, desktop Safari, desktop Firefox
- Postmark warmed up via 10-20 test sends to owned inboxes before any real-user email
- Canary monitoring configured to page Rollin on post-deploy anomalies (via gstack `/canary` skill or equivalent)

### Bug severity rubric

- **P0 — launch blocker (hard stop):** data loss, child data exposure, any COPPA/CCPA violation, superadmin lockout, payment errors, auth bypass, RLS bypass, any cross-tenant data leak
- **P1 — launch blocker unless documented workaround:** core flow broken (cannot sign up / cannot record / cannot message), AA a11y failure on a primary flow, email delivery failure, notification failure, performance regression >2× baseline
- **P2 — ship with it, fix in week 1:** secondary flow broken, cosmetic regressions, refresh-recoverable inconsistent states
- **P3 — backlog:** polish, edge cases, known-safe deferrals

### Ship decision

Objective criteria only: **all gates pass + zero open P0/P1 + 48h staging soak with zero new P0/P1 + first real end-to-end loop completes successfully.** No judgment-call tiebreaker; if a gate fails, the answer is "not yet," not "ship anyway."

### Post-launch posture

No formal Stage-1.5 canary phase. Ship → immediately resume Stage 2 planning. Sentry + PostHog + Supabase health alerts handle passive monitoring; Rollin is on informal pager for the first week but not as a gated stage.

---

## Propagation plan

1. **During grill-me (now):** every deferral decision updates this file before moving on
2. **End of grill-me:** file is frozen as Stage 1 scoping input
3. **`/write-a-prd` step:** this file becomes the "Explicitly Deferred" appendix of `docs/prds/stage-1-foundation.md`
4. **`/prd-to-issues` step:** Stage 1 issues exclude deferred items; deferred items are tagged with future-stage labels for tracking
5. **Each future stage:**
   - Re-read this file as grill-me input ("what did we say would come in Stage 2?")
   - Move items from "deferred" → "in progress" → "shipped" with commit refs
   - Add new deferrals discovered during that stage's grill-me
6. **Audit gate:** before any stage ships, diff the shipped feature list against this file to ensure nothing has been silently dropped

---

## Deferred — entire personas

### Superadmin persona — UPDATED 2026-04-14 (Q14-pre)
**Status:** NO LONGER DEFERRED AS A WHOLE. Split into:
- **Core superadmin (8 pages) → IN Stage 1** — see "In Stage 1 Scope" section above
- **Superadmin polish pages → still deferred** — see "Deferred — superadmin polish" section below

### Teacher mobile app
- **Polymet source:** No dedicated prototype — Polymet's `src/mobile/` and `src/polymet/prototypes/mobile-student-app.tsx` only cover the student persona
- **Target stage:** Stage 3+ (or indefinite)
- **Reason deferred:** Teacher workflows are desktop-first in Polymet's design (multi-column dashboards, data tables, finance pages). Adding a teacher mobile app is scope beyond Polymet parity.
- **Dependencies:** User demand signal from real teachers, validated Stage 1 web product
- **Risk notes:** Web-responsive design for teacher pages on phone should be "usable" but not "optimized" in Stage 1.

### Parent mobile app
- **Polymet source:** No dedicated prototype
- **Target stage:** Stage 3+ (or indefinite)
- **Reason deferred:** Same as teacher — no Polymet prototype exists; web-responsive is sufficient for Stage 1.
- **Dependencies:** User demand signal
- **Risk notes:** Parent is the payer; if parents need app-level features later (biometric unlock for payment auth, push notification depth), reconsider.

---

## Deferred — superadmin polish

### superadmin-billing-page — DEFERRED 2026-04-14 (Q14a Decision 5)
- **Polymet source:** `superadmin-billing-page.tsx`, `BillingRecord`, `PlatformRevenueSummary` entities
- **Target stage:** Stage 2-3 (ships with Stripe Connect when platform-fee revenue from tuition actually starts flowing)
- **Reason deferred:** DailyRiff business model is pure marketplace — no studio SaaS subscription, so there is nothing to bill in Stage 1. The page has no content until Stage 2 Connect activation produces real platform-fee revenue from tuition payments.
- **Dependencies:** Stripe Connect Express shipped (Stage 2-3), actual tuition payments flowing, application_fee_amount accumulated
- **Risk notes:** Originally scoped IN during Q14-pre; reverted OUT during Q14a Decision 5 when user confirmed pure-marketplace model. Employee `billing` role also deferred in lockstep.

### superadmin-analytics-page
- **Polymet source:** `superadmin-analytics-page.tsx`, various platform analytics components
- **Target stage:** Stage 2-3
- **Reason deferred:** Dashboard-home covers basic metrics in Stage 1. Rich platform analytics (revenue breakdown, studio growth charts, cohort analysis) is polish without validated questions to answer.
- **Dependencies:** Real data volume to justify

### superadmin-logs-page
- **Polymet source:** `superadmin-logs-page.tsx`, `ActivityLog` entity
- **Target stage:** Stage 2
- **Reason deferred:** Stage 1 writes audit-log rows to an `activity_logs` table (impersonations, verification actions, billing events) but does not build the viewer UI. Supabase Studio is the Stage 1 viewer.
- **Dependencies:** None (schema reserved in Stage 1, UI deferred)
- **Risk notes:** The *table* must exist in Stage 1 — impersonation audit is a compliance requirement. Only the UI is deferred.

### superadmin-notifications-page (blast to users across studios)
- **Polymet source:** `superadmin-notifications-page.tsx`
- **Target stage:** Stage 2
- **Reason deferred:** Platform-wide blast messaging is an operational feature you can handle manually in Stage 1 via direct email or per-studio messaging. Formal UI with targeting, scheduling, A/B can wait.
- **Dependencies:** None

### superadmin-invitations-page (outbound non-waitlist invitations)
- **Polymet source:** `superadmin-invitations-page.tsx`, `invitations-page.tsx`, `invitation-templates.tsx`
- **Target stage:** Stage 2
- **Reason deferred:** Stage 1 waitlist approval flow covers "how to invite a specific studio to join." A richer invitation manager with templates, bulk sending, and tracking is polish.
- **Dependencies:** None

### superadmin-integrations-page
- **Polymet source:** `superadmin-integrations-page.tsx`, `Integration`, `Webhook`, `APIEndpoint` entities
- **Target stage:** Stage 3+
- **Reason deferred:** No integrations exist to manage. Premature.
- **Dependencies:** Real integration partnerships (Google Calendar sync, Zoom, QuickBooks, etc.) exist

### superadmin-system-page (infrastructure health)
- **Polymet source:** `superadmin-system-page.tsx`, `SystemMetric` entity
- **Target stage:** Indefinite
- **Reason deferred:** System health monitoring is a Datadog/Grafana/Sentry concern, not an in-app page. Build external observability instead.
- **Dependencies:** None — likely never building this in-app

### Superadmin search command (⌘K)
- **Polymet source:** `superadmin-search-command.tsx`
- **Target stage:** Stage 2-3
- **Reason deferred:** Same as studio-side command palette (GZ9). Not primary.

---

## Deferred — waitlist polish

Waitlist core (basic signup, approval, per-recipient message) is IN Stage 1. The following polish features remain deferred.

### Waitlist A/B testing framework
- **Polymet source:** `email-ab-testing-manager.tsx`, `waitlist-ab-testing-sms-summary.tsx`
- **Target stage:** Stage 3+
- **Reason deferred:** A/B testing conversion funnels before you have statistically meaningful traffic is superstition. Run manual experiments via ad-hoc SQL until you have real volume.
- **Dependencies:** Meaningful waitlist traffic (likely 500+ entries minimum)

### Waitlist email template manager
- **Polymet source:** `waitlist-email-templates.tsx`
- **Target stage:** Stage 2
- **Reason deferred:** Stage 1 uses hardcoded email templates in FastAPI code for the 3-4 waitlist transactional emails (joined, approved, invited, reminder). Template manager UI is polish.
- **Dependencies:** None

### Waitlist SMS templates
- **Polymet source:** `waitlist-sms-templates.tsx`
- **Target stage:** Stage 2+ (also blocked by SMS deferral)
- **Reason deferred:** Depends on SMS being enabled generally, which is Stage 2+.
- **Dependencies:** 10DLC + Twilio (see general SMS deferral)

### Waitlist reminder scheduler
- **Polymet source:** `waitlist-reminder-scheduler.tsx`
- **Target stage:** Stage 2
- **Reason deferred:** Stage 1 uses simple cron + email for waitlist reminders (e.g., "you've been on the waitlist 30 days, still interested?"). Scheduler UI with custom triggers, multi-step sequences, and per-cohort logic is polish.
- **Dependencies:** None

### Waitlist analytics dashboard
- **Polymet source:** `waitlist-analytics-dashboard.tsx`, `waitlist-enhancements-summary.tsx`
- **Target stage:** Stage 2-3
- **Reason deferred:** Rich waitlist analytics (conversion rates, cohort analysis, source attribution) is polish without real traffic.
- **Dependencies:** Real waitlist volume

### Blast messaging to waitlist (bulk)
- **Polymet source:** `send-waitlist-message-dialog.tsx` (bulk/A/B variants)
- **Target stage:** Stage 2
- **Reason deferred:** Stage 1 ships single-recipient waitlist messaging only. Bulk send (message all "cold" entries, message all entries who joined in March, etc.) is polish.
- **Dependencies:** None

---

## Deferred — items found in rigorous audit agent pass (2026-04-14)

### Undo/redo for critical actions
- **Polymet source:** Cross-cutting pattern — implicit in Polymet component design but no dedicated file
- **Target stage:** Stage 2-3
- **Reason deferred:** Undo/redo (e.g., "undo delete assignment", "undo sent message", "restore archived student") is a premium UX pattern but requires: reversible action log, per-action compensating transactions, UI affordances for undo windows. Polymet does not actually implement it despite hinting at it. Stage 1 ships with explicit confirmation dialogs on destructive actions instead ("Are you sure? Type DELETE to confirm" for the weightiest actions).
- **Dependencies:** Enough user complaints about irreversible actions to justify the engineering

### Polymet /examples/ render harnesses
- **Polymet source:** ~227 `.render.tsx` files under `src/polymet/examples/`
- **Target stage:** Never — not product features
- **Reason deferred:** These are Polymet's internal Storybook-like render harnesses, paired 1:1 with components and pages for design preview inside Polymet's own dev environment. They are not standalone features. Each one's parent file (the component or page it renders) is already classified elsewhere in this doc. Audit complete; no further action needed per-file.
- **Dependencies:** None — complete category ignore

### Polymet /plans/ internal design docs
- **Polymet source:** ~19 `.md` files under `src/polymet/plans/` (ada-compliance-plan, backend-integration-plan, clean-sheet-architecture-plan, college-student-verification-plan, comprehensive-enhancements-plan, dashboard-enhancements-plan, lesson-and-reminder-features-plan, mobile-app-restructure-plan, mobile-implementation-plan, music-studio-dashboard-plan, navigation-fixes-plan, navigation-updates-plan, payment-billing-system-plan, prototype-cleanup-plan, student-enhancements-plan, superadmin-dashboard-enhancements-plan, verification-system-plan, waitlist-system-plan, college-verification-update-plan)
- **Target stage:** Reference only — never build as product
- **Reason deferred:** These are Polymet's internal architecture/design planning markdown documents, not product features. They're Polymet's equivalent of what we're writing in the grill-me tracking doc. Worth reading once for reference insights, but not part of the port.
- **Dependencies:** None
- **Risk notes:** Some may contain useful implementation guidance (e.g., `payment-billing-system-plan.md`, `mobile-implementation-plan.md`) — worth a skim during Stage 1 implementation to borrow ideas.

---

## Deferred — items found in gap-analysis pass 2026-04-14

### security-page (public marketing info)
- **Polymet source:** `security-page.tsx` (251 lines)
- **Target stage:** Stage 2
- **Reason deferred:** Public marketing page listing security features (encryption, infrastructure, privacy posture, audits). Not a launch blocker — security-conscious prospects can be directed to it post-launch.
- **Dependencies:** None

### help-center-page (support docs / FAQ)
- **Polymet source:** `help-center-page.tsx`
- **Target stage:** Stage 2
- **Reason deferred:** Stage 1 support is "email `hello@dailyriff.com`"; a full help center requires article-authoring tooling + ongoing content pipeline. Defer until first 30 studios surface the most common questions worth documenting.
- **Dependencies:** Enough support volume to justify

### parent-documents-page
- **Polymet source:** `parent-documents-page.tsx` (28 lines — literally "Coming Soon" placeholder in Polymet itself)
- **Target stage:** Stage 3+
- **Reason deferred:** Polymet never actually built this feature; page is an empty stub. Whatever "documents" means (studio policies PDFs? forms? liability waivers?) needs its own product discovery before building.
- **Dependencies:** Product discovery on what a "document" is

### mobile-component-showcase
- **Polymet source:** `mobile-component-showcase.tsx`
- **Target stage:** Never — not a product feature
- **Reason deferred:** This was Polymet's own internal design-review tool for previewing mobile components inside the web prototype. Not a user-facing feature. Delete entirely when porting.
- **Dependencies:** None

### Dashboard draggable grid
- **Polymet source:** `draggable-grid.tsx`
- **Target stage:** Stage 2
- **Reason deferred:** UX polish — users drag dashboard cards to reorder. Nice but not primary. Ship fixed layouts in Stage 1.
- **Dependencies:** None

### Export / print menus and print-friendly views
- **Polymet source:** `export-print-menu.tsx`
- **Target stage:** Stage 2-3
- **Reason deferred:** Reporting polish. CSV export of payments or attendance is useful for studios doing taxes but can be a Stage 2 feature after first tax season surfaces the demand.
- **Dependencies:** None

### Advanced filters panels
- **Polymet source:** `advanced-filters-panel.tsx`
- **Target stage:** Stage 2
- **Reason deferred:** Multi-dimensional filtering on lists (students by age range + instrument + payment status + last-lesson-date). Stage 1 ships basic single-dimension filters + text search.
- **Dependencies:** Real data volume justifies the complexity

### Student/lesson transfers between studios
- **Polymet source:** `transfer-analytics-chart.tsx`, `transfer-history-filters.tsx`, `transfer-notification-toast.tsx`
- **Target stage:** Stage 3+
- **Reason deferred:** Cross-studio flow (student moves from Studio A to Studio B, data transfers with them). Complex — touches multi-tenancy, data export, consent, payment history. Not needed until students actually transfer at meaningful volume.
- **Dependencies:** Multiple studios with overlapping student populations

### Teacher reviews / ratings system
- **Polymet source:** `reviews-dialog.tsx`
- **Target stage:** Stage 3+
- **Reason deferred:** Review system is its own feature domain: review collection, moderation, abuse handling, public display, response workflows. Premature for a Stage 1 studio-operations tool.
- **Dependencies:** Product decision on whether DailyRiff is a marketplace with public teacher profiles (currently no — private studios)

### Public teacher discovery / teacher map
- **Polymet source:** `teacher-map-dialog.tsx`
- **Target stage:** Stage 3+
- **Reason deferred:** Turns DailyRiff into a teacher-finder marketplace. Orthogonal to Stage 1 studio-operations focus. Different product direction.
- **Dependencies:** Strategic decision on marketplace vs pure SaaS positioning

### Referral program
- **Polymet source:** `refer-teacher-dialog.tsx`
- **Target stage:** Stage 3+
- **Reason deferred:** Growth feature — teachers refer other teachers for credit/reward. Meaningful only when studios are paying DailyRiff (Stage 2+) so there's something to credit.
- **Dependencies:** Stripe Connect active + revenue flowing

### Student demographics dashboard
- **Polymet source:** `student-demographics-dialog.tsx`
- **Target stage:** Stage 2-3
- **Reason deferred:** Aggregate demographic breakdowns (age distribution, instrument mix, retention cohorts). Analytics polish that works only at scale.
- **Dependencies:** Data volume

### Group lessons / message groups
- **Polymet source:** `create-group-dialog.tsx`, `message-groups` mock data
- **Target stage:** Stage 2
- **Reason deferred:** Group-lesson support (one lesson slot, multiple students, shared notes). Polymet models it but Stage 1 ships individual lessons only. Adding group lessons later is a schema addition (`lesson_participants` junction table), not a migration.
- **Dependencies:** None

### Dashboard preview dialogs (cross-persona)
- **Polymet source:** `student-dashboard-preview-dialog.tsx`, `teacher-dashboard-preview-dialog.tsx`
- **Target stage:** Stage 2-3
- **Reason deferred:** "See what your student/parent sees" preview is an admin convenience. Impersonation flow (Q17.4) covers the core use case for superadmin; teacher-to-student preview is polish.
- **Dependencies:** None

### College enrollment verification
- **Polymet source:** `CollegeVerification` interface in `music-studio-data.tsx`
- **Target stage:** Stage 2-3
- **Reason deferred:** Verify student is enrolled in college, unlock student discount. Niche — assumes DailyRiff offers student discounts, which is a pricing decision not made yet. Verification mechanics (enrollment letter upload, .edu email check) are non-trivial.
- **Dependencies:** Pricing strategy decision; Stripe Connect active

---

## Deferred — business features

### Recitals (GZ1)
- **Polymet source:** `recitals-page.tsx`, `create-recital-dialog`, `edit-recital-dialog`, `edit-recital-pieces-dialog`, `assign-recital-piece-dialog`, `update-participant-status-dialog`; `Recital`, `RecitalParticipant`, `RecitalPiece` entities in `music-studio-data.tsx`
- **Target stage:** Stage 2
- **Reason deferred:** Episodic feature (twice a year per studio, not daily). Zero dependency on core loop, so deferring costs nothing. 3-5 pages + workflow = 1-2 weeks of Stage 1 work better spent elsewhere.
- **Dependencies:** None
- **Risk notes:** If first 5 target studios cite recitals as daily-use, promote to Stage 1.

### Sheet music library (GZ2)
- **Polymet source:** `sheet-music-library-page.tsx`, `student-sheet-music-page.tsx`
- **Target stage:** Stage 2-3
- **Reason deferred:** Requires a second file-upload pipeline (PDFs, thumbnails, viewer integration). Also copyright liability — teachers uploading copyrighted material is a real DMCA surface needing legal review before enablement.
- **Dependencies:** Second R2 upload pipeline; DMCA takedown process; teacher indemnity terms in ToS
- **Risk notes:** **Legal review required before Stage 2 build.** Cannot ship without explicit teacher ToS updates around copyright.

### Dedicated reminders UI (GZ5)
- **Polymet source:** `reminders-page.tsx`, `reminders-card.tsx`, `create-reminder-dialog.tsx`, `Reminder` entity in `music-studio-data.tsx`
- **Target stage:** Stage 2 (only if user demand emerges)
- **Reason deferred:** 80% of reminder functionality is handled by the Stage 1 messaging + notifications cluster. Dedicated reminders surface is polish, not primary.
- **Dependencies:** None
- **Risk notes:** If first 20 studios complain that scheduled-self-reminders are distinct from messages, promote.

### Achievement badges / gamification
- **Polymet source:** `achievement-badges-display.tsx`, `child-achievements-dialog.tsx`
- **Target stage:** Stage 2-3
- **Reason deferred:** Rewards systems appear simple but require an event bus, a rules engine, a design discussion about what's rewarding vs. Skinner-boxy, and an ongoing content pipeline. Premature before streaks + analytics are live to observe behavior.
- **Dependencies:** Stage 1 practice streak + analytics shipped and observed for ≥1 month
- **Risk notes:** Design question is harder than engineering question. Don't skip the design discussion.

### Pricing templates management
- **Polymet source:** `manage-pricing-plans-dialog.tsx`, `pricing-templates-data.tsx`
- **Target stage:** Stage 2 (with Stripe Connect)
- **Reason deferred:** Pricing templates make sense when tuition charges actually go through the platform. In ledger MVP, studios enter amounts manually per payment.
- **Dependencies:** Stripe Connect Express onboarding (Stage 2-3)
- **Risk notes:** Schema reservation: `studios.pricing_template` jsonb column can be added now as nullable so Stage 2 doesn't need migration.

### Bank account management for studios
- **Polymet source:** `manage-bank-account-dialog.tsx`
- **Target stage:** Stage 2-3 (with Stripe Connect Express)
- **Reason deferred:** Bank accounts for studios are only meaningful once Connect is live. In ledger MVP, studios receive money outside the platform.
- **Dependencies:** Stripe Connect Express
- **Risk notes:** Stripe Connect Express embeds the bank account collection flow inside its hosted onboarding — the custom dialog may be unnecessary once Connect lands.

### Revenue trend charts / financial analytics
- **Polymet source:** `revenue-trend-chart.tsx`, `financial-overview-card.tsx`, `financial-snapshot-card.tsx`, `analytics-insights-card.tsx`, `studio-growth-chart.tsx`, `transfer-analytics-chart.tsx`
- **Target stage:** Stage 2-3
- **Reason deferred:** Dashboard polish, not primary. Stage 1 ships a simple "outstanding balance" number and a list of recent payments; that's enough for ledger MVP.
- **Dependencies:** None (can ship anytime post-MVP)

### Skill progress tracker / practice timeline charts
- **Polymet source:** `skill-progress-tracker.tsx`, `practice-timeline-chart.tsx`, `progress-milestones-card.tsx`
- **Target stage:** Stage 2-3
- **Reason deferred:** Analytics polish. Stage 1 ships streak + weekly minutes + assignment completion rate — enough for the core gamification payoff without the analytics pipeline.
- **Dependencies:** Stage 1 practice data accumulated for ≥1 month to validate what charts are useful

### Command palette / global search (⌘K)
- **Polymet source:** `search-command-dialog.tsx`, `superadmin-search-command.tsx`
- **Target stage:** Stage 2-3
- **Reason deferred:** Product polish, not primary. Postgres full-text search across 5-6 tables is an afternoon project once data volumes justify it.
- **Dependencies:** None

### Advanced settings / privacy controls
- **Polymet source:** persona-specific `*-settings-page.tsx` files (full versions)
- **Target stage:** Stage 2
- **Reason deferred:** Stage 1 ships essentials only: change password, email preferences, logout, delete account, notification toggles. Integration settings, advanced privacy, data export UI deferred.
- **Dependencies:** None
- **Risk notes:** Data export for COPPA compliance is handled manually in Stage 1 (parent emails request → you handle via Supabase Studio). Must transition to self-serve before ~100 active parents or ops burden becomes unmanageable.

### Studio profile settings (elaborate version)
- **Polymet source:** `studio-profile-page.tsx`, `teacher-profile-settings-page.tsx` (elaborate views)
- **Target stage:** Stage 2
- **Reason deferred:** Stage 1 ships a minimal profile editor (name, studio name, contact info, bio, studio code). Elaborate Polymet profile with multiple tabs, custom branding, policy documents, etc. deferred.
- **Dependencies:** None

### Onboarding celebration page
- **Polymet source:** `onboarding-complete-page.tsx`
- **Target stage:** Not building — replace with toast + redirect
- **Reason deferred:** Violates pixel-perfect rule formally, but celebratory pages are 2 seconds of UX for first-time users only. Toast is equivalent value at 1% of the build cost.
- **Dependencies:** None
- **Risk notes:** Explicit pixel-perfect rule violation. Noted for audit.

---

## Deferred — communication features

### SMS messaging (general)
- **Polymet source:** Polymet designs SMS into `send-message-dialog.tsx` as a "send via SMS" toggle, plus `sms-reminder-config.tsx`, `waitlist-sms-templates.tsx`
- **Target stage:** Stage 2+
- **Reason deferred:** 10DLC registration (1-2 weeks, $4 + monthly per brand/campaign), Twilio integration, opt-out keyword compliance, quiet hours, carrier filtering risk. Email fallback already solves "reach offline recipient" in Stage 1.
- **Dependencies:** 10DLC brand registration; Twilio account; opt-out handling
- **Risk notes:** Most requested feature by first 10 studios will likely be SMS. Plan to evaluate 10DLC registration within 2 months of Stage 1 launch.

### SMS lesson reminders
- **Polymet source:** `sms-reminder-config.tsx`
- **Target stage:** Stage 2
- **Reason deferred:** Same as general SMS — 10DLC blocker.
- **Dependencies:** Same as general SMS

### Message attachments
- **Polymet source:** `send-message-dialog.tsx` (attachment UI)
- **Target stage:** Stage 2
- **Reason deferred:** Reuses R2 upload pipeline from recordings, but adds MIME validation, size limits, moderation surface, and UI complexity. Text-only messaging is sufficient for Stage 1.
- **Dependencies:** Recording upload pipeline shipped (Stage 1 provides this as a prerequisite)

### Nested / threaded replies
- **Target stage:** Stage 2-3
- **Reason deferred:** Flat threading (one thread per conversation pair) is sufficient in Stage 1. Nested replies require a reply-to relationship model and UI for rendering trees.
- **Dependencies:** User feedback on whether flat is sufficient

### Typing indicators / presence
- **Target stage:** Indefinite
- **Reason deferred:** Premature polish. Bandwidth cost, no clear Polymet UI justification.
- **Dependencies:** None

### Inbound email reply parsing
- **Target stage:** Stage 2
- **Reason deferred:** Stage 1 email fallback is one-way: notification-only, reply happens by returning to the app. Two-way email (reply-via-email → thread) requires SPF/DKIM/DMARC setup, bounce handling, email content parsing, attachment extraction.
- **Dependencies:** Email provider upgrade (Resend → SendGrid or Postmark inbound), SPF/DKIM/DMARC config

### Waitlist blast messaging — UPDATED 2026-04-14
- **Polymet source:** `send-waitlist-message-dialog.tsx`
- **Status:** PARTIAL. Single-recipient waitlist messaging is IN Stage 1. Bulk/A/B variants remain deferred — see "Deferred — waitlist polish" section above.

---

## Deferred — payments & commerce

### Stripe Connect Express marketplace
- **Target stage:** Stage 2-3
- **Reason deferred:** Ledger MVP in Stage 1 (per Q4). Schema is Connect-ready (nullable `stripe_account_id`, `stripe_payment_intent_id`, `application_fee_amount`, `transfer_id`, `stripe_customer_id` columns reserved from Stage 1). Stage 2 turns on Connect onboarding flow + actual charges.
- **Dependencies:** Stage 1 ledger MVP shipped and validated
- **Risk notes:** Platform fee set to 3% default at Stage 2 launch. Adjustable.

### Real tuition charges
- **Target stage:** Stage 2-3 (ships with Connect)
- **Reason deferred:** Ledger MVP only in Stage 1. Actual money movement requires Connect.
- **Dependencies:** Stripe Connect Express

### 1099-K tax logic
- **Target stage:** Not building — handled by Stripe automatically when Connect lands
- **Reason deferred:** Stripe Express Connect auto-issues 1099-K to connected studios above federal/state thresholds. DailyRiff does not build this.
- **Dependencies:** Stripe Connect Express (outsources the problem)

---

## Deferred — student account lifecycle

### Age-based account conversion automation
- **Polymet source:** `src/core/domain/services/account-conversion-service.ts`, `account-conversion-dialog.tsx`
- **Target stage:** Stage 1 (MUST ship, not deferred) — but initial scope is manual conversion, not birthday-automated
- **Reason:** COPPA compliance requires 13/18 milestone handling. Stage 1 scope: dialog exists, manual trigger by parent or teacher, data migration on conversion. Birthday-triggered auto-conversion (scheduled job that prompts on birthday) is Stage 2 polish.
- **Dependencies:** Student/parent data model in Stage 1
- **Risk notes:** Moved here because I want to explicitly track that auto-birthday triggering is NOT in Stage 1 even though the conversion flow itself IS. Nuance.

---

## Deferred — compliance & certification

### COPPA Safe Harbor certification
- **Target stage:** Stage 3+
- **Reason deferred:** Certification (iKeepSafe, kidSAFE, etc.) costs $5-15k and takes months. Stage 1 complies with COPPA via Stripe micro-charge VPC + signed-form fallback without certification. Certification is a marketing + enterprise-sales enabler, not a legal prerequisite.
- **Dependencies:** Real user base, funds available
- **Risk notes:** Certification may become a prerequisite for school district sales.

### SOC 2 Type 2 audit
- **Target stage:** Stage 4+
- **Reason deferred:** Enterprise-sales enabler. Not a legal prerequisite. Meaningful cost + time.
- **Dependencies:** Enterprise sales pipeline exists

### Data retention policies (beyond simple delete-on-request)
- **Target stage:** Stage 2-3
- **Reason deferred:** Stage 1 = indefinite retention + delete on COPPA request. Structured retention (auto-purge after N years, per-data-type retention windows, anonymization rules) is Stage 2-3 polish.
- **Dependencies:** Storage costs justify the engineering

### Self-serve data export (COPPA / GDPR)
- **Target stage:** Stage 2
- **Reason deferred:** Stage 1 handles requests manually via Supabase Studio + ops email. Self-serve "download my child's data" button is Stage 2.
- **Dependencies:** Ops burden exceeds manual handling (~100 active parents)

---

## Deferred — recording pipeline polish

### TUS resumable upload protocol
- **Target stage:** Stage 2
- **Reason deferred:** Direct-to-R2 signed-URL uploads handle 5-60 min files fine over reasonable connections. Resumable TUS is polish for flaky mobile networks. Retry-from-zero on drop is acceptable in Stage 1.
- **Dependencies:** Complaints about dropped uploads on cellular

### Server-side AAC transcoding
- **Target stage:** Not building
- **Reason deferred:** All capture targets (iOS Safari, Android Chrome, Expo iOS, Expo Android) produce AAC/MP4 natively. Polymet's abandoned "edge function for AAC→MP3 conversion" solves a problem that doesn't exist with modern codec support.
- **Dependencies:** None — dismissed permanently

### Advanced recording retention / auto-cleanup policies (server-side)
- **Target stage:** Stage 2+
- **Reason deferred:** Stage 1 = indefinite server retention. Client-side cache is 10 files / 7 days per Polymet (preserved). Server-side retention policies are a cost-driven decision that can wait until storage costs force it.
- **Dependencies:** Storage cost accumulation

---

## Deferred — auth providers

### Facebook OAuth
- **Polymet source:** `oauth-facebook-page.tsx`
- **Target stage:** Stage 2+
- **Reason deferred:** Low teacher-demographic usage, extra compliance surface, not required by App Store. Google + Apple covers 95% of OAuth demand.
- **Dependencies:** Demand signal from real users

---

## Deferred — UI polish & dashboard widgets

### Practice tracking card (full version)
- **Target stage:** Stage 2
- **Reason deferred:** Stage 1 ships streak + weekly minutes + completion rate. Full Polymet practice-tracking card with multiple chart types, period selectors, and historical comparison is polish.

### Feature-demo / integration-test / time-savings dialogs
- **Polymet source:** `feature-demo-dialog.tsx`, `integration-test-dialog.tsx`, `time-savings-dialog.tsx`, `video-demo-dialog.tsx`
- **Target stage:** Indefinite
- **Reason deferred:** These look like sales/marketing demo fluff embedded in the prototype — "look at this feature!" popups, not actual product features. Likely never building.
- **Dependencies:** Confirmation that these are demo-only, not real UX
- **Risk notes:** Need to verify with user whether these are real features or prototype demo-ware.

### Studio branding / white-label — RESOLVED 2026-04-14 (Q15)
- **Status:** PARTIAL. Light-touch branding (logo + primary color from constrained palette + display name) is IN Stage 1. Full white-label features remain deferred — see below.

### Custom domains per studio
- **Target stage:** Stage 3+
- **Reason deferred:** DNS verification, TLS cert management, per-domain Next.js routing, and "domain pending verification" states are real operational overhead. Cloudflare for SaaS + Vercel domains API handle the mechanics but add cost and support burden. Deferred until there's demand from paying studios.
- **Dependencies:** Paying customers requesting it

### Custom email from-address per studio
- **Target stage:** Indefinite
- **Reason deferred:** Requires each studio to configure SPF/DKIM/DMARC on their own DNS to authorize DailyRiff's mail servers. Most music teachers don't know what DKIM is. Stage 1 solution: `"{Studio Name} via DailyRiff" <hello@dailyriff.com>` display name, which preserves studio identity in the `From:` line without per-studio DNS work.
- **Dependencies:** Probably never worth the support burden

### Custom typography per studio
- **Target stage:** Indefinite
- **Reason deferred:** Google Fonts integration + per-studio font loading + performance concerns. Design system polish, not user value.
- **Dependencies:** None — likely never

### Free-form hex color input for studio branding
- **Target stage:** Indefinite
- **Reason deferred:** Accessibility risk (teacher picks neon yellow; WCAG contrast breaks). Stage 1 ships a constrained 12-swatch palette of WCAG-AA-tested colors to eliminate this risk. Free-form hex would require runtime contrast-ratio validation + fallback logic.
- **Dependencies:** None — likely never

### Custom layout variants per studio
- **Target stage:** Indefinite
- **Reason deferred:** Architectural complexity for marginal benefit. Studios customize colors + logo, not page structure.
- **Dependencies:** None

---

## Indefinitely deferred / probably never

### Biometric authentication (Face ID / Touch ID)
- **Reason:** Native-only, premature for web-first product

### Offline-first SQLite / IndexedDB sync
- **Reason:** Polymet docs claim this but never implemented. Client-side cache (10 files / 7 days) covers 80% of the value at 5% of the cost.

### Background recording support
- **Reason:** Web can't do it; native would require Expo. Polymet's prototype doesn't demand it.

### A/B testing framework (general, not waitlist-specific)
- **Polymet source:** `email-ab-testing-manager.tsx`
- **Reason:** Waitlist A/B is moved to "Deferred — waitlist polish" above. General cross-product A/B testing is premature until real traffic exists.

### Webhook configuration UI (studio-facing)
- **Polymet source:** `webhook-config-dialog.tsx`
- **Reason:** Integrations feature, superadmin-scoped, deferred with superadmin.

---

## Pre-launch compliance + legal action items

These are non-feature work items that are blockers for Stage 1 launch. They are not "deferred features" — they are **launch prerequisites**. Track each through completion before Stage 1 goes live.

### Terms of Service
- **Status:** NOT WRITTEN
- **Owner:** Rollin + legal counsel
- **Must document:**
  - **Impersonation policy** (Q17.4): studios agree that DailyRiff support may access their account for support purposes, with notification after-the-fact, reason logged, restricted scope (no destructive actions)
  - **Platform marketplace model** (Q4): no SaaS fee charged to studios in Stage 1; future platform fee on tuition payments disclosed as planned
  - **Studio responsibilities**: accurate data entry, compliance with local music teaching regulations, honoring refund/cancellation policies set in their own finances
  - **Content ownership**: studios retain ownership of student recordings and data; DailyRiff holds storage + processing rights only
  - **Dispute resolution**: arbitration clause (typical), governing law, venue
  - **Acceptable use**: no harassment, no illegal content, no copyright infringement, no uploading others' copyrighted sheet music (anticipating Stage 2)
- **Blocker:** Cannot accept studio signups before ToS exists
- **Target date:** Before first waitlist approval

### Privacy Policy
- **Status:** NOT WRITTEN
- **Owner:** Rollin + legal counsel (edtech-experienced)
- **Must document:**
  - **COPPA compliance**: under-13 data collection practices, parental rights, how to review/delete/revoke, contact info for privacy officer (you, or designated role)
  - **VPC methods** (Q7): Stripe micro-charge + signed-form escape hatch, how consent evidence is stored, retention
  - **Data categories collected**: audio recordings, names, emails, payment data, usage analytics, device info
  - **Data retention**: 15-day grace period deletion (Q16.3), indefinite server retention until parent requests deletion, client-side cache 10 files / 7 days
  - **Data sharing**: Supabase (processor), Cloudflare R2 (storage), Stripe (payments), Postmark (email), Sentry (error monitoring), PostHog (analytics). Each with its own DPA.
  - **Parental rights**: access, delete, revoke, export (manual in Stage 1)
  - **Cookies and tracking**: what's set, why, consent mechanism
  - **Child safety**: no public profiles, no student-to-student messaging, no cross-studio data access
  - **State-specific disclosures**: California (CCPA-for-minors), Illinois (BIPA if any biometrics added later), etc.
- **Blocker:** Cannot accept any signup before privacy policy exists
- **Target date:** Before first waitlist approval

### Legal review: Sentry replay masking approach (Q17.3)
- **Status:** NOT STARTED
- **Owner:** Rollin + privacy counsel
- **What to review:** whether the "mask all inputs + text + media by default, disable entirely on parent/student routes" approach satisfies COPPA's prohibition on collecting PI from children without consent
- **Budget:** ~$500-1000 for 1 hour with an edtech-experienced privacy lawyer
- **Blocker:** Cannot enable Sentry replay in prod without sign-off
- **Target date:** Before Stage 1 prod deploy

### Legal review: R2 30-day versioning window COPPA carve-out (Q25.d)
- **Status:** NOT STARTED
- **Owner:** Rollin + privacy counsel
- **What to review:** whether the 30-day R2 object-versioning retention window satisfies COPPA's "delete on parent request" requirement when paired with (a) the 15-day soft-delete grace period, (b) the delete-marker making bytes inaccessible to all users during the versioning window, and (c) explicit disclosure of the window as a "recoverable deletion period" in the privacy policy. If counsel says no, fallback is a 1-day versioning retention on hard-deleted COPPA objects specifically.
- **Bundled with:** existing Q17.3 / Q17.4 legal review (same lawyer, same session, same ~$500-1000 budget)
- **Blocker:** Cannot enable R2 versioning on the prod recordings bucket without sign-off
- **Target date:** Before Stage 1 prod deploy

### Legal review: Impersonation policy (Q17.4)
- **Status:** NOT STARTED
- **Owner:** Rollin + legal counsel
- **What to review:** whether delayed-notification impersonation (without prior consent) is enforceable in ToS, what disclosure language is needed, whether audit retention is sufficient
- **Bundled with:** ToS review above (same lawyer, same session)
- **Blocker:** Cannot use impersonation in prod without sign-off
- **Target date:** Before Stage 1 prod deploy

### DNS setup for email deliverability
- **Status:** NOT STARTED
- **Owner:** Rollin (with Postmark setup wizard)
- **Work:** Configure SPF, DKIM, DMARC records on `dailyriff.com` to authorize Postmark as a sender. Verify with Postmark's testing tools. Run MXToolbox or Mail-Tester check to confirm deliverability score ≥9/10.
- **Blocker:** Low score = invitation emails land in spam = signup funnel broken
- **Target date:** 2 weeks before Stage 1 launch (allows reputation warm-up time)

### Stripe account setup + COPPA VPC disclosure
- **Status:** NOT STARTED
- **Owner:** Rollin
- **Work:** Create DailyRiff Stripe account in test mode (dev/staging) and live mode (prod). Configure Setup Intent flow for COPPA VPC. Document the $0.50 micro-charge disclosure language shown to parents during VPC flow. Ensure the micro-charge description string in Stripe is clear (e.g., "DAILYRIFF VERIFICATION - REFUNDED").
- **Blocker:** Cannot collect VPC without this
- **Target date:** Before Stage 1 prod deploy

### Superadmin TOTP break-glass runbook (Q20)
- **Status:** NOT WRITTEN
- **Owner:** Rollin
- **Work:** Document the emergency procedure for the sole-owner lockout scenario: direct Supabase Studio SQL access path to clear the MFA requirement on the owner's auth row, stored in a location Rollin can access without logging into DailyRiff itself. TOTP recovery codes generated at enrollment must be stored in password manager + printed offsite backup (safe deposit box or fireproof home safe) before going live.
- **Blocker:** Cannot enable mandatory superadmin TOTP without a documented recovery path — a solo operator locking themselves out of their own platform with no recovery is an unacceptable failure mode.
- **Target date:** Before first superadmin TOTP enrollment in prod

### DailyRiff employee agreements (for future staff)
- **Status:** NOT NEEDED YET (solo operator in Stage 1)
- **Owner:** Rollin when first hire happens
- **Work:** Standard confidentiality + IP assignment agreements for any DailyRiff employees with access to studio/student/parent data. Required before granting non-owner roles in the superadmin system.
- **Blocker:** Cannot grant support/verifier role access to a non-employee
- **Target date:** Before first hire (possibly post-Stage 1)

### Incident response plan
- **Status:** NOT WRITTEN
- **Owner:** Rollin
- **Work:** Document what to do if: data breach, child data exposure, Stripe account compromise, Supabase outage affecting compliance, subpoena for child data. Include notification timelines (COPPA breach notification is "without unreasonable delay"), who to contact, what to preserve.
- **Blocker:** Not a launch blocker, but required within first 90 days of prod
- **Target date:** 60 days post-launch

### COPPA complaint handling address
- **Status:** NOT SET UP
- **Owner:** Rollin
- **Work:** Designate a privacy contact email (e.g., `privacy@dailyriff.com`), wire it to your inbox, publish in privacy policy + footer. Commit to responding within statutory timeframes (30 days for most parental requests).
- **Blocker:** Privacy policy cannot be published without this
- **Target date:** Before first waitlist approval

---

## Questions still open in grill-me (not yet deferred, just unanswered)

All Stage 1 scoping questions resolved as of 2026-04-14. Any new unknowns surface in the next grill-me pass.

---

## Update log

- **2026-04-14** (grill-me session): Initial creation with all deferrals from Q2–Q13. Superadmin, teacher/parent mobile apps, Recitals, Sheet music, Reminders, Achievements, Pricing templates, Bank account, Revenue charts, Skill progress, Command palette, Advanced settings, Elaborate profile, Onboarding celebration, SMS messaging + reminders, Message attachments, Nested threading, Typing indicators, Inbound email, Waitlist messaging, Stripe Connect, Real tuition, 1099-K, Auto birthday conversion, COPPA Safe Harbor, SOC 2, Structured retention, Self-serve data export, TUS upload, Server AAC transcoding, Server retention policies, Facebook OAuth, Practice tracking full, Demo dialogs, Studio branding (tentative), Biometrics, Offline sync, Background recording, A/B testing, Webhooks.

- **2026-04-14** (rigorous audit agent pass — gap-analysis pass 2): Ran a dedicated Explore agent to audit every file under `src/polymet/` against the tracking doc. Findings:
  - **Added to In Stage 1 (missed by informal pass 1):** `studio-onboarding-page`, `teacher-profile-settings-page`, `studio-profile-page`, `theme-toggle`, `guardian-detail-dialog`, `lesson-history-card`, `account-conversion-dialog` (manual trigger; birthday-auto still deferred)
  - **New deferrals captured:** undo/redo cross-cutting pattern (Stage 2-3)
  - **Category ignores confirmed:** `/examples/` directory (~227 render harness files, all paired with parent components already classified — complete category ignore), `/plans/` directory (~19 internal Polymet design docs — reference only, never build)
  - **Agent classification errors corrected:** agent misread tracking doc and listed `oauth-apple-page` as Stage 3+ (wrong — Q13 committed Apple IN), `account-conversion-dialog` as deferred (wrong — manual flow IS in Stage 1), `platform-pricing-data` as IN "free tier only" (wrong — Q14a Decision 5 confirmed no SaaS fees, IGNORE as reference to non-existent feature)
  - **Cross-cutting concerns agent surfaced, status check:** optimistic UI (covered by Supabase Realtime), undo/redo (now deferred above), impersonation audit (Q17.4), COPPA deletion (Q16.3), recording upload retry (Q9), session state management (implementation detail), email notification orchestration (Q12 + Postmark), multi-child batch signup (Q14b), studio RBAC (Stage 1 = teacher-owner only; fuller roles deferred), Expo screens (separate repo, not in web audit)
  - **Final confidence:** no critical product features are silently missing from scope. Every file under `src/polymet/` now has an explicit disposition.

- **2026-04-14** (gap-analysis pass): Systematic review of all Polymet pages and components against grill-me decisions to ensure nothing was silently ignored. Result: 6 marketing/static pages added to In Stage 1 scope (home, about, contact, privacy-policy, terms-of-service, accessibility), 9 feature items added to In Stage 1 scope (student-practice-sessions-page, report-absence-dialog flow, lesson-recording-player, breadcrumb-navigation, dashboard-alert-banner, plus 4 already-implicit items flagged explicitly), 14 new deferred entries added (security-page, help-center-page, parent-documents-page, mobile-component-showcase, draggable-grid, export-print-menu, advanced-filters-panel, transfer-* trio, reviews-dialog, teacher-map-dialog, refer-teacher-dialog, student-demographics-dialog, create-group-dialog/message-groups, dashboard-preview dialogs, college-verification). Polymet internal design docs (ada-compliance-summary, coppa-compliance-guide, navigation-improvements-summary, parent-dashboard-enhancements, waitlist-enhancements-summary, backend-integration-points, employee-roles-guide, platform-pricing-data) confirmed as ignore — they are Polymet planning artifacts, not product features. No silently-ignored items remain.

- **2026-04-14** (grill-me Q29): Beta rollout plan resolved. 3-5 studios (hard cap 5), personal-network + warm-intro sourcing only. White-glove support: onboarding Zoom calls, shared Slack Connect channels, weekly check-ins, manual data-entry assistance, zero-friction bug reporting. Graduation criteria (all four): 60% retention at 6 weeks, 70% student engagement, zero P0 bugs in final 2 weeks, Sean Ellis PMF signal from ≥2 teachers. Duration: 6 weeks min / 12 weeks max. Post-beta: gradual GA at 5-10 studios/week for 8 weeks before reconsidering auto-approve. Scope adds: private beta landing page, beta email sequence, `studios.beta_cohort` flag, `beta_feedback` table + `/beta/feedback` form.

- **2026-04-14** (grill-me session complete): All Stage 1 scoping questions (Q2-Q29) resolved across multiple grill-me passes and audit agent passes. Stage 1 scope is frozen. Doc transitions from "living during grill-me" to "authoritative input for `/write-a-prd` → `docs/prds/stage-1-foundation.md`." Future updates happen only on explicit re-scoping decisions.

- **2026-04-14** (grill-me Q28): Secret inventory + rotation resolved. 18 secret classes cataloged with blast radius, canonical storage (1Password as source of truth), and tiered rotation cadences (90 days for catastrophic; 180 for payment/email; 365 for session-nuking JWT signing; vendor-interval for mobile submission keys). `secret_rotation_schedule` table tracks due dates with 7-day advance email reminder via pg_cron. Canonical 8-step rotation runbook (1Password first, then derived copies). Pre-launch blockers: 1Password vault setup, runbook written, schedule table seeded, dev laptop encrypted.

- **2026-04-14** (grill-me Q27): Observability + on-call resolved. BetterStack free-tier uptime (phone+push P0 channel, public status page). Sentry/PostHog/Supabase/Cloudflare/Stripe/Postmark alerting tiered P0/P1/P2. `pg_cron` heartbeat pattern for silent-cron detection. Solo-operator SLA: 15min P0 waking, 30min overnight, P1 within 2h. Vacation coverage disclosed in ToS as "P0 may wait until Rollin is back." Incident break-glass runbook added as pre-launch blocker. Stage 1 observability incremental cost: $0.

- **2026-04-14** (grill-me Q26): Browser / device support matrix committed. Desktop: last 2 stable of Chrome/Edge/Firefox/Safari. Mobile web: iOS Safari 15+, Android Chrome last 2 stable. Expo: iOS 15.1+ / Android 7 (API 24)+. Recording: MIME-negotiated Opus or AAC, hard-fail on unsupported, no server transcoding. CI: Playwright × Chromium/Firefox/WebKit for smoke + manual real-Safari + real-iPhone + real-Android per release. Explicit won't-fix list: IE, Opera Mini, Samsung Internet untested, headless browsers blocked at Cloudflare.

- **2026-04-14** (grill-me Q25): R2 backup / DR for recordings resolved. Tier 1: R2 object versioning with 30-day retention (~$0.75/mo). Tier 2: application-level soft delete extended to every delete path. Tier 3 (cross-cloud Glacier): deferred to Stage 2. R2 credentials split into read+write+presign (FastAPI) vs delete-only (pg_cron worker) for blast-radius limitation. COPPA carve-out: 30-day versioning window disclosed in privacy policy as "recoverable deletion period," bundled into the existing legal review. Restore and forensics runbook items added as pre-launch blockers.

- **2026-04-14** (grill-me Q24): Rate limiting + abuse prevention resolved with four-layer defense (Cloudflare WAF → FastAPI slowapi → GoTrue built-ins → business-rule caps). Webhook replay defense via idempotency_log. Auth enumeration defense. hCaptcha on public forms. R2 cost alerts at $10/$20/$40. **Introduced cross-cutting "platform-settings" principle:** every app-owned tunable lives in a `platform_settings` table and is editable live from a new `superadmin-platform-settings-page` with audit trail. Vendor-side settings (Cloudflare, GoTrue) are read-only mirrors sourced from the prod deploy runbook. Superadmin Stage 1 page count grows from 7 to 8.

- **2026-04-14** (grill-me Q23): Superadmin bootstrap resolved. One-shot `apps/api/scripts/bootstrap_first_owner.py` with hard sanity checks (empty employees table + existing auth user + pre-enrolled TOTP). TOTP enrollment happens via Supabase Auth's native flow before the script runs. Same script runs against staging first for prod path validation. No break-glass twin script — destructive ops live in the Q20 break-glass runbook as documented SQL only.

- **2026-04-14** (grill-me session paused mid-Q23, end of workday): Q18-Q22 closed (playback auth, mobile CI, Supabase migrations, superadmin 2FA, launch criteria, timezones). Q23 superadmin bootstrap in progress — recommendation delivered (Option B: one-shot `bootstrap_first_owner.py` script with hard sanity checks), user not yet responded to sub-questions a-d. Remaining grill queue after Q23: Q24 rate limiting, Q25 R2 backup/DR, Q26 browser/device matrix, Q27 observability alerting, Q28 secret rotation, Q29 beta rollout plan. All tracked in TaskList.

- **2026-04-14** (grill-me Q22): Timezone + locale resolved. Studio-local TZ canonical via `studios.timezone` IANA column; all scheduling/reminders resolve against studio TZ. Always-display-studio-local with TZ abbreviation visible (no viewer-local conversion). `timestamptz` storage, `pg_cron` runs in UTC with `AT TIME ZONE` conversion. Studio TZ change does not auto-migrate existing events (Stage 2 rebase feature). en-US only, no i18n framework, deferred indefinitely.

- **2026-04-14** (grill-me Q21): Stage 1 launch criteria / definition-of-done formalized. Launch = first full real-user end-to-end loop + 48h soak + zero P0/P1. Four pre-launch gates (legal, security, quality, operational) with explicit checklists. P0-P3 severity rubric defined. Ship decision is objective-criteria-only, no judgment-call tiebreaker. No formal post-launch canary phase (informal monitoring only, straight to Stage 2 planning).

- **2026-04-14** (grill-me Q20): Superadmin account security resolved. TOTP mandatory for all DailyRiff employees (hard-block without); no SMS; WebAuthn deferred to Stage 2 (GoTrue gap). Studio-side TOTP optional+nagged; parent/student no 2FA. Superadmin session 8h/1h-idle. Solo-owner recovery via password-manager-stored recovery codes + documented Supabase Studio break-glass runbook (new pre-launch blocker). Failed-auth alerting at 3 attempts/15min. All MFA events audit-logged.

- **2026-04-14** (grill-me Q19): CI/CD extensions resolved. **Q19.1 Mobile EAS:** tag-triggered production builds only (`mobile-v*` tags) via `eas build` + `eas submit` to TestFlight + Play Internal Testing; `mobile-hotfix-*` tags trigger `eas update` OTA; `workflow_dispatch` for ad-hoc. One `production` profile; no per-PR EAS builds; no `preview` profile. Per-PR validation stays at jest-expo + tsc --noEmit. **Q19.2 Migrations:** Alembic stays as app-table source of truth; `supabase db push` for RLS/auth objects only. Staging auto-applies on merge to master + re-seeds; prod requires GitHub environment approval gate with SQL preview artifact. Expand-then-contract enforced by PR checklist; forward-fix only for schema rollback; Supabase PITR as data safety net. **Tier decision:** Pro for prod ($25/mo, non-negotiable for auto-pause avoidance + PITR), Free for staging (re-seedable). Total Stage 1 Supabase cost: $25/mo.

- **2026-04-14** (grill-me Q18): Recording playback authorization model resolved. Default-deny allow-list (student + parents + assigned teacher + studio owner; superadmin only via impersonation). Enforcement via FastAPI-minted 5-min presigned R2 URLs; no proxy streaming. Impersonation playbacks logged to `impersonation_playback_log`; normal playbacks not audited. Download-resistance explicitly a non-goal (soft `controlsList="nodownload"` only). Co-teacher access, external shares, and hard DRM deferred to Stage 2-3.

- **2026-04-14** (grill-me Q17): Final housekeeping bundle resolved.
  - Q17.1 Data seeding: hybrid — Polymet mocks verbatim + synthetic edge-case generator
  - Q17.2 Email provider: Postmark + React Email
  - Q17.3 Analytics: PostHog events only (no session replay) + Sentry masked error replay with nuclear defaults
  - Q17.4 Impersonation: delayed-notification with live-mode override; required reason field; restricted scope
  - Added new section "Pre-launch compliance + legal action items" tracking 9 non-feature launch blockers: ToS, privacy policy, Sentry replay legal review, impersonation policy legal review, DNS setup, Stripe account setup, employee agreements (future), incident response plan, COPPA complaint handling address. All Stage 1 launch blockers except two (employee agreements post-Stage-1 if no hires; incident response plan 60 days post-launch).

- **2026-04-14** (grill-me Q14a Decision 5): DailyRiff business model confirmed as pure marketplace — studios use the platform free, DailyRiff monetizes only via platform fee on tuition payments (Stage 2+ via Stripe Connect). Consequences:
  - `superadmin-billing-page` moved from In Stage 1 scope to Deferred (Stage 2-3)
  - `EmployeePermissions` billing role moved from Stage 1 to Stage 2-3
  - `studios` table schema simplifies: no `subscription_id`, no `subscription_status`, no `trial_ends_at`. Just `stripe_account_id nullable` for future Connect payouts.
  - Stage 1 Stripe surface is ONLY the COPPA VPC Setup Intent flow on parent cards ($0.50 auth+void). Zero revenue to DailyRiff in Stage 1.
  - Stage 1 superadmin core drops from 8 pages to 7.

- **2026-04-14** (grill-me Q14-pre correction): Superadmin was INCORRECTLY deferred in the initial creation. Corrected per user direction:
  - **Un-deferred and moved to IN Stage 1 scope:** Superadmin core (8 pages: dashboard-home, studios, studio-detail, users, user-detail, verification-queue, billing, employees), waitlist core (waitlist page + approve-waitlist dialog + single-recipient waitlist messaging + public waitlist-invite-signup + waitlist-confirmation pages), DailyRiff employee auth + role-based permissions (owner/support/billing/verifier), impersonation flow with audit logging, real Stripe subscription billing for studios paying DailyRiff SaaS fee.
  - **Newly itemized as deferred (replacing "superadmin entire"):** superadmin-analytics-page, superadmin-logs-page (UI; table kept for audit), superadmin-notifications-page (blast), superadmin-invitations-page (non-waitlist outbound), superadmin-integrations-page, superadmin-system-page, superadmin-search-command.
  - **Newly itemized as deferred (waitlist polish):** Waitlist A/B testing, waitlist email template manager, waitlist SMS templates, waitlist reminder scheduler, waitlist analytics dashboard, waitlist blast messaging (bulk variants).
  - **Restructured file:** Added "In Stage 1 Scope" section at top. Renamed file purpose from "Explicitly Deferred Features" to "Feature Inventory (In Scope + Explicitly Deferred)" to track both current and future items.
  - **Scope impact:** Stage 1 page count grows from ~40-50 to ~55-70. Stage 1 timeline grows by ~3-4 weeks for superadmin work plus ~1-2 weeks for waitlist core. New infrastructure: DailyRiff employee auth + role system, Stripe subscription billing for studios, impersonation with audit.
