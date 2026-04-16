/**
 * API client utilities for the DailyRiff web app.
 *
 * All fetch calls to the FastAPI backend go through these helpers
 * so auth headers and base URL are applied consistently.
 */

import { getWebEnv } from "@/lib/env";

export function getApiBaseUrl(): string {
  const { supabaseUrl } = getWebEnv();
  return supabaseUrl.replace(":54321", ":8000");
}

export async function apiFetch<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const base = getApiBaseUrl();
  const token =
    typeof window !== "undefined"
      ? localStorage.getItem("supabase_access_token")
      : null;

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
