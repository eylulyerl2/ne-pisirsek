import { afterEach, describe, expect, it, vi } from "vitest";
import { mockFetch } from "../test-utils";
import { ApiError, request, setUnauthorizedHandler, tokenStore } from "./api";
import { api } from "./endpoints";

afterEach(() => {
  vi.unstubAllGlobals();
  setUnauthorizedHandler(null);
});

describe("API istemcisi", () => {
  it("oturum açıkken Authorization başlığı ekler", async () => {
    tokenStore.set("abc123");
    let header: string | undefined;
    vi.stubGlobal(
      "fetch",
      vi.fn(async (_url: string, init: RequestInit) => {
        header = (init.headers as Record<string, string>).Authorization;
        return new Response(JSON.stringify({ ok: true }), { status: 200 });
      }),
    );
    await request("/auth/me");
    expect(header).toBe("Bearer abc123");
  });

  it("giriş isteğini form olarak, jetonsuz gönderir", async () => {
    tokenStore.set("eski");
    const calls = mockFetch({ "POST /auth/login": { body: { access_token: "t", token_type: "bearer" } } });
    await api.login("ayse@example.com", "gizli-sifre");
    expect(calls[0].body).toEqual({ username: "ayse@example.com", password: "gizli-sifre" });
  });

  it("boş parametreleri atlar, dizileri tekrarlı gönderir", async () => {
    const calls = mockFetch({ "GET /meals": { body: { items: [], total: 0, limit: 24, offset: 0 } } });
    await api.meals({ q: "", region: ["ege", "marmara"], category: undefined, max_cost: 300 });
    expect(calls[0].search).toBe("?region=ege&region=marmara&max_cost=300");
  });

  it("204 yanıtında boş döner", async () => {
    mockFetch({ "DELETE /plans/1": () => ({ status: 204 }) });
    await expect(api.deletePlan("1")).resolves.toBeUndefined();
  });

  it("hata gövdesini Türkçe mesaja çevirip ApiError fırlatır", async () => {
    mockFetch({ "POST /auth/register": () => ({ status: 409, body: { detail: "Bu e-posta adresi zaten kayıtlı" } }) });
    const error = (await api.register({ email: "a@b.co", password: "12345678", full_name: "A" }).catch((e) => e)) as ApiError;
    expect(error).toBeInstanceOf(ApiError);
    expect(error.status).toBe(409);
    expect(error.message).toBe("Bu e-posta adresi zaten kayıtlı");
  });

  it("oturum açıkken gelen 401'de oturum kapatma işleyicisini çağırır", async () => {
    tokenStore.set("gecersiz");
    const handler = vi.fn();
    setUnauthorizedHandler(handler);
    mockFetch({ "GET /plans": () => ({ status: 401, body: { detail: "Kimlik doğrulanamadı" } }) });
    await expect(api.plans()).rejects.toThrow("Kimlik doğrulanamadı");
    expect(handler).toHaveBeenCalledOnce();
  });

  it("yanlış şifre 401'i oturum kapatmayı tetiklemez", async () => {
    const handler = vi.fn();
    setUnauthorizedHandler(handler);
    mockFetch({ "POST /auth/login": () => ({ status: 401, body: { detail: "E-posta veya şifre hatalı" } }) });
    await expect(api.login("a@b.co", "yanlis")).rejects.toThrow("E-posta veya şifre hatalı");
    expect(handler).not.toHaveBeenCalled();
  });

  it("ağ hatasında anlaşılır mesaj verir", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed to fetch")));
    const error = (await request("/plans").catch((e) => e)) as ApiError;
    expect(error).toBeInstanceOf(ApiError);
    expect(error.status).toBe(0);
    expect(error.message).toContain("Sunucuya ulaşılamadı");
  });
});
