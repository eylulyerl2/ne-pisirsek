import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { AlternativesSheet } from "../components/AlternativesSheet";
import { DishDetail } from "../components/DishDetail";
import { DishRow } from "../components/DishRow";
import { EmptyState, ErrorNote, Spinner } from "../components/Feedback";
import { GenerateOptionsForm } from "../components/GenerateOptionsForm";
import { Icon } from "../components/Icon";
import { WeekNavigator } from "../components/WeekNavigator";
import { ScopeSelect } from "../components/ScopeSelect";
import { useFamilies, useGeneratePlan, usePlan, usePlans, useSetCompleted } from "../hooks/queries";
import { useScope } from "../hooks/useScope";
import { useWeek } from "../hooks/useWeek";
import type { DayPlan, GenerateOptions, PlanDetail, PlannedMeal } from "../services/types";
import { dayDate, dayName, formatDayMonth, isSameDay } from "../utils/dates";
import { formatMoney } from "../utils/format";
import { keepParams } from "../utils/nav";

const DEFAULT_OPTIONS: GenerateOptions = { meal_types: ["dinner"], compose: true };

export function PlanPage() {
  const week = useWeek();
  const scope = useScope();
  const families = useFamilies();
  const family = families.data?.find((f) => f.family_id === scope.familyId);
  const plans = usePlans(scope.familyId);
  const summary = plans.data?.find((p) => p.week_start_date === week.weekStart);
  const plan = usePlan(summary?.plan_id);
  const generate = useGeneratePlan();
  const setDone = useSetCompleted(summary?.plan_id ?? "");

  const [options, setOptions] = useState<GenerateOptions>(DEFAULT_OPTIONS);
  const [warnings, setWarnings] = useState<string[]>([]);
  const [detail, setDetail] = useState<PlannedMeal | null>(null);
  const [swap, setSwap] = useState<PlannedMeal | null>(null);
  const [regenerating, setRegenerating] = useState(false);

  useEffect(() => {
    setWarnings([]);
    setRegenerating(false);
  }, [week.weekStart]);

  function createMenu() {
    generate.mutate(
      { weekStart: week.weekStart, planId: summary?.plan_id, familyId: scope.familyId, options },
      {
        onSuccess: (data) => {
          setWarnings(data.warnings);
          setRegenerating(false);
        },
      },
    );
  }

  const loading = plans.isPending || (!!summary && plan.isPending);
  const error = plans.error ?? plan.error;
  const hasMeals = (plan.data?.planned_meals.length ?? 0) > 0;

  return (
    <div className="stack">
      <div className="page-head">
        <div>
          <h1>{family ? `${family.name} · Haftalık plan` : "Haftalık plan"}</h1>
          <p>
            {family
              ? `${family.member_count} kişilik aile planı; üyelerin tercihlerinin ortalamasına göre hazırlanır.`
              : "Ne pişireceğinize karar vermek artık kolay."}
          </p>
        </div>
        <WeekNavigator
          monday={week.monday}
          isCurrentWeek={week.isCurrentWeek}
          onPrevious={week.previous}
          onNext={week.next}
          onToday={week.today}
        />
      </div>

      <ScopeSelect familyId={scope.familyId} onChange={scope.setFamilyId} />

      {error && <ErrorNote error={error} onRetry={() => { plans.refetch(); plan.refetch(); }} />}
      {plans.error && scope.familyId && (
        <div>
          <button type="button" className="btn" onClick={() => scope.setFamilyId(null)}>
            Kişisel plana dön
          </button>
        </div>
      )}
      {generate.error && <ErrorNote error={generate.error} />}
      {loading && <Spinner label="Plan yükleniyor" />}

      {!loading && !error && !hasMeals && (
        <div className="card card-pad">
          <EmptyState title="Bu hafta için menü henüz yok">
            <p>Tercihlerinize göre çorba, ana yemek, pilav ve salatadan oluşan bir haftalık menü hazırlayalım.</p>
            <div style={{ textAlign: "left", maxWidth: 460, margin: "20px auto 0" }}>
              <GenerateOptionsForm value={options} onChange={setOptions} />
            </div>
            <button type="button" className="btn btn-primary" disabled={generate.isPending} onClick={createMenu}>
              {generate.isPending ? "Menü hazırlanıyor…" : "Menü oluştur"}
            </button>
          </EmptyState>
        </div>
      )}

      {warnings.length > 0 && (
        <div className="banner" role="status">
          <div className="grow">
            <strong>Menü hazır, ancak bir not var:</strong>
            <ul>
              {warnings.map((warning) => (
                <li key={warning}>{warning}</li>
              ))}
            </ul>
          </div>
          <button type="button" className="btn btn-sm btn-ghost" onClick={() => setWarnings([])} aria-label="Uyarıyı kapat">
            <Icon name="x" size={16} />
          </button>
        </div>
      )}

      {plan.data && hasMeals && (
        <>
          <PlanSummary plan={plan.data} weekStart={week.weekStart} familyId={scope.familyId} />
          <div className="days">
            {[1, 2, 3, 4, 5, 6, 7].map((day) => (
              <DayCard
                key={day}
                day={day}
                plan={plan.data.days.find((d) => d.day_of_week === day)}
                date={dayDate(week.monday, day)}
                onOpen={setDetail}
                onSwap={setSwap}
                onToggleDone={(dish, done) => setDone.mutate({ plannedMealId: dish.planned_meal_id, isCompleted: done })}
              />
            ))}
          </div>

          <div className="card card-pad stack" style={{ gap: 12 }}>
            {!regenerating ? (
              <div className="row" style={{ justifyContent: "space-between" }}>
                <span className="muted">Menü beğenmediniz mi? Baştan hazırlatabilirsiniz.</span>
                <button type="button" className="btn" onClick={() => setRegenerating(true)}>
                  <Icon name="refresh" size={18} />
                  Yeniden oluştur
                </button>
              </div>
            ) : (
              <>
                <div className="banner" role="alert">
                  Yeniden oluşturmak, bu haftada elle yaptığınız değişiklikleri siler.
                </div>
                <GenerateOptionsForm value={options} onChange={setOptions} />
                <div className="row">
                  <button type="button" className="btn btn-primary" disabled={generate.isPending} onClick={createMenu}>
                    {generate.isPending ? "Hazırlanıyor…" : "Evet, yeniden oluştur"}
                  </button>
                  <button type="button" className="btn" onClick={() => setRegenerating(false)}>
                    Vazgeç
                  </button>
                </div>
              </>
            )}
          </div>
        </>
      )}

      {detail && <DishDetail mealId={detail.meal.meal_id} servings={detail.servings} onClose={() => setDetail(null)} />}
      {swap && summary && <AlternativesSheet planId={summary.plan_id} dish={swap} onClose={() => setSwap(null)} />}
    </div>
  );
}

