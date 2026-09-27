from collections import Counter, defaultdict

import pytest

from app.recommendation.engine import (
    MAX_DISHES_PER_MEAL,
    MealCandidate,
    Preferences,
    _Scoring,
    combine_preferences,
    generate_weekly_plan,
    is_eligible,
    needs_side,
    rank_alternatives,
)


def meal(mid, cats, time=30, cost=100.0, cal=300.0, servings=4, personal=(), community=None, region=None, starchy=False):
    return MealCandidate(
        meal_id=mid, name=mid, categories=frozenset(cats), total_time_minutes=time, estimated_cost=cost,
        servings=servings, calories=cal, personal_ratings=tuple(personal), community_rating=community,
        region=region, starchy=starchy,
    )


CATALOG = [
    # ana yemekler
    meal("kuru-fasulye", ["baklagil"]),
    meal("nohut", ["baklagil"]),
    meal("ispanak", ["sebze"]),
    meal("taze-fasulye", ["sebze"]),
    meal("karniyarik", ["sebze", "et"]),
    meal("etli-guvec", ["sebze", "et"]),
    meal("tavuk-sote", ["tavuk"]),
    meal("tavuk-sis", ["tavuk"]),
    meal("kofte", ["et"]),
    meal("tas-kebabi", ["et"]),
    meal("somon", ["balik"]),
    meal("hamsi", ["balik"]),
    meal("makarna", ["pilav-makarna"]),
    meal("manti", ["et", "pilav-makarna", "hamur-isi"]),
    meal("dolma", ["sebze", "et"], starchy=True),
    # çorbalar
    meal("mercimek-corba", ["corba", "baklagil"]),
    meal("ezogelin", ["corba", "baklagil"]),
    meal("domates-corba", ["corba"]),
    meal("tarhana", ["corba"]),
    meal("yayla", ["corba"]),
    # yan yemekler
    meal("pilav", ["pilav-makarna", "yan-yemek"]),
    meal("bulgur", ["pilav-makarna", "yan-yemek"]),
    meal("sehriyeli", ["pilav-makarna", "yan-yemek"]),
    meal("nohutlu-pilav", ["pilav-makarna", "yan-yemek", "baklagil"]),
    meal("misir-ekmegi", ["yan-yemek", "hamur-isi"], region="karadeniz"),
    meal("domatesli-bulgur", ["pilav-makarna", "yan-yemek"]),
    # salatalar
    meal("coban", ["salata"]),
    meal("gavurdagi", ["salata"]),
    meal("cacik", ["salata", "yan-yemek"]),
    meal("borulce-salata", ["salata", "baklagil"]),
    meal("kisir", ["salata"]),
    meal("roka", ["salata"]),
    meal("mevsim", ["salata"]),
    meal("piyaz", ["salata", "baklagil"]),
    # diğer
    meal("menemen", ["kahvalti"]),
    meal("pogaca", ["kahvalti", "hamur-isi"]),
    meal("sutlac", ["tatli"]),
]
BY_ID = {m.meal_id: m for m in CATALOG}


def run(prefs=None, candidates=CATALOG, types=("dinner",), seed=1, servings=2, **kwargs):
    return generate_weekly_plan(candidates, prefs or Preferences(), types, servings, seed, **kwargs)


def by_slot(result):
    slots = defaultdict(list)
    for a in result.assignments:
        slots[(a.day_of_week, a.meal_type)].append(a)
    return slots


def of_course(result, course):
    return [a for a in result.assignments if a.course == course]


def main_category_counts(result):
    counts = Counter()
    for a in of_course(result, "main"):
        counts.update(BY_ID[a.meal_id].categories)
    return counts


# --- Kap düzeni -------------------------------------------------------------

def test_every_slot_has_exactly_one_main_dish():
    result = run(types=("lunch", "dinner"))
    slots = by_slot(result)
    assert set(slots) == {(d, t) for d in range(1, 8) for t in ("lunch", "dinner")}
    for dishes in slots.values():
        assert sum(a.course == "main" for a in dishes) == 1


