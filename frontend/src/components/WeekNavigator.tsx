import { formatWeekRange } from "../utils/dates";
import { Icon } from "./Icon";

interface WeekNavigatorProps {
  monday: Date;
  isCurrentWeek: boolean;
  onPrevious: () => void;
  onNext: () => void;
  onToday: () => void;
}

export function WeekNavigator({ monday, isCurrentWeek, onPrevious, onNext, onToday }: WeekNavigatorProps) {
  return (
    <div className="week-nav" role="group" aria-label="Hafta seçimi">
      <button type="button" className="btn btn-icon" onClick={onPrevious} aria-label="Önceki hafta">
        <Icon name="left" />
      </button>
      <div className="week-label" aria-live="polite">
        <strong>{formatWeekRange(monday)}</strong>
        <small>{isCurrentWeek ? "Bu hafta" : "Haftalık plan"}</small>
      </div>
      <button type="button" className="btn btn-icon" onClick={onNext} aria-label="Sonraki hafta">
        <Icon name="right" />
      </button>
      {!isCurrentWeek && (
        <button type="button" className="btn btn-sm" onClick={onToday}>
          Bu hafta
        </button>
      )}
    </div>
  );
}
