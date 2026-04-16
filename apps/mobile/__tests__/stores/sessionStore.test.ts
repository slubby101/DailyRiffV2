import {
  useSessionStore,
  setSecureStoreBridge,
  PendingRecording,
} from "../../src/stores/sessionStore";

// In-memory SecureStore mock (system boundary — this is an external API)
function createMockSecureStore() {
  const store = new Map<string, string>();
  return {
    getItemAsync: jest.fn(async (key: string) => store.get(key) ?? null),
    setItemAsync: jest.fn(async (key: string, value: string) => {
      store.set(key, value);
    }),
    deleteItemAsync: jest.fn(async (key: string) => {
      store.delete(key);
    }),
    _store: store,
  };
}


beforeEach(() => {
  useSessionStore.setState({
    user: null,
    lastHealthCheck: null,
    pendingRecordings: [],
    isRestoringSession: false,
  });
  // Reset bridge to null — persistence tests set their own bridge
  setSecureStoreBridge(null);
});

describe("sessionStore", () => {
  it("starts with null user", () => {
    const { user } = useSessionStore.getState();
    expect(user).toBeNull();
  });

  it("sets a user", () => {
    useSessionStore.getState().setUser({ id: "1", email: "a@b.com" });
    expect(useSessionStore.getState().user).toEqual({
      id: "1",
      email: "a@b.com",
    });
  });

  it("clears the session", () => {
    useSessionStore.getState().setUser({ id: "1", email: "a@b.com" });
    useSessionStore
      .getState()
      .setLastHealthCheck({ status: "ok", version: "0.0.0", git_sha: "dev" });
    useSessionStore.getState().addPendingRecording(makePendingRecording());
    useSessionStore.getState().clearSession();
    const state = useSessionStore.getState();
    expect(state.user).toBeNull();
    expect(state.lastHealthCheck).toBeNull();
    expect(state.pendingRecordings).toEqual([]);
  });

  it("sets last health check", () => {
    const response = { status: "ok", version: "0.0.0", git_sha: "abc123" };
    useSessionStore.getState().setLastHealthCheck(response);
    expect(useSessionStore.getState().lastHealthCheck).toEqual(response);
  });

  it("updates user to a different user", () => {
    useSessionStore.getState().setUser({ id: "1", email: "a@b.com" });
    useSessionStore.getState().setUser({ id: "2", email: "c@d.com" });
    expect(useSessionStore.getState().user).toEqual({
      id: "2",
      email: "c@d.com",
    });
  });

  it("sets user to null", () => {
    useSessionStore.getState().setUser({ id: "1", email: "a@b.com" });
    useSessionStore.getState().setUser(null);
    expect(useSessionStore.getState().user).toBeNull();
  });

  it("starts with isRestoringSession false", () => {
    expect(useSessionStore.getState().isRestoringSession).toBe(false);
  });
});

describe("pendingRecordings", () => {
  it("starts with empty pending recordings", () => {
    expect(useSessionStore.getState().pendingRecordings).toEqual([]);
  });

  it("adds a pending recording", () => {
    const recording = makePendingRecording();
    useSessionStore.getState().addPendingRecording(recording);
    expect(useSessionStore.getState().pendingRecordings).toEqual([recording]);
  });

  it("adds multiple pending recordings", () => {
    const r1 = makePendingRecording({ localUri: "file:///a.m4a" });
    const r2 = makePendingRecording({ localUri: "file:///b.m4a" });
    useSessionStore.getState().addPendingRecording(r1);
    useSessionStore.getState().addPendingRecording(r2);
    expect(useSessionStore.getState().pendingRecordings).toHaveLength(2);
  });

  it("removes a pending recording by localUri", () => {
    const r1 = makePendingRecording({ localUri: "file:///a.m4a" });
    const r2 = makePendingRecording({ localUri: "file:///b.m4a" });
    useSessionStore.getState().addPendingRecording(r1);
    useSessionStore.getState().addPendingRecording(r2);
    useSessionStore.getState().removePendingRecording("file:///a.m4a");
    expect(useSessionStore.getState().pendingRecordings).toEqual([r2]);
  });

  it("does nothing when removing a non-existent recording", () => {
    const r1 = makePendingRecording({ localUri: "file:///a.m4a" });
    useSessionStore.getState().addPendingRecording(r1);
    useSessionStore.getState().removePendingRecording("file:///nonexistent.m4a");
    expect(useSessionStore.getState().pendingRecordings).toEqual([r1]);
  });

  it("clears all pending recordings", () => {
    useSessionStore.getState().addPendingRecording(makePendingRecording());
    useSessionStore
      .getState()
      .addPendingRecording(makePendingRecording({ localUri: "file:///b.m4a" }));
    useSessionStore.getState().clearPendingRecordings();
    expect(useSessionStore.getState().pendingRecordings).toEqual([]);
  });
});