def test_meals_have_at_most_three_dishes():
    for seed in range(20):
        for dishes in by_slot(run(types=("lunch", "dinner"), seed=seed)).values():
            assert len(dishes) <= MAX_DISHES_PER_MEAL


def test_each_course_uses_the_right_kind_of_dish():
    for seed in range(10):
        for a in run(types=("lunch", "dinner"), seed=seed).assignments:
            categories = BY_ID[a.meal_id].categories
            if a.course == "soup":
                assert "corba" in categories
            elif a.course == "side":
                assert "yan-yemek" in categories and "salata" not in categories
            elif a.course == "salad":
                assert "salata" in categories
            else:
                assert not categories & {"kahvalti", "tatli", "salata", "yan-yemek", "corba"}


def test_soup_is_a_separate_course_not_a_main_dish():
    assert not any("corba" in BY_ID[a.meal_id].categories for a in of_course(run(), "main"))


def test_same_seed_is_deterministic_and_different_seeds_vary():
    ids = lambda r: [(a.day_of_week, a.course, a.meal_id) for a in r.assignments]
    assert ids(run(seed=7)) == ids(run(seed=7))
    assert any(ids(run(seed=s)) != ids(run(seed=7)) for s in range(1, 20))


def test_family_servings_apply_to_every_course():
    assert all(a.servings == 5 for a in run(servings=5).assignments)


# --- Yan yemek kuralları ----------------------------------------------------

def test_needs_side_rules():
    assert needs_side(BY_ID["kuru-fasulye"])
    assert needs_side(BY_ID["tavuk-sote"])
    assert needs_side(BY_ID["kofte"])
    assert needs_side(BY_ID["karniyarik"])
    assert not needs_side(BY_ID["ispanak"])
    assert not needs_side(BY_ID["somon"])
    assert not needs_side(BY_ID["makarna"])
    assert not needs_side(BY_ID["manti"])
    assert not needs_side(BY_ID["dolma"])


def test_mains_that_need_a_side_get_one_and_others_do_not():
    for seed in range(20):
        for dishes in by_slot(run(types=("lunch", "dinner"), seed=seed)).values():
            main = BY_ID[next(a.meal_id for a in dishes if a.course == "main")]
            has_side = any(a.course == "side" for a in dishes)
            assert has_side == needs_side(main), main.name


def test_legume_side_is_not_paired_with_a_legume_main():
    for seed in range(40):
        for dishes in by_slot(run(types=("lunch", "dinner"), seed=seed)).values():
            main = BY_ID[next(a.meal_id for a in dishes if a.course == "main")]
            for a in dishes:
                if a.course in ("side", "salad") and "baklagil" in main.categories:
                    assert "baklagil" not in BY_ID[a.meal_id].categories


def test_regional_side_scores_higher_next_to_a_regional_main():
    scoring = _Scoring(CATALOG, Preferences(), 2)
    main = meal("akcaabat", ["et"], region="karadeniz")
    kwargs = dict(course="side", meal_type="dinner", composed=True, main=main, slot_dishes=[main], uses=Counter(),
                  main_category_counts=Counter(), previous_id=None, slot_budget_left=None)
    assert scoring.score(BY_ID["misir-ekmegi"], **kwargs) > scoring.score(BY_ID["pilav"], **kwargs)
    national = meal("kofte", ["et"], region="turkiye")
    kwargs.update(main=national, slot_dishes=[national])
    assert scoring.score(BY_ID["misir-ekmegi"], **kwargs) == scoring.score(BY_ID["pilav"], **kwargs)


def test_excluded_meals_never_appear():
    for seed in range(20):
        result = run(types=("lunch", "dinner"), seed=seed, exclude_ids=["pilav", "bulgur", "sehriyeli"])
        used = {a.meal_id for a in result.assignments}
        assert not used & {"pilav", "bulgur", "sehriyeli"}
        assert any(a.course == "side" for a in result.assignments)


# --- Çorba ve sıklık hedefleri ---------------------------------------------

