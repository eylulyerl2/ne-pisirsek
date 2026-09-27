import { useInfiniteQuery, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ApiError } from "../services/api";
import { api, type MealFilters } from "../services/endpoints";
import type {
  FamilyRole,
  GenerateOptions,
  GenerateResponse,
  PlanDetail,
  Preferences,
  Rating,
  ShoppingList,
} from "../services/types";

const DAY = 24 * 60 * 60 * 1000;

export const keys = {
  plans: (familyId?: string | null) => ["plans", familyId ?? "me"] as const,
  families: ["families"] as const,
  family: (id: string) => ["family", id] as const,
  familyInvitations: (id: string) => ["family-invitations", id] as const,
  plan: (id: string) => ["plan", id] as const,
  shopping: (planId: string) => ["shopping", planId] as const,
  preferences: ["preferences"] as const,
};

export function useCategories() {
  return useQuery({ queryKey: ["categories"], queryFn: api.categories, staleTime: DAY });
}

export function useRegions() {
  return useQuery({ queryKey: ["regions"], queryFn: api.regions, staleTime: DAY });
}

export function useMeals(filters: Omit<MealFilters, "offset" | "limit">) {
  return useInfiniteQuery({
    queryKey: ["meals", filters],
    queryFn: ({ pageParam }) => api.meals({ ...filters, limit: 24, offset: pageParam }),
    initialPageParam: 0,
    getNextPageParam: (last) => (last.offset + last.limit < last.total ? last.offset + last.limit : undefined),
  });
}

export function useMeal(id: string | null) {
  return useQuery({ queryKey: ["meal", id], queryFn: () => api.meal(id as string), enabled: id !== null });
}

export function usePlans(familyId?: string | null) {
  return useQuery({ queryKey: keys.plans(familyId), queryFn: () => api.plans(familyId) });
}

export function usePlan(id: string | undefined) {
  // Aile üyeleri aynı planı düzenleyebildiğinden sekmeye dönünce güncel hali alınır
  return useQuery({
    queryKey: keys.plan(id ?? ""),
    queryFn: () => api.plan(id as string),
    enabled: !!id,
    refetchOnWindowFocus: true,
  });
}

/** Planı (yoksa) oluşturur ve menüyü üretir. */
export function useGeneratePlan() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({
      weekStart,
      planId,
      familyId,
      options,
    }: {
      weekStart: string;
      planId?: string;
      familyId?: string | null;
      options: GenerateOptions;
    }): Promise<GenerateResponse> => {
      const id = planId ?? (await api.createPlan(weekStart, familyId)).plan_id;
      return api.generate(id, options);
    },
    onSuccess: async (data) => {
      queryClient.setQueryData(keys.plan(data.plan.plan_id), data.plan);
      await queryClient.invalidateQueries({ queryKey: ["plans"] });
      await queryClient.invalidateQueries({ queryKey: keys.shopping(data.plan.plan_id) });
    },
  });
}

function usePlanMutation<TVars>(mutationFn: (vars: TVars) => Promise<unknown>, planId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: keys.plan(planId) }),
  });
}

export function useAlternatives(planId: string, plannedMealId: string) {
  return useQuery({
    queryKey: ["alternatives", planId, plannedMealId],
    queryFn: () => api.alternatives(planId, plannedMealId, 8),
    staleTime: 0,
    gcTime: 0,
  });
}

export function useReplaceMeal(planId: string) {
  return usePlanMutation(
    ({ plannedMealId, mealId }: { plannedMealId: string; mealId?: string }) =>
      api.replace(planId, plannedMealId, mealId),
    planId,
  );
}

export function useRemoveMeal(planId: string) {
  return usePlanMutation((plannedMealId: string) => api.removePlannedMeal(planId, plannedMealId), planId);
}

