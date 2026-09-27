import uuid
from collections import defaultdict

from sqlalchemy import func
from sqlalchemy.orm import Session, selectinload

from app.models import FamilyMember, Meal, MealIngredient, MealRating, PlannedMeal, UserPreference, WeeklyPlan
from app.recommendation.engine import (
    COURSE_ORDER,
    MEAL_TYPE_ORDER,
    GenerationResult,
    MealCandidate,
    Preferences,
    combine_preferences,
    generate_weekly_plan,
    rank_alternatives,
)
from app.schemas.plan import AlternativeMeal, DayPlan, MealBrief, MealSlot, PlanDetail, PlannedMealResponse

DEFAULT_SERVINGS = 2

STARCHY_INGREDIENTS = frozenset({"Lavaş", "Pide hamuru", "Yufka", "Makarna", "Spagetti"})
STARCHY_IF_LARGE = {"Pirinç": 50, "Bulgur": 50, "İnce bulgur": 50}


def owner_user_ids(db: Session, plan: WeeklyPlan) -> list[uuid.UUID]:
    if plan.user_id is not None:
        return [plan.user_id]
    rows = db.query(FamilyMember.user_id).filter(FamilyMember.family_id == plan.family_id).all()
    return [user_id for (user_id,) in rows]


def default_servings(db: Session, plan: WeeklyPlan) -> int:
    if plan.user_id is None:
        return max(len(owner_user_ids(db, plan)), 1)
    prefs = db.query(UserPreference).filter(UserPreference.user_id == plan.user_id).first()
    return prefs.servings_per_meal if prefs else DEFAULT_SERVINGS


def _to_float(value) -> float | None:
    return None if value is None else float(value)


def _preferences_for(db: Session, user_ids: list[uuid.UUID]) -> Preferences:
    rows = db.query(UserPreference).filter(UserPreference.user_id.in_(user_ids)).all()
    return combine_preferences(
        [
            Preferences(
                daily_calorie_target=row.daily_calorie_target,
                calorie_tolerance_percent=_to_float(row.calorie_tolerance_percent) or 10.0,
                max_time_minutes=row.max_preparation_time_minutes,
                weekly_budget=_to_float(row.weekly_budget),
                soup_frequency=row.soup_frequency_per_week,
                vegetable_frequency=row.vegetable_frequency_per_week,
                legume_frequency=row.legume_frequency_per_week,
            )
            for row in rows
        ]
    )


def _is_starchy(meal: Meal, slugs: set) -> bool:
    if slugs & {"pilav-makarna", "hamur-isi"}:
        return True
    for item in meal.ingredients:
        name = item.ingredient.name
        if name in STARCHY_INGREDIENTS:
            return True
        if name in STARCHY_IF_LARGE and item.quantity is not None and float(item.quantity) >= STARCHY_IF_LARGE[name]:
            return True
    return False


def _load_all_candidates(db: Session, user_ids: list[uuid.UUID]) -> list[tuple[MealCandidate, bool]]:
    """Tüm yemekleri (aktif/pasif) aday olarak döndürür; pasifler yalnızca eski planları çözmek içindir."""
    meals = (
        db.query(Meal)
        .options(
            selectinload(Meal.categories),
            selectinload(Meal.nutrition),
            selectinload(Meal.ingredients).selectinload(MealIngredient.ingredient),
        )
        .all()
    )
    community = {
        meal_id: float(avg)
        for meal_id, avg in db.query(MealRating.meal_id, func.avg(MealRating.rating)).group_by(MealRating.meal_id)
    }
    personal: dict = defaultdict(list)
    for meal_id, rating in db.query(MealRating.meal_id, MealRating.rating).filter(MealRating.user_id.in_(user_ids)):
        personal[meal_id].append(rating)

    result = []
    for m in meals:
        slugs = {c.slug for c in m.categories}
        result.append(
            (
                MealCandidate(
                    meal_id=m.meal_id,
                    name=m.name,
                    categories=frozenset(slugs),
                    total_time_minutes=(m.preparation_time_minutes or 0) + (m.cooking_time_minutes or 0),
                    estimated_cost=_to_float(m.estimated_cost),
                    servings=m.servings,
                    calories=_to_float(m.nutrition.calories) if m.nutrition else None,
                    personal_ratings=tuple(personal.get(m.meal_id, ())),
                    community_rating=community.get(m.meal_id),
                    region=m.region,
                    starchy=_is_starchy(m, slugs),
                ),
                m.is_active,
            )
        )
    return result


