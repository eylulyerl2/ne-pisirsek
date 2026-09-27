import { useEffect, useRef, useState } from "react";
import { useDeleteRating, useMeal, useMyRating, useRateMeal } from "../hooks/queries";
import { formatAmount, formatDuration, formatMoney, scaleQuantity } from "../utils/format";
import { ErrorNote, Spinner } from "./Feedback";
import { Sheet } from "./Sheet";
import { StarDisplay, StarInput } from "./StarRating";

interface DishDetailProps {
  mealId: string;
  /** Plandaki porsiyon sayısı; verilirse malzeme miktarları buna göre ölçeklenir. */
  servings?: number;
  onClose: () => void;
}

export function recipeSteps(instructions: string): string[] {
  return instructions
    .split("\n")
    .map((line) => line.replace(/^\s*\d+[.)]\s*/, "").trim())
    .filter(Boolean);
}

function MyRatingSection({ mealId }: { mealId: string }) {
  const { data: myRating, isPending } = useMyRating(mealId);
  const rate = useRateMeal(mealId);
  const remove = useDeleteRating(mealId);
  const [stars, setStars] = useState(0);
  const [comment, setComment] = useState("");
  const [editingComment, setEditingComment] = useState(false);
  // Sunucudan gelen puan yalnızca ilk yüklemede local state'e aktarılır: sonrasında local state
  // tek kaynaktır, aksi halde kendi isteğimizin dönüşü (örn. yıldıza basıp hemen yorum yazarken)
  // henüz yazılmakta olan yorumu kapatıp sıfırlayabilir.
  const hydrated = useRef(false);

  useEffect(() => {
    if (hydrated.current || isPending) return;
    hydrated.current = true;
    setStars(myRating?.rating ?? 0);
    setComment(myRating?.comment ?? "");
  }, [isPending, myRating]);

  function choose(value: number) {
    setStars(value);
    rate.mutate({ rating: value, comment: comment.trim() || undefined });
  }

  function saveComment() {
    rate.mutate({ rating: stars, comment: comment.trim() || undefined }, { onSuccess: () => setEditingComment(false) });
  }

  const busy = rate.isPending || remove.isPending;

  return (
    <section aria-labelledby="rating-title" className="stack" style={{ gap: 8 }}>
      <h3 id="rating-title">Puanınız</h3>
      {isPending ? (
        <Spinner label="Puanınız yükleniyor" />
      ) : (
        <>
          <div className="row" style={{ gap: 12 }}>
            <StarInput value={stars} onChange={choose} disabled={busy} />
            {myRating && (
              <button
                type="button"
                className="btn btn-sm btn-ghost"
                disabled={busy}
                onClick={() => {
                  remove.mutate();
                  setStars(0);
                  setComment("");
                }}
              >
                Puanı kaldır
              </button>
            )}
          </div>
          {stars > 0 &&
            (editingComment ? (
              <div className="stack" style={{ gap: 8 }}>
                <label htmlFor="rating-comment" className="visually-hidden">
                  Yorumunuz
                </label>
                <textarea
                  id="rating-comment"
                  className="input"
                  rows={2}
                  maxLength={1000}
                  placeholder="Bu yemek hakkında bir notunuz var mı? (isteğe bağlı)"
                  value={comment}
                  onChange={(event) => setComment(event.target.value)}
                />
                <div className="row">
                  <button type="button" className="btn btn-sm btn-primary" disabled={busy} onClick={saveComment}>
                    Kaydet
                  </button>
                  <button type="button" className="btn btn-sm" onClick={() => setEditingComment(false)}>
                    Vazgeç
                  </button>
                </div>
              </div>
            ) : (
              <button type="button" className="btn btn-sm btn-ghost" style={{ alignSelf: "flex-start" }} onClick={() => setEditingComment(true)}>
                {comment ? `“${comment}”` : "Yorum ekle"}
              </button>
            ))}
          {rate.error !== null && <ErrorNote error={rate.error} />}
          {remove.error !== null && <ErrorNote error={remove.error} />}
        </>
      )}
    </section>
  );
}

export function DishDetail({ mealId, servings, onClose }: DishDetailProps) {
  const { data: meal, isPending, error, refetch } = useMeal(mealId);
  const [showRecipe, setShowRecipe] = useState(false);

  const portions = servings ?? meal?.servings ?? 1;

  return (
    <Sheet title={meal?.name ?? "Yemek"} onClose={onClose}>
      {isPending && <Spinner />}
      {error && <ErrorNote error={error} onRetry={() => refetch()} />}
      {meal && (
        <>
          <div className="row">
            {meal.region_name && <span className="badge badge-region">{meal.region_name}</span>}
            {meal.categories.map((c) => (
              <span key={c.slug} className="badge">
                {c.name}
              </span>
            ))}
          </div>
          <StarDisplay value={meal.average_rating} count={meal.rating_count} />
          {meal.description && <p className="muted">{meal.description}</p>}

          <div className="facts">
            <div className="fact">
              <b>{formatDuration(meal.total_time_minutes)}</b>
              <span>Toplam süre</span>
            </div>
            <div className="fact">
              <b>{formatMoney(meal.estimated_cost, meal.currency)}</b>
              <span>{meal.servings} kişilik tahmini maliyet</span>
            </div>
            {meal.nutrition?.calories != null && (
              <div className="fact">
                <b>{Math.round(meal.nutrition.calories)} kcal</b>
                <span>Porsiyon başına</span>
              </div>
            )}
            {meal.nutrition?.protein_grams != null && (
              <div className="fact">
                <b>
                  {Math.round(meal.nutrition.protein_grams)} / {Math.round(meal.nutrition.carbohydrate_grams ?? 0)} /{" "}
                  {Math.round(meal.nutrition.fat_grams ?? 0)} g
                </b>
                <span>Protein / karb. / yağ</span>
              </div>
            )}
          </div>

          <MyRatingSection key={meal.meal_id} mealId={meal.meal_id} />

          <section aria-labelledby="ingredients-title">
            <h3 id="ingredients-title" style={{ marginBottom: 8 }}>
              Malzemeler <span className="muted small">({portions} kişilik)</span>
            </h3>
            <ul className="ingredients">
              {meal.ingredients.map((ingredient) => (
                <li key={ingredient.name}>
                  <span>{ingredient.name}</span>
                  <span className="amount">
                    {formatAmount(scaleQuantity(ingredient.quantity, meal.servings, portions), ingredient.unit)}
                  </span>
                </li>
              ))}
            </ul>
          </section>

          {meal.instructions && (
            <section aria-labelledby="recipe-title">
              <div className="row" style={{ justifyContent: "space-between" }}>
                <h3 id="recipe-title">Yapılışı</h3>
                <button
                  type="button"
                  className="btn btn-sm"
                  aria-expanded={showRecipe}
                  onClick={() => setShowRecipe((value) => !value)}
                >
                  {showRecipe ? "Tarifi gizle" : "Tarifi göster"}
                </button>
              </div>
              {showRecipe && (
                <ol className="recipe" style={{ marginTop: 12 }}>
                  {recipeSteps(meal.instructions).map((step, index) => (
                    <li key={index}>{step}</li>
                  ))}
                </ol>
              )}
            </section>
          )}

          {meal.source_type !== "seed" && meal.source_url && (
            <p className="muted small">
              Kaynak:{" "}
              <a href={meal.source_url} target="_blank" rel="noreferrer">
                {meal.source_url}
              </a>
            </p>
          )}
        </>
      )}
    </Sheet>
  );
}