export function useSetCompleted(planId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ plannedMealId, isCompleted }: { plannedMealId: string; isCompleted: boolean }) =>
      api.setCompleted(planId, plannedMealId, isCompleted),
    onMutate: async ({ plannedMealId, isCompleted }) => {
      // İptal hemen başlatılır ama beklenmez: kutu, yenileme bitene kadar eski hâline dönüp titremesin
      const cancelled = queryClient.cancelQueries({ queryKey: keys.plan(planId) });
      const previous = queryClient.getQueryData<PlanDetail>(keys.plan(planId));
      if (previous) {
        const mark = (d: { planned_meal_id: string }) => d.planned_meal_id === plannedMealId;
        queryClient.setQueryData<PlanDetail>(keys.plan(planId), {
          ...previous,
          planned_meals: previous.planned_meals.map((d) => (mark(d) ? { ...d, is_completed: isCompleted } : d)),
          days: previous.days.map((day) => ({
            ...day,
            meals: day.meals.map((slot) => ({
              ...slot,
              dishes: slot.dishes.map((d) => (mark(d) ? { ...d, is_completed: isCompleted } : d)),
            })),
          })),
        });
      }
      await cancelled;
      return { previous };
    },
    onError: (_error, _vars, context) => {
      if (context?.previous) queryClient.setQueryData(keys.plan(planId), context.previous);
    },
    onSettled: () => queryClient.invalidateQueries({ queryKey: keys.plan(planId) }),
  });
}

const SHOPPING_POLL_MS = 15_000;
const CHECK_MUTATION_KEY = ["shopping-check"] as const;

export function useShoppingList(planId: string | undefined) {
  const queryClient = useQueryClient();
  return useQuery({
    queryKey: keys.shopping(planId ?? ""),
    enabled: !!planId,
    refetchOnWindowFocus: true,
    // Markette biri, evde diğeri: işaretler birbirine yansısın. Kendi işaretleme işlemi sürerken yenilenmez.
    refetchInterval: () => (queryClient.isMutating({ mutationKey: CHECK_MUTATION_KEY }) > 0 ? false : SHOPPING_POLL_MS),
    queryFn: async (): Promise<ShoppingList | null> => {
      try {
        return await api.shoppingList(planId as string);
      } catch (error) {
        if (error instanceof ApiError && error.status === 404) return null;
        throw error;
      }
    },
  });
}

export function useBuildShoppingList(planId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => api.buildShoppingList(planId),
    onSuccess: (data) => queryClient.setQueryData(keys.shopping(planId), data),
  });
}

export function useCheckItem(planId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationKey: CHECK_MUTATION_KEY,
    mutationFn: ({ itemId, isChecked }: { itemId: string; isChecked: boolean }) =>
      api.checkItem(planId, itemId, isChecked),
    onMutate: async ({ itemId, isChecked }) => {
      const cancelled = queryClient.cancelQueries({ queryKey: keys.shopping(planId) });
      const previous = queryClient.getQueryData<ShoppingList | null>(keys.shopping(planId));
      if (previous) {
        queryClient.setQueryData<ShoppingList>(keys.shopping(planId), {
          ...previous,
          items: previous.items.map((i) => (i.item_id === itemId ? { ...i, is_checked: isChecked } : i)),
        });
      }
      await cancelled;
      return { previous };
    },
    onError: (_error, _vars, context) => {
      if (context?.previous) queryClient.setQueryData(keys.shopping(planId), context.previous);
    },
    onSettled: () => queryClient.invalidateQueries({ queryKey: keys.shopping(planId) }),
  });
}

export function usePreferences() {
  return useQuery({ queryKey: keys.preferences, queryFn: api.preferences });
}

export function useUpdatePreferences() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: Partial<Preferences>) => api.updatePreferences(body),
    onSuccess: (data) => queryClient.setQueryData(keys.preferences, data),
  });
}

export function useFamilies() {
  return useQuery({ queryKey: keys.families, queryFn: api.families });
}

export function useFamily(id: string | undefined) {
  return useQuery({ queryKey: keys.family(id ?? ""), queryFn: () => api.family(id as string), enabled: !!id });
}

export function useFamilyInvitations(id: string, enabled: boolean) {
  return useQuery({ queryKey: keys.familyInvitations(id), queryFn: () => api.familyInvitations(id), enabled });
}