def generate_plan_meals(
    db: Session,
    plan: WeeklyPlan,
    meal_types: list[str],
    seed: int | None,
    compose: bool = True,
    exclude_ids: list[uuid.UUID] | None = None,
) -> GenerationResult:
    """Plani yeniden uretir; mevcut planlanmis yemekler silinir."""
    user_ids = owner_user_ids(db, plan)
    result = generate_weekly_plan(
        candidates=[c for c, active in _load_all_candidates(db, user_ids) if active],
        prefs=_preferences_for(db, user_ids),
        meal_types=meal_types,
        servings=default_servings(db, plan),
        seed=seed,
        compose=compose,
        exclude_ids=exclude_ids or [],
    )
    db.query(PlannedMeal).filter(PlannedMeal.plan_id == plan.plan_id).delete(synchronize_session=False)
    db.add_all(
        PlannedMeal(
            plan_id=plan.plan_id,
            meal_id=a.meal_id,
            day_of_week=a.day_of_week,
            meal_type=a.meal_type,
            course=a.course,
            servings=a.servings,
        )
        for a in result.assignments
    )
    db.commit()
    return result


def _brief(meal: Meal) -> MealBrief:
    return MealBrief(
        meal_id=meal.meal_id,
        name=meal.name,
        image_url=meal.image_url,
        region=meal.region,
        total_time_minutes=(meal.preparation_time_minutes or 0) + (meal.cooking_time_minutes or 0),
        calories_per_serving=_to_float(meal.nutrition.calories) if meal.nutrition else None,
        categories=[c.slug for c in meal.categories],
        has_recipe=meal.has_recipe,
    )


def _scaled_cost(meal: Meal, servings: int) -> float | None:
    if meal.estimated_cost is None:
        return None
    return round(float(meal.estimated_cost) * servings / max(meal.servings, 1), 2)


def planned_meal_response(planned: PlannedMeal) -> PlannedMealResponse:
    return PlannedMealResponse(
        planned_meal_id=planned.planned_meal_id,
        day_of_week=planned.day_of_week,
        meal_type=planned.meal_type,
        course=planned.course,
        servings=planned.servings,
        is_completed=planned.is_completed,
        estimated_cost=_scaled_cost(planned.meal, planned.servings),
        meal=_brief(planned.meal),
    )


def plan_detail(db: Session, plan: WeeklyPlan) -> PlanDetail:
    rows = (
        db.query(PlannedMeal)
        .options(
            selectinload(PlannedMeal.meal).selectinload(Meal.categories),
            selectinload(PlannedMeal.meal).selectinload(Meal.nutrition),
        )
        .filter(PlannedMeal.plan_id == plan.plan_id)
        .all()
    )
    rows.sort(key=lambda p: (p.day_of_week, MEAL_TYPE_ORDER.index(p.meal_type), COURSE_ORDER.index(p.course), p.meal.name))
    items = [planned_meal_response(p) for p in rows]

    days: dict = {}
    for item in items:
        slots = days.setdefault(item.day_of_week, {})
        slots.setdefault(item.meal_type, []).append(item)
    day_plans = [
        DayPlan(day_of_week=day, meals=[MealSlot(meal_type=t, dishes=dishes) for t, dishes in slots.items()])
        for day, slots in sorted(days.items())
    ]

    costs = [i.estimated_cost for i in items if i.estimated_cost is not None]
    return PlanDetail(
        plan_id=plan.plan_id,
        user_id=plan.user_id,
        family_id=plan.family_id,
        week_start_date=plan.week_start_date,
        status=plan.status,
        created_at=plan.created_at,
        planned_meals=items,
        days=day_plans,
        estimated_total_cost=round(sum(costs), 2) if costs else None,
    )


def suggest_alternatives(
    db: Session, plan: WeeklyPlan, planned: PlannedMeal, limit: int = 6, seed: int | None = None
) -> list[AlternativeMeal]:
    """Planlanan yemeğin yerine konabilecek yemekleri, aynı öğün ve haftalık plan bağlamında sıralar."""
    user_ids = owner_user_ids(db, plan)
    everything = _load_all_candidates(db, user_ids)
    by_id = {c.meal_id: c for c, _ in everything}
    active = [c for c, is_active in everything if is_active]

    others = [
        p for p in db.query(PlannedMeal).filter(PlannedMeal.plan_id == plan.plan_id).all()
        if p.planned_meal_id != planned.planned_meal_id
    ]
    same_slot = [p for p in others if p.day_of_week == planned.day_of_week and p.meal_type == planned.meal_type]
    main = next((by_id[p.meal_id] for p in same_slot if p.course == "main"), None)

    ranked = rank_alternatives(
        active,
        _preferences_for(db, user_ids),
        course=planned.course,
        meal_type=planned.meal_type,
        current=by_id[planned.meal_id],
        main=main,
        slot_dishes=[by_id[p.meal_id] for p in same_slot],
        plan_meals=[by_id[p.meal_id] for p in others],
        servings=planned.servings,
        day_meal_ids=[p.meal_id for p in others if p.day_of_week == planned.day_of_week],
        limit=limit,
        seed=seed,
    )
    if not ranked:
        return []
    meals = {
        m.meal_id: m
        for m in db.query(Meal)
        .options(selectinload(Meal.categories), selectinload(Meal.nutrition))
        .filter(Meal.meal_id.in_([c.meal_id for c in ranked]))
    }
    return [
        AlternativeMeal(**_brief(meals[c.meal_id]).model_dump(), estimated_cost=_scaled_cost(meals[c.meal_id], planned.servings))
        for c in ranked
    ]
