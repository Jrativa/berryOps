import axios from "axios";

import { api } from "./axios.instance";

function unauthorized(url: string, config: Record<string, unknown> = {}) {
  return { response: { status: 401 }, config: { url, headers: {}, ...config } };
}

// Ejecuta los interceptores registrados sin tocar la red
const handlers = (api.interceptors as unknown as {
  request: { handlers: { fulfilled: (c: unknown) => Promise<{ headers: Record<string, string> }> }[] };
  response: { handlers: { rejected: (e: unknown) => Promise<unknown> }[] };
});
const onRequest = (cfg: unknown) => handlers.request.handlers[0].fulfilled(cfg);
const onError = (err: unknown) => handlers.response.handlers[0].rejected(err);

describe("axios.instance", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it("inyecta el access token en cada petición", async () => {
    sessionStorage.setItem("access_token", "abc");
    const cfg = await onRequest({ headers: {} });
    expect(cfg.headers.Authorization).toBe("Bearer abc");
  });

  it("ante un 401 refresca con el token en el body, guarda los nuevos y reintenta", async () => {
    sessionStorage.setItem("refresh_token", "r1");
    const post = vi.spyOn(axios, "post").mockResolvedValue({ data: { access_token: "a2", refresh_token: "r2" } });
    const adapter = vi.fn().mockResolvedValue({ status: 200, data: "ok", headers: {}, config: {}, statusText: "OK" });
    api.defaults.adapter = adapter;

    await onError(unauthorized("/inventory/plots"));

    expect(post).toHaveBeenCalledWith(expect.stringContaining("/auth/refresh"), { refresh_token: "r1" }, expect.anything());
    expect(sessionStorage.getItem("access_token")).toBe("a2");
    expect(sessionStorage.getItem("refresh_token")).toBe("r2");
    expect(adapter).toHaveBeenCalledTimes(1);
    expect(adapter.mock.calls[0][0].headers.get("Authorization")).toBe("Bearer a2");
  });

  it("un 401 en /auth/login no dispara refresh", async () => {
    sessionStorage.setItem("refresh_token", "r1");
    const post = vi.spyOn(axios, "post");
    await expect(onError(unauthorized("/auth/login"))).rejects.toBeDefined();
    expect(post).not.toHaveBeenCalled();
  });

  it("sin refresh token no intenta refrescar", async () => {
    const post = vi.spyOn(axios, "post");
    await expect(onError(unauthorized("/inventory/plots"))).rejects.toBeDefined();
    expect(post).not.toHaveBeenCalled();
  });

  it("no reintenta dos veces la misma petición", async () => {
    sessionStorage.setItem("refresh_token", "r1");
    const post = vi.spyOn(axios, "post");
    await expect(onError(unauthorized("/x", { _retry: true }))).rejects.toBeDefined();
    expect(post).not.toHaveBeenCalled();
  });

  describe.each([2, 5])("%i peticiones paralelas con 401", (n) => {
    function deferred<T>() {
      let resolve!: (v: T) => void;
      let reject!: (e: unknown) => void;
      const promise = new Promise<T>((res, rej) => { resolve = res; reject = rej; });
      return { promise, resolve, reject };
    }

    it("disparan un único refresh y todas se reintentan con el token nuevo", async () => {
      sessionStorage.setItem("refresh_token", "r1");
      const gate = deferred<{ data: { access_token: string; refresh_token: string } }>();
      const post = vi.spyOn(axios, "post").mockReturnValue(gate.promise);
      const adapter = vi.fn().mockResolvedValue({ status: 200, data: "ok", headers: {}, config: {}, statusText: "OK" });
      api.defaults.adapter = adapter;

      const results = Promise.all(
        Array.from({ length: n }, (_, i) => onError(unauthorized(`/x/${i}`))),
      );
      gate.resolve({ data: { access_token: "a2", refresh_token: "r2" } });
      await results;

      expect(post).toHaveBeenCalledTimes(1);
      expect(post).toHaveBeenCalledWith(expect.stringContaining("/auth/refresh"), { refresh_token: "r1" }, expect.anything());
      expect(adapter).toHaveBeenCalledTimes(n);
      adapter.mock.calls.forEach(([cfg]) => expect(cfg.headers.get("Authorization")).toBe("Bearer a2"));
    });

    it("si el refresh compartido falla, todas fallan y se cierra la sesión una sola vez", async () => {
      sessionStorage.setItem("access_token", "a");
      sessionStorage.setItem("refresh_token", "r1");
      const post = vi.spyOn(axios, "post").mockRejectedValue(new Error("expired"));
      const assignments: string[] = [];
      vi.stubGlobal("location", { set href(v: string) { assignments.push(v); } });

      const settled = await Promise.allSettled(
        Array.from({ length: n }, (_, i) => onError(unauthorized(`/x/${i}`))),
      );

      expect(settled.every((r) => r.status === "rejected")).toBe(true);
      expect(post).toHaveBeenCalledTimes(1);
      expect(assignments).toEqual(["/login"]);
      expect(sessionStorage.getItem("refresh_token")).toBeNull();
    });
  });

  it("tras terminar un refresh, un 401 posterior inicia uno nuevo", async () => {
    sessionStorage.setItem("refresh_token", "r1");
    const post = vi.spyOn(axios, "post").mockResolvedValue({ data: { access_token: "a2", refresh_token: "r2" } });
    api.defaults.adapter = vi.fn().mockResolvedValue({ status: 200, data: "ok", headers: {}, config: {}, statusText: "OK" });

    await onError(unauthorized("/a"));
    await onError(unauthorized("/b"));

    expect(post).toHaveBeenCalledTimes(2);
    expect(post.mock.calls[1][1]).toEqual({ refresh_token: "r2" });
  });

  it("si el refresh falla limpia la sesión y manda a /login", async () => {
    sessionStorage.setItem("access_token", "a");
    sessionStorage.setItem("refresh_token", "r1");
    vi.spyOn(axios, "post").mockRejectedValue(new Error("expired"));
    const loc = { href: "" };
    vi.stubGlobal("location", loc);
    await expect(onError(unauthorized("/x"))).rejects.toThrow("expired");
    expect(sessionStorage.getItem("access_token")).toBeNull();
    expect(loc.href).toBe("/login");
  });
});