def test_soup_days_match_the_soup_frequency():
    for seed in range(20):
        for wanted in (0, 1, 2, 3, 5):
            result = run(Preferences(soup_frequency=wanted), types=("lunch", "dinner"), seed=seed)
            assert len(of_course(result, "soup")) == wanted


def test_soups_are_spread_over_the_week():
    result = run(Preferences(soup_frequency=3), seed=3)
    days = sorted(a.day_of_week for a in of_course(result, "soup"))
    assert len(set(days)) == 3
    assert all(b - a >= 2 for a, b in zip(days, days[1:]))


def test_vegetable_and_legume_targets_apply_to_main_dishes():
    for seed in range(20):
        counts = main_category_counts(run(Preferences(vegetable_frequency=2, legume_frequency=1), seed=seed))
        assert counts["sebze"] == 2
        assert counts["baklagil"] == 1


def test_zero_frequency_excludes_the_category_from_main_dishes():
    for seed in range(10):
        result = run(Preferences(soup_frequency=0, vegetable_frequency=0, legume_frequency=0), seed=seed)
        counts = main_category_counts(result)
        assert counts["sebze"] == counts["baklagil"] == 0
        assert not of_course(result, "soup")


def test_quotas_are_capped_to_available_slots():
    result = run(Preferences(soup_frequency=7, vegetable_frequency=7, legume_frequency=7))
    assert len(of_course(result, "main")) == 7
    assert len(of_course(result, "soup")) == 7


def test_missing_categories_produce_warnings():
    no_soup = [m for m in CATALOG if "corba" not in m.categories]
    assert any("Çorba bulunamadı" in w for w in run(candidates=no_soup).warnings)
    no_veg = [m for m in CATALOG if "sebze" not in m.categories]
    assert any("sebze yemeği" in w for w in run(candidates=no_veg).warnings)


def test_without_sides_or_salads_the_plan_still_works():
    mains_only = [m for m in CATALOG if not m.categories & {"yan-yemek", "salata"}]
    result = run(candidates=mains_only)
    assert len(of_course(result, "main")) == 7
    assert not of_course(result, "side") and not of_course(result, "salad")


# --- Tek kaplı (compose=False) mod ------------------------------------------

def test_single_dish_mode_has_one_dish_per_slot_and_soups_count_as_mains():
    for seed in range(20):
        result = run(Preferences(soup_frequency=2, vegetable_frequency=2, legume_frequency=1), types=("lunch", "dinner"),
                     seed=seed, compose=False)
        assert len(result.assignments) == 14
        assert all(a.course == "main" for a in result.assignments)
        counts = Counter()
        for a in result.assignments:
            counts.update(BY_ID[a.meal_id].categories)
        assert counts["corba"] == 2 and counts["sebze"] == 2


# --- Kısıtlar ve puanlama ---------------------------------------------------

def test_breakfast_and_snack_use_their_own_categories_and_single_dish():
    result = run(types=("breakfast", "snack"))
    for a in result.assignments:
        assert a.course == "main"
        assert ("kahvalti" if a.meal_type == "breakfast" else "tatli") in BY_ID[a.meal_id].categories


def test_no_meal_used_more_than_twice_and_no_back_to_back_mains():
    for seed in range(20):
        result = run(types=("lunch", "dinner"), seed=seed)
        assert max(Counter(a.meal_id for a in result.assignments).values()) <= 2
        mains = [a.meal_id for a in sorted(of_course(result, "main"), key=lambda a: (a.day_of_week, ("lunch", "dinner").index(a.meal_type)))]
        assert all(a != b for a, b in zip(mains, mains[1:]))


def test_time_limit_is_respected_for_every_course():
    slow = {"karniyarik", "kuru-fasulye", "pilav", "tarhana", "coban"}
    catalog = [meal(m.meal_id, m.categories, time=90, region=m.region, starchy=m.starchy) if m.meal_id in slow else m for m in CATALOG]
    result = run(Preferences(max_time_minutes=45), candidates=catalog)
    assert not {a.meal_id for a in result.assignments} & slow
    assert not result.warnings


