import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { InvitationPreview } from "../services/types";
import { mockFetch, renderWithProviders } from "../test-utils";
import { JoinPage } from "./JoinPage";

const auth = vi.hoisted(() => ({
  user: null as null | { user_id: string; full_name: string },
  loading: false,
  login: vi.fn(),
  completeLogin: vi.fn(),
  logout: vi.fn(),
}));
vi.mock("../hooks/useAuth", () => ({ useAuth: () => auth }));

beforeEach(() => {
  auth.user = null;
  auth.loading = false;
  auth.login.mockReset().mockResolvedValue(undefined);
  auth.completeLogin.mockReset().mockResolvedValue(undefined);
  auth.logout.mockReset();
});
afterEach(() => vi.unstubAllGlobals());

const preview = (over: Partial<InvitationPreview> = {}): InvitationPreview => ({
  family_name: "Yılmaz Ailesi",
  inviter_name: "Ayşe Yılmaz",
  label: "Elif",
  status: "pending",
  usable: true,
  expires_at: "2026-10-05T10:00:00Z",
  ...over,
});

const family = { family_id: "f9", name: "Yılmaz Ailesi", role: "member", created_by: "u1", member_count: 3, created_at: null };

const routes = (previewBody: unknown = preview()) => ({
  "GET /invitations/preview": previewBody,
  "POST /invitations/join": { access_token: "jwt-token", token_type: "bearer", family },
  "POST /invitations/accept": family,
});

const open = (query = "?kod=tok123") =>
  renderWithProviders(
    <Routes>
      <Route path="/katil" element={<JoinPage />} />
      <Route path="/aile/:id" element={<p>Aile sayfası</p>} />
    </Routes>,
    { route: `/katil${query}` },
  );

async function fillNewAccount(over: { code?: string; name?: string; username?: string; password?: string; email?: string } = {}) {
  await userEvent.type(screen.getByLabelText(/Davet şifresi/), over.code ?? "482917");
  await userEvent.type(screen.getByLabelText("Ad soyad"), over.name ?? "Elif Yılmaz");
  await userEvent.type(screen.getByLabelText("Kullanıcı adı"), over.username ?? "elif.y");
  await userEvent.type(screen.getByLabelText("Şifre"), over.password ?? "guclusifre123");
  if (over.email) await userEvent.type(screen.getByLabelText(/E-posta/), over.email);
}

describe("JoinPage: davet durumu", () => {
  it("davet edeni, aileyi ve etiketi gösterir", async () => {
    mockFetch(routes());
    open();
    expect(await screen.findByText(/Merhaba Elif!/)).toBeInTheDocument();
    expect(screen.getByText("Ayşe Yılmaz")).toBeInTheDocument();
    expect(screen.getByText("Yılmaz Ailesi")).toBeInTheDocument();
    expect(screen.getByLabelText(/Davet şifresi/)).toBeInTheDocument();
  });

  it("kod yoksa veya davet bilinmiyorsa 'bulunamadı' der", async () => {
    mockFetch({ "GET /invitations/preview": () => ({ status: 404, body: { detail: "Davet bulunamadı" } }) });
    open("?kod=yok");
    expect(await screen.findByText(/Bu davet bulunamadı/)).toBeInTheDocument();
    expect(screen.queryByLabelText(/Davet şifresi/)).not.toBeInTheDocument();
  });

  it("bağlantıda kod yoksa istek atmadan uyarır", async () => {
    const calls = mockFetch(routes());
    open("");
    expect(await screen.findByText(/Bu davet bulunamadı/)).toBeInTheDocument();
    expect(calls).toHaveLength(0);
  });

  it.each([
    ["accepted", /daha önce kullanılmış/],
    ["expired", /süresi dolmuş/],
    ["locked", /kilitlendi/],
  ] as const)("%s davette form göstermez, nedenini açıklar", async (status, message) => {
    mockFetch(routes(preview({ status, usable: false })));
    open();
    expect(await screen.findByRole("alert")).toHaveTextContent(message);
    expect(screen.queryByLabelText(/Davet şifresi/)).not.toBeInTheDocument();
  });
});

