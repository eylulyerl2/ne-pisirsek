import { Link } from "react-router-dom";
import { EmptyState, ErrorNote, Spinner } from "../components/Feedback";
import { Icon } from "../components/Icon";
import { ScopeSelect } from "../components/ScopeSelect";
import { WeekNavigator } from "../components/WeekNavigator";
import { useBuildShoppingList, useCheckItem, usePlan, usePlans, useShoppingList } from "../hooks/queries";
import { useScope } from "../hooks/useScope";
import { useWeek } from "../hooks/useWeek";
import { formatShoppingAmount } from "../utils/format";
import { keepParams } from "../utils/nav";

export function ShoppingPage() {
  const week = useWeek();
  const scope = useScope();
  const plans = usePlans(scope.familyId);
  const summary = plans.data?.find((p) => p.week_start_date === week.weekStart);
  const plan = usePlan(summary?.plan_id);
  const list = useShoppingList(summary?.plan_id);
  const build = useBuildShoppingList(summary?.plan_id ?? "");
  const check = useCheckItem(summary?.plan_id ?? "");

  const hasMeals = (plan.data?.planned_meals.length ?? 0) > 0;
  const items = list.data?.items ?? [];
  const checked = items.filter((i) => i.is_checked).length;
  const loading = plans.isPending || (!!summary && (plan.isPending || list.isPending));
  const error = plans.error ?? plan.error ?? list.error;

  return (
    <div className="stack">
      <div className="page-head">
        <div>
          <h1>Alışveriş listesi</h1>
          <p>Haftalık menünüzün malzemeleri, porsiyona göre toplanmış halde.</p>
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

      {error && <ErrorNote error={error} />}
      {plans.error && scope.familyId && (
        <div>
          <button type="button" className="btn" onClick={() => scope.setFamilyId(null)}>
            Kişisel plana dön
          </button>
        </div>
      )}
      {build.error && <ErrorNote error={build.error} />}
      {loading && <Spinner label="Liste yükleniyor" />}

      {!loading && !error && !hasMeals && (
        <div className="card card-pad">
          <EmptyState title="Bu hafta için menü yok">
            <p>Alışveriş listesi menünüzden hazırlanır. Önce haftalık menüyü oluşturun.</p>
            <Link className="btn btn-primary" to={{ pathname: "/plan", search: keepParams(`?hafta=${week.weekStart}${scope.familyId ? `&aile=${scope.familyId}` : ""}`) }}>
              Menü oluştur
            </Link>
          </EmptyState>
        </div>
      )}

      {!loading && !error && hasMeals && !list.data && (
        <div className="card card-pad">
          <EmptyState title="Liste henüz hazırlanmadı">
            <p>Menüdeki tüm yemeklerin malzemelerini tek listede toplayalım.</p>
            <button type="button" className="btn btn-primary" disabled={build.isPending} onClick={() => build.mutate()}>
              {build.isPending ? "Hazırlanıyor…" : "Alışveriş listesini oluştur"}
            </button>
          </EmptyState>
        </div>
      )}

      {list.data && (
        <>
          <div className="card card-pad stack" style={{ gap: 10 }}>
            <div className="row" style={{ justifyContent: "space-between" }}>
              <strong>
                {checked} / {items.length} ürün alındı
              </strong>
              <button type="button" className="btn btn-sm" disabled={build.isPending} onClick={() => build.mutate()}>
                <Icon name="refresh" size={16} />
                Listeyi yenile
              </button>
            </div>
            <div
              className="progress"
              role="progressbar"
              aria-valuemin={0}
              aria-valuemax={items.length}
              aria-valuenow={checked}
              aria-label="Alışveriş ilerlemesi"
            >
              <div style={{ width: `${items.length ? (checked / items.length) * 100 : 0}%` }} />
            </div>
            <p className="muted small">Menüde değişiklik yaptıysanız "Listeyi yenile" ile güncelleyin; işaretlediğiniz ürünler korunur.</p>
          </div>

          <ul className="card shopping-list" aria-label="Alışveriş ürünleri">
            {items.map((item) => (
              <li key={item.item_id}>
                <label className={`shopping-item${item.is_checked ? " checked" : ""}`}>
                  <input
                    type="checkbox"
                    className="check"
                    checked={item.is_checked}
                    onChange={(event) => check.mutate({ itemId: item.item_id, isChecked: event.target.checked })}
                  />
                  <span className="name">{item.name}</span>
                  <span className="amount">{formatShoppingAmount(item.quantity, item.unit)}</span>
                </label>
              </li>
            ))}
          </ul>
        </>
      )}
    </div>
  );
}
