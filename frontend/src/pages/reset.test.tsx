import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { PasswordResetPreview, Preferences } from "../services/types";
import { mockFetch, renderWithProviders } from "../test-utils";
import { PreferencesPage } from "./PreferencesPage";
import { ResetPasswordPage } from "./ResetPasswordPage";

const auth = vi.hoisted(() => ({
  user: { user_id: "u1", full_name: "Elif Yılmaz", email: null, username: "elif.y" } as { user_id: string; full_name: string; email: string | null; username: string | null },
  loading: false,
  completeLogin: vi.fn(),
  setUser: vi.fn(),
}));
vi.mock("../hooks/useAuth", () => ({ useAuth: () => auth }));

beforeEach(() => {
  auth.loading = false;
  auth.completeLogin.mockReset().mockResolvedValue(undefined);
  auth.setUser.mockReset();
});
afterEach(() => vi.unstubAllGlobals());

const preview = (over: Partial<PasswordResetPreview> = {}): PasswordResetPreview => ({
  full_name: "Elif Yılmaz",
  username: "elif.y",
  status: "pending",
  usable: true,
  expires_at: "2026-09-29T10:00:00Z",
  ...over,
});

const openReset = (query = "?kod=rt1") =>
  renderWithProviders(
    <Routes>
      <Route path="/sifre-sifirla" element={<ResetPasswordPage />} />
      <Route path="/plan" element={<p>Plan sayfası</p>} />
    </Routes>,
    { route: `/sifre-sifirla${query}` },
  );

async function fill(code = "654321", password = "yepyeni-sifre-77", again = password) {
  await userEvent.type(await screen.findByLabelText(/Sıfırlama şifresi/), code);
  await userEvent.type(screen.getByLabelText("Yeni şifre"), password);
  await userEvent.type(screen.getByLabelText("Yeni şifre (tekrar)"), again);
}

