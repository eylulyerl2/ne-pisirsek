import { useCallback, useMemo } from "react";
import { useSearchParams } from "react-router-dom";
import { addDays, mondayOf, parseISODate, toISODate } from "../utils/dates";

/** Seçili hafta adres çubuğunda (?hafta=2026-09-28) tutulur; sayfalar arasında paylaşılır. */
export function useWeek() {
  const [params, setParams] = useSearchParams();
  const raw = params.get("hafta");

  const monday = useMemo(() => {
    const parsed = raw && /^\d{4}-\d{2}-\d{2}$/.test(raw) ? parseISODate(raw) : new Date();
    return mondayOf(Number.isNaN(parsed.getTime()) ? new Date() : parsed);
  }, [raw]);

  const setMonday = useCallback(
    (next: Date) => {
      const copy = new URLSearchParams(params);
      copy.set("hafta", toISODate(mondayOf(next)));
      setParams(copy, { replace: true });
    },
    [params, setParams],
  );

  return {
    monday,
    weekStart: toISODate(monday),
    next: () => setMonday(addDays(monday, 7)),
    previous: () => setMonday(addDays(monday, -7)),
    today: () => setMonday(new Date()),
    isCurrentWeek: toISODate(monday) === toISODate(mondayOf(new Date())),
  };
}
