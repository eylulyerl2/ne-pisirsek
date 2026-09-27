from decimal import Decimal

from sqlalchemy.orm import Session, selectinload

from app.models import Meal, MealIngredient, PlannedMeal, ShoppingItem, ShoppingList, WeeklyPlan
from app.schemas.shopping import ShoppingItemResponse, ShoppingListResponse

_TR_ALPHABET = "abcçdefgğhıijklmnoöprsştuüvyz"
_TR_ORDER = {ch: i for i, ch in enumerate(_TR_ALPHABET)}


def tr_sort_key(text: str) -> list:
    lowered = text.replace("I", "ı").replace("İ", "i").lower()
    return [_TR_ORDER.get(ch, len(_TR_ORDER) + ord(ch)) for ch in lowered]


def load_shopping_list(db: Session, plan: WeeklyPlan) -> ShoppingList | None:
    return (
        db.query(ShoppingList)
        .options(selectinload(ShoppingList.items).selectinload(ShoppingItem.ingredient))
        .filter(ShoppingList.plan_id == plan.plan_id)
        .first()
    )


def shopping_list_response(shopping_list: ShoppingList) -> ShoppingListResponse:
    items = [
        ShoppingItemResponse(
            item_id=item.item_id,
            ingredient_id=item.ingredient_id,
            name=item.ingredient.name,
            quantity=None if item.quantity is None else float(item.quantity),
            unit=item.unit,
            estimated_price=None if item.estimated_price is None else float(item.estimated_price),
            is_checked=item.is_checked,
        )
        for item in shopping_list.items
    ]
    items.sort(key=lambda i: (i.is_checked, tr_sort_key(i.name), i.unit or ""))
    return ShoppingListResponse(
        list_id=shopping_list.list_id, plan_id=shopping_list.plan_id, created_at=shopping_list.created_at, items=items
    )


def rebuild_shopping_list(db: Session, plan: WeeklyPlan) -> ShoppingList | None:
    """Plandaki yemeklerin malzemelerini toplar. Ayni malzeme ve birim tek satirda birlesir,
    daha once isaretlenen satirlar isaretli kalir. Plan bossa None doner."""
    rows = (
        db.query(PlannedMeal.servings, Meal.servings, MealIngredient.ingredient_id, MealIngredient.quantity, MealIngredient.unit)
        .join(Meal, Meal.meal_id == PlannedMeal.meal_id)
        .join(MealIngredient, MealIngredient.meal_id == Meal.meal_id)
        .filter(PlannedMeal.plan_id == plan.plan_id)
        .all()
    )
    if not rows:
        return None

    totals: dict = {}
    for planned_servings, meal_servings, ingredient_id, quantity, unit in rows:
        key = (ingredient_id, unit)
        if quantity is None:
            totals.setdefault(key, None)
            continue
        scaled = Decimal(quantity) * Decimal(planned_servings) / Decimal(max(meal_servings, 1))
        totals[key] = (totals.get(key) or Decimal(0)) + scaled

    shopping_list = db.query(ShoppingList).filter(ShoppingList.plan_id == plan.plan_id).first()
    checked: set = set()
    if shopping_list is None:
        shopping_list = ShoppingList(plan_id=plan.plan_id)
        db.add(shopping_list)
        db.flush()
    else:
        old = db.query(ShoppingItem).filter(ShoppingItem.list_id == shopping_list.list_id).all()
        checked = {(i.ingredient_id, i.unit) for i in old if i.is_checked}
        db.query(ShoppingItem).filter(ShoppingItem.list_id == shopping_list.list_id).delete(synchronize_session=False)

    db.add_all(
        ShoppingItem(
            list_id=shopping_list.list_id,
            ingredient_id=ingredient_id,
            unit=unit,
            quantity=None if total is None else total.quantize(Decimal("0.001")),
            is_checked=(ingredient_id, unit) in checked,
        )
        for (ingredient_id, unit), total in totals.items()
    )
    db.commit()
    return load_shopping_list(db, plan)