describe("ResetPasswordPage", () => {
  it("hangi hesap için sıfırlama yapıldığını gösterir", async () => {
    mockFetch({ "GET /password-resets/preview": preview() });
    openReset();
    expect(await screen.findByText(/için yeni şifre belirleyin/)).toHaveTextContent("Elif Yılmaz (@elif.y) için yeni şifre belirleyin");
  });

  it("doğru şifreyle yeni şifreyi kaydeder, giriş yaptırır ve plana gider", async () => {
    const calls = mockFetch({ "GET /password-resets/preview": preview(), "POST /password-resets/complete": { access_token: "jwt", token_type: "bearer" } });
    openReset();
    await fill("654 321");
    await userEvent.click(screen.getByRole("button", { name: "Şifremi yenile ve giriş yap" }));
    expect(await screen.findByText("Plan sayfası")).toBeInTheDocument();
    expect(calls.find((c) => c.method === "POST")?.body).toEqual({ token: "rt1", code: "654 321", new_password: "yepyeni-sifre-77" });
    expect(auth.completeLogin).toHaveBeenCalledWith("jwt");
  });

  it("şifreler uyuşmazsa istek atmadan uyarır", async () => {
    const calls = mockFetch({ "GET /password-resets/preview": preview() });
    openReset();
    await fill("654321", "yepyeni-sifre-77", "baska-sifre-1234");
    await userEvent.click(screen.getByRole("button", { name: "Şifremi yenile ve giriş yap" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Şifreler aynı değil");
    expect(calls.some((c) => c.method === "POST")).toBe(false);
  });

  it("yanlış şifrede kalan hakkı gösterir ve giriş yaptırmaz", async () => {
    mockFetch({ "GET /password-resets/preview": preview(), "POST /password-resets/complete": () => ({ status: 403, body: { detail: "Şifre hatalı. Kalan deneme hakkı: 4" } }) });
    openReset();
    await fill("000000");
    await userEvent.click(screen.getByRole("button", { name: "Şifremi yenile ve giriş yap" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Kalan deneme hakkı: 4");
    expect(auth.completeLogin).not.toHaveBeenCalled();
  });

  it("kısa şifreyi sunucunun Türkçe mesajıyla gösterir", async () => {
    mockFetch({
      "GET /password-resets/preview": preview(),
      "POST /password-resets/complete": () => ({ status: 422, body: { detail: [{ type: "string_too_short", loc: ["body", "new_password"], msg: "x", ctx: { min_length: 8 } }] } }),
    });
    openReset();
    await fill("654321", "kisa", "kisa");
    await userEvent.click(screen.getByRole("button", { name: "Şifremi yenile ve giriş yap" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Yeni şifre en az 8 karakter olmalı");
  });

  it("şifre yazılmadan düğme kapalıdır", async () => {
    mockFetch({ "GET /password-resets/preview": preview() });
    openReset();
    expect(await screen.findByRole("button", { name: "Şifremi yenile ve giriş yap" })).toBeDisabled();
  });

  it.each([
    ["used", /daha önce kullanılmış/],
    ["expired", /süresi dolmuş/],
    ["locked", /kilitlendi/],
  ] as const)("%s bağlantıda form göstermez, nedenini açıklar", async (status, message) => {
    mockFetch({ "GET /password-resets/preview": preview({ status, usable: false }) });
    openReset();
    expect(await screen.findByRole("alert")).toHaveTextContent(message);
    expect(screen.queryByLabelText(/Sıfırlama şifresi/)).not.toBeInTheDocument();
  });

  it("bilinmeyen bağlantı için 'bulunamadı' der", async () => {
    mockFetch({ "GET /password-resets/preview": () => ({ status: 404, body: { detail: "yok" } }) });
    openReset("?kod=yok");
    expect(await screen.findByText(/Bu bağlantı bulunamadı/)).toBeInTheDocument();
  });

  it("kod olmayan bağlantıda istek atmaz", async () => {
    const calls = mockFetch({});
    openReset("");
    expect(await screen.findByText(/Bu bağlantı bulunamadı/)).toBeInTheDocument();
    expect(calls).toHaveLength(0);
  });
});

describe("Tercihler: şifre değiştirme", () => {
  const prefs: Preferences = {
    daily_calorie_target: null,
    calorie_tolerance_percent: 10,
    protein_target_grams: null,
    carbohydrate_target_grams: null,
    fat_target_grams: null,
    servings_per_meal: 2,
    soup_frequency_per_week: 2,
    vegetable_frequency_per_week: 2,
    legume_frequency_per_week: 1,
    max_preparation_time_minutes: null,
    weekly_budget: null,
    currency: "TRY",
  };

  async function fillPassword(current: string, next: string, again = next) {
    await userEvent.type(await screen.findByLabelText("Mevcut şifre"), current);
    await userEvent.type(screen.getByLabelText("Yeni şifre"), next);
    await userEvent.type(screen.getByLabelText("Yeni şifre (tekrar)"), again);
  }

  it("mevcut şifreyle yeni şifreyi gönderir ve alanları temizler", async () => {
    const calls = mockFetch({ "GET /users/me/preferences": prefs, "POST /users/me/password": () => ({ status: 204 }) });
    renderWithProviders(<PreferencesPage />);
    await fillPassword("eski-sifre-1", "yepyeni-sifre-77");
    await userEvent.click(screen.getByRole("button", { name: "Şifreyi değiştir" }));
    expect(await screen.findByText("Şifreniz değiştirildi.")).toBeInTheDocument();
    expect(calls.find((c) => c.path === "/users/me/password")?.body).toEqual({ current_password: "eski-sifre-1", new_password: "yepyeni-sifre-77" });
    expect(screen.getByLabelText("Mevcut şifre")).toHaveValue("");
  });

  it("yeni şifreler uyuşmazsa istek atmaz", async () => {
    const calls = mockFetch({ "GET /users/me/preferences": prefs });
    renderWithProviders(<PreferencesPage />);
    await fillPassword("eski-sifre-1", "yepyeni-sifre-77", "baska-sifre-1234");
    await userEvent.click(screen.getByRole("button", { name: "Şifreyi değiştir" }));
    expect(await screen.findByText("Yeni şifreler aynı değil")).toBeInTheDocument();
    expect(calls.some((c) => c.path === "/users/me/password")).toBe(false);
  });

  it("yanlış mevcut şifrede sunucu mesajını gösterir", async () => {
    mockFetch({ "GET /users/me/preferences": prefs, "POST /users/me/password": () => ({ status: 403, body: { detail: "Mevcut şifre hatalı" } }) });
    renderWithProviders(<PreferencesPage />);
    await fillPassword("yanlis", "yepyeni-sifre-77");
    await userEvent.click(screen.getByRole("button", { name: "Şifreyi değiştir" }));
    await waitFor(() => expect(screen.getByText("Mevcut şifre hatalı")).toBeInTheDocument());
    expect(screen.queryByText("Şifreniz değiştirildi.")).not.toBeInTheDocument();
  });
});
