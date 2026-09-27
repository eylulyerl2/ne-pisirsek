import sys
import uuid
from collections import Counter

from app.database import SessionLocal
from app.models import Category, Ingredient, Meal, MealCategory, MealIngredient
from app.services.mealdb import DEFAULT_SERVINGS, SOURCE_TYPE, MealDBBlocked, fetch_all_meals, parse_meal


def main(dry_run: bool) -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    print("TheMealDB'den tarifler çekiliyor (ücretsiz anahtar)...")
    try:
        raw_meals = fetch_all_meals()
    except MealDBBlocked as error:
        print(f"DURDURULDU: {error}")
        print("Veritabanına hiçbir şey yazılmadı.")
        return 2

    parsed, skipped = [], Counter()
    for raw in raw_meals:
        meal, reason = parse_meal(raw)
        if meal is None:
            skipped[reason] += 1
        else:
            parsed.append(meal)
    print(f"{len(raw_meals)} tarif çekildi; {len(parsed)} tanesi uygun. Atlananlar: {dict(skipped)}")
    print("Kategori dağılımı:", dict(Counter(slug for m in parsed for slug in m.category_slugs)))
    if dry_run:
        print("--dry-run: veritabanına yazılmadı.")
        return 0

    db = SessionLocal()
    try:
        categories = {c.slug: c for c in db.query(Category).all()}
        missing = {slug for m in parsed for slug in m.category_slugs} - set(categories)
        if missing:
            print(f"Kategori bulunamadı: {sorted(missing)}. Önce seed.py çalıştırın.")
            return 1

        existing_ids = {
            external_id
            for (external_id,) in db.query(Meal.external_id).filter(Meal.source_type == SOURCE_TYPE)
        }
        ingredients = {i.name: i for i in db.query(Ingredient).all()}

        parsed_ids = {m.external_id for m in parsed}
        stale = (
            db.query(Meal)
            .filter(Meal.source_type == SOURCE_TYPE, Meal.is_active.is_(True), Meal.external_id.notin_(parsed_ids))
            .all()
        )
        for meal in stale:
            meal.is_active = False

        new_meals = [m for m in parsed if m.external_id not in existing_ids]
        meal_ids = {m.external_id: uuid.uuid4() for m in new_meals}
        for meal in new_meals:
            db.add(
                Meal(
                    meal_id=meal_ids[meal.external_id],
                    name=meal.name,
                    image_url=meal.image_url,
                    instructions=meal.instructions,
                    source_url=meal.source_url,
                    servings=DEFAULT_SERVINGS,
                    source_type=SOURCE_TYPE,
                    external_id=meal.external_id,
                )
            )
            for name, _, _ in meal.ingredients:
                if name not in ingredients:
                    ingredients[name] = Ingredient(ingredient_id=uuid.uuid4(), name=name)
                    db.add(ingredients[name])
        db.flush()

        for meal in new_meals:
            meal_id = meal_ids[meal.external_id]
            for slug in meal.category_slugs:
                db.add(MealCategory(meal_id=meal_id, category_id=categories[slug].category_id))
            for name, quantity, unit in meal.ingredients:
                db.add(
                    MealIngredient(
                        meal_id=meal_id, ingredient_id=ingredients[name].ingredient_id, quantity=quantity, unit=unit
                    )
                )
        added = len(new_meals)
        db.commit()
        print(f"Tamam: {added} yeni tarif eklendi, {len(parsed) - added} tanesi zaten vardı, {len(stale)} eski tarif pasife alındı.")
        return 0
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main(dry_run="--dry-run" in sys.argv))
