# Rate Limiting — Cloudflare + GoTrue Configuration Runbook

Four-layer defense-in-depth. Layers A (Cloudflare) and C (GoTrue) are vendor-side; Layers B (slowapi) and D (business-rule caps) are app-owned and tunable via `platform_settings`.

## Layer A — Cloudflare WAF

Configure in Cloudflare dashboard for the production domain.

### WAF rules

1. **Bot Fight Mode**: ON (Dashboard → Security → Bots)
2. **OWASP managed ruleset**: ON, paranoia level 1 (Security → WAF → Managed rules)
3. **Rate limiting rule** (Security → WAF → Rate limiting rules):
   - Name: `api-global-ip-rate-limit`
   - Expression: `(http.request.uri.path matches "^/api/")`
   - Rate: 50 requests per 10 seconds per IP
   - Action: Block for 60 seconds
   - Response: 429 JSON `{"detail": "Too many requests"}`

### Under Attack Mode (break-glass)

Enable via Dashboard → Overview → Under Attack Mode toggle. Adds JS challenge to all requests. Use only during active DDoS — adds ~5 seconds to every page load.

### Verification

```bash
# Test rate limit (should get 429 after 50 rapid requests)
for i in $(seq 1 55); do
  curl -s -o /dev/null -w "%{http_code}\n" https://api.dailyriff.com/health
done
```

## Layer C — Supabase GoTrue

Configure via Supabase Dashboard → Authentication → Rate Limits.

### Settings

| Action | Limit | Notes |
|---|---|---|
| Sign-up | 10/hr per IP | Default is higher; tighten |
| Sign-in | 10/5min per IP | Prevents brute force |
| Password reset | 5/hr per email | Prevents email bombing |
| Magic link | Disabled | Not used in DailyRiff |
| Email OTP | Disabled | Not used |

### Verification

These are read-only from the app's perspective. Mirrored in the superadmin platform-settings page (read-only section).

```bash
# Check GoTrue config
curl -s "$SUPABASE_URL/auth/v1/settings" -H "apikey: $SUPABASE_ANON_KEY" | jq .
```

## Layers B + D — App-Owned (platform_settings)

Tunable live via superadmin platform-settings page or direct DB update.

### Layer B — slowapi per-route limits

Stored in `platform_settings.rate_limit_overrides` (JSON object).

Default rates (hardcoded fallbacks if no override):

| Route key | Default rate | Endpoint |
|---|---|---|
| `device_register` | 10/minute | `POST /devices/register` |
| `auth_login` | 10/5minute | `POST /auth/login` (future) |
| `auth_signup` | 10/hour | `POST /auth/signup` (future) |
| `recordings_upload_url` | 50/minute | `POST /recordings/upload-url` (future) |
| `messages_send` | 30/minute | `POST /messages` (future) |
| `waitlist_submit` | 5/hour | `POST /waitlist` (future) |
| `coppa_vpc_charge` | 3/hour | `POST /coppa/vpc-charge` (future) |
| `password_reset` | 5/hour | `POST /auth/password-reset` (future) |

Override example (SQL):
```sql
UPDATE platform_settings
SET value_json = '{"device_register": "5/minute", "messages_send": "10/minute"}'
WHERE key = 'rate_limit_overrides';
```

### Layer D — Business-rule caps

Each cap is stored as a separate `platform_settings` row with key prefix `cap_`.

| Cap key | Default | Meaning |
|---|---|---|
| `cap_recordings_per_student_per_day` | 50 | Max recordings per student per day |
| `cap_messages_per_user_per_day` | 200 | Max messages per user per day |
| `cap_waitlist_per_email_lifetime` | 1 | Max waitlist submissions per email |
| `cap_waitlist_per_ip_lifetime` | 3 | Max waitlist submissions per IP |
| `cap_push_per_user_per_day` | 20 | Max push notifications per user per day |
| `cap_coppa_vpc_per_parent_per_day` | 3 | Max COPPA VPC charge attempts per 24h |

Override example:
```sql
UPDATE platform_settings
SET value_json = '100'
WHERE key = 'cap_recordings_per_student_per_day';
```

## Webhook Hardening

- **Stripe**: HMAC-SHA256 signature verification with 5-minute timestamp tolerance. Replay defense via `idempotency_log` table (unique on `(provider, event_id)`).
- **Postmark**: HMAC-SHA256 signature verification. Same `idempotency_log` dedup.

## Enumeration Defense

- Password reset always returns HTTP 200 with constant minimum latency (200ms) regardless of whether the email exists.
- Signup for an existing email sends a notification to the existing user rather than disclosing account existence.

## hCaptcha

Required on public forms (waitlist, public signup). Set `HCAPTCHA_SECRET` env var to enable. When unset, captcha verification is bypassed (dev/test mode).
