from decimal import Decimal

import httpx
import pytest

from app.services import mealdb
from app.services.mealdb import MealDBBlocked, canonical_ingredient, map_categories, parse_meal, parse_measure


@pytest.mark.parametrize(
    "text, expected",
    [
        ("1 tsp", (Decimal("1"), "ck")),
        ("2 tablespoons", (Decimal("2"), "yk")),
        ("3  tablespoons", (Decimal("3"), "yk")),
        ("2 tblsp", (Decimal("2"), "yk")),
        ("1 cup", (Decimal("1"), "su bardağı")),
        ("1 1/2 cups", (Decimal("1.5"), "su bardağı")),
        ("1/2 tsp", (Decimal("0.5"), "ck")),
        ("½ cup", (Decimal("0.5"), "su bardağı")),
        ("1½ cups", (Decimal("1.5"), "su bardağı")),
        ("100g", (Decimal("100"), "g")),
        ("1.5kg", (Decimal("1500"), "g")),
        ("150ml", (Decimal("150"), "ml")),
        ("1 lb", (Decimal("454"), "g")),
        ("8 oz", (Decimal("227"), "g")),
        ("2", (Decimal("2"), "adet")),
        ("1 large", (Decimal("1"), "adet")),
        ("1 chopped", (Decimal("1"), "adet")),
        ("2 cloves minced", (Decimal("2"), "diş")),
        ("2-3 tbsp", (Decimal("3"), "yk")),
        ("Pinch", (Decimal("1"), "tutam")),
        ("pinch", (Decimal("1"), "tutam")),
        ("Handful", (Decimal("1"), "avuç")),
        ("Bunch", (Decimal("1"), "demet")),
        ("To taste", (None, None)),
        ("Garnish", (None, None)),
        ("For frying", (None, None)),
        ("", (None, None)),
        (None, (None, None)),
        ("0", (None, None)),
    ],
)
def test_parse_measure(text, expected):
    assert parse_measure(text) == expected


def test_canonical_ingredient_maps_common_names_and_merges_variants():
    assert canonical_ingredient("Onions") == canonical_ingredient("onion") == "Soğan"
    assert canonical_ingredient("  Olive  Oil ") == "Zeytinyağı"
    assert canonical_ingredient("Kaffir lime leaves") == "Kaffir lime leaves"


def meal(name, category, ingredients, area="British", meal_id="1"):
    data = {"idMeal": meal_id, "strMeal": name, "strCategory": category, "strArea": area, "strInstructions": "a\r\nb"}
    for i, ingredient in enumerate(ingredients, start=1):
        if isinstance(ingredient, tuple):
            data[f"strIngredient{i}"], data[f"strMeasure{i}"] = ingredient
        else:
            data[f"strIngredient{i}"], data[f"strMeasure{i}"] = ingredient, "1"
    return data


def test_pork_and_alcohol_are_excluded():
    assert parse_meal(meal("Roast", "Pork", ["Pork"]))[1] == "domuz"
    assert parse_meal(meal("Pasta", "Pasta", ["Spaghetti", "Bacon"]))[1] == "domuz"
    assert parse_meal(meal("Stew", "Beef", ["Beef", "Red Wine"]))[1] == "alkol"
    assert parse_meal(meal("Cake", "Dessert", ["Flour", "Dark Rum"]))[1] == "alkol"
    assert parse_meal(meal("Burger", "Beef", ["Beef", "Hamburger buns"]))[1] is None


def test_vinegar_and_graham_are_not_flagged():
    assert parse_meal(meal("Salad", "Vegetarian", ["Red Wine Vinegar", "Tomato"]))[1] is None
    assert parse_meal(meal("Pie", "Dessert", ["Graham crackers", "Butter"]))[1] is None
    assert parse_meal(meal("Ginger cake", "Dessert", ["Ginger", "Flour"]))[1] is None


def test_category_mapping():
    assert map_categories(meal("Kebab", "Lamb", ["Lamb"])) == {"et"}
    assert map_categories(meal("Corba", "Side", ["Red Lentils", "Onion"])) == {"corba", "baklagil"}
    assert map_categories(meal("Creamy Tomato Soup", "Vegetarian", ["Tomato"])) == {"sebze", "corba"}
    assert map_categories(meal("Aubergine couscous salad", "Side", ["Couscous"])) == {"salata", "pilav-makarna"}
    assert map_categories(meal("Chickpea curry", "Vegan", ["Chickpeas", "Coconut milk"])) == {"sebze", "baklagil"}
    assert map_categories(meal("Rice pudding", "Dessert", ["Rice", "Milk"])) == {"tatli"}
    assert map_categories(meal("Black bean noodles", "Chicken", ["Black bean sauce", "Noodles"])) == {"tavuk", "pilav-makarna"}


