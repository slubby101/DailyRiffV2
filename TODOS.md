# DailyRiff TODOS

Items deferred from the Stage 1 planning cycle (2026-04-15) that should be revisited before or during Stage 2 planning. The authoritative scope tracker for **features** deferred to Stage 2+ lives in `docs/prds/stage-1-deferred-features.md`. This file captures **process / review / engineering debt** items that aren't features themselves.

---

## Deferred from this review cycle

### Outside-voice plan review — RAN 2026-04-15, findings parked for next cycle
- **What:** Codex CLI (`codex-cli 0.120.0`, reasoning effort = high) reviewed `docs/prds/stage-1-foundation.md` after the inside pipeline (grill-me Q1–Q29, design review, eng review F1–F11) had landed.
- **Status:** Findings NOT applied. User instructed "ignore all codex for now, document for next dev cycle."
- **One exception applied:** Codex #19 surfaced that the PRD's "Further Notes" section still said Stage 1 "retires `auth.py` and `realtime_outbox`" even though the Architecture section had been corrected earlier in the session to say both are preserved. This was an internal contradiction in the PRD (a bug in my prior edits, not a codex recommendation). Fixed in the same commit that added this TODOS section. Revert via `git revert` if you want the codex finding to be fully parked.

### Codex findings parked for next dev cycle review

