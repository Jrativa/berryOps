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
