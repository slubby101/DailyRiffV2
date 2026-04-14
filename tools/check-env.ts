#!/usr/bin/env tsx
/**
 * Env var validator — runs before `pnpm dev`. Fails fast listing missing required vars.
 * Reads process.env, prints a clear error, exits 1 if any required var is unset or empty.
 */

const REQUIRED_VARS = [
  'SUPABASE_URL',
  'SUPABASE_ANON_KEY',
  'SUPABASE_SERVICE_ROLE',
  'SUPABASE_JWT_SECRET',
  'DATABASE_URL',
  'VAPID_PUBLIC_KEY',
  'VAPID_PRIVATE_KEY',
  'VAPID_EMAIL',
] as const;

export type EnvSource = Record<string, string | undefined>;

export function findMissing(env: EnvSource, required: readonly string[] = REQUIRED_VARS): string[] {
  return required.filter((name) => {
    const value = env[name];
    return value === undefined || value.trim() === '';
  });
}

export function formatError(missing: string[]): string {
  const lines = [
    'check-env: missing required environment variables:',
    ...missing.map((name) => `  - ${name}`),
    '',
    'Copy .env.example to .env and fill in the required values.',
  ];
  return lines.join('\n');
}

function main(): void {
  const missing = findMissing(process.env);
  if (missing.length > 0) {
    console.error(formatError(missing));
    process.exit(1);
  }
  console.log('check-env: all required environment variables present.');
}

// Run when invoked directly (tsx/node). Skip when imported as a module in tests.
const invokedDirectly =
  typeof process !== 'undefined' &&
  process.argv[1] !== undefined &&
  /check-env\.(ts|js|mjs|cjs)$/.test(process.argv[1]);

if (invokedDirectly) {
  main();
}
