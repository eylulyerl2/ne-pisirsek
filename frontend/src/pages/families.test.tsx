import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { FamilyDetail, FamilySummary, Invitation } from "../services/types";
import { mockFetch, renderWithProviders } from "../test-utils";
import { formatCode, inviteLink, inviteMessage, keepParams, resetLink, resetMessage } from "../utils/nav";
import { FamiliesPage } from "./FamiliesPage";
import { FamilyDetailPage } from "./FamilyDetailPage";

vi.mock("../hooks/useAuth", () => ({
  useAuth: () => ({ user: { user_id: "u-ayse", email: "ayse@example.com", username: null, full_name: "Ayşe Yılmaz" } }),
}));

afterEach(() => vi.unstubAllGlobals());

const summary = (over: Partial<FamilySummary> = {}): FamilySummary => ({
  family_id: "f1",
  name: "Yılmaz Ailesi",
  role: "admin",
  created_by: "u-ayse",
  member_count: 2,
  created_at: null,
  ...over,
});

const detail = (role: "admin" | "member" = "admin", createdBy = "u-ayse", resetPending = false): FamilyDetail => ({
  ...summary({ role, created_by: createdBy }),
  members: [
    { user_id: "u-ayse", full_name: "Ayşe Yılmaz", username: null, avatar_url: null, role, joined_at: "2026-09-01T10:00:00Z", can_reset_password: false, reset_pending: false },
    {
      user_id: "u-elif",
      full_name: "Elif Yılmaz",
      username: "elif.y",
      avatar_url: null,
      role: "member",
      joined_at: "2026-09-02T10:00:00Z",
      can_reset_password: role === "admin",
      reset_pending: role === "admin" && resetPending,
    },
  ],
});

const invitation = (over: Partial<Invitation> = {}): Invitation => ({
  invitation_id: "i1",
  family_id: "f1",
  label: "Elif",
  token: "tok123",
  status: "pending",
  failed_attempts: 0,
  expires_at: "2026-10-05T10:00:00Z",
  created_at: null,
  code: null,
  ...over,
});

function detailRoutes(role: "admin" | "member" = "admin", createdBy = "u-ayse", invitations: Invitation[] = [invitation()], resetPending = false) {
  return {
    "GET /families/f1": detail(role, createdBy, resetPending),
    "GET /families/f1/invitations": invitations,
    "GET /families": [summary({ role })],
  };
}

const renderDetail = () =>
  renderWithProviders(
    <Routes>
      <Route path="/aile/:familyId" element={<FamilyDetailPage />} />
      <Route path="/aile" element={<p>Aile listesi sayfası</p>} />
    </Routes>,
    { route: "/aile/f1" },
  );

describe("FamiliesPage", () => {
  it("aileleri rol ve üye sayısıyla listeler", async () => {
    mockFetch({ "GET /families": [summary(), summary({ family_id: "f2", name: "Kaya Ailesi", role: "member", member_count: 4 })] });
    renderWithProviders(<FamiliesPage />);
    expect(await screen.findByRole("heading", { name: "Yılmaz Ailesi" })).toBeInTheDocument();
    expect(screen.getByText("4 üye · Üye")).toBeInTheDocument();
  });

  it("ailesi olmayana yeni aile kurmayı ve davet bağlantısını anlatır", async () => {
    mockFetch({ "GET /families": [] });
    renderWithProviders(<FamiliesPage />);
    expect(await screen.findByText("Henüz bir ailede değilsiniz")).toBeInTheDocument();
    expect(screen.getByText(/davet bağlantısını açıp şifreyi girin/)).toBeInTheDocument();
  });

  it("yeni aile oluşturur; boş adla düğme kapalıdır", async () => {
    const calls = mockFetch({ "GET /families": [], "POST /families": summary({ name: "Demir Ailesi" }) });
    renderWithProviders(<FamiliesPage />);
    const button = await screen.findByRole("button", { name: "Aile oluştur" });
    expect(button).toBeDisabled();
    await userEvent.type(screen.getByLabelText("Aile adı"), "Demir Ailesi");
    await userEvent.click(button);
    await waitFor(() => expect(calls.find((c) => c.method === "POST")?.body).toEqual({ name: "Demir Ailesi" }));
  });
});

