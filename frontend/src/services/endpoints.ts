import { request } from "./api";
import type {
  Alternative,
  Category,
  FamilyDetail,
  FamilyMember,
  FamilyRole,
  FamilySummary,
  GenerateOptions,
  GenerateResponse,
  Invitation,
  InvitationPreview,
  JoinResult,
  MealDetail,
  MealList,
  MyRating,
  PasswordResetCreated,
  Rating,
  PasswordResetPreview,
  PlanDetail,
  PlanSummary,
  PlannedMeal,
  Preferences,
  Region,
  ShoppingItem,
  ShoppingList,
  Token,
  User,
} from "./types";

export interface MealFilters {
  q?: string;
  category?: string[];
  region?: string[];
  max_time_minutes?: number;
  max_cost?: number;
  limit?: number;
  offset?: number;
}

export const api = {
  register: (body: { email: string; password: string; full_name: string }) =>
    request<User>("/auth/register", { method: "POST", body, auth: false }),
  login: (identifier: string, password: string) =>
    request<Token>("/auth/login", { method: "POST", form: { username: identifier, password }, auth: false }),
  me: () => request<User>("/auth/me"),
  updateProfile: (body: Partial<Pick<User, "full_name" | "avatar_url" | "preferred_language">>) =>
    request<User>("/users/me", { method: "PATCH", body }),
  preferences: () => request<Preferences>("/users/me/preferences"),
  updatePreferences: (body: Partial<Preferences>) =>
    request<Preferences>("/users/me/preferences", { method: "PATCH", body }),

  categories: () => request<Category[]>("/categories", { auth: false }),
  regions: () => request<Region[]>("/regions", { auth: false }),
  meals: (filters: MealFilters) => request<MealList>("/meals", { params: { ...filters }, auth: false }),
  meal: (id: string) => request<MealDetail>(`/meals/${id}`, { auth: false }),

  plans: (familyId?: string | null) =>
    request<PlanSummary[]>("/plans", { params: { limit: 100, family_id: familyId ?? undefined } }),
  createPlan: (weekStart: string, familyId?: string | null) =>
    request<PlanSummary>("/plans", {
      method: "POST",
      body: { week_start_date: weekStart, ...(familyId ? { family_id: familyId } : {}) },
    }),
  plan: (id: string) => request<PlanDetail>(`/plans/${id}`),
  generate: (id: string, options: GenerateOptions) =>
    request<GenerateResponse>(`/plans/${id}/generate`, { method: "POST", body: options }),
  deletePlan: (id: string) => request<void>(`/plans/${id}`, { method: "DELETE" }),

  alternatives: (planId: string, plannedMealId: string, limit = 8) =>
    request<Alternative[]>(`/plans/${planId}/meals/${plannedMealId}/alternatives`, { params: { limit } }),
  replace: (planId: string, plannedMealId: string, mealId?: string) =>
    request<PlannedMeal>(`/plans/${planId}/meals/${plannedMealId}/replace`, {
      method: "POST",
      body: mealId ? { meal_id: mealId } : {},
    }),
  removePlannedMeal: (planId: string, plannedMealId: string) =>
    request<void>(`/plans/${planId}/meals/${plannedMealId}`, { method: "DELETE" }),
  setCompleted: (planId: string, plannedMealId: string, isCompleted: boolean) =>
    request<PlannedMeal>(`/plans/${planId}/meals/${plannedMealId}`, {
      method: "PATCH",
      body: { is_completed: isCompleted },
    }),

  shoppingList: (planId: string) => request<ShoppingList>(`/plans/${planId}/shopping-list`),
  buildShoppingList: (planId: string) =>
    request<ShoppingList>(`/plans/${planId}/shopping-list`, { method: "POST" }),
  checkItem: (planId: string, itemId: string, isChecked: boolean) =>
    request<ShoppingItem>(`/plans/${planId}/shopping-list/items/${itemId}`, {
      method: "PATCH",
      body: { is_checked: isChecked },
    }),

  families: () => request<FamilySummary[]>("/families"),
  createFamily: (name: string) => request<FamilySummary>("/families", { method: "POST", body: { name } }),
  family: (id: string) => request<FamilyDetail>(`/families/${id}`),
  renameFamily: (id: string, name: string) =>
    request<FamilySummary>(`/families/${id}`, { method: "PATCH", body: { name } }),
  deleteFamily: (id: string) => request<void>(`/families/${id}`, { method: "DELETE" }),
  setMemberRole: (familyId: string, userId: string, role: FamilyRole) =>
    request<FamilyMember>(`/families/${familyId}/members/${userId}`, { method: "PATCH", body: { role } }),
  removeMember: (familyId: string, userId: string) =>
    request<void>(`/families/${familyId}/members/${userId}`, { method: "DELETE" }),
  createInvitation: (familyId: string, label?: string) =>
    request<Invitation>(`/families/${familyId}/invitations`, { method: "POST", body: label ? { label } : {} }),
  regenerateInvitation: (familyId: string, invitationId: string) =>
    request<Invitation>(`/families/${familyId}/invitations/${invitationId}/regenerate`, { method: "POST" }),
  familyInvitations: (familyId: string) => request<Invitation[]>(`/families/${familyId}/invitations`),
  revokeInvitation: (familyId: string, invitationId: string) =>
    request<void>(`/families/${familyId}/invitations/${invitationId}`, { method: "DELETE" }),
  previewInvitation: (token: string) =>
    request<InvitationPreview>("/invitations/preview", { params: { token }, auth: false }),
  joinWithNewAccount: (body: {
    token: string;
    code: string;
    full_name: string;
    username: string;
    password: string;
    email?: string;
  }) => request<JoinResult>("/invitations/join", { method: "POST", body, auth: false }),
  acceptInvitation: (token: string, code: string) =>
    request<FamilySummary>("/invitations/accept", { method: "POST", body: { token, code } }),
  createPasswordReset: (familyId: string, userId: string) =>
    request<PasswordResetCreated>(`/families/${familyId}/members/${userId}/password-reset`, { method: "POST" }),
  cancelPasswordReset: (familyId: string, userId: string) =>
    request<void>(`/families/${familyId}/members/${userId}/password-reset`, { method: "DELETE" }),
  previewPasswordReset: (token: string) =>
    request<PasswordResetPreview>("/password-resets/preview", { params: { token }, auth: false }),
  completePasswordReset: (body: { token: string; code: string; new_password: string }) =>
    request<Token>("/password-resets/complete", { method: "POST", body, auth: false }),
  changePassword: (body: { current_password: string; new_password: string }) =>
    request<void>("/users/me/password", { method: "POST", body }),
  myRating: (mealId: string) => request<Rating>(`/meals/${mealId}/rating`),
  rateMeal: (mealId: string, rating: number, comment?: string) =>
    request<Rating>(`/meals/${mealId}/rating`, { method: "PUT", body: { rating, comment: comment || undefined } }),
  deleteRating: (mealId: string) => request<void>(`/meals/${mealId}/rating`, { method: "DELETE" }),
  myRatings: () => request<MyRating[]>("/users/me/ratings"),
};