Codex returned 20 substantive findings. All 20 remain actionable. Review them at Stage 2 kickoff OR when revisiting Stage 1 scope mid-beta. Grouped by type below. Raw codex output not preserved in the repo (it's in the session transcript + gstack analytics at `~/.gstack/analytics/`).

#### Bucket A — Contradictions / bugs (1 applied, rest parked)

- **C19 (APPLIED):** PRD "Further Notes" section contradicted the Architecture section on Stage 0 auth widening + `realtime_outbox` retention. Fixed.

#### Bucket B — Real technical gaps the inside review missed (8 findings, all parked)

- **C3 — Identity model collisions.** Can one `auth.users` row be owner+teacher, parent+teacher, parent across multiple studios, or student→teen→adult without table/role collisions? The PRD names `students`, `parents`, `teachers`, `dailyriff_employees` tables but never specifies the join pattern. Affects schema and auth for every persona-scoped router. **Where to fix:** new "Identity model" subsection in PRD § Implementation Decisions, committed to a single-row-per-auth-user `profiles` table with persona enum + explicit `studio_members` junction.
- **C4 — Assignment state machine fuzzy.** `assignments.status ∈ active/completed/overdue` is defined but not *what makes* an assignment complete (first valid recording? teacher-marked? multiple recordings count?). Also: late uploads after due_date — do they still ack? Re-open completed? **Where to fix:** new "Assignment lifecycle" subsection.
- **C5 — CRITICAL: Server-side duration verification missing.** PRD's 300–3600 second DB CHECK constraint only validates whatever value the client sends. A malicious student can send `duration_seconds=360` for a 10-second recording and the server accepts. **The entire "proof of practice" claim is fake without server-side audio decode.** **Where to fix:** add requirement that `upload-complete` runs `ffprobe` or `mutagen` on the R2 object and rejects if measured duration diverges from client-reported by >5%. DB CHECK becomes secondary defense.
- **C7 — COPPA deletion scope incomplete.** PRD covers DB + R2 but NOT: Supabase PITR (7-day retention), daily Supabase backups, Postmark email logs, Sentry events with user context, PostHog events, BetterStack logs, **local Expo mobile device caches**. "Permanent deletion" is undefined across the real data estate. **Where to fix:** add "COPPA deletion surface area" table mapping every data sink to its deletion mechanism, retention, and whether vendor-assisted.
- **C8 — R2 versioning + PITR vs deletion promise = architectural dependency.** PRD's Q25.d carve-out treats it as a legal review item; codex argues it's an architectural decision that can invalidate the storage strategy late. **Where to fix:** elevate from "legal review" to "pre-implementation decision" OR default to 1-day versioning retention for COPPA objects now.
- **C9 — Offline recording cache = regulated storage.** Expo 10-recording local cache on child's phone is outside deletion control. If consent is revoked or child is deleted, recordings on the device linger. **Where to fix:** on app launch, read each cached recording's child consent status; wipe if revoked or pending_deletion; fail-safe wipe all cached recordings if API unreachable for >24h.
- **C11 — Alembic + `supabase db push` split creates disagreement windows.** Code can land before its RLS policy does. Inside review noted the split but treated it as benign. **Where to fix:** require any slice adding a tenant-scoped table to ship both scripts in the same PR / same merge / same CI run, enforced by CI.
- **C12 — "Audit trail first" contradicted by manual Supabase Studio operations.** PRD principle says every sensitive op writes to `activity_logs` first. But manual ops (seed scripts, break-glass runbooks) via Supabase Studio bypass FastAPI entirely. **Where to fix:** amend principle — every *application-layer* op writes audit; manual ops must write to `activity_logs` via SQL snippet in the runbook, and `activity_logs` gains a `source enum('app', 'manual_sql', 'pg_cron')` column.

#### Bucket C — Strategic scope concerns (9 findings, all parked)

Codex argues Stage 1 is overscoped for a solo-operator serving a 3–5 studio warm-intro beta. Individual findings:

- **C1 — Plan too big for solo-operator MVP.** Web for 4 personas + Expo + realtime + push + messaging + payments ledger + waitlist + superadmin suite + compliance + formal a11y = "small SaaS company roadmap," not a beta foundation.
- **C2 — Drop Expo mobile for Stage 1.** Mobile web recording is enough for 3–5 studios. Expo doubles release, QA, auth, notification, media, and support burden before PMF signal exists. **Claude's read:** partial agree — worth serious consideration; would save ~2 slices and all EAS/signing headache. If mobile browser recording works, defer native Expo to Stage 1.5.
- **C13 — `platform_settings` overreach.** Making nearly every knob live-editable adds a second product to build (config validation, blast-radius control, rollback, cache coherency). **Claude's read:** partial agree — keep the table + service (other services read from it); defer the live-editable superadmin UI to Stage 2.
- **C14 — Notification system oversized and race-prone.** Realtime + polling fallback + email fallback + web push + Expo push + templates + prefs + queues + cron drains is too many moving parts for "teacher hears about recording" + "user hears about message." **Claude's read:** disagree — the complexity is inherent to 3-channel delivery. Simpler would mean dropping push, which hurts the product.
- **C15 — Lesson system under-modeled.** Recurrence + DST + attendance + absences + makeups + calendar export needs explicit exception semantics. The simple rows + recurrence flags schema isn't enough. **Claude's read:** agree — this is a real gap. Recurring lesson exception handling is a known-hard modeling problem. Worth adding a "Lesson exception model" subsection.
- **C16 — Payments ledger = liability magnet with weak upside.** Manual charges/refunds/balances without real processing will create disputes and bad data you later unwind. **Claude's read:** partial agree — could ship even simpler: display-only for parents, teacher-entered data with no invariants enforced, explicit "this is a notebook not a ledger" disclaimer. Revisit when Stripe Connect lands in Stage 2.
- **C17 — Public waitlist miscalibrated for warm-intro beta.** Invite-only is simpler and safer for the first 3–5 studios. Public acquisition surfaces are attack surface + support load before the loop is proven. **Claude's read:** agree — ship a private beta landing page with token-gated invitation, defer the public waitlist form to Stage 1.5 when traffic warrants it.
- **C18 — Launch gates not aligned with team size.** 7 straight green days + manual a11y per persona + multi-engine + multi-device + legal + runbooks + app-store flow + 48h observation is "a serious org's release checklist." Solo operator will slip forever or silently stop honoring the bar. **Claude's read:** disagree — the gates are a forcing function for a high-stakes COPPA product. Relaxing feels like permission to ship sloppy. But the 7-day CI green requirement specifically could relax to 48h.
- **C20 — Operator scale before user value.** Building employees page, secret-rotation UI, platform-settings UI, beta-feedback surface, verification queue, access-logs viewer before proving teachers and students actually use the recording loop is backwards. **Claude's read:** partial agree — impersonation + verification queue are launch-critical (COPPA + support). Employees page, secret-rotation UI, and platform-settings UI can defer to Stage 1.5.

#### Bucket D — Technical detail (2 findings, parked)

- **C6 — Raw browser-recorded audio without transcoding is a product risk.** Codec fragmentation, playback inconsistencies, file-size variance, cross-browser debugging on the most important workflow. **Claude's read:** disagree with codex — PRD intentionally preserves Stage 0's "no AAC transcoding" decision, and MediaRecorder across modern browsers produces playable output via `<audio>`. Revisit only if real beta studios hit playback bugs.
- **C10 — Staging contradiction.** PRD says "staging = reseedable demo on free tier" AND "staging running full copy of prod for 7 days with no drift." These are different environments with different risk rules. **Claude's read:** agree — the language is inconsistent. Should clarify: staging is reseedable demo for development; a separate "pre-prod soak" environment runs for the 7-day pre-launch gate, or the 7-day gate is moved to running against prod itself (canary-style).

### Recommended next-cycle review sequence

1. **First, resolve Bucket B findings** (8 real technical gaps). These are bugs/gaps, not scope calls. Apply fixes to PRD before any Stage 2 planning happens.
2. **Then, work through Bucket C with explicit scope decisions** at Stage 1 midpoint review (~3 weeks into implementation, when the core loop slices are landing). This is the right moment to ask "is anything we scoped actually unnecessary?" because you'll have real data on Ralph throughput.
3. **Bucket D is lowest priority** — revisit only if implementation surfaces the issue.

### Visual mockups for 4 focus surfaces (deferred 2026-04-15)
- **What:** Generate approved mockups for marketing homepage (#24), student recording flow (#28), teacher pending-reviews (#28), studio onboarding (#25) using the gstack designer against `docs/DESIGN.md` as the calibration target.
- **Why:** These are the four surfaces where design decisions drive the product's success or failure. Right now implementers have text specs but no visual reference. Mockups crystallize intent and prevent drift.
- **When:** Before each respective slice's implementation kicks off. Not blocking — text specs + DESIGN.md are enough for Ralph to proceed — but strongly recommended for #24 especially (marketing homepage is the highest-risk surface for AI slop).
- **Context:** The gstack designer binary is available at `~/.claude/skills/gstack/design/dist/design.exe`. Each surface takes ~3 min to generate 3 variants + comparison board.
- **Command:** `$D variants --brief "<per-surface brief from PRD>" --count 3 --output-dir ~/.gstack/projects/dailyriffv2/designs/<surface>-<date>/`
- **Output destination:** `~/.gstack/projects/dailyriffv2/designs/` (never commit to repo).

### Marketing copy + legal voice review (Slice 34 / #51)
- **What:** Real copy for marketing homepage, about, contact, privacy policy, ToS, accessibility statement — and final voice tone across all user-facing flows.
- **Why:** PRD § Voice & Copy commits to rules (no "Welcome to DailyRiff," no "Unlock the power of") but doesn't produce real copy. Implementation will ship placeholder "DRAFT — legal review pending" banners per the design review decision.
- **When:** Before launch. Currently scoped inside Slice 34 / #51 as part of the launch gate pack. Requires edtech-experienced counsel engagement.
- **Context:** Stage 1 PRD § Voice & Copy has the rules but not the output. Privacy policy is the largest chunk (needs to include R2 30-day versioning COPPA carve-out, cookie table, PostHog disclosure, Sentry replay masking disclosure).
- **Action:** Part of Slice 34 / #51 — engage counsel + internal voice lead when the UI shell is 60%+ shipped.

---

## Post-launch design re-evaluation (Stage 1.5)

Four design decisions in Stage 1 are opinionated defaults that should be validated against real studio feedback. Revisit after 6–12 weeks of beta usage, coincident with beta graduation criteria (Q29).

- **Fraunces display font** — does the editorial warmth land with real teachers and students, or do they find it harder to scan than sans? Check: heatmap data on dashboard dwell time, qualitative beta feedback forms, NVDA+VoiceOver user comments.
- **Warm amber brand primary** — does the amber feel warm-intentional or dated? Check: beta studio feedback on first-impression color reaction, whether studios override it via the 12-swatch picker.
- **12-swatch per-studio palette adoption** — do studios actually customize, or leave DailyRiff default? If <20% of studios change it, the 12-swatch feature is engineering waste. If >60% change it, add more swatches or allow custom hex.
- **Mobile UI library deferral** — Stage 1 ships pure RN StyleSheet + small local primitives (no NativeWind/Tamagui). Revisit when mobile screen count grows beyond the initial 5. If screens take >1 day each because of style boilerplate, add NativeWind.

---

## Engineering debt deliberately incurred in Stage 1

These are decisions to ship with known limitations because alternatives would bloat Stage 1. Each has a clear trigger for when to revisit.

### In-process caches (single Railway instance assumption)
- **`platform_settings` 30-sec TTL cache** — in-process, stale for 30s on writes from a different instance. Stage 1 runs a single Railway instance, so this is fine. **Revisit when:** adding a second Railway instance.
- **JWKS cache in `auth.py`** — in-process, same problem. **Revisit when:** horizontal scale OR JWKS rotation frequency exceeds cache TTL.
- **slowapi rate limit storage** — in-memory on single instance. **Revisit when:** second Railway instance (migrate to Redis backend).

### Notification queue concurrency
- **`notifications_drain` pg_cron concurrency limit: 20** — adjustable via `platform_settings`. **Revisit when:** queue depth alert fires repeatedly (>100 pending for >5 min) and increasing the limit doesn't help. Then: migrate to Celery/Arq/Dramatiq worker.

### No full-text search
- **Messages, resources, students list** — no Postgres `tsvector` indexes. Search is via `ILIKE`. **Revisit when:** real studio has >50 students and search latency >300ms.

### No Redis anywhere
- **Optional in Stage 0**, still absent in Stage 1. Every cache is in-process. **Revisit when:** horizontal scale needed OR a specific use case demands cross-instance coordination (e.g., WebSocket pub/sub for live features Stage 2+).

### Alembic migration naming — timestamp prefix is a convention, not a tooling enforcement
- **F5 decision:** timestamp-prefixed filenames like `20260415_1432_studios.py`. Enforced by PR checklist, not by Alembic itself. **Revisit when:** a developer forgets the convention and breaks the head chain. Then: add a pre-commit hook or CI script that validates filename format.

### Parent/student 2FA absent
- **PRD § Q20:** superadmin TOTP required, studio staff optional, parent/student none. **Revisit when:** a single parent account compromise surfaces (inevitable post-launch) or when WebAuthn ships in GoTrue.

### No activity_logs viewer UI
- **Stage 1:** `activity_logs` table exists (compliance requirement), but the UI viewer is deferred. Supabase Studio is the Stage 1 viewer. **Revisit when:** staff beyond Rollin joins superadmin ops (staff should not need raw SQL access).

---

## Documentation debt

### `docs/DESIGN.md` completeness
- Written 2026-04-15 from Polymet baseline + Stage 1 PRD. Missing: **real product screenshots** (can't exist until implementation), **component catalog with code examples** (happens in Slice 2 / #19 implementation), **exact Tailwind plugin versions** (pinned when #19 lands).

### `docs/runbooks/` — all launch prerequisites
Required pre-launch per Stage 1 PRD § Launch Criteria:
- `docs/runbooks/superadmin-mfa-clear.md` (scaffolded in Slice 5 / #22)
- `docs/runbooks/jwt-rotation.md`
- `docs/runbooks/pitr-restore.md`
- `docs/runbooks/coppa-hard-delete.md`
- `docs/runbooks/r2-object-recovery.md`
- `docs/runbooks/incident-response.md`
- `docs/runbooks/break-glass.md`
- `docs/runbooks/prod-deploy.md`
- `docs/runbooks/secret-rotation.md`

None of these exist yet. All are scoped inside their respective slices and Slice 35 / #52 (launch gate pack).

### `docs/prds/stage-2-foundation.md`
- **When:** After Stage 1 launches and ~4 weeks of real beta feedback. Uses beta feedback to scope Stage 2 (likely: Stripe Connect, cross-studio transfers, help center, teacher mobile, SMS).
- **Authoritative deferred feature list:** `docs/prds/stage-1-deferred-features.md` — read this before any Stage 2 scoping.

---

## Review pipeline — skills not run in Stage 1 review cycle

The gstack review dashboard has 5 review types. Stage 1 cycle ran 2 of them fully.

| Review | Status | When to run |
|---|---|---|
| **Plan eng review** | ✓ Ran 2026-04-15 | Re-run if architecture assumptions shift |
| **Plan design review** | ✓ Ran 2026-04-15 | Re-run after visual mockups ship |
| **Plan CEO review** | ✗ Not run | Consider running at Stage 2 kickoff to challenge scope ambition |
| **Plan devex review** | ✗ Not run | Defer indefinitely — Stage 1 is not a developer-facing product |
| **Outside voice** | ✗ Skipped 2026-04-15 | See above |

---

## Process notes

- **Commit hygiene:** Stage 1 PRD updates landed on `fix/ci-install` branch via PR #53 (merged to master at `21c42bb` on 2026-04-15). The branch also carried 6 CI fix commits — next time, use a separate branch for PRD edits to keep commit history cleaner.
- **Issue comment trail:** 18 targeted comments posted across 14 issues to bridge PRD updates to slice-level acceptance criteria. This pattern works but is labor-intensive. If review cycles become more frequent, consider a single "Stage 1 review deltas" aggregator issue that each slice links to.
- **Design consultation skipped interactive phases:** The `/design-consultation` skill has a multi-phase interactive flow (product context → research → proposal → drill-downs → preview). For this cycle it was run "just write DESIGN.md from Polymet + PRD" to save time. Full interactive run recommended for Stage 2 design consultation (e.g., if we add new personas or surfaces).
