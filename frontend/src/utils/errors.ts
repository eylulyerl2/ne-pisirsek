const FIELD_LABELS: Record<string, string> = {
  email: "E-posta",
  username: "Kullanıcı adı",
  code: "Şifre",
  label: "Etiket",
  password: "Şifre",
  current_password: "Mevcut şifre",
  new_password: "Yeni şifre",
  full_name: "Ad soyad",
  avatar_url: "Profil resmi",
  daily_calorie_target: "Günlük kalori hedefi",
  calorie_tolerance_percent: "Kalori toleransı",
  protein_target_grams: "Protein hedefi",
  carbohydrate_target_grams: "Karbonhidrat hedefi",
  fat_target_grams: "Yağ hedefi",
  servings_per_meal: "Öğün başına porsiyon",
  soup_frequency_per_week: "Haftalık çorba sayısı",
  vegetable_frequency_per_week: "Haftalık sebze yemeği sayısı",
  legume_frequency_per_week: "Haftalık baklagil sayısı",
  max_preparation_time_minutes: "En uzun hazırlık süresi",
  weekly_budget: "Haftalık bütçe",
  currency: "Para birimi",
  name: "Ad",
  rating: "Puan",
};

interface ValidationIssue {
  type?: string;
  loc?: (string | number)[];
  msg?: string;
  ctx?: Record<string, unknown>;
}

function describeIssue(issue: ValidationIssue): string {
  const field = String(issue.loc?.[issue.loc.length - 1] ?? "");
  const label = FIELD_LABELS[field] ?? "Bu alan";
  const ctx = issue.ctx ?? {};
  switch (issue.type) {
    case "missing":
      return `${label} zorunlu`;
    case "string_too_short":
      return `${label} en az ${ctx.min_length} karakter olmalı`;
    case "string_too_long":
      return `${label} en fazla ${ctx.max_length} karakter olmalı`;
    case "greater_than_equal":
      return `${label} en az ${ctx.ge} olmalı`;
    case "less_than_equal":
      return `${label} en fazla ${ctx.le} olmalı`;
    case "int_parsing":
    case "float_parsing":
    case "int_from_float":
      return `${label} geçerli bir sayı olmalı`;
    case "string_pattern_mismatch":
      return `${label} geçerli biçimde değil`;
    case "literal_error":
    case "enum":
      return `${label} için geçersiz bir seçim yapıldı`;
    case "uuid_parsing":
      return "Geçersiz kimlik";
    case "value_error": {
      const msg = issue.msg ?? "";
      if (/valid email/i.test(msg)) return "Geçerli bir e-posta adresi girin";
      const cleaned = msg.replace(/^Value error,\s*/i, "");
      return /[ğüşöçıİĞÜŞÖÇ]|olmalı|olamaz|bırakılamaz/.test(cleaned) ? cleaned : `${label} geçersiz`;
    }
    default:
      return `${label} geçersiz`;
  }
}

/** FastAPI'nin döndürdüğü hata gövdesini kullanıcıya gösterilecek Türkçe bir mesaja çevirir. */
export function formatApiError(status: number, payload: unknown): string {
  const detail = (payload as { detail?: unknown } | null)?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail) && detail.length > 0) {
    return [...new Set(detail.map((d) => describeIssue(d as ValidationIssue)))].join(". ");
  }
  if (status === 401) return "Oturumunuz sona erdi, lütfen tekrar giriş yapın";
  if (status === 403) return "Bu işlem için yetkiniz yok";
  if (status === 404) return "Aradığınız kayıt bulunamadı";
  if (status === 429) return "Çok fazla istek gönderildi, lütfen biraz bekleyin";
  if (status >= 500) return "Sunucuda bir sorun oluştu, lütfen daha sonra tekrar deneyin";
  return "İşlem tamamlanamadı";
}

export const NETWORK_ERROR = "Sunucuya ulaşılamadı. İnternet bağlantınızı kontrol edip tekrar deneyin.";
