import random
from collections import Counter
from dataclasses import dataclass, field
from statistics import mean, median
from typing import Any, Sequence

MEAL_TYPE_ORDER = ("breakfast", "lunch", "dinner", "snack")
MAIN_TYPES = ("lunch", "dinner")
CALORIE_SHARE = {"breakfast": 0.25, "lunch": 0.35, "dinner": 0.35, "snack": 0.05}
MAIN_CALORIE_SHARE = 0.6

COURSE_ORDER = ("soup", "main", "side", "salad")
COURSE_LABELS = {"soup": "çorba", "main": "ana yemek", "side": "yan yemek", "salad": "salata"}
MAX_DISHES_PER_MEAL = 3

FREQUENCY_CATEGORIES = ("corba", "sebze", "baklagil")
CATEGORY_LABELS = {"corba": "çorba", "sebze": "sebze yemeği", "baklagil": "baklagil"}
NON_MAIN_CATEGORIES = frozenset({"kahvalti", "tatli", "salata", "yan-yemek"})
SLOT_ONLY_CATEGORIES = {"breakfast": frozenset({"kahvalti"}), "snack": frozenset({"tatli"})}
MEAL_TYPE_LABELS = {"breakfast": "kahvaltı", "lunch": "öğle yemeği", "dinner": "akşam yemeği", "snack": "ara öğün"}

MAX_USES_PER_WEEK = 2

# Kural gevsetme seviyeleri (0 = hicbiri gevsetilmez)
RELAX_REPEAT, RELAX_FREQUENCY, RELAX_TIME, RELAX_DISLIKE = 1, 2, 3, 4
RELAX_LABELS = {
    RELAX_REPEAT: "tekrar sınırı esnetildi",
    RELAX_FREQUENCY: "sebze/baklagil sıklık hedefi esnetildi",
    RELAX_TIME: "süre sınırı esnetildi",
    RELAX_DISLIKE: "düşük puanlı yemek seçildi",
}


@dataclass(frozen=True)
class MealCandidate:
    meal_id: Any
    name: str
    categories: frozenset
    total_time_minutes: int
    estimated_cost: float | None
    servings: int
    calories: float | None
    personal_ratings: tuple = ()
    community_rating: float | None = None
    region: str | None = None
    starchy: bool = False

    @property
    def disliked(self) -> bool:
        return 1 in self.personal_ratings

    def cost_for(self, servings: int) -> float | None:
        if self.estimated_cost is None:
            return None
        return self.estimated_cost * servings / max(self.servings, 1)


@dataclass(frozen=True)
class Preferences:
    daily_calorie_target: int | None = None
    calorie_tolerance_percent: float = 10.0
    max_time_minutes: int | None = None
    weekly_budget: float | None = None
    soup_frequency: int = 2
    vegetable_frequency: int = 2
    legume_frequency: int = 1


@dataclass(frozen=True)
class Assignment:
    day_of_week: int
    meal_type: str
    meal_id: Any
    servings: int
    course: str = "main"


@dataclass
class GenerationResult:
    assignments: list
    warnings: list
    estimated_total_cost: float


def combine_preferences(prefs: Sequence[Preferences]) -> Preferences:
    """Aile uyeleri icin tek bir tercih seti uretir."""
    if not prefs:
        return Preferences()
    if len(prefs) == 1:
        return prefs[0]

    def avg(values):
        values = [v for v in values if v is not None]
        return mean(values) if values else None

    calories = avg(p.daily_calorie_target for p in prefs)
    times = [p.max_time_minutes for p in prefs if p.max_time_minutes is not None]
    budgets = [p.weekly_budget for p in prefs if p.weekly_budget is not None]
    return Preferences(
        daily_calorie_target=round(calories) if calories is not None else None,
        calorie_tolerance_percent=mean(p.calorie_tolerance_percent for p in prefs),
        max_time_minutes=min(times) if times else None,
        weekly_budget=max(budgets) if budgets else None,
        soup_frequency=round(mean(p.soup_frequency for p in prefs)),
        vegetable_frequency=round(mean(p.vegetable_frequency for p in prefs)),
        legume_frequency=round(mean(p.legume_frequency for p in prefs)),
    )


def is_eligible(course: str, meal_type: str, meal: MealCandidate, compose: bool = True, allow_soup_main: bool = False) -> bool:
    categories = meal.categories
    if meal_type in SLOT_ONLY_CATEGORIES:
        return course == "main" and bool(categories & SLOT_ONLY_CATEGORIES[meal_type])
    if course == "main":
        if categories & NON_MAIN_CATEGORIES:
            return False
        return not (compose and "corba" in categories and not allow_soup_main)
    if course == "soup":
        return "corba" in categories and not (categories & {"kahvalti", "tatli"})
    if course == "side":
        return "yan-yemek" in categories and "salata" not in categories
    if course == "salad":
        return "salata" in categories
    return False


