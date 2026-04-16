# Changelog

All notable changes to DailyRiff will be documented in this file.

## [0.3.0.0] - 2026-04-16

### Added
- **Impersonation sessions:** superadmin can impersonate any user with mandatory reason, scope restrictions, Account Access Log, 8-hour auto-expiry
- **Account conversion:** manual age-class transitions (minor→teen, teen→adult) with parent consent tracking
- **Lessons + attendance:** lesson scheduling, recurring occurrences, attendance tracking, absence policies, ICS calendar export
- **Student dashboard:** streak service (current + longest + weekly minutes), 5 web pages (dashboard, assignments, recordings, sessions, profile)
- **Parent dashboard:** children overview with per-child summary, schedule, progress (gated by permission), payments, messages, deletion request dialog
- **Beta rollout scaffolding:** feedback collection, landing page tokens, onboarding checklist
- **COPPA 15-day grace deletion:** parent-initiated with email confirmation, T-7/T-1 reminders, hard-delete worker (pg_cron), R2 deletion queue
- **R2 credential scoping:** separate API client (read/write) vs deletion worker client (delete-capable) with distinct env vars
- **Data seeding:** Polymet reference data + edge-case seed scripts with Makefile targets
- **Expo student mobile app:** 5 screens (dashboard, assignments, recording, profile, settings) with MediaRecorder, session persistence via Zustand
- **2.5-stage deploy pipeline:** GitHub Actions workflow with staging auto-deploy + production manual approval gate, EAS build profiles

### Fixed
- COPPA deletion: wrong column name (child_id → child_user_id) in parent-child verification
- COPPA deletion: missing parent ownership check on confirmation endpoint
- Impersonation: role escalation prevented (impersonated sessions get role=None, not superadmin)
- Impersonation: 8-hour session TTL (was unlimited)
- COPPA deletion: constant-time token hash comparison (hmac.compare_digest)
- Student + parent dashboards: 1-year lookback on streak queries (was unbounded)
- Lessons: 10k row safety cap on ICS calendar export

## [0.2.0.0] - 2026-04-16

### Added
- **Waitlist pipeline:** public submission with hCaptcha, superadmin management (approve, reject, message, bypass invite)
- **Invitation system:** studio-scoped invitations with SHA-256 hashed tokens, batch parent invites, token regeneration, public redemption with age-class routing
- **Core loop backend:** assignments, recordings, auto-acknowledge trigger (Postgres function fires on upload confirmation)
- **Recording playback authorization:** default-deny policy (student, parent with permission, assigned teacher, studio owner, superadmin via impersonation)
- **COPPA VPC service:** Stripe Setup Intent flow, signed-form escape hatch, revocation with 30-day auto-delete scheduling, webhook with idempotency
- **Teacher student management:** student list/detail, parent permission editing, equipment loan tracking
- **Payment ledger:** studio-scoped CRUD, refund endpoint, outstanding balance aggregation
- **Marketing pages:** homepage, about, contact, privacy policy, terms of service, accessibility statement
- **Superadmin surface:** 8 pages (studios, verification queue, waitlist, users stub) with MFA gate
- **Studio onboarding:** create studio flow with 12-swatch color picker from design system
- **Notification service extension:** 18 notification templates across 15 events and 4 personas, per-category preference toggles
- **Rate limiting infrastructure:** 4-layer system (slowapi middleware, business caps, webhook idempotency, enumeration defense) with Redis backend and memory fallback
- **Retention cleanup:** pg_cron jobs for mfa_failure_log (30d) and idempotency_log (90d)
- **8 Alembic migrations** (0009-0016) with RLS policies
- **Shared pagination helper** for all list endpoints (default 100, max 500)
- **Unique partial index** on coppa_consents.stripe_setup_intent_id

### Fixed
- Race condition in invitation redemption (atomic WHERE status='pending' on UPDATE)
- Waitlist public endpoint no longer leaks bypass_token or ip_address (separate response schema)
- Payment amount now requires positive value, status not caller-settable on creation
- Invitation regeneration scoped to studio_id (prevents cross-tenant IDOR)
- Refund endpoint guards against double-refund (WHERE status='paid')

### Changed
- `dailyriff_employees` table with role enum and MFA gate (warn-only in dev)
- Rate limiter storage switched from memory to Redis when REDIS_URL is set
