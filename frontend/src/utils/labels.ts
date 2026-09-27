import type { Course, MealType } from "../services/types";

export const MEAL_TYPE_LABELS: Record<MealType, string> = {
  breakfast: "Kahvaltı",
  lunch: "Öğle yemeği",
  dinner: "Akşam yemeği",
  snack: "Ara öğün",
};

export const COURSE_LABELS: Record<Course, string> = {
  soup: "Çorba",
  main: "Ana yemek",
  side: "Yan yemek",
  salad: "Salata",
};

export const PLAN_STATUS_LABELS = {
  draft: "Taslak",
  active: "Aktif",
  completed: "Tamamlandı",
  archived: "Arşiv",
} as const;