def needs_side(main: MealCandidate) -> bool:
    """Tek başına karbonhidratı olmayan et/tavuk/baklagil ana yemeklerine pilav gibi bir yan yemek eşlik eder."""
    categories = main.categories
    if main.starchy or categories & {"pilav-makarna", "hamur-isi", "balik"}:
        return False
    return bool(categories & {"et", "tavuk", "baklagil"})


def _spread(indices: list, count: int) -> list:
    if count <= 0 or not indices:
        return []
    count = min(count, len(indices))
    return [indices[int((i + 0.5) * len(indices) / count)] for i in range(count)]


def _quotas(prefs: Preferences, main_slot_count: int, compose: bool) -> tuple[dict, int]:
    """(ana yemek kotaları, çorba günü sayısı). Çorba menüde ayrı bir kap olduğundan ana yemek kotasına girmez."""
    quotas = {
        "corba": max(prefs.soup_frequency, 0),
        "sebze": max(prefs.vegetable_frequency, 0),
        "baklagil": max(prefs.legume_frequency, 0),
    }
    soup_days = 0
    if compose:
        soup_days = min(quotas.pop("corba"), main_slot_count)
    while sum(quotas.values()) > main_slot_count:
        largest = max(quotas, key=quotas.get)
        quotas[largest] -= 1
    return quotas, soup_days


def _place_required(main_indices: list, quotas: dict) -> dict:
    """Kota kategorilerini haftaya esit araliklarla yayar; komsu ogunler farkli kategori olur."""
    order = []
    remaining = dict(quotas)
    while any(remaining.values()):
        for category in FREQUENCY_CATEGORIES:
            if remaining.get(category, 0) > 0:
                order.append(category)
                remaining[category] -= 1
    if not order:
        return {}
    n = len(main_indices)
    return {main_indices[int((i + 0.5) * n / len(order))]: category for i, category in enumerate(order)}


class _Scoring:
    """Üretimde ve alternatif önerirken aynı puanlama kullanılır."""

    def __init__(self, candidates: Sequence[MealCandidate], prefs: Preferences, servings: int):
        self.prefs = prefs
        self.servings = servings
        known = [c.estimated_cost / max(c.servings, 1) for c in candidates if c.estimated_cost is not None]
        self.fallback_unit_cost = median(known) if known else None

    def cost_of(self, meal: MealCandidate) -> float | None:
        # Maliyeti bilinmeyen yemek bedava sayilmasin diye bilinenlerin medyani varsayilir
        cost = meal.cost_for(self.servings)
        if cost is None and self.fallback_unit_cost is not None:
            return self.fallback_unit_cost * self.servings
        return cost

    def calorie_target(self, meal_type: str) -> float | None:
        if not self.prefs.daily_calorie_target:
            return None
        return self.prefs.daily_calorie_target * CALORIE_SHARE[meal_type]

    def _calorie_penalty(self, calories: float | None, target: float | None) -> float:
        if not target or not calories:
            return 0.0
        deviation = abs(calories - target) / target
        excess = max(0.0, deviation - self.prefs.calorie_tolerance_percent / 100)
        return 2.0 * min(excess, 1.5)

    def score(
        self,
        meal: MealCandidate,
        *,
        course: str,
        meal_type: str,
        composed: bool,
        main: MealCandidate | None,
        slot_dishes: Sequence[MealCandidate],
        uses: Counter,
        main_category_counts: Counter,
        previous_id: Any,
        slot_budget_left: float | None,
    ) -> float:
        value = 0.0
        if meal.personal_ratings:
            value += mean(meal.personal_ratings) - 3
        elif meal.community_rating is not None:
            value += 0.3 * (meal.community_rating - 3)

        slot_target = self.calorie_target(meal_type)
        if course == "main" and composed and meal_type in MAIN_TYPES:
            value -= self._calorie_penalty(meal.calories, slot_target and slot_target * MAIN_CALORIE_SHARE)
        elif slot_target and meal.calories:
            so_far = sum(d.calories or 0 for d in slot_dishes)
            value -= self._calorie_penalty(so_far + meal.calories, slot_target)

        cost = self.cost_of(meal)
        if slot_budget_left is not None and cost is not None:
            # Bütçe bittiğinde bile ucuz yemek pahalıdan ayırt edilebilsin diye referansa taban konur
            floor = 0.5 * (self.fallback_unit_cost or 0) * self.servings
            reference = max(slot_budget_left, floor, 1e-9)
            value -= 2.0 * min(max(cost / reference - 1, 0), 2.0)

        value -= 3.0 * uses[meal.meal_id]
        if meal.meal_id == previous_id:
            value -= 5.0

        if course == "main":
            value -= 0.4 * sum(main_category_counts[c] for c in meal.categories if c not in FREQUENCY_CATEGORIES)
        elif main is not None:
            if meal.region and meal.region == main.region and meal.region != "turkiye":
                value += 0.4
            if "baklagil" in meal.categories and "baklagil" in main.categories:
                value -= 2.0 if course == "side" else 1.5
            if course == "soup" and "sebze" in meal.categories and "sebze" in main.categories:
                value -= 0.6
        return value


