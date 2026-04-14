import { create } from "zustand";
import type { HealthResponse } from "@dailyriff/api-client";

interface SessionState {
  user: { id: string; email: string } | null;
  lastHealthCheck: HealthResponse | null;
  setUser: (user: { id: string; email: string } | null) => void;
  setLastHealthCheck: (response: HealthResponse | null) => void;
  clearSession: () => void;
}

export const useSessionStore = create<SessionState>((set) => ({
  user: null,
  lastHealthCheck: null,
  setUser: (user) => set({ user }),
  setLastHealthCheck: (response) => set({ lastHealthCheck: response }),
  clearSession: () => set({ user: null, lastHealthCheck: null }),
}));