function PlanSummary({ plan, weekStart, familyId }: { plan: PlanDetail; weekStart: string; familyId: string | null }) {
  const done = plan.planned_meals.filter((d) => d.is_completed).length;
  return (
    <div className="card summary-strip">
      <div className="stat">
        <b>{formatMoney(plan.estimated_total_cost)}</b>
        <span>Tahmini haftalık maliyet</span>
      </div>
      <div className="stat">
        <b>{plan.planned_meals.length}</b>
        <span>Planlanan yemek</span>
      </div>
      {plan.planned_meals[0] && (
        <div className="stat">
          <b>{plan.planned_meals[0].servings} kişilik</b>
          <span>Porsiyon</span>
        </div>
      )}
      <div className="stat">
        <b>
          {done}/{plan.planned_meals.length}
        </b>
        <span>Pişirilen</span>
      </div>
      <div className="spacer" />
      <Link className="btn btn-primary" to={{ pathname: "/alisveris", search: keepParams(`?hafta=${weekStart}${familyId ? `&aile=${familyId}` : ""}`) }}>
        <Icon name="cart" size={18} />
        Alışveriş listesi
      </Link>
    </div>
  );
}

interface DayCardProps {
  day: number;
  plan: DayPlan | undefined;
  date: Date;
  onOpen: (dish: PlannedMeal) => void;
  onSwap: (dish: PlannedMeal) => void;
  onToggleDone: (dish: PlannedMeal, done: boolean) => void;
}

function DayCard({ day, plan, date, onOpen, onSwap, onToggleDone }: DayCardProps) {
  const today = isSameDay(date, new Date());
  return (
    <section className={`card day-card${today ? " today" : ""}`} aria-label={dayName(day)}>
      <div className="day-head">
        <h2>{dayName(day)}</h2>
        <span>{today ? `Bugün · ${formatDayMonth(date)}` : formatDayMonth(date)}</span>
      </div>
      {!plan || plan.meals.length === 0 ? (
        <p className="muted small">Bu gün için planlanmış yemek yok.</p>
      ) : (
        plan.meals.map((slot) => (
          <div key={slot.meal_type}>
            <div className="slot-title">{slot.meal_type_name}</div>
            <div className="dishes">
              {slot.dishes.map((dish) => (
                <DishRow key={dish.planned_meal_id} dish={dish} onOpen={onOpen} onSwap={onSwap} onToggleDone={onToggleDone} />
              ))}
            </div>
          </div>
        ))
      )}
    </section>
  );
}