def generate_weekly_plan(
    candidates: Sequence[MealCandidate],
    prefs: Preferences,
    meal_types: Sequence[str],
    servings: int,
    seed: int | None = None,
    compose: bool = True,
    exclude_ids: Sequence[Any] = (),
) -> GenerationResult:
    rng = random.Random(seed)
    excluded = set(exclude_ids)
    pool_all = [c for c in candidates if c.meal_id not in excluded]
    scoring = _Scoring(pool_all, prefs, servings)

    types = [t for t in MEAL_TYPE_ORDER if t in set(meal_types)]
    slots = [(day, t) for day in range(1, 8) for t in types]
    main_indices = [i for i, (_, t) in enumerate(slots) if t in MAIN_TYPES]
    quotas, soup_days = _quotas(prefs, len(main_indices), compose)
    required_by_slot = _place_required(main_indices, quotas)
    soup_slots = set(_spread(main_indices, soup_days))

    warnings: list = []
    for category, wanted in quotas.items():
        if wanted and not any(category in c.categories and is_eligible("main", "dinner", c, compose) for c in pool_all):
            warnings.append(f"'{CATEGORY_LABELS[category]}' kategorisinde yemek bulunamadı, sıklık hedefi karşılanamadı.")
    if soup_days and not any(is_eligible("soup", "dinner", c) for c in pool_all):
        warnings.append("Çorba bulunamadı, çorba günleri planlanamadı.")

    uses: Counter = Counter()
    main_category_counts: Counter = Counter()
    relaxed: Counter = Counter()
    empty: Counter = Counter()
    assignments: list = []
    total_cost = 0.0
    previous_id: dict = {}

    def pick(course, meal_type, *, required, saturated, main, slot_dishes, slot_budget_left, quota_categories):
        def allowed(meal: MealCandidate, level: int) -> bool:
            if not is_eligible(course, meal_type, meal, compose):
                return False
            if meal in slot_dishes:
                return False
            if level < RELAX_DISLIKE and meal.disliked:
                return False
            if level < RELAX_TIME and prefs.max_time_minutes is not None and meal.total_time_minutes > prefs.max_time_minutes:
                return False
            if level < RELAX_FREQUENCY and course == "main" and meal_type in MAIN_TYPES:
                if required and required not in meal.categories:
                    return False
                if meal.categories & saturated & quota_categories:
                    return False
            if level < RELAX_REPEAT:
                if uses[meal.meal_id] >= MAX_USES_PER_WEEK or meal.meal_id == previous_id.get(course):
                    return False
                if main is not None and "baklagil" in meal.categories and "baklagil" in main.categories:
                    return False
            return True

        for level in range(0, RELAX_DISLIKE + 1):
            pool = [m for m in pool_all if allowed(m, level)]
            if pool:
                best = max(
                    pool,
                    key=lambda m: scoring.score(
                        m,
                        course=course,
                        meal_type=meal_type,
                        composed=compose,
                        main=main,
                        slot_dishes=slot_dishes,
                        uses=uses,
                        main_category_counts=main_category_counts,
                        previous_id=previous_id.get(course),
                        slot_budget_left=slot_budget_left,
                    )
                    + rng.uniform(0, 0.5),
                )
                return best, level
        return None, 0

    def commit(meal, course, day, meal_type, level):
        nonlocal total_cost
        assignments.append(Assignment(day, meal_type, meal.meal_id, servings, course))
        uses[meal.meal_id] += 1
        previous_id[course] = meal.meal_id
        if level:
            relaxed[(course, level)] += 1
        total_cost += scoring.cost_of(meal) or 0.0
        return scoring.cost_of(meal) or 0.0

    quota_categories = frozenset(quotas)
    for index, (day, meal_type) in enumerate(slots):
        required = required_by_slot.get(index)
        if required and main_category_counts[required] >= quotas[required]:
            required = None
        saturated = {c for c in quotas if main_category_counts[c] >= quotas[c]}

        remaining_slots = len(slots) - index
        budget_left = None if prefs.weekly_budget is None else max(prefs.weekly_budget - total_cost, 0)
        slot_budget = None if budget_left is None else budget_left / remaining_slots
        composed_slot = compose and meal_type in MAIN_TYPES
        main_budget = None if slot_budget is None else slot_budget * (0.65 if composed_slot else 1.0)

        main, level = pick(
            "main", meal_type, required=required, saturated=saturated, main=None, slot_dishes=[],
            slot_budget_left=main_budget, quota_categories=quota_categories,
        )
        if main is None:
            empty[("main", meal_type)] += 1
            continue
        spent = commit(main, "main", day, meal_type, level)
        main_category_counts.update(main.categories)

        if not composed_slot:
            continue

        order = []
        if needs_side(main):
            order.append("side")
        if index in soup_slots:
            order.append("soup")
        order.append("salad")
        dishes = [main]
        for course in order[: MAX_DISHES_PER_MEAL - 1]:
            left = None if slot_budget is None else max(slot_budget - spent, 0)
            extra, level = pick(
                course, meal_type, required=None, saturated=frozenset(), main=main, slot_dishes=dishes,
                slot_budget_left=left, quota_categories=quota_categories,
            )
            if extra is None:
                if course == "soup":
                    empty[("soup", meal_type)] += 1
                continue
            spent += commit(extra, course, day, meal_type, level)
            dishes.append(extra)

    for (course, level), count in sorted(relaxed.items()):
        warnings.append(f"{count} {COURSE_LABELS[course]} için {RELAX_LABELS[level]} (yeterli seçenek yoktu).")
    for (course, meal_type), count in empty.items():
        target = COURSE_LABELS[course] if course != "main" else MEAL_TYPE_LABELS[meal_type]
        warnings.append(f"{count} {target} için uygun yemek bulunamadı.")
    if prefs.weekly_budget is not None and total_cost > prefs.weekly_budget:
        warnings.append(
            f"Tahmini maliyet ({total_cost:.0f}) haftalık bütçeyi ({prefs.weekly_budget:.0f}) aşıyor."
        )
    return GenerationResult(assignments=assignments, warnings=warnings, estimated_total_cost=round(total_cost, 2))


