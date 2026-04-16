# Changelog

All notable changes to DailyRiff will be documented in this file.

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
