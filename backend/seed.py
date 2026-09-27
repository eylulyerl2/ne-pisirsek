import re
import sys
import uuid

from app.database import SessionLocal
from app.models import Category, Ingredient, Meal, MealCategory, MealIngredient, MealNutrition
from app.seed_data import ALL_MEALS
from app.seed_data.ingredients import INGREDIENT_UNITS

SOURCE_TYPE = "seed"
HIDDEN_SOURCES = ("themealdb",)
# Maliyetler yaklaşık TL'dir; fiyatlar değiştikçe tek değerle ölçeklenir.
COST_MULTIPLIER = 1.0

CATEGORIES = [
    ("Çorba", "corba"),
    ("Sebze Yemeği", "sebze"),
    ("Baklagil", "baklagil"),
    ("Et Yemeği", "et"),
    ("Tavuk", "tavuk"),
    ("Balık", "balik"),
    ("Pilav ve Makarna", "pilav-makarna"),
    ("Salata", "salata"),
    ("Kahvaltı", "kahvalti"),
    ("Tatlı", "tatli"),
    ("Yan Yemek", "yan-yemek"),
    ("Hamur İşi", "hamur-isi"),
]

_ASCII = str.maketrans("çğıöşüÇĞİÖŞÜ", "cgiosuCGIOSU")


def slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.translate(_ASCII).lower()).strip("-")


def seed() -> None:
    db = SessionLocal()
    try:
        categories = {}
        for name, slug in CATEGORIES:
            category = db.query(Category).filter_by(slug=slug).first()
            if category is None:
                category = Category(name=name, slug=slug)
                db.add(category)
            else:
                category.name = name
            categories[slug] = category

        ingredients = {i.name: i for i in db.query(Ingredient).all()}
        for name, unit in INGREDIENT_UNITS.items():
            if name not in ingredients:
                ingredients[name] = Ingredient(ingredient_id=uuid.uuid4(), name=name)
                db.add(ingredients[name])
            ingredients[name].default_unit = unit
        db.flush()

        existing = db.query(Meal).filter(Meal.source_type == SOURCE_TYPE).all()
        by_external = {m.external_id: m for m in existing if m.external_id}
        by_name = {m.name: m for m in existing if not m.external_id}

        added, updated, meals = 0, 0, []
        for dish in ALL_MEALS:
            slug = slugify(dish["name"])
            meal = by_external.get(slug) or by_name.get(dish["name"])
            if meal is None:
                meal = Meal(meal_id=uuid.uuid4(), source_type=SOURCE_TYPE)
                db.add(meal)
                added += 1
            else:
                updated += 1
            meal.external_id = slug
            meal.name = dish["name"]
            meal.description = dish["desc"]
            meal.region = dish["region"]
            meal.preparation_time_minutes = dish["prep"]
            meal.cooking_time_minutes = dish["cook"]
            meal.servings = dish["servings"]
            meal.estimated_cost = round(dish["cost"] * COST_MULTIPLIER, 2)
            meal.currency = "TRY"
            meal.instructions = dish["recipe"]
            meal.is_active = True
            meals.append((meal, dish))
        db.flush()

        meal_ids = [m.meal_id for m, _ in meals]
        db.query(MealCategory).filter(MealCategory.meal_id.in_(meal_ids)).delete(synchronize_session=False)
        db.query(MealIngredient).filter(MealIngredient.meal_id.in_(meal_ids)).delete(synchronize_session=False)
        nutrition_by_id = {
            n.meal_id: n for n in db.query(MealNutrition).filter(MealNutrition.meal_id.in_(meal_ids))
        }
        for meal, dish in meals:
            for slug in dish["categories"]:
                db.add(MealCategory(meal_id=meal.meal_id, category_id=categories[slug].category_id))
            for name, quantity in dish["ingredients"]:
                db.add(
                    MealIngredient(
                        meal_id=meal.meal_id,
                        ingredient_id=ingredients[name].ingredient_id,
                        quantity=quantity,
                        unit=INGREDIENT_UNITS[name],
                    )
                )
            kcal, protein, carb, fat, fiber = dish["nutrition"]
            nutrition = nutrition_by_id.get(meal.meal_id) or MealNutrition(meal_id=meal.meal_id)
            nutrition.calories, nutrition.protein_grams = kcal, protein
            nutrition.carbohydrate_grams, nutrition.fat_grams, nutrition.fiber_grams = carb, fat, fiber
            db.add(nutrition)

        current = {m.meal_id for m, _ in meals}
        retired = [m for m in existing if m.meal_id not in current and m.is_active]
        for meal in retired:
            meal.is_active = False
        hidden = (
            db.query(Meal)
            .filter(Meal.source_type.in_(HIDDEN_SOURCES), Meal.is_active.is_(True))
            .update({Meal.is_active: False}, synchronize_session=False)
        )

        db.commit()
        print(
            f"Seed tamam: {len(categories)} kategori, {added} yeni ve {updated} güncellenen yemek, "
            f"{len(retired)} eski seed yemeği ve {hidden} dış kaynak yemeği pasife alındı."
        )
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    seed()
