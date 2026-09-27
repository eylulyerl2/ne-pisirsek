export type MealType = "breakfast" | "lunch" | "dinner" | "snack";
export type Course = "main" | "soup" | "side" | "salad";

export interface User {
  user_id: string;
  email: string | null;
  username: string | null;
  full_name: string;
  avatar_url: string | null;
  preferred_language: string;
}

export interface Category {
  category_id: string;
  name: string;
  slug: string;
}

export interface Region {
  slug: string;
  name: string;
}

export interface Nutrition {
  calories: number | null;
  protein_grams: number | null;
  carbohydrate_grams: number | null;
  fat_grams: number | null;
  fiber_grams: number | null;
}

export interface MealSummary {
  meal_id: string;
  name: string;
  description: string | null;
  image_url: string | null;
  preparation_time_minutes: number | null;
  cooking_time_minutes: number | null;
  servings: number;
  estimated_cost: number | null;
  currency: string;
  region: string | null;
  region_name: string | null;
  has_recipe: boolean;
  categories: Category[];
  nutrition: Nutrition | null;
  total_time_minutes: number;
}

export interface Ingredient {
  name: string;
  quantity: number | null;
  unit: string | null;
  is_optional: boolean;
}

export interface MealDetail extends MealSummary {
  instructions: string | null;
  source_type: string;
  source_url: string | null;
  ingredients: Ingredient[];
  average_rating: number | null;
  rating_count: number;
}

export interface MealList {
  items: MealSummary[];
  total: number;
  limit: number;
  offset: number;
}

export interface MealBrief {
  meal_id: string;
  name: string;
  image_url: string | null;
  region: string | null;
  total_time_minutes: number;
  calories_per_serving: number | null;
  categories: string[];
  has_recipe: boolean;
}

export interface Alternative extends MealBrief {
  estimated_cost: number | null;
}

export interface PlannedMeal {
  planned_meal_id: string;
  day_of_week: number;
  meal_type: MealType;
  course: Course;
  course_name: string;
  servings: number;
  is_completed: boolean;
  estimated_cost: number | null;
  meal: MealBrief;
}

export interface MealSlot {
  meal_type: MealType;
  meal_type_name: string;
  dishes: PlannedMeal[];
}

export interface DayPlan {
  day_of_week: number;
  meals: MealSlot[];
}

export interface PlanSummary {
  plan_id: string;
  user_id: string | null;
  family_id: string | null;
  week_start_date: string;
  status: "draft" | "active" | "completed" | "archived";
  created_at: string | null;
}

export interface PlanDetail extends PlanSummary {
  planned_meals: PlannedMeal[];
  days: DayPlan[];
  estimated_total_cost: number | null;
}

export interface GenerateResponse {
  plan: PlanDetail;
  warnings: string[];
}

export interface GenerateOptions {
  meal_types: MealType[];
  compose: boolean;
  seed?: number;
  exclude_meal_ids?: string[];
}

export interface ShoppingItem {
  item_id: string;
  ingredient_id: string;
  name: string;
  quantity: number | null;
  unit: string | null;
  estimated_price: number | null;
  is_checked: boolean;
}

export interface ShoppingList {
  list_id: string;
  plan_id: string;
  created_at: string | null;
  items: ShoppingItem[];
}

export interface Preferences {
  daily_calorie_target: number | null;
  calorie_tolerance_percent: number;
  protein_target_grams: number | null;
  carbohydrate_target_grams: number | null;
  fat_target_grams: number | null;
  servings_per_meal: number;
  soup_frequency_per_week: number;
  vegetable_frequency_per_week: number;
  legume_frequency_per_week: number;
  max_preparation_time_minutes: number | null;
  weekly_budget: number | null;
  currency: string;
}

export interface Token {
  access_token: string;
  token_type: string;
}

export type FamilyRole = "admin" | "member";

export interface FamilySummary {
  family_id: string;
  name: string;
  role: FamilyRole;
  created_by: string;
  member_count: number;
  created_at: string | null;
}

export interface FamilyMember {
  user_id: string;
  full_name: string;
  username: string | null;
  avatar_url: string | null;
  role: FamilyRole;
  joined_at: string | null;
  can_reset_password: boolean;
  reset_pending: boolean;
}

export interface FamilyDetail extends FamilySummary {
  members: FamilyMember[];
}

export interface Invitation {
  invitation_id: string;
  family_id: string;
  label: string | null;
  token: string;
  status: "pending" | "accepted" | "expired" | "locked";
  failed_attempts: number;
  expires_at: string;
  created_at: string | null;
  /** Tek kullanımlık şifre: yalnızca oluşturma/yenileme yanıtında gelir. */
  code: string | null;
}

export interface InvitationPreview {
  family_name: string;
  inviter_name: string;
  label: string | null;
  status: Invitation["status"];
  usable: boolean;
  expires_at: string;
}

export interface JoinResult {
  access_token: string;
  token_type: string;
  family: FamilySummary;
}

export interface PasswordResetCreated {
  token: string;
  /** Tek kullanımlık şifre: yalnızca oluşturma yanıtında bir kez gelir. */
  code: string;
  expires_at: string;
  member_name: string;
}

export interface PasswordResetPreview {
  full_name: string;
  username: string | null;
  status: "pending" | "used" | "locked" | "expired";
  usable: boolean;
  expires_at: string;
}

export interface Rating {
  rating_id: string;
  meal_id: string;
  rating: number;
  comment: string | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface MyRating extends Rating {
  meal_name: string;
}
