import type { GenerateOptions, MealType } from "../services/types";
import { MEAL_TYPE_LABELS } from "../utils/labels";

const ORDER: MealType[] = ["breakfast", "lunch", "dinner", "snack"];

interface Props {
  value: GenerateOptions;
  onChange: (value: GenerateOptions) => void;
}

export function GenerateOptionsForm({ value, onChange }: Props) {
  function toggleType(type: MealType) {
    const has = value.meal_types.includes(type);
    if (has && value.meal_types.length === 1) return;
    const next = has ? value.meal_types.filter((t) => t !== type) : [...value.meal_types, type];
    onChange({ ...value, meal_types: ORDER.filter((t) => next.includes(t)) });
  }

  return (
    <div className="stack" style={{ gap: 12 }}>
      <div className="field">
        <span className="label" id="meal-types-label">
          Hangi öğünler planlansın?
        </span>
        <div className="chips" role="group" aria-labelledby="meal-types-label">
          {ORDER.map((type) => (
            <button
              key={type}
              type="button"
              className="chip"
              aria-pressed={value.meal_types.includes(type)}
              onClick={() => toggleType(type)}
            >
              {MEAL_TYPE_LABELS[type]}
            </button>
          ))}
        </div>
      </div>
      <label className="row" style={{ gap: 10, cursor: "pointer" }}>
        <input
          type="checkbox"
          className="check"
          checked={value.compose}
          onChange={(event) => onChange({ ...value, compose: event.target.checked })}
        />
        <span>
          <strong>Tam sofra kur</strong>
          <span className="muted small" style={{ display: "block" }}>
            Ana yemeğe çorba, pilav ve salata ekler. Kapalıysa her öğün tek yemek olur.
          </span>
        </span>
      </label>
    </div>
  );
}
