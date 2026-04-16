import { getApiBaseUrl, apiFetch } from "@/lib/api";

describe("getApiBaseUrl", () => {
  const originalEnv = process.env;

  beforeEach(() => {
    process.env = { ...originalEnv };
    process.env.NEXT_PUBLIC_SUPABASE_URL = "http://localhost:54321";
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY = "test-key";
  });

  afterAll(() => {
    process.env = originalEnv;
  });

  it("replaces Supabase port with API port", () => {
    expect(getApiBaseUrl()).toBe("http://localhost:8000");
  });
});

describe("apiFetch", () => {
  const originalEnv = process.env;
  let originalFetch: typeof global.fetch;

  beforeEach(() => {
    process.env = { ...originalEnv };
    process.env.NEXT_PUBLIC_SUPABASE_URL = "http://localhost:54321";
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY = "test-key";
    originalFetch = global.fetch;
  });

  afterEach(() => {
    global.fetch = originalFetch;
    if (typeof localStorage !== "undefined") {
      localStorage.clear();
    }
  });

  afterAll(() => {
    process.env = originalEnv;
  });

  it("sends GET request and returns JSON", async () => {
    const mockData = { id: "123", name: "test" };
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: () => Promise.resolve(mockData),
    });

    const result = await apiFetch("/health");

    expect(result).toEqual(mockData);
    expect(global.fetch).toHaveBeenCalledWith(
      "http://localhost:8000/health",
      expect.objectContaining({
        headers: expect.objectContaining({
          "Content-Type": "application/json",
        }),
      }),
    );
  });

  it("throws on non-OK response", async () => {
    global.fetch = jest.fn().mockResolvedValue({
      ok: false,
      status: 403,
      text: () => Promise.resolve("Forbidden"),
    });

    await expect(apiFetch("/admin/studios")).rejects.toThrow("API 403");
  });

  it("returns undefined for 204 No Content", async () => {
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      status: 204,
    });

    const result = await apiFetch("/employees/123", { method: "DELETE" });

    expect(result).toBeUndefined();
  });

  it("includes auth token from localStorage when present", async () => {
    // Mock localStorage
    const store: Record<string, string> = {
      supabase_access_token: "test-jwt-token",
    };
    Object.defineProperty(global, "localStorage", {
      value: {
        getItem: (key: string) => store[key] ?? null,
        setItem: (key: string, value: string) => { store[key] = value; },
        clear: () => { for (const k in store) delete store[k]; },
        removeItem: (key: string) => { delete store[key]; },
      },
      writable: true,
      configurable: true,
    });

    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: () => Promise.resolve({}),
    });

    await apiFetch("/settings");

    expect(global.fetch).toHaveBeenCalledWith(
      "http://localhost:8000/settings",
      expect.objectContaining({
        headers: expect.objectContaining({
          Authorization: "Bearer test-jwt-token",
        }),
      }),
    );
  });
});
