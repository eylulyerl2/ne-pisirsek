import type { PlannedMeal } from "../services/types";
import { formatDuration, formatMoney } from "../utils/format";
import { Icon } from "./Icon";

interface DishRowProps {
  dish: PlannedMeal;
  onOpen: (dish: PlannedMeal) => void;
  onSwap: (dish: PlannedMeal) => void;
  onToggleDone: (dish: PlannedMeal, done: boolean) => void;
}

export function DishRow({ dish, onOpen, onSwap, onToggleDone }: DishRowProps) {
  const { meal } = dish;
  return (
    <div className={`dish${dish.is_completed ? " done" : ""}`} data-course={dish.course}>
      <label className="check-wrap" title="Pişirildi olarak işaretle">
        <input
          type="checkbox"
          className="check"
          checked={dish.is_completed}
          onChange={(event) => onToggleDone(dish, event.target.checked)}
          aria-label={`${meal.name} pişirildi`}
        />
      </label>
      <button type="button" className="dish-main" onClick={() => onOpen(dish)} aria-label={`${meal.name} ayrıntıları`}>
        <span className="dish-name">{meal.name}</span>
        <span className="dish-meta">
          <span className="course-label">{dish.course_name}</span>
          <span>{formatDuration(meal.total_time_minutes)}</span>
          {dish.estimated_cost !== null && <span>{formatMoney(dish.estimated_cost)}</span>}
        </span>
      </button>
      <button
        type="button"
        className="btn btn-sm btn-icon"
        onClick={() => onSwap(dish)}
        aria-label={`${meal.name} yemeğini değiştir`}
        title="Değiştir"
      >
        <Icon name="swap" size={18} />
      </button>
    </div>
  );
}