describe("session persistence", () => {
  it("persists user to SecureStore on setUser", async () => {
    const mockStore = createMockSecureStore();
    setSecureStoreBridge(mockStore);

    useSessionStore.getState().setUser({ id: "u1", email: "test@test.com" });
    await flushPromises();

    expect(mockStore.setItemAsync).toHaveBeenCalledWith(
      "dailyriff_session",
      JSON.stringify({ id: "u1", email: "test@test.com" }),
    );
  });

  it("deletes session from SecureStore when user set to null", async () => {
    const mockStore = createMockSecureStore();
    setSecureStoreBridge(mockStore);

    useSessionStore.getState().setUser({ id: "u1", email: "test@test.com" });
    await flushPromises();
    useSessionStore.getState().setUser(null);
    await flushPromises();

    expect(mockStore.deleteItemAsync).toHaveBeenCalledWith("dailyriff_session");
  });

  it("persists pending recordings to SecureStore on add", async () => {
    const mockStore = createMockSecureStore();
    setSecureStoreBridge(mockStore);

    const recording = makePendingRecording();
    useSessionStore.getState().addPendingRecording(recording);
    await flushPromises();

    expect(mockStore.setItemAsync).toHaveBeenCalledWith(
      "dailyriff_pending_recordings",
      JSON.stringify([recording]),
    );
  });

  it("persists pending recordings to SecureStore on remove", async () => {
    const mockStore = createMockSecureStore();
    setSecureStoreBridge(mockStore);

    useSessionStore.getState().addPendingRecording(makePendingRecording());
    await flushPromises();
    useSessionStore.getState().removePendingRecording("file:///tmp/recording.m4a");
    await flushPromises();

    expect(mockStore.setItemAsync).toHaveBeenCalledWith(
      "dailyriff_pending_recordings",
      JSON.stringify([]),
    );
  });

  it("persists pending recordings to SecureStore on clear", async () => {
    const mockStore = createMockSecureStore();
    setSecureStoreBridge(mockStore);

    useSessionStore.getState().addPendingRecording(makePendingRecording());
    await flushPromises();
    useSessionStore.getState().clearPendingRecordings();
    await flushPromises();

    // The last call should persist empty array
    const calls = mockStore.setItemAsync.mock.calls.filter(
      (c: [string, string]) => c[0] === "dailyriff_pending_recordings",
    );
    expect(calls[calls.length - 1][1]).toBe("[]");
  });

  it("restores session from SecureStore", async () => {
    const mockStore = createMockSecureStore();
    const user = { id: "u2", email: "restored@test.com" };
    const recordings = [makePendingRecording()];
    mockStore._store.set("dailyriff_session", JSON.stringify(user));
    mockStore._store.set(
      "dailyriff_pending_recordings",
      JSON.stringify(recordings),
    );
    setSecureStoreBridge(mockStore);

    await useSessionStore.getState().restoreSession();

    const state = useSessionStore.getState();
    expect(state.user).toEqual(user);
    expect(state.pendingRecordings).toEqual(recordings);
    expect(state.isRestoringSession).toBe(false);
  });

  it("handles missing SecureStore data gracefully on restore", async () => {
    const mockStore = createMockSecureStore();
    setSecureStoreBridge(mockStore);

    await useSessionStore.getState().restoreSession();

    const state = useSessionStore.getState();
    expect(state.user).toBeNull();
    expect(state.pendingRecordings).toEqual([]);
    expect(state.isRestoringSession).toBe(false);
  });

  it("handles corrupted SecureStore data on restore", async () => {
    const mockStore = createMockSecureStore();
    mockStore._store.set("dailyriff_session", "not valid json{{{");
    setSecureStoreBridge(mockStore);

    await useSessionStore.getState().restoreSession();

    // Should not crash — falls back to defaults
    expect(useSessionStore.getState().isRestoringSession).toBe(false);
  });

  it("sets isRestoringSession to true during restore", async () => {
    const mockStore = createMockSecureStore();
    const observed: boolean[] = [];

    // Wrap getItemAsync to observe isRestoringSession during execution
    const originalGet = mockStore.getItemAsync;
    mockStore.getItemAsync.mockImplementation(async (key: string) => {
      observed.push(useSessionStore.getState().isRestoringSession);
      return originalGet(key);
    });
    setSecureStoreBridge(mockStore);

    await useSessionStore.getState().restoreSession();

    // isRestoringSession should have been true during both getItemAsync calls
    expect(observed.length).toBeGreaterThanOrEqual(1);
    expect(observed.every((v) => v === true)).toBe(true);
    // After restore completes, it should be false
    expect(useSessionStore.getState().isRestoringSession).toBe(false);
  });

  it("clears SecureStore on clearSession", async () => {
    const mockStore = createMockSecureStore();
    setSecureStoreBridge(mockStore);

    useSessionStore.getState().setUser({ id: "u1", email: "x@y.com" });
    await flushPromises();
    useSessionStore.getState().clearSession();
    await flushPromises();

    expect(mockStore.deleteItemAsync).toHaveBeenCalledWith("dailyriff_session");
    expect(mockStore.deleteItemAsync).toHaveBeenCalledWith(
      "dailyriff_pending_recordings",
    );
  });

  it("persistSession is a no-op when no bridge is set", async () => {
    setSecureStoreBridge(null);
    useSessionStore.getState().setUser({ id: "u1", email: "x@y.com" });
    await flushPromises();
    // Should not throw — just a no-op
    expect(useSessionStore.getState().user).toEqual({ id: "u1", email: "x@y.com" });
  });

  it("restoreSession is a no-op when no bridge is set", async () => {
    setSecureStoreBridge(null);
    await useSessionStore.getState().restoreSession();
    expect(useSessionStore.getState().user).toBeNull();
    expect(useSessionStore.getState().isRestoringSession).toBe(false);
  });

  it("clearSession works when no bridge is set", () => {
    setSecureStoreBridge(null);
    useSessionStore.setState({ user: { id: "u1", email: "x@y.com" } });
    useSessionStore.getState().clearSession();
    expect(useSessionStore.getState().user).toBeNull();
  });

  it("handles SecureStore write failure gracefully", async () => {
    const mockStore = createMockSecureStore();
    mockStore.setItemAsync.mockRejectedValue(new Error("SecureStore unavailable"));
    mockStore.deleteItemAsync.mockRejectedValue(new Error("SecureStore unavailable"));
    setSecureStoreBridge(mockStore);

    // Should not throw
    useSessionStore.getState().setUser({ id: "u1", email: "x@y.com" });
    await flushPromises();

    expect(useSessionStore.getState().user).toEqual({ id: "u1", email: "x@y.com" });
  });
});

// --- Helpers ---

function makePendingRecording(
  overrides?: Partial<PendingRecording>,
): PendingRecording {
  return {
    localUri: "file:///tmp/recording.m4a",
    studioId: "studio-1",
    assignmentId: "assign-1",
    durationSeconds: 120,
    createdAt: "2026-04-16T00:00:00.000Z",
    ...overrides,
  };
}

function flushPromises() {
  return new Promise<void>((resolve) => setTimeout(resolve, 0));
}
