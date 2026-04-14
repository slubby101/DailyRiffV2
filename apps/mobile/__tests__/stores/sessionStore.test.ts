import { useSessionStore } from "../../src/stores/sessionStore";

beforeEach(() => {
  useSessionStore.setState({
    user: null,
    lastHealthCheck: null,
  });
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
    useSessionStore.getState().clearSession();
    const state = useSessionStore.getState();
    expect(state.user).toBeNull();
    expect(state.lastHealthCheck).toBeNull();
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
});
