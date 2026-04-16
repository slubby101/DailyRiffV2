/**
 * API client utilities for the DailyRiff web app.
 *
 * All fetch calls to the FastAPI backend go through these helpers
 * so auth headers and base URL are applied consistently.
 */

import { getWebEnv } from "@/lib/env";

export function getApiBaseUrl(): string {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL;
  if (apiUrl) return apiUrl;
  const { supabaseUrl } = getWebEnv();
  const url = new URL(supabaseUrl);
  if (url.port === "54321") {
    url.port = "8000";
  }
  return url.origin;
}

function getAccessToken(): string | null {
  if (typeof window === "undefined") return null;
  const projectRef = process.env.NEXT_PUBLIC_SUPABASE_PROJECT_REF;
  if (projectRef) {
    const key = `sb-${projectRef}-auth-token`;
    const raw = localStorage.getItem(key);
    if (raw) {
      try {
        const parsed = JSON.parse(raw);
        return parsed?.access_token ?? null;
      } catch {
        return null;
      }
    }
  }
  for (let i = 0; i < localStorage.length; i++) {
    const k = localStorage.key(i);
    if (k?.startsWith("sb-") && k.endsWith("-auth-token")) {
      try {
        const parsed = JSON.parse(localStorage.getItem(k) ?? "");
        return parsed?.access_token ?? null;
      } catch {
        continue;
      }
    }
  }
  return null;
}

export async function apiFetch<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const base = getApiBaseUrl();
  const token = getAccessToken();

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const res = await fetch(`${base}${path}`, {
    ...options,
    headers,
  });

  if (!res.ok) {
    const body = await res.text();
    throw new Error(`API ${res.status}: ${body}`);
  }

  if (res.status === 204) {
    return undefined as T;
  }

  return res.json();
}