def rank_alternatives(
    candidates: Sequence[MealCandidate],
    prefs: Preferences,
    *,
    course: str,
    meal_type: str,
    current: MealCandidate,
    main: MealCandidate | None = None,
    slot_dishes: Sequence[MealCandidate] = (),
    plan_meals: Sequence[MealCandidate],
    servings: int,
    day_meal_ids: Sequence[Any] = (),
    exclude_ids: Sequence[Any] = (),
    limit: int = 8,
    seed: int | None = None,
) -> list:
    """Planlanmış bir yemek yerine konabilecek yemekleri en uygundan başlayarak sıralar.

    main: aynı öğünün ana yemeği (değiştirilen ana yemek değilse); eşleştirme kuralları için.
    slot_dishes: aynı öğündeki diğer yemekler (değiştirilen hariç), kalori toplamı için.
    plan_meals: haftalık plandaki tüm yemekler (değiştirilen hariç), tekrar puanı için.
    """
    rng = random.Random(seed)
    excluded = set(exclude_ids) | set(day_meal_ids) | {current.meal_id}
    pool_all = [c for c in candidates if c.meal_id not in excluded]
    scoring = _Scoring(candidates, prefs, servings)

    uses = Counter(m.meal_id for m in plan_meals)
    main_category_counts: Counter = Counter()
    for m in plan_meals:
        main_category_counts.update(m.categories)
    if course == "main":
        main = None

    def allowed(meal: MealCandidate, level: int) -> bool:
        if not is_eligible(course, meal_type, meal, allow_soup_main="corba" in current.categories):
            return False
        if level < RELAX_DISLIKE and meal.disliked:
            return False
        if level < RELAX_TIME and prefs.max_time_minutes is not None and meal.total_time_minutes > prefs.max_time_minutes:
            return False
        if level < RELAX_REPEAT and uses[meal.meal_id] >= MAX_USES_PER_WEEK:
            return False
        return True

    pool = []
    for level in range(0, RELAX_DISLIKE + 1):
        pool = [m for m in pool_all if allowed(m, level)]
        if pool:
            break

    composed = course != "main" or len(slot_dishes) > 0
    budget_left = None
    if prefs.weekly_budget is not None:
        budget_left = prefs.weekly_budget / 7

    def rank(meal: MealCandidate) -> float:
        value = scoring.score(
            meal,
            course=course,
            meal_type=meal_type,
            composed=composed,
            main=main,
            slot_dishes=slot_dishes,
            uses=uses,
            main_category_counts=main_category_counts,
            previous_id=None,
            slot_budget_left=budget_left,
        )
        # Haftalık sebze/baklagil hedefi bozulmasın diye aynı kategorideki yemek tercih edilir
        if course == "main":
            value += 1.0 * len(meal.categories & current.categories & frozenset(FREQUENCY_CATEGORIES))
        return value + rng.uniform(0, 0.5)

    return sorted(pool, key=rank, reverse=True)[:limit]
