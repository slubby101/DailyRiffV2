# Break-glass: Clear superadmin MFA

Use this runbook when a superadmin is locked out of MFA (lost authenticator,
device failure, etc.) and cannot complete TOTP verification.

## Prerequisites

- Direct database access (psql or Supabase Studio) with the `postgres` role
- A second owner-level employee must approve the action out-of-band (Slack DM, phone call)

## Steps

### 1. Confirm identity out-of-band

Contact the locked-out superadmin via a channel they controlled before lockout
(phone number on file, personal email). Confirm they are requesting the reset.

### 2. Unenroll TOTP factors

```sql
-- Find the user's MFA factors
SELECT id, factor_type, status, created_at
FROM auth.mfa_factors
WHERE user_id = '<USER_UUID>';

-- Delete verified TOTP factors to allow re-enrollment
DELETE FROM auth.mfa_factors
WHERE user_id = '<USER_UUID>'
  AND factor_type = 'totp'
  AND status = 'verified';
```

### 3. Log the action

```sql
INSERT INTO activity_logs (user_id, action, entity_type, entity_id, details)
VALUES (
  '<APPROVER_UUID>',
  'mfa_break_glass',
  'auth_user',
  '<LOCKED_OUT_USER_UUID>',
  '{"reason": "Lost authenticator device", "approved_by": "<APPROVER_EMAIL>"}'::jsonb
);
```

### 4. Notify the user

Tell the superadmin their TOTP has been cleared. They must re-enroll TOTP
immediately on next login via the GoTrue native flow before accessing any
superadmin routes.

### 5. Clear the MFA failure log (optional)

If the lockout generated failure alerts:

```sql
DELETE FROM mfa_failure_log
WHERE user_id = '<USER_UUID>'
  AND created_at > now() - interval '1 hour';
```

## Post-incident

- Verify the user re-enrolled TOTP successfully
- Review `activity_logs` for the `mfa_break_glass` entry
- If the lockout was suspicious, rotate the user's password as well
