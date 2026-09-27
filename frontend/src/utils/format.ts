const UNIT_NAMES: Record<string, string> = {
  yk: "yemek kaşığı",
  ck: "çay kaşığı",
};

const FRACTIONS: [number, string][] = [
  [0.25, "¼"],
  [0.33, "⅓"],
  [0.5, "½"],
  [0.67, "⅔"],
  [0.75, "¾"],
];

export function formatMoney(value: number | null | undefined, currency = "TRY"): string {
  if (value === null || value === undefined) return "—";
  const symbol = currency === "TRY" ? "₺" : currency;
  return `${symbol}${Math.round(value).toLocaleString("tr-TR")}`;
}

export function formatDuration(minutes: number | null | undefined): string {
  if (!minutes) return "—";
  if (minutes < 60) return `${minutes} dk`;
  const hours = Math.floor(minutes / 60);
  const rest = minutes % 60;
  return rest ? `${hours} sa ${rest} dk` : `${hours} sa`;
}

function trimNumber(value: number): string {
  return value.toLocaleString("tr-TR", { maximumFractionDigits: 2 });
}

/** 0.5 -> "½", 1.5 -> "1½", 2 -> "2", 0.1 -> "0,1" */
export function formatQuantity(quantity: number): string {
  const whole = Math.floor(quantity + 1e-9);
  const fraction = quantity - whole;
  if (fraction < 0.02) return trimNumber(whole);
  const match = FRACTIONS.find(([value]) => Math.abs(fraction - value) < 0.02);
  if (match) return whole > 0 ? `${whole}${match[1]}` : match[1];
  return trimNumber(quantity);
}

/** Miktarı birimiyle okunur hale getirir: 1500 g -> "1,5 kg", 0.5 yk -> "½ yemek kaşığı". */
export function formatAmount(quantity: number | null, unit: string | null): string {
  if (quantity === null) return "";
  if (unit === "g" && quantity >= 1000) return `${trimNumber(quantity / 1000)} kg`;
  if (unit === "ml" && quantity >= 1000) return `${trimNumber(quantity / 1000)} L`;
  const name = unit ? (UNIT_NAMES[unit] ?? unit) : "";
  // Gram ve mililitrede kesir simgesi yerine ondalık yazılır: 2,5 g
  const amount = unit === "g" || unit === "ml" ? trimNumber(quantity) : formatQuantity(quantity);
  return `${amount}${name ? ` ${name}` : ""}`;
}

export function scaleQuantity(quantity: number | null, from: number, to: number): number | null {
  if (quantity === null || from <= 0) return quantity;
  return (quantity * to) / from;
}

const WHOLE_UNITS = new Set(["adet", "diş", "dilim", "kutu", "paket"]);

function ceilTo(value: number, step: number): number {
  return Math.ceil(value / step - 1e-9) * step;
}

/**
 * Alışveriş listesi için miktarı satın alınabilir hale yuvarlar (hep yukarı):
 * 1⅓ adet -> 2 adet, 83⅓ g -> 85 g, 7,83 çay kaşığı -> 8 çay kaşığı.
 */
export function formatShoppingAmount(quantity: number | null, unit: string | null): string {
  if (quantity === null) return "";
  let rounded = quantity;
  if (unit && WHOLE_UNITS.has(unit)) rounded = Math.max(1, Math.ceil(quantity - 1e-9));
  else if (unit === "g" || unit === "ml") rounded = quantity >= 50 ? ceilTo(quantity, 5) : Math.ceil(quantity - 1e-9);
  else if (unit === "demet" || unit === "yk" || unit === "ck") rounded = quantity >= 10 ? Math.ceil(quantity - 1e-9) : ceilTo(quantity, 0.5);
  return formatAmount(rounded, unit);
}
