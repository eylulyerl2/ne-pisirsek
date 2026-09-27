const DAY_NAMES = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"];
const dayMonth = new Intl.DateTimeFormat("tr-TR", { day: "numeric", month: "long" });
const dayMonthYear = new Intl.DateTimeFormat("tr-TR", { day: "numeric", month: "long", year: "numeric" });

/** Yerel saat dilimine göre YYYY-AA-GG (UTC'ye çevirmeden, gün kayması olmasın diye). */
export function toISODate(date: Date): string {
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, "0");
  const d = String(date.getDate()).padStart(2, "0");
  return `${y}-${m}-${d}`;
}

export function parseISODate(value: string): Date {
  const [y, m, d] = value.split("-").map(Number);
  return new Date(y, m - 1, d);
}

export function addDays(date: Date, days: number): Date {
  const copy = new Date(date.getFullYear(), date.getMonth(), date.getDate());
  copy.setDate(copy.getDate() + days);
  return copy;
}

/** Verilen tarihin haftasının Pazartesi'si (hafta Pazartesi'de başlar). */
export function mondayOf(date: Date): Date {
  const offset = (date.getDay() + 6) % 7;
  return addDays(date, -offset);
}

export function dayName(dayOfWeek: number): string {
  return DAY_NAMES[dayOfWeek - 1] ?? "";
}

export function dayDate(monday: Date, dayOfWeek: number): Date {
  return addDays(monday, dayOfWeek - 1);
}

export function formatDayMonth(date: Date): string {
  return dayMonth.format(date);
}

export function formatWeekRange(monday: Date): string {
  const sunday = addDays(monday, 6);
  if (monday.getFullYear() === sunday.getFullYear()) {
    return `${dayMonth.format(monday)} – ${dayMonthYear.format(sunday)}`;
  }
  return `${dayMonthYear.format(monday)} – ${dayMonthYear.format(sunday)}`;
}

export function isSameDay(a: Date, b: Date): boolean {
  return toISODate(a) === toISODate(b);
}
