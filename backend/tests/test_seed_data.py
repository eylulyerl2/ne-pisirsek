import re
from collections import Counter

import pytest

from app.constants import REGIONS
from app.seed_data import ALL_MEALS
from app.seed_data.ingredients import INGREDIENT_UNITS

CATEGORY_SLUGS = {
    "corba", "sebze", "baklagil", "et", "tavuk", "balik", "pilav-makarna", "salata", "kahvalti", "tatli",
    "yan-yemek", "hamur-isi",
}
IDS = [m["name"] for m in ALL_MEALS]


def test_there_is_a_substantial_catalog():
    assert len(ALL_MEALS) >= 120


def test_names_are_unique():
    duplicates = [n for n, c in Counter(IDS).items() if c > 1]
    assert not duplicates


@pytest.mark.parametrize("meal", ALL_MEALS, ids=IDS)
def test_meal_is_well_formed(meal):
    assert meal["region"] in REGIONS
    assert meal["categories"] and set(meal["categories"]) <= CATEGORY_SLUGS
    assert len(set(meal["categories"])) == len(meal["categories"])
    assert meal["servings"] >= 1
    assert meal["prep"] >= 0 and meal["cook"] >= 0 and meal["prep"] + meal["cook"] > 0 or "salata" in meal["categories"]
    assert meal["cost"] > 0
    assert len(meal["desc"]) >= 15
    assert meal["name"] == meal["name"].strip()

    steps = re.findall(r"^\d+\. ", meal["recipe"], flags=re.M)
    assert len(steps) >= 3, "tarif en az 3 adım içermeli"
    assert [int(s.split(".")[0]) for s in steps] == list(range(1, len(steps) + 1)), "adım numaraları sıralı olmalı"


@pytest.mark.parametrize("meal", ALL_MEALS, ids=IDS)
def test_ingredients_are_known_and_positive(meal):
    names = [name for name, _ in meal["ingredients"]]
    assert names, "malzeme listesi boş"
    assert len(set(names)) == len(names), "aynı malzeme iki kez yazılmış"
    unknown = [n for n in names if n not in INGREDIENT_UNITS]
    assert not unknown, f"sözlükte olmayan malzeme: {unknown}"
    assert all(quantity > 0 for _, quantity in meal["ingredients"])


@pytest.mark.parametrize("meal", ALL_MEALS, ids=IDS)
def test_nutrition_is_plausible_and_consistent(meal):
    kcal, protein, carb, fat, fiber = meal["nutrition"]
    assert 40 <= kcal <= 900
    assert min(protein, carb, fat, fiber) >= 0
    estimated = 4 * protein + 4 * carb + 9 * fat
    assert abs(kcal - estimated) / kcal <= 0.4, f"kalori ({kcal}) makrolarla ({estimated:.0f}) uyuşmuyor"


def test_every_ingredient_in_the_dictionary_is_used():
    used = {name for meal in ALL_MEALS for name, _ in meal["ingredients"]}
    assert not (set(INGREDIENT_UNITS) - used), sorted(set(INGREDIENT_UNITS) - used)


def test_units_are_from_the_expected_set():
    assert set(INGREDIENT_UNITS.values()) <= {"g", "ml", "adet", "yk", "ck", "diş", "demet", "dilim"}


def test_every_category_and_region_has_meals():
    categories = Counter(c for m in ALL_MEALS for c in m["categories"])
    for slug, minimum in {"corba": 10, "baklagil": 8, "sebze": 20, "et": 20, "tavuk": 8, "balik": 8, "tatli": 8,
                          "kahvalti": 5, "salata": 6, "pilav-makarna": 8, "yan-yemek": 4, "hamur-isi": 5}.items():
        assert categories[slug] >= minimum, f"{slug}: {categories[slug]}"
    regions = Counter(m["region"] for m in ALL_MEALS)
    assert set(regions) == set(REGIONS)
    assert all(count >= 3 for count in regions.values()), dict(regions)


def test_side_dishes_are_not_mains():
    for meal in ALL_MEALS:
        if "yan-yemek" in meal["categories"]:
            assert not set(meal["categories"]) & {"et", "tavuk", "balik", "corba", "tatli", "kahvalti"}


def test_no_pork_or_alcohol():
    banned = re.compile(r"\b(domuz|jambon|şarap|rakı|bira|votka|rom|likör)\b", re.I)
    for meal in ALL_MEALS:
        text = " ".join([meal["name"], meal["desc"], meal["recipe"], *[n for n, _ in meal["ingredients"]]])
        assert not banned.search(text), meal["name"]