describe("FamilyDetailPage: roller ve görünürlük", () => {
  it("kurucu her şeyi görür: üyeler, davet, silme", async () => {
    mockFetch(detailRoutes("admin"));
    renderDetail();
    expect(await screen.findByRole("heading", { name: "Yılmaz Ailesi" })).toBeInTheDocument();
    expect(screen.getByText(/Kurucu/)).toBeInTheDocument();
    expect(screen.getByText(/@elif\.y/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Bağlantı ve şifre oluştur" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Aileyi sil" })).toBeInTheDocument();
  });

  it("kurucu olmayan yönetici üyeleri ve daveti yönetir ama 'Aileyi sil' görmez", async () => {
    mockFetch(detailRoutes("admin", "u-baska"));
    renderDetail();
    await screen.findByRole("heading", { name: "Yılmaz Ailesi" });
    expect(screen.getByRole("button", { name: "Bağlantı ve şifre oluştur" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Yönetici yap" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Aileyi sil" })).not.toBeInTheDocument();
    expect(screen.queryByText("Tehlikeli bölge")).not.toBeInTheDocument();
  });

  it("üyeye davet, rol ve silme kontrollerini göstermez", async () => {
    mockFetch(detailRoutes("member", "u-baska"));
    renderDetail();
    await screen.findByRole("heading", { name: "Yılmaz Ailesi" });
    expect(screen.queryByRole("button", { name: "Bağlantı ve şifre oluştur" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Yönetici yap" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Aileyi sil" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Adı değiştir" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Aileden ayrıl" })).toBeInTheDocument();
  });

  it("kurucu silmeyi iki adımda onaylar ve listeye döner", async () => {
    const calls = mockFetch({ ...detailRoutes(), "DELETE /families/f1": () => ({ status: 204 }) });
    renderDetail();
    await userEvent.click(await screen.findByRole("button", { name: "Aileyi sil" }));
    expect(calls.some((c) => c.method === "DELETE")).toBe(false);
    await userEvent.click(screen.getByRole("button", { name: "Evet, ailemi sil" }));
    expect(await screen.findByText("Aile listesi sayfası")).toBeInTheDocument();
  });

  it("silme onayından vazgeçilirse hiçbir şey silinmez", async () => {
    const calls = mockFetch(detailRoutes());
    renderDetail();
    await userEvent.click(await screen.findByRole("button", { name: "Aileyi sil" }));
    await userEvent.click(screen.getByRole("button", { name: "Vazgeç" }));
    expect(screen.getByRole("button", { name: "Aileyi sil" })).toBeInTheDocument();
    expect(calls.some((c) => c.method === "DELETE")).toBe(false);
  });

  it("sunucu silmeyi reddederse Türkçe mesajı gösterir", async () => {
    mockFetch({ ...detailRoutes(), "DELETE /families/f1": () => ({ status: 403, body: { detail: "Aileyi yalnızca kurucusu silebilir" } }) });
    renderDetail();
    await userEvent.click(await screen.findByRole("button", { name: "Aileyi sil" }));
    await userEvent.click(screen.getByRole("button", { name: "Evet, ailemi sil" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Aileyi yalnızca kurucusu silebilir");
  });
});

describe("FamilyDetailPage: bağlantı ve tek kullanımlık şifre", () => {
  it("davet oluşturunca bağlantıyı ve şifreyi (3+3 gruplu) gösterir", async () => {
    const calls = mockFetch({
      ...detailRoutes("admin", "u-ayse", []),
      "POST /families/f1/invitations": invitation({ token: "yeni-token", code: "482917" }),
    });
    renderDetail();
    await userEvent.type(await screen.findByLabelText(/Kimin için/), "Elif");
    await userEvent.click(screen.getByRole("button", { name: "Bağlantı ve şifre oluştur" }));
    expect(await screen.findByText(inviteLink("yeni-token"))).toBeInTheDocument();
    expect(screen.getByLabelText("Tek kullanımlık şifre")).toHaveTextContent("482 917");
    expect(screen.getByText("Elif için davet hazır")).toBeInTheDocument();
    expect(calls.find((c) => c.method === "POST")?.body).toEqual({ label: "Elif" });
  });

  it("etiketsiz davet boş gövdeyle oluşur", async () => {
    const calls = mockFetch({ ...detailRoutes("admin", "u-ayse", []), "POST /families/f1/invitations": invitation({ label: null, code: "123456" }) });
    renderDetail();
    await userEvent.click(await screen.findByRole("button", { name: "Bağlantı ve şifre oluştur" }));
    expect(await screen.findByText("Davet hazır")).toBeInTheDocument();
    expect(calls.find((c) => c.method === "POST")?.body).toEqual({});
  });

  it("hazır mesajı (aile adı, bağlantı, şifre) panoya kopyalar", async () => {
    const user = userEvent.setup();
    mockFetch({ ...detailRoutes("admin", "u-ayse", []), "POST /families/f1/invitations": invitation({ token: "abc", code: "482917" }) });
    renderDetail();
    await user.click(await screen.findByRole("button", { name: "Bağlantı ve şifre oluştur" }));
    await user.click(await screen.findByRole("button", { name: "Bağlantı ve şifreyi kopyala" }));
    expect(await navigator.clipboard.readText()).toBe(inviteMessage("Yılmaz Ailesi", "abc", "482917"));
    expect(screen.getByRole("button", { name: "Kopyalandı ✓" })).toBeInTheDocument();
  });

  it("bekleyen davetleri listeler ama şifreyi göstermez", async () => {
    mockFetch(detailRoutes("admin", "u-ayse", [invitation({ failed_attempts: 2 })]));
    renderDetail();
    const row = (await screen.findByText("Elif", { selector: "strong" })).closest("li") as HTMLElement;
    expect(within(row).getByText(/2 yanlış deneme/)).toBeInTheDocument();
    expect(screen.queryByLabelText("Tek kullanımlık şifre")).not.toBeInTheDocument();
  });

  it("kilitli daveti belirtir; 'Yeni şifre üret' yeni şifreyi gösterir", async () => {
    const calls = mockFetch({
      ...detailRoutes("admin", "u-ayse", [invitation({ status: "locked", failed_attempts: 5, label: null })]),
      "POST /families/f1/invitations/i1/regenerate": invitation({ code: "654321", label: null }),
    });
    renderDetail();
    expect(await screen.findByText(/Kilitli: çok fazla yanlış şifre denendi/)).toBeInTheDocument();
    expect(screen.getByText("İsimsiz davet")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Yeni şifre üret" }));
    expect(await screen.findByLabelText("Tek kullanımlık şifre")).toHaveTextContent("654 321");
    expect(calls.some((c) => c.method === "POST" && c.path.endsWith("/regenerate"))).toBe(true);
  });

  it("bekleyen daveti iptal eder", async () => {
    const calls = mockFetch({ ...detailRoutes(), "DELETE /families/f1/invitations/i1": () => ({ status: 204 }) });
    renderDetail();
    const row = (await screen.findByText("Elif", { selector: "strong" })).closest("li") as HTMLElement;
    await userEvent.click(within(row).getByRole("button", { name: "İptal et" }));
    await waitFor(() => expect(calls.some((c) => c.method === "DELETE" && c.path.endsWith("/invitations/i1"))).toBe(true));
  });

  it("davet oluşturma hatasını Türkçe gösterir", async () => {
    mockFetch({ ...detailRoutes("admin", "u-ayse", []), "POST /families/f1/invitations": () => ({ status: 409, body: { detail: "Çok fazla açık davet var, önce bazılarını iptal edin" } }) });
    renderDetail();
    await userEvent.click(await screen.findByRole("button", { name: "Bağlantı ve şifre oluştur" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Çok fazla açık davet var");
  });
});

describe("FamilyDetailPage: şifre sıfırlama", () => {
  const created = { token: "reset-tok", code: "654321", expires_at: "2026-09-29T10:00:00Z", member_name: "Elif Yılmaz" };

  it("yalnızca ailenin açtığı hesaplar için 'Şifre sıfırla' gösterir (kendisi için değil)", async () => {
    mockFetch(detailRoutes());
    renderDetail();
    await screen.findByRole("heading", { name: "Yılmaz Ailesi" });
    expect(screen.getAllByRole("button", { name: "Şifre sıfırla" })).toHaveLength(1);
    const elifRow = screen.getByText("Elif Yılmaz").closest("li") as HTMLElement;
    expect(within(elifRow).getByRole("button", { name: "Şifre sıfırla" })).toBeInTheDocument();
  });

  it("üye (yönetici olmayan) sıfırlama düğmesi görmez", async () => {
    mockFetch(detailRoutes("member", "u-baska"));
    renderDetail();
    await screen.findByRole("heading", { name: "Yılmaz Ailesi" });
    expect(screen.queryByRole("button", { name: "Şifre sıfırla" })).not.toBeInTheDocument();
  });

  it("bağlantı ve tek kullanımlık şifre üretir, hazır mesajı kopyalar", async () => {
    const user = userEvent.setup();
    const calls = mockFetch({ ...detailRoutes(), "POST /families/f1/members/u-elif/password-reset": created });
    renderDetail();
    await user.click(await screen.findByRole("button", { name: "Şifre sıfırla" }));
    expect(await screen.findByText("Elif Yılmaz için şifre sıfırlama bağlantısı hazır")).toBeInTheDocument();
    expect(screen.getByText(resetLink("reset-tok"))).toBeInTheDocument();
    expect(screen.getByLabelText("Tek kullanımlık şifre")).toHaveTextContent("654 321");
    expect(screen.getByText(/24 saat geçerli/)).toBeInTheDocument();
    expect(calls.some((c) => c.method === "POST" && c.path === "/families/f1/members/u-elif/password-reset")).toBe(true);

    await user.click(screen.getByRole("button", { name: "Bağlantı ve şifreyi kopyala" }));
    expect(await navigator.clipboard.readText()).toBe(resetMessage("reset-tok", "654321"));
  });

  it("bekleyen sıfırlamayı belirtir; yenileme ve iptal sunar", async () => {
    const calls = mockFetch({ ...detailRoutes("admin", "u-ayse", [], true), "DELETE /families/f1/members/u-elif/password-reset": () => ({ status: 204 }) });
    renderDetail();
    expect(await screen.findByText(/Şifre sıfırlama bekliyor/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Yeni sıfırlama bağlantısı" })).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Sıfırlamayı iptal et" }));
    await waitFor(() => expect(calls.some((c) => c.method === "DELETE" && c.path.endsWith("/password-reset"))).toBe(true));
  });

  it("sunucu reddederse Türkçe mesajı gösterir", async () => {
    mockFetch({ ...detailRoutes(), "POST /families/f1/members/u-elif/password-reset": () => ({ status: 403, body: { detail: "Bu hesabı aile açmadığı için şifresini yalnızca hesap sahibi değiştirebilir" } }) });
    renderDetail();
    await userEvent.click(await screen.findByRole("button", { name: "Şifre sıfırla" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("yalnızca hesap sahibi değiştirebilir");
    expect(screen.queryByText(/bağlantısı hazır/)).not.toBeInTheDocument();
  });
});

describe("FamilyDetailPage: üye yönetimi", () => {
  it("üyeyi yönetici yapar", async () => {
    const calls = mockFetch({ ...detailRoutes(), "PATCH /families/f1/members/u-elif": { user_id: "u-elif", full_name: "Elif Yılmaz", username: "elif.y", avatar_url: null, role: "admin", joined_at: null } });
    renderDetail();
    await userEvent.click(await screen.findByRole("button", { name: "Yönetici yap" }));
    await waitFor(() => expect(calls.find((c) => c.method === "PATCH")?.body).toEqual({ role: "admin" }));
  });

  it("üyeyi çıkarmak iki adımlı onay ister", async () => {
    const calls = mockFetch({ ...detailRoutes(), "DELETE /families/f1/members/u-elif": () => ({ status: 204 }) });
    renderDetail();
    await userEvent.click(await screen.findByRole("button", { name: "Çıkar" }));
    expect(screen.getByText("Elif Yılmaz çıkarılsın mı?")).toBeInTheDocument();
    expect(calls.some((c) => c.method === "DELETE")).toBe(false);
    await userEvent.click(screen.getByRole("button", { name: "Evet, çıkar" }));
    await waitFor(() => expect(calls.some((c) => c.method === "DELETE" && c.path.endsWith("u-elif"))).toBe(true));
  });

  it("tek yönetici ayrılmaya çalışınca sunucu mesajını gösterir ve sayfada kalır", async () => {
    mockFetch({
      ...detailRoutes(),
      "DELETE /families/f1/members/u-ayse": () => ({ status: 400, body: { detail: "Ailedeki tek yönetici çıkarılamaz. Önce başka bir yönetici atayın veya aileyi silin" } }),
    });
    renderDetail();
    await userEvent.click(await screen.findByRole("button", { name: "Aileden ayrıl" }));
    await userEvent.click(screen.getByRole("button", { name: "Evet, ayrıl" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Ailedeki tek yönetici çıkarılamaz");
    expect(screen.getByRole("heading", { name: "Yılmaz Ailesi" })).toBeInTheDocument();
  });

  it("ayrılınca aile listesine döner", async () => {
    mockFetch({ ...detailRoutes("member", "u-baska"), "DELETE /families/f1/members/u-ayse": () => ({ status: 204 }) });
    renderDetail();
    await userEvent.click(await screen.findByRole("button", { name: "Aileden ayrıl" }));
    await userEvent.click(screen.getByRole("button", { name: "Evet, ayrıl" }));
    expect(await screen.findByText("Aile listesi sayfası")).toBeInTheDocument();
  });

  it("aileyi yeniden adlandırır", async () => {
    const calls = mockFetch({ ...detailRoutes(), "PATCH /families/f1": summary({ name: "Yılmazlar" }) });
    renderDetail();
    await userEvent.click(await screen.findByRole("button", { name: "Adı değiştir" }));
    const input = screen.getByLabelText("Aile adı");
    await userEvent.clear(input);
    await userEvent.type(input, "Yılmazlar");
    await userEvent.click(screen.getByRole("button", { name: "Kaydet" }));
    await waitFor(() => expect(calls.find((c) => c.method === "PATCH" && c.path === "/families/f1")?.body).toEqual({ name: "Yılmazlar" }));
  });

  it("üye olunmayan aile için hata ve dönüş bağlantısı gösterir", async () => {
    mockFetch({ "GET /families/f1": () => ({ status: 404, body: { detail: "Aile bulunamadı" } }) });
    renderDetail();
    expect(await screen.findByRole("alert")).toHaveTextContent("Aile bulunamadı");
    expect(screen.getByRole("link", { name: "Ailelerime dön" })).toBeInTheDocument();
  });
});

describe("gezinme ve davet yardımcıları", () => {
  it("yalnızca hafta ve aile parametrelerini korur", () => {
    expect(keepParams("?hafta=2026-09-28&aile=f1&x=1")).toBe("?hafta=2026-09-28&aile=f1");
    expect(keepParams("?aile=f1")).toBe("?aile=f1");
    expect(keepParams("?x=1")).toBe("");
    expect(keepParams("")).toBe("");
  });

  it("davet bağlantısı ve şifre biçimi", () => {
    expect(inviteLink("abc-DEF_1", "https://nepisirsek.example")).toBe("https://nepisirsek.example/katil?kod=abc-DEF_1");
    expect(inviteLink("a b", "https://x.y")).toBe("https://x.y/katil?kod=a%20b");
    expect(formatCode("482917")).toBe("482 917");
    expect(formatCode("123")).toBe("123");
    expect(resetLink("t k", "https://x.y")).toBe("https://x.y/sifre-sifirla?kod=t%20k");
    expect(resetMessage("tok", "482917", "https://x.y")).toBe("Şifreni yenilemek için:\nhttps://x.y/sifre-sifirla?kod=tok\nŞifre: 482 917");
    expect(inviteMessage("Yılmaz Ailesi", "tok", "482917", "https://x.y")).toBe("Yılmaz Ailesi ailesine katıl:\nhttps://x.y/katil?kod=tok\nŞifre: 482 917");
  });
});