def test_sides_and_starters_that_are_not_soup_or_salad_are_skipped():
    assert parse_meal(meal("Hummus", "Side", ["Chickpeas", "Tahini"]))[1] == "yan yemek/başlangıç"
    assert parse_meal(meal("Mushroom soup", "Starter", ["Mushrooms"]))[0] is not None


def test_parse_meal_merges_duplicate_ingredients_and_cleans_text():
    parsed, reason = parse_meal(
        meal("Curry", "Chicken", [("Onion", "1"), ("Onions", "2"), ("Salt", "1 tsp"), ("Salt", "2 tsp"), ("Water", "To taste")])
    )
    assert reason is None
    by_name = {n: (q, u) for n, q, u in parsed.ingredients}
    assert by_name["Soğan"] == (Decimal("3"), "adet")
    assert by_name["Tuz"] == (Decimal("3"), "ck")
    assert by_name["Su"] == (None, None)
    assert parsed.instructions == "a\nb"


def response(status, body=None, text=None):
    request = httpx.Request("GET", "https://example.test")
    if body is not None:
        return httpx.Response(status, json=body, request=request)
    return httpx.Response(status, text=text or "", request=request)


@pytest.mark.parametrize("status", [401, 402, 403, 429])
def test_blocked_statuses_stop_the_import(status):
    with pytest.raises(MealDBBlocked):
        mealdb._raise_if_blocked(response(status, text="nope"))


def test_payment_message_in_body_stops_the_import():
    with pytest.raises(MealDBBlocked):
        mealdb._raise_if_blocked(response(200, text="Please become a Patreon supporter to use this endpoint"))
    with pytest.raises(MealDBBlocked):
        mealdb._raise_if_blocked(response(200, body={"error": "premium key required"}))


def test_normal_responses_pass_and_unknown_errors_are_not_called_payment():
    mealdb._raise_if_blocked(response(200, body={"meals": None}))
    mealdb._raise_if_blocked(response(200, body={"meals": [{"idMeal": "1"}]}))
    with pytest.raises(RuntimeError):
        mealdb._raise_if_blocked(response(500, text="oops"))
    with pytest.raises(RuntimeError):
        mealdb._raise_if_blocked(response(200, text="<html>maintenance</html>"))


@pytest.mark.parametrize(
    "name, category",
    [
        ("Achiote Oil (Aceite Achiotado) Recipe", "Vegetarian"),
        ("Ají de Aguacate Recipe (Colombian Spicy Avocado Sauce)", "Vegetarian"),
        ("Syrian Bread", "Vegetarian"),
        ("Yorkshire Puddings", "Vegetarian"),
        ("Peanut sauce", "Miscellaneous"),
    ],
)
def test_sauces_breads_and_oils_are_not_imported_as_meals(name, category):
    assert parse_meal(meal(name, category, ["Flour", "Water"]))[1] == "yemek değil (sos/ekmek/yağ)"


@pytest.mark.parametrize(
    "name, category",
    [
        ("Chicken with peanut sauce and rice", "Chicken"),
        ("Chicken in Orange Sauce Recipe (Pollo a la Naranja)", "Chicken"),
        ("Prawns with Romesco sauce", "Seafood"),
        ("Falafel Pita Sandwich with Tahini Sauce", "Vegetarian"),
        ("Camaro Grelhado Com Molho Cru (Grilled Prawns with Green Onion Sauce)", "Seafood"),
        ("Fasoliyyeh Bi Z-Zayt (Syrian Green Beans with Olive Oil)", "Vegetarian"),
        ("Griddled aubergines with sesame dressing", "Vegetarian"),
        ("Spanish Tortilla", "Vegetarian"),
        ("Pollo en Salsa", "Chicken"),
        ("Macaroni Pudding", "Pasta"),
        ("Rice pudding", "Dessert"),
        ("Bread and butter pudding", "Dessert"),
        ("Pancakes with syrup", "Breakfast"),
        ("Pizza Express Margherita", "Vegetarian"),
    ],
)
def test_real_meals_are_kept(name, category):
    assert parse_meal(meal(name, category, ["Flour", "Water"]))[0] is not None
