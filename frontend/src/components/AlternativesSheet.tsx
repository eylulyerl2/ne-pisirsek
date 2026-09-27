import { useEffect, useState } from "react";
import { useAlternatives, useMeals, useRemoveMeal, useReplaceMeal } from "../hooks/queries";
import type { PlannedMeal } from "../services/types";
import { formatDuration, formatMoney } from "../utils/format";
import { ErrorNote, Spinner } from "./Feedback";
import { Icon } from "./Icon";
import { Sheet } from "./Sheet";

interface AlternativesSheetProps {
  planId: string;
  dish: PlannedMeal;
  onClose: () => void;
}

type Tab = "suggested" | "search";

function useDebounced<T>(value: T, delay = 300): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(timer);
  }, [value, delay]);
  return debounced;
}

export function AlternativesSheet({ planId, dish, onClose }: AlternativesSheetProps) {
  const [tab, setTab] = useState<Tab>("suggested");
  const [query, setQuery] = useState("");
  const debouncedQuery = useDebounced(query.trim());

  const alternatives = useAlternatives(planId, dish.planned_meal_id);
  const search = useMeals({ q: debouncedQuery || undefined });
  const replace = useReplaceMeal(planId);
  const remove = useRemoveMeal(planId);
  const busy = replace.isPending || remove.isPending;
  const failure = replace.error ?? remove.error;

  function choose(mealId?: string) {
    replace.mutate({ plannedMealId: dish.planned_meal_id, mealId }, { onSuccess: onClose });
  }

  const searchResults = search.data?.pages.flatMap((page) => page.items) ?? [];

  return (
    <Sheet
      title={`${dish.course_name} değiştir`}
      onClose={onClose}
      footer={
        <>
          <button type="button" className="btn btn-danger" disabled={busy} onClick={() => remove.mutate(dish.planned_meal_id, { onSuccess: onClose })}>
            Bu yemeği kaldır
          </button>
          <button type="button" className="btn btn-primary" disabled={busy} onClick={() => choose()}>
            <Icon name="refresh" size={18} />
            Başka öner
          </button>
        </>
      }
    >
      <p className="muted">
        Şu an: <strong style={{ color: "var(--text)" }}>{dish.meal.name}</strong>
      </p>

      <div className="tabs" role="tablist" aria-label="Alternatif kaynağı">
        <button type="button" role="tab" aria-selected={tab === "suggested"} onClick={() => setTab("suggested")}>
          Önerilenler
        </button>
        <button type="button" role="tab" aria-selected={tab === "search"} onClick={() => setTab("search")}>
          Tüm yemeklerde ara
        </button>
      </div>

      {failure && <ErrorNote error={failure} />}

      {tab === "suggested" && (
        <>
          {alternatives.isPending && <Spinner />}
          {alternatives.error && <ErrorNote error={alternatives.error} onRetry={() => alternatives.refetch()} />}
          {alternatives.data?.length === 0 && <p className="muted">Bu öğün için başka uygun öneri bulunamadı. Arama sekmesini deneyin.</p>}
          <ul className="alt-list">
            {alternatives.data?.map((alternative) => (
              <li key={alternative.meal_id} className="alt">
                <div className="info">
                  <strong>{alternative.name}</strong>
                  <span className="muted small">
                    {formatDuration(alternative.total_time_minutes)} · {formatMoney(alternative.estimated_cost)}
                    {alternative.calories_per_serving ? ` · ${Math.round(alternative.calories_per_serving)} kcal` : ""}
                  </span>
                </div>
                <button type="button" className="btn btn-sm" disabled={busy} onClick={() => choose(alternative.meal_id)}>
                  Seç
                </button>
              </li>
            ))}
          </ul>
        </>
      )}

      {tab === "search" && (
        <>
          <div className="field">
            <label htmlFor="alt-search" className="visually-hidden">
              Yemek ara
            </label>
            <input
              id="alt-search"
              className="input"
              type="search"
              placeholder="Örn. makarna, bulgur, cacık…"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              autoFocus
            />
          </div>
          {search.isPending && <Spinner />}
          {search.error && <ErrorNote error={search.error} />}
          {search.data && searchResults.length === 0 && <p className="muted">Sonuç bulunamadı.</p>}
          <ul className="alt-list">
            {searchResults.map((meal) => (
              <li key={meal.meal_id} className="alt">
                <div className="info">
                  <strong>{meal.name}</strong>
                  <span className="muted small">
                    {meal.categories.map((c) => c.name).join(", ")} · {formatDuration(meal.total_time_minutes)}
                  </span>
                </div>
                <button type="button" className="btn btn-sm" disabled={busy} onClick={() => choose(meal.meal_id)}>
                  Seç
                </button>
              </li>
            ))}
          </ul>
        </>
      )}
    </Sheet>
  );
}
