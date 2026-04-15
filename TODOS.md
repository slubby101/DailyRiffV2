# DailyRiff TODOS

Items deferred from the Stage 1 planning cycle (2026-04-15) that should be revisited before or during Stage 2 planning. The authoritative scope tracker for **features** deferred to Stage 2+ lives in `docs/prds/stage-1-deferred-features.md`. This file captures **process / review / engineering debt** items that aren't features themselves.

---

## Deferred from this review cycle

### Outside-voice plan review (skipped 2026-04-15)
- **What:** Run an independent second AI reviewer (codex or Claude subagent) against `docs/prds/stage-1-foundation.md` to catch structural blind spots the review pipeline missed.
- **Why:** The Stage 1 PRD is 2200+ lines, 36 slices, the highest-stakes document in the repo. Cross-model review is cheap signal on whether the plan has a gaping hole.
- **When:** Before implementation starts in earnest. Ideally before Ralph runs on slices beyond Slice 0 / #17.
- **Context:** Was offered at the end of `/plan-eng-review` and deliberately skipped for time. The review pipeline (grill-me Q1–Q29, design review Pass 1–7, eng review F1–F11 + failure-mode gaps) is thorough but single-model.
- **Estimated effort:** 2–5 min if codex is available. Results will be either "no new findings" (confidence boost) or "1–3 structural issues we missed" (saves a week of implementation rework).
- **Action:** Run `/plan-eng-review` and select "A) Run outside voice" at the end, OR invoke directly with `codex exec` on the PRD.

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