def test_disliked_meal_is_avoided_in_every_course():
    disliked = {"tavuk-sote", "pilav", "coban", "yayla"}
    catalog = [meal(m.meal_id, m.categories, personal=(1,), region=m.region, starchy=m.starchy) if m.meal_id in disliked else m for m in CATALOG]
    for seed in range(20):
        used = {a.meal_id for a in run(candidates=catalog, types=("lunch", "dinner"), seed=seed).assignments}
        assert not used & disliked


def test_highly_rated_meals_are_preferred():
    catalog = [meal(m.meal_id, m.categories, personal=(5,), region=m.region, starchy=m.starchy) if m.meal_id == "somon" else m for m in CATALOG]
    hits = sum(any(a.meal_id == "somon" for a in run(candidates=catalog, seed=s).assignments) for s in range(20))
    assert hits == 20


def test_budget_steers_towards_cheaper_meals():
    pricey = {"somon", "kofte", "tas-kebabi", "tavuk-sis", "hamsi"}
    catalog = [meal(m.meal_id, m.categories, cost=400.0 if m.meal_id in pricey else 60.0, region=m.region, starchy=m.starchy) for m in CATALOG]
    cheap = run(Preferences(weekly_budget=300), candidates=catalog)
    free = run(Preferences(), candidates=catalog)
    assert cheap.estimated_total_cost < free.estimated_total_cost


def test_over_budget_produces_warning():
    assert any("bütçe" in w for w in run(Preferences(weekly_budget=1)).warnings)


def test_calorie_target_prefers_closer_main_dishes():
    heavy = {"tavuk-sote", "kofte", "somon", "tas-kebabi", "tavuk-sis", "hamsi"}
    catalog = [meal(m.meal_id, m.categories, cal=650.0 if m.meal_id in heavy else 90.0, region=m.region, starchy=m.starchy) for m in CATALOG]
    prefs = Preferences(daily_calorie_target=2000, soup_frequency=0, vegetable_frequency=0, legume_frequency=0)
    mains = [BY_ID[a.meal_id].categories for a in of_course(run(prefs, candidates=catalog), "main")]
    light = [c for c in mains if not c & {"et", "tavuk", "balik"}]
    assert len(light) <= 1


def test_unknown_cost_is_estimated_not_treated_as_free():
    catalog = [meal(m.meal_id, m.categories, cost=None, region=m.region, starchy=m.starchy) for m in CATALOG]
    catalog[0] = meal("kuru-fasulye", ["baklagil"], cost=100.0)
    assert run(candidates=catalog).estimated_total_cost > 100


def test_relaxes_rules_and_warns_when_variety_is_too_low():
    result = run(candidates=[meal("menemen", ["kahvalti"])], types=("breakfast",))
    assert len(result.assignments) == 7
    assert any("esnetildi" in w for w in result.warnings)


def test_reports_slots_that_cannot_be_filled():
    result = run(candidates=[meal("tavuk", ["tavuk"])], types=("breakfast",))
    assert result.assignments == []
    assert any("kahvaltı" in w for w in result.warnings)


# --- Alternatifler ----------------------------------------------------------

def alternatives(course, current, slot_dishes, plan_meals=(), **kwargs):
    return rank_alternatives(
        CATALOG, kwargs.pop("prefs", Preferences()), course=course, meal_type="dinner", current=BY_ID[current],
        main=BY_ID[slot_dishes[0]] if slot_dishes and course != "main" else None,
        slot_dishes=[BY_ID[d] for d in slot_dishes], plan_meals=[BY_ID[m] for m in plan_meals], servings=2, **kwargs,
    )


def test_side_alternatives_are_other_side_dishes():
    result = alternatives("side", "pilav", ["kofte"], limit=10)
    names = [m.meal_id for m in result]
    assert "pilav" not in names
    assert set(names) == {"bulgur", "sehriyeli", "nohutlu-pilav", "misir-ekmegi", "domatesli-bulgur"}


