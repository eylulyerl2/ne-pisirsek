import { useEffect, useState } from "react";
import { DishDetail } from "../components/DishDetail";
import { EmptyState, ErrorNote, Spinner } from "../components/Feedback";
import { Icon } from "../components/Icon";
import { useCategories, useMeals, useRegions } from "../hooks/queries";
import { formatDuration, formatMoney } from "../utils/format";

export function MealsPage() {
  const [text, setText] = useState("");
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState("");
  const [region, setRegion] = useState("");
  const [selected, setSelected] = useState<string | null>(null);

  useEffect(() => {
    const timer = setTimeout(() => setQuery(text.trim()), 300);
    return () => clearTimeout(timer);
  }, [text]);

  const categories = useCategories();
  const regions = useRegions();
  const meals = useMeals({
    q: query || undefined,
    category: category ? [category] : undefined,
    region: region ? [region] : undefined,
  });

  const items = meals.data?.pages.flatMap((page) => page.items) ?? [];
  const total = meals.data?.pages[0]?.total ?? 0;

  return (
    <div className="stack">
      <div className="page-head">
        <div>
          <h1>Yemekler</h1>
          <p>Bölgelere göre gezin; yemeğe dokunarak malzemelerini ve isterseniz tarifini görün.</p>
        </div>
      </div>

      <div className="toolbar">
        <div className="field">
          <label htmlFor="meal-search" className="visually-hidden">
            Yemek ara
          </label>
          <div style={{ position: "relative" }}>
            <input
              id="meal-search"
              className="input"
              type="search"
              placeholder="Yemek ara… (örn. kuru fasulye)"
              value={text}
              onChange={(event) => setText(event.target.value)}
              style={{ paddingLeft: 42 }}
            />
            <span style={{ position: "absolute", left: 13, top: 11, color: "var(--muted)" }}>
              <Icon name="search" />
            </span>
          </div>
        </div>
        <div className="field">
          <label htmlFor="region-filter" className="visually-hidden">
            Bölge
          </label>
          <select id="region-filter" className="select" value={region} onChange={(event) => setRegion(event.target.value)}>
            <option value="">Tüm bölgeler</option>
            {regions.data?.map((r) => (
              <option key={r.slug} value={r.slug}>
                {r.name}
              </option>
            ))}
          </select>
        </div>
        <div className="chips" role="group" aria-label="Kategori">
          <button type="button" className="chip" aria-pressed={category === ""} onClick={() => setCategory("")}>
            Tümü
          </button>
          {categories.data?.map((c) => (
            <button
              key={c.slug}
              type="button"
              className="chip"
              aria-pressed={category === c.slug}
              onClick={() => setCategory(category === c.slug ? "" : c.slug)}
            >
              {c.name}
            </button>
          ))}
        </div>
      </div>

      {meals.error && <ErrorNote error={meals.error} onRetry={() => meals.refetch()} />}
      {meals.isPending && <Spinner label="Yemekler yükleniyor" />}
      {meals.data && items.length === 0 && (
        <EmptyState title="Yemek bulunamadı">
          <p>Arama veya filtreleri değiştirmeyi deneyin.</p>
        </EmptyState>
      )}

      {items.length > 0 && (
        <>
          <p className="muted small" aria-live="polite">
            {total} yemek
          </p>
          <div className="meal-grid">
            {items.map((meal) => (
              <button key={meal.meal_id} type="button" className="card meal-card" onClick={() => setSelected(meal.meal_id)}>
                <h3>{meal.name}</h3>
                {meal.description && <p>{meal.description}</p>}
                <div className="meta">
                  {meal.region_name && <span className="badge badge-region">{meal.region_name}</span>}
                  <span className="badge">
                    <Icon name="clock" size={13} />
                    {formatDuration(meal.total_time_minutes)}
                  </span>
                  <span className="badge">{formatMoney(meal.estimated_cost, meal.currency)}</span>
                </div>
              </button>
            ))}
          </div>
          {meals.hasNextPage && (
            <div style={{ textAlign: "center" }}>
              <button type="button" className="btn" disabled={meals.isFetchingNextPage} onClick={() => meals.fetchNextPage()}>
                {meals.isFetchingNextPage ? "Yükleniyor…" : "Daha fazla göster"}
              </button>
            </div>
          )}
        </>
      )}

      {selected && <DishDetail mealId={selected} onClose={() => setSelected(null)} />}
    </div>
  );
}
