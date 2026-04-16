import { create } from "zustand";
import type { HealthResponse } from "@dailyriff/api-client";

export interface PendingRecording {
  localUri: string;
  studioId: string;
  assignmentId: string;
  durationSeconds: number;
  createdAt: string;
}

export interface SessionState {
  user: { id: string; email: string } | null;
  lastHealthCheck: HealthResponse | null;
  pendingRecordings: PendingRecording[];
  isRestoringSession: boolean;

  setUser: (user: { id: string; email: string } | null) => void;
  setLastHealthCheck: (response: HealthResponse | null) => void;
  clearSession: () => void;

  addPendingRecording: (recording: PendingRecording) => void;
  removePendingRecording: (localUri: string) => void;
  clearPendingRecordings: () => void;

  persistSession: () => Promise<void>;
  restoreSession: () => Promise<void>;
}

function noop() {}

// SecureStore is injected at runtime to keep the store testable without mocking modules.
// In production, the root layout calls `setSecureStoreBridge` before `restoreSession`.
let _secureStoreGet: ((key: string) => Promise<string | null>) | null = null;
let _secureStoreSet: ((key: string, value: string) => Promise<void>) | null = null;
let _secureStoreDelete: ((key: string) => Promise<void>) | null = null;

export function setSecureStoreBridge(bridge: {
  getItemAsync: (key: string) => Promise<string | null>;
  setItemAsync: (key: string, value: string) => Promise<void>;
  deleteItemAsync: (key: string) => Promise<void>;
} | null) {
  if (bridge) {
    _secureStoreGet = bridge.getItemAsync;
    _secureStoreSet = bridge.setItemAsync;
    _secureStoreDelete = bridge.deleteItemAsync;
  } else {
    _secureStoreGet = null;
    _secureStoreSet = null;
    _secureStoreDelete = null;
  }
}

const SESSION_KEY = "dailyriff_session";
const PENDING_RECORDINGS_KEY = "dailyriff_pending_recordings";

export const useSessionStore = create<SessionState>((set, get) => ({
  user: null,
  lastHealthCheck: null,
  pendingRecordings: [],
  isRestoringSession: false,

  setUser: (user) => {
    set({ user });
    get().persistSession();
  },

  setLastHealthCheck: (response) => set({ lastHealthCheck: response }),

  clearSession: () => {
    set({ user: null, lastHealthCheck: null, pendingRecordings: [] });
    if (_secureStoreDelete) {
      Promise.all([
        _secureStoreDelete(SESSION_KEY),
        _secureStoreDelete(PENDING_RECORDINGS_KEY),
      ]).catch(noop);
    }
  },

  addPendingRecording: (recording) => {
    const current = get().pendingRecordings;
    set({ pendingRecordings: [...current, recording] });
    get().persistSession();
  },

  removePendingRecording: (localUri) => {
    const current = get().pendingRecordings;
    set({ pendingRecordings: current.filter((r) => r.localUri !== localUri) });
    get().persistSession();
  },

  clearPendingRecordings: () => {
    set({ pendingRecordings: [] });
    get().persistSession();
  },

  persistSession: async () => {
    if (!_secureStoreSet) return;
    const { user, pendingRecordings } = get();
    try {
      if (user) {
        await _secureStoreSet(SESSION_KEY, JSON.stringify(user));
      } else {
        await _secureStoreDelete?.(SESSION_KEY);
      }
      await _secureStoreSet(
        PENDING_RECORDINGS_KEY,
        JSON.stringify(pendingRecordings),
      );
    } catch {
      // SecureStore write failure is non-fatal
    }
  },

  restoreSession: async () => {
    if (!_secureStoreGet) return;
    set({ isRestoringSession: true });
    try {
      const userJson = await _secureStoreGet(SESSION_KEY);
      const pendingJson = await _secureStoreGet(PENDING_RECORDINGS_KEY);

      const user = userJson ? JSON.parse(userJson) : null;
      const pendingRecordings = pendingJson ? JSON.parse(pendingJson) : [];

      set({ user, pendingRecordings, isRestoringSession: false });
    } catch {
      set({ isRestoringSession: false });
    }
  },
}));