def test_alternatives_skip_meals_already_served_that_day_and_excluded_ones():
    result = alternatives("side", "pilav", ["kofte"], day_meal_ids=["bulgur"], exclude_ids=["sehriyeli"], limit=10)
    assert {m.meal_id for m in result} == {"nohutlu-pilav", "misir-ekmegi", "domatesli-bulgur"}


def test_legume_side_ranks_last_next_to_a_legume_main():
    result = alternatives("side", "pilav", ["kuru-fasulye"], limit=10, seed=1)
    assert result[-1].meal_id == "nohutlu-pilav"


def test_main_alternatives_prefer_the_same_frequency_category():
    tops = Counter()
    for seed in range(30):
        first = alternatives("main", "ispanak", [], seed=seed, limit=3)
        tops.update("sebze" in m.categories for m in first[:1])
    assert tops[True] == 30


def test_main_alternatives_are_never_soups_or_sides():
    for m in alternatives("main", "kofte", ["kofte"], limit=50):
        assert not m.categories & {"corba", "yan-yemek", "salata", "kahvalti", "tatli"}


def test_soup_and_salad_alternatives():
    assert {m.meal_id for m in alternatives("soup", "tarhana", ["kofte"], limit=10)} == {"mercimek-corba", "ezogelin", "domates-corba", "yayla"}
    assert {m.meal_id for m in alternatives("salad", "coban", ["kofte"], limit=10)} == {"gavurdagi", "cacik", "borulce-salata", "kisir", "roka", "mevsim", "piyaz"}


def test_alternatives_respect_dislikes_time_and_limit():
    catalog = [meal("bulgur", ["pilav-makarna", "yan-yemek"], personal=(1,)), *[m for m in CATALOG if m.meal_id != "bulgur"]]
    result = rank_alternatives(catalog, Preferences(), course="side", meal_type="dinner", current=BY_ID["pilav"],
                               main=BY_ID["kofte"], slot_dishes=[BY_ID["kofte"]], plan_meals=[], servings=2, limit=2)
    assert len(result) == 2 and "bulgur" not in [m.meal_id for m in result]


def test_alternatives_penalize_meals_already_used_in_the_plan():
    result = alternatives("side", "pilav", ["kofte"], plan_meals=["bulgur", "bulgur"], limit=10, seed=1)
    assert result[-1].meal_id == "bulgur" or "bulgur" not in [m.meal_id for m in result[:2]]


def test_alternatives_never_include_the_current_meal():
    for course, current in (("main", "kofte"), ("side", "pilav"), ("soup", "tarhana"), ("salad", "coban")):
        assert current not in [m.meal_id for m in alternatives(course, current, ["kofte"], limit=50)]


# --- Uygunluk ve tercihler --------------------------------------------------

def test_eligibility():
    assert is_eligible("main", "dinner", BY_ID["kofte"])
    assert not is_eligible("main", "dinner", BY_ID["tarhana"])
    assert is_eligible("main", "dinner", BY_ID["tarhana"], compose=False)
    assert not is_eligible("main", "dinner", BY_ID["pilav"])
    assert is_eligible("side", "dinner", BY_ID["pilav"])
    assert not is_eligible("side", "dinner", BY_ID["cacik"])
    assert is_eligible("salad", "dinner", BY_ID["cacik"])
    assert is_eligible("main", "breakfast", BY_ID["menemen"])
    assert not is_eligible("soup", "breakfast", BY_ID["tarhana"])


def test_combine_preferences():
    combined = combine_preferences(
        [
            Preferences(daily_calorie_target=1800, max_time_minutes=30, weekly_budget=1000, soup_frequency=2),
            Preferences(daily_calorie_target=2200, max_time_minutes=60, weekly_budget=1500, soup_frequency=3),
            Preferences(daily_calorie_target=None, max_time_minutes=None, weekly_budget=None, soup_frequency=2),
        ]
    )
    assert combined.daily_calorie_target == 2000
    assert combined.max_time_minutes == 30
    assert combined.weekly_budget == 1500
    assert combine_preferences([]) == Preferences()