describe("JoinPage: yeni hesapla katılım (e-postasız)", () => {
  it("şifre ve hesap bilgileriyle hesap açar, girişi tamamlar ve aileye gider", async () => {
    const calls = mockFetch(routes());
    open();
    await screen.findByLabelText(/Davet şifresi/);
    await fillNewAccount({ code: "482 917" });
    await userEvent.click(screen.getByRole("button", { name: "Hesap oluştur ve katıl" }));
    expect(await screen.findByText("Aile sayfası")).toBeInTheDocument();
    const post = calls.find((c) => c.method === "POST");
    expect(post?.path).toBe("/invitations/join");
    expect(post?.body).toEqual({ token: "tok123", code: "482 917", full_name: "Elif Yılmaz", username: "elif.y", password: "guclusifre123" });
    expect(auth.completeLogin).toHaveBeenCalledWith("jwt-token");
  });

  it("isteğe bağlı e-posta yazılırsa gönderilir", async () => {
    const calls = mockFetch(routes());
    open();
    await screen.findByLabelText(/Davet şifresi/);
    await fillNewAccount({ email: "elif@example.com" });
    await userEvent.click(screen.getByRole("button", { name: "Hesap oluştur ve katıl" }));
    await screen.findByText("Aile sayfası");
    expect(calls.find((c) => c.method === "POST")?.body).toMatchObject({ email: "elif@example.com" });
  });

  it("şifre yazılmadan düğme kapalıdır", async () => {
    mockFetch(routes());
    open();
    expect(await screen.findByRole("button", { name: "Hesap oluştur ve katıl" })).toBeDisabled();
  });

  it("yanlış şifrede kalan hakkı gösterir ve sayfada kalır", async () => {
    mockFetch({ ...routes(), "POST /invitations/join": () => ({ status: 403, body: { detail: "Şifre hatalı. Kalan deneme hakkı: 4" } }) });
    open();
    await screen.findByLabelText(/Davet şifresi/);
    await fillNewAccount({ code: "000000" });
    await userEvent.click(screen.getByRole("button", { name: "Hesap oluştur ve katıl" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Şifre hatalı. Kalan deneme hakkı: 4");
    expect(screen.queryByText("Aile sayfası")).not.toBeInTheDocument();
    expect(auth.completeLogin).not.toHaveBeenCalled();
  });

  it("kilitlenince sunucunun mesajını gösterir", async () => {
    mockFetch({ ...routes(), "POST /invitations/join": () => ({ status: 423, body: { detail: "Çok fazla yanlış şifre denendiği için davet kilitlendi. Aile yöneticisinden yeni bir şifre isteyin" } }) });
    open();
    await screen.findByLabelText(/Davet şifresi/);
    await fillNewAccount();
    await userEvent.click(screen.getByRole("button", { name: "Hesap oluştur ve katıl" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("kilitlendi");
  });

  it("geçersiz kullanıcı adını sunucunun Türkçe mesajıyla gösterir", async () => {
    mockFetch({
      ...routes(),
      "POST /invitations/join": () => ({
        status: 422,
        body: { detail: [{ type: "value_error", loc: ["body", "username"], msg: "Value error, Kullanıcı adı 3-30 karakter olmalı; yalnızca küçük harf (a-z), rakam, nokta, tire ve alt çizgi içerebilir" }] },
      }),
    });
    open();
    await screen.findByLabelText(/Davet şifresi/);
    await fillNewAccount({ username: "Çocuk!" });
    await userEvent.click(screen.getByRole("button", { name: "Hesap oluştur ve katıl" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Kullanıcı adı 3-30 karakter olmalı");
  });

  it("alınmış kullanıcı adında 409 mesajını gösterir", async () => {
    mockFetch({ ...routes(), "POST /invitations/join": () => ({ status: 409, body: { detail: "Bu kullanıcı adı alınmış" } }) });
    open();
    await screen.findByLabelText(/Davet şifresi/);
    await fillNewAccount();
    await userEvent.click(screen.getByRole("button", { name: "Hesap oluştur ve katıl" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Bu kullanıcı adı alınmış");
  });
});

describe("JoinPage: mevcut hesapla katılım", () => {
  it("'Hesabım var' sekmesinde giriş yapıp şifreyle katılır", async () => {
    const calls = mockFetch(routes());
    open();
    await screen.findByLabelText(/Davet şifresi/);
    await userEvent.click(screen.getByRole("tab", { name: "Hesabım var" }));
    await userEvent.type(screen.getByLabelText(/Davet şifresi/), "482917");
    await userEvent.type(screen.getByLabelText("E-posta veya kullanıcı adı"), "elif.y");
    await userEvent.type(screen.getByLabelText("Şifre"), "guclusifre123");
    await userEvent.click(screen.getByRole("button", { name: "Giriş yap ve katıl" }));
    expect(await screen.findByText("Aile sayfası")).toBeInTheDocument();
    expect(auth.login).toHaveBeenCalledWith("elif.y", "guclusifre123");
    expect(calls.find((c) => c.method === "POST" && c.path === "/invitations/accept")?.body).toEqual({ token: "tok123", code: "482917" });
  });

  it("giriş yapmış kullanıcı yalnızca şifreyi girip katılır", async () => {
    auth.user = { user_id: "u1", full_name: "Can Yılmaz" };
    const calls = mockFetch(routes());
    open();
    expect(await screen.findByText(/hesabıyla katılacaksınız/)).toHaveTextContent("Can Yılmaz");
    expect(screen.queryByRole("tab", { name: "Hesabım var" })).not.toBeInTheDocument();
    await userEvent.type(screen.getByLabelText(/Davet şifresi/), "482917");
    await userEvent.click(screen.getByRole("button", { name: "Aileye katıl" }));
    expect(await screen.findByText("Aile sayfası")).toBeInTheDocument();
    expect(auth.login).not.toHaveBeenCalled();
    expect(calls.find((c) => c.path === "/invitations/accept")?.body).toEqual({ token: "tok123", code: "482917" });
  });

  it("yanlış şifrede giriş yapmış kullanıcıya hata gösterir", async () => {
    auth.user = { user_id: "u1", full_name: "Can Yılmaz" };
    mockFetch({ ...routes(), "POST /invitations/accept": () => ({ status: 403, body: { detail: "Şifre hatalı. Kalan deneme hakkı: 3" } }) });
    open();
    await userEvent.type(await screen.findByLabelText(/Davet şifresi/), "111111");
    await userEvent.click(screen.getByRole("button", { name: "Aileye katıl" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Kalan deneme hakkı: 3");
  });

  it("'Başka bir hesapla devam et' oturumu kapatır", async () => {
    auth.user = { user_id: "u1", full_name: "Can Yılmaz" };
    mockFetch(routes());
    open();
    await userEvent.click(await screen.findByRole("button", { name: "Başka bir hesapla devam et" }));
    await waitFor(() => expect(auth.logout).toHaveBeenCalled());
  });
});