function useInvalidating<TVars, TData>(mutationFn: (vars: TVars) => Promise<TData>, invalidate: (vars: TVars) => readonly (readonly unknown[])[]) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn,
    onSuccess: async (_data, vars) => {
      await Promise.all(invalidate(vars).map((queryKey) => queryClient.invalidateQueries({ queryKey })));
    },
  });
}

export function useCreateFamily() {
  return useInvalidating((name: string) => api.createFamily(name), () => [keys.families]);
}

export function useRenameFamily(familyId: string) {
  return useInvalidating((name: string) => api.renameFamily(familyId, name), () => [keys.families, keys.family(familyId)]);
}

export function useDeleteFamily(familyId: string) {
  return useInvalidating(() => api.deleteFamily(familyId), () => [keys.families, ["plans"]]);
}

export function useSetMemberRole(familyId: string) {
  return useInvalidating(
    ({ userId, role }: { userId: string; role: FamilyRole }) => api.setMemberRole(familyId, userId, role),
    () => [keys.family(familyId), keys.families],
  );
}

export function useRemoveMember(familyId: string) {
  return useInvalidating(
    (userId: string) => api.removeMember(familyId, userId),
    () => [keys.family(familyId), keys.families, ["plans"]],
  );
}

export function useCreateInvitation(familyId: string) {
  return useInvalidating(
    (label?: string) => api.createInvitation(familyId, label),
    () => [keys.familyInvitations(familyId)],
  );
}

export function useRegenerateInvitation(familyId: string) {
  return useInvalidating(
    (invitationId: string) => api.regenerateInvitation(familyId, invitationId),
    () => [keys.familyInvitations(familyId)],
  );
}

export function useRevokeInvitation(familyId: string) {
  return useInvalidating(
    (invitationId: string) => api.revokeInvitation(familyId, invitationId),
    () => [keys.familyInvitations(familyId)],
  );
}

export function usePreviewInvitation(token: string | null) {
  return useQuery({
    queryKey: ["invitation-preview", token],
    queryFn: () => api.previewInvitation(token as string),
    enabled: !!token,
    retry: false,
    staleTime: 0,
  });
}

export function useAcceptInvitation() {
  return useInvalidating(
    ({ token, code }: { token: string; code: string }) => api.acceptInvitation(token, code),
    () => [keys.families, ["invitation-preview"]],
  );
}

export function useCreatePasswordReset(familyId: string) {
  return useInvalidating((userId: string) => api.createPasswordReset(familyId, userId), () => [keys.family(familyId)]);
}

export function useCancelPasswordReset(familyId: string) {
  return useInvalidating((userId: string) => api.cancelPasswordReset(familyId, userId), () => [keys.family(familyId)]);
}

export function usePreviewPasswordReset(token: string | null) {
  return useQuery({
    queryKey: ["password-reset-preview", token],
    queryFn: () => api.previewPasswordReset(token as string),
    enabled: !!token,
    retry: false,
    staleTime: 0,
  });
}

export function useMyRating(mealId: string | null) {
  return useQuery({
    queryKey: ["rating", mealId ?? ""],
    enabled: !!mealId,
    queryFn: async (): Promise<Rating | null> => {
      try {
        return await api.myRating(mealId as string);
      } catch (error) {
        if (error instanceof ApiError && error.status === 404) return null;
        throw error;
      }
    },
  });
}

export function useRateMeal(mealId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ rating, comment }: { rating: number; comment?: string }) => api.rateMeal(mealId, rating, comment),
    onSuccess: async (data) => {
      queryClient.setQueryData(["rating", mealId], data);
      await queryClient.invalidateQueries({ queryKey: ["meal", mealId] });
    },
  });
}

export function useDeleteRating(mealId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => api.deleteRating(mealId),
    onSuccess: async () => {
      queryClient.setQueryData(["rating", mealId], null);
      await queryClient.invalidateQueries({ queryKey: ["meal", mealId] });
    },
  });
}

export function useMyRatings() {
  return useQuery({ queryKey: ["my-ratings"], queryFn: api.myRatings });
}
