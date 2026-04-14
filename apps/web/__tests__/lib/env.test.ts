import { getWebEnv } from "@/lib/env";

describe("getWebEnv", () => {
  const originalEnv = process.env;

  beforeEach(() => {
    process.env = { ...originalEnv };
  });

  afterAll(() => {
    process.env = originalEnv;
  });

  it("returns env values when all required vars are set", () => {
    process.env.NEXT_PUBLIC_SUPABASE_URL = "http://localhost:54321";
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY = "test-key";
    process.env.NEXT_PUBLIC_VAPID_PUBLIC_KEY = "vapid-key";

    const env = getWebEnv();

    expect(env.supabaseUrl).toBe("http://localhost:54321");
    expect(env.supabaseAnonKey).toBe("test-key");
    expect(env.vapidPublicKey).toBe("vapid-key");
  });

  it("throws when NEXT_PUBLIC_SUPABASE_URL is missing", () => {
    delete process.env.NEXT_PUBLIC_SUPABASE_URL;
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY = "test-key";

    expect(() => getWebEnv()).toThrow("NEXT_PUBLIC_SUPABASE_URL is required");
  });

  it("throws when NEXT_PUBLIC_SUPABASE_ANON_KEY is missing", () => {
    process.env.NEXT_PUBLIC_SUPABASE_URL = "http://localhost:54321";
    delete process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

    expect(() => getWebEnv()).toThrow(
      "NEXT_PUBLIC_SUPABASE_ANON_KEY is required"
    );
  });

  it("returns undefined for vapidPublicKey when not set", () => {
    process.env.NEXT_PUBLIC_SUPABASE_URL = "http://localhost:54321";
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY = "test-key";
    delete process.env.NEXT_PUBLIC_VAPID_PUBLIC_KEY;

    const env = getWebEnv();

    expect(env.vapidPublicKey).toBeUndefined();
  });
});
