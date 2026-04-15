"use client";

import { useQuery } from "@tanstack/react-query";
import type { HealthResponse } from "@dailyriff/api-client";
import { getWebEnv } from "@/lib/env";

async function fetchHealth(): Promise<HealthResponse> {
  const { supabaseUrl } = getWebEnv();
  const apiUrl = supabaseUrl.replace(":54321", ":8000");
  const res = await fetch(`${apiUrl}/health`);
  if (!res.ok) throw new Error(`Health check failed: ${res.status}`);
  return res.json();
}

export function useHealth() {
  return useQuery({
    queryKey: ["health"],
    queryFn: fetchHealth,
    retry: false,
  });
}
