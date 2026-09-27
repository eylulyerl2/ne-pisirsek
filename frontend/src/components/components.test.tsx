import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { Alternative, MealDetail, PlannedMeal } from "../services/types";
import { mockFetch, renderWithProviders } from "../test-utils";
import { AlternativesSheet } from "./AlternativesSheet";
import { DishDetail, recipeSteps } from "./DishDetail";

afterEach(() => vi.unstubAllGlobals());

const brief = (id: string, name: string) => ({
  meal_id: id,
  name,
  image_url: null,
  region: null,
  total_time_minutes: 30,
  calories_per_serving: 250,
  categories: ["yan-yemek"],
  has_recipe: true,
});

const pilav: PlannedMeal = {
  planned_meal_id: "pm-1",
  day_of_week: 2,
  meal_type: "dinner",
  course: "side",
  course_name: "Yan yemek",
  servings: 2,
  is_completed: false,
  estimated_cost: 30,
  meal: brief("m-pilav", "Pirinç Pilavı"),
};

const alternatives: Alternative[] = [
  { ...brief("m-bulgur", "Bulgur Pilavı"), estimated_cost: 25 },
  { ...brief("m-misir", "Mısır Ekmeği"), estimated_cost: 20 },
];

describe("AlternativesSheet", () => {
  const routes = () => ({
    "GET /plans/p1/meals/pm-1/alternatives": alternatives,
    "POST /plans/p1/meals/pm-1/replace": { ...pilav, meal: brief("m-bulgur", "Bulgur Pilavı") },
    "DELETE /plans/p1/meals/pm-1": () => ({ status: 204 }),
    "GET /meals": { items: [{ meal_id: "m-makarna", name: "Sebzeli Makarna", categories: [{ name: "Pilav ve Makarna", slug: "pilav-makarna", category_id: "c" }], total_time_minutes: 25 }], total: 1, limit: 24, offset: 0 },
  });

  it("mevcut yemeği ve önerileri listeler", async () => {
    mockFetch(routes());
    renderWithProviders(<AlternativesSheet planId="p1" dish={pilav} onClose={() => {}} />);
    expect(screen.getByRole("dialog", { name: "Yan yemek değiştir" })).toBeInTheDocument();
    expect(screen.getByText("Pirinç Pilavı")).toBeInTheDocument();
    expect(await screen.findByText("Bulgur Pilavı")).toBeInTheDocument();
    expect(screen.getByText("Mısır Ekmeği")).toBeInTheDocument();
  });

  it("öneriyi seçince o yemekle değiştirir ve kapanır", async () => {
    const calls = mockFetch(routes());
    const onClose = vi.fn();
    renderWithProviders(<AlternativesSheet planId="p1" dish={pilav} onClose={onClose} />);
    await screen.findByText("Bulgur Pilavı");
    await userEvent.click(screen.getAllByRole("button", { name: "Seç" })[0]);
    await waitFor(() => expect(onClose).toHaveBeenCalled());
    const replace = calls.find((c) => c.method === "POST");
    expect(replace?.path).toBe("/plans/p1/meals/pm-1/replace");
    expect(replace?.body).toEqual({ meal_id: "m-bulgur" });
  });

  it("'Başka öner' yemek belirtmeden otomatik değiştirir", async () => {
    const calls = mockFetch(routes());
    const onClose = vi.fn();
    renderWithProviders(<AlternativesSheet planId="p1" dish={pilav} onClose={onClose} />);
    await userEvent.click(screen.getByRole("button", { name: /Başka öner/ }));
    await waitFor(() => expect(onClose).toHaveBeenCalled());
    expect(calls.find((c) => c.method === "POST")?.body).toEqual({});
  });

  it("yemeği kaldırabilir", async () => {
    const calls = mockFetch(routes());
    const onClose = vi.fn();
    renderWithProviders(<AlternativesSheet planId="p1" dish={pilav} onClose={onClose} />);
    await userEvent.click(screen.getByRole("button", { name: "Bu yemeği kaldır" }));
    await waitFor(() => expect(onClose).toHaveBeenCalled());
    expect(calls.some((c) => c.method === "DELETE" && c.path === "/plans/p1/meals/pm-1")).toBe(true);
  });

  it("tüm yemeklerde arayıp seçebilir (pilav yerine makarna)", async () => {
    const calls = mockFetch(routes());
    const onClose = vi.fn();
    renderWithProviders(<AlternativesSheet planId="p1" dish={pilav} onClose={onClose} />);
    await userEvent.click(screen.getByRole("tab", { name: "Tüm yemeklerde ara" }));
    await userEvent.type(screen.getByLabelText("Yemek ara"), "makarna");
    await waitFor(() => expect(calls.some((c) => c.path === "/meals" && c.search.includes("q=makarna"))).toBe(true));
    expect(await screen.findByText("Sebzeli Makarna")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Seç" }));
    await waitFor(() => expect(onClose).toHaveBeenCalled());
    expect(calls.find((c) => c.method === "POST")?.body).toEqual({ meal_id: "m-makarna" });
  });

  it("hata olursa mesajı gösterir ve açık kalır", async () => {
    mockFetch({
      ...routes(),
      "POST /plans/p1/meals/pm-1/replace": () => ({ status: 409, body: { detail: "Uygun bir alternatif bulunamadı" } }),
    });
    const onClose = vi.fn();
    renderWithProviders(<AlternativesSheet planId="p1" dish={pilav} onClose={onClose} />);
    await userEvent.click(screen.getByRole("button", { name: /Başka öner/ }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Uygun bir alternatif bulunamadı");
    expect(onClose).not.toHaveBeenCalled();
  });

  it("Esc ile kapanır", async () => {
    mockFetch(routes());
    const onClose = vi.fn();
    renderWithProviders(<AlternativesSheet planId="p1" dish={pilav} onClose={onClose} />);
    await userEvent.keyboard("{Escape}");
    expect(onClose).toHaveBeenCalled();
  });
});

describe("DishDetail", () => {
  const meal: MealDetail = {
    meal_id: "m1",
    name: "Kuru Fasulye",
    description: "Salçalı, tereyağlı klasik kuru fasulye.",
    image_url: null,
    preparation_time_minutes: 15,
    cooking_time_minutes: 70,
    servings: 4,
    estimated_cost: 150,
    currency: "TRY",
    region: "turkiye",
    region_name: "Türkiye Geneli",
    has_recipe: true,
    categories: [{ category_id: "c", name: "Baklagil", slug: "baklagil" }],
    nutrition: { calories: 320, protein_grams: 18, carbohydrate_grams: 48, fat_grams: 6, fiber_grams: 14 },
    total_time_minutes: 85,
    instructions: "1. Fasulyeyi ıslatın.\n2. Haşlayın.\n3. Servis edin.",
    source_type: "seed",
    source_url: null,
    ingredients: [
      { name: "Kuru fasulye", quantity: 300, unit: "g", is_optional: false },
      { name: "Tereyağı", quantity: 1, unit: "yk", is_optional: false },
    ],
    average_rating: null,
    rating_count: 0,
  };

  it("tarifi varsayılan olarak gizler, istenince gösterir", async () => {
    mockFetch({ "GET /meals/m1": meal });
    renderWithProviders(<DishDetail mealId="m1" onClose={() => {}} />);
    expect(await screen.findByRole("heading", { name: "Kuru Fasulye" })).toBeInTheDocument();
    expect(screen.queryByText("Fasulyeyi ıslatın.")).not.toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Tarifi göster" }));
    expect(screen.getByText("Fasulyeyi ıslatın.")).toBeInTheDocument();
    expect(screen.getAllByRole("listitem").length).toBeGreaterThanOrEqual(3);

    await userEvent.click(screen.getByRole("button", { name: "Tarifi gizle" }));
    expect(screen.queryByText("Fasulyeyi ıslatın.")).not.toBeInTheDocument();
  });

  it("malzemeleri plandaki porsiyona göre ölçekler", async () => {
    mockFetch({ "GET /meals/m1": meal });
    renderWithProviders(<DishDetail mealId="m1" servings={2} onClose={() => {}} />);
    expect(await screen.findByText("150 g")).toBeInTheDocument();
    expect(screen.getByText("½ yemek kaşığı")).toBeInTheDocument();
    expect(screen.getByText(/\(2 kişilik\)/)).toBeInTheDocument();
  });

  it("bölge, süre ve besin değerlerini gösterir", async () => {
    mockFetch({ "GET /meals/m1": meal });
    renderWithProviders(<DishDetail mealId="m1" onClose={() => {}} />);
    expect(await screen.findByText("Türkiye Geneli")).toBeInTheDocument();
    expect(screen.getByText("1 sa 25 dk")).toBeInTheDocument();
    expect(screen.getByText("320 kcal")).toBeInTheDocument();
  });

  it("yükleme hatasında mesaj gösterir", async () => {
    mockFetch({ "GET /meals/m1": () => ({ status: 404, body: { detail: "Yemek bulunamadı" } }) });
    renderWithProviders(<DishDetail mealId="m1" onClose={() => {}} />);
    expect(await screen.findByRole("alert")).toHaveTextContent("Yemek bulunamadı");
  });

  it("tarif adımlarındaki numaraları temizler", () => {
    expect(recipeSteps("1. Ilk\n2) İkinci\n\n 3. Üçüncü ")).toEqual(["Ilk", "İkinci", "Üçüncü"]);
  });

  it("ortalama puanı ve puanlama sayısını gösterir", async () => {
    mockFetch({ "GET /meals/m1": { ...meal, average_rating: 4.5, rating_count: 12 } });
    renderWithProviders(<DishDetail mealId="m1" onClose={() => {}} />);
    expect(await screen.findByLabelText("4.5 / 5 yıldız, 12 puanlama")).toBeInTheDocument();
    expect(screen.getByText("4.5 (12)")).toBeInTheDocument();
  });

  it("henüz puanlanmamış yemekte uyarı gösterir", async () => {
    mockFetch({ "GET /meals/m1": meal });
    renderWithProviders(<DishDetail mealId="m1" onClose={() => {}} />);
    expect(await screen.findByText("Henüz puanlanmamış")).toBeInTheDocument();
  });

  describe("puanlama", () => {
    it("kendi puanınız yoksa yıldızlar boş başlar, tıklayınca kaydedilir", async () => {
      const calls = mockFetch({
        "GET /meals/m1": meal,
        "GET /meals/m1/rating": () => ({ status: 404, body: { detail: "Bu yemeği henüz puanlamadınız" } }),
        "PUT /meals/m1/rating": { rating_id: "r1", meal_id: "m1", rating: 4, comment: null, created_at: null, updated_at: null },
      });
      renderWithProviders(<DishDetail mealId="m1" onClose={() => {}} />);
      const stars = await screen.findAllByRole("radio", { name: /yıldız/ });
      expect(screen.getByRole("radio", { name: "1 yıldız" })).toHaveAttribute("aria-checked", "false");
      await userEvent.click(stars[3]);
      await waitFor(() => expect(calls.find((c) => c.method === "PUT")?.body).toEqual({ rating: 4, comment: undefined }));
      expect(await screen.findByRole("button", { name: "Yorum ekle" })).toBeInTheDocument();
    });

    it("mevcut puanı ve yorumu gösterir; kaldır düğmesiyle siler", async () => {
      const calls = mockFetch({
        "GET /meals/m1": meal,
        "GET /meals/m1/rating": { rating_id: "r1", meal_id: "m1", rating: 5, comment: "Harika oldu", created_at: null, updated_at: null },
        "DELETE /meals/m1/rating": () => ({ status: 204 }),
      });
      renderWithProviders(<DishDetail mealId="m1" onClose={() => {}} />);
      expect(await screen.findByRole("radio", { name: "5 yıldız" })).toHaveAttribute("aria-checked", "true");
      expect(screen.getByRole("button", { name: "“Harika oldu”" })).toBeInTheDocument();
      await userEvent.click(screen.getByRole("button", { name: "Puanı kaldır" }));
      await waitFor(() => expect(calls.some((c) => c.method === "DELETE" && c.path === "/meals/m1/rating")).toBe(true));
      expect(screen.queryByRole("button", { name: "Puanı kaldır" })).not.toBeInTheDocument();
    });

    it("yorum ekleyip kaydedebilir", async () => {
      const calls = mockFetch({
        "GET /meals/m1": meal,
        "GET /meals/m1/rating": { rating_id: "r1", meal_id: "m1", rating: 3, comment: null, created_at: null, updated_at: null },
        "PUT /meals/m1/rating": { rating_id: "r1", meal_id: "m1", rating: 3, comment: "Biraz tuzsuz oldu", created_at: null, updated_at: null },
      });
      renderWithProviders(<DishDetail mealId="m1" onClose={() => {}} />);
      await userEvent.click(await screen.findByRole("button", { name: "Yorum ekle" }));
      await userEvent.type(screen.getByLabelText("Yorumunuz"), "Biraz tuzsuz oldu");
      await userEvent.click(screen.getByRole("button", { name: "Kaydet" }));
      await waitFor(() => expect(calls.find((c) => c.method === "PUT")?.body).toEqual({ rating: 3, comment: "Biraz tuzsuz oldu" }));
      expect(await screen.findByRole("button", { name: "“Biraz tuzsuz oldu”" })).toBeInTheDocument();
    });

    it("puanlama hatasını gösterir", async () => {
      mockFetch({
        "GET /meals/m1": meal,
        "GET /meals/m1/rating": () => ({ status: 404, body: { detail: "yok" } }),
        "PUT /meals/m1/rating": () => ({ status: 500, body: { detail: "Sunucu hatası" } }),
      });
      renderWithProviders(<DishDetail mealId="m1" onClose={() => {}} />);
      const stars = await screen.findAllByRole("radio", { name: /yıldız/ });
      await userEvent.click(stars[0]);
      expect(await screen.findByRole("alert")).toHaveTextContent("Sunucu hatası");
    });

    it("ok tuşlarıyla puan değiştirilebilir", async () => {
      const calls = mockFetch({
        "GET /meals/m1": meal,
        "GET /meals/m1/rating": { rating_id: "r1", meal_id: "m1", rating: 2, comment: null, created_at: null, updated_at: null },
        "PUT /meals/m1/rating": { rating_id: "r1", meal_id: "m1", rating: 3, comment: null, created_at: null, updated_at: null },
      });
      renderWithProviders(<DishDetail mealId="m1" onClose={() => {}} />);
      await screen.findByRole("radiogroup", { name: "Puanınız" });
      screen.getByRole("radio", { name: "2 yıldız" }).focus();
      await userEvent.keyboard("{ArrowRight}");
      await waitFor(() => expect(calls.filter((c) => c.method === "PUT").at(-1)?.body).toEqual({ rating: 3, comment: undefined }));
    });
  });
});
