import re
import time
from dataclasses import dataclass, field
from decimal import Decimal

import httpx

SOURCE_TYPE = "themealdb"
BASE_URL = "https://www.themealdb.com/api/json/v1/1"
DEFAULT_SERVINGS = 4

EXCLUDE_PORK = True
EXCLUDE_ALCOHOL = True


class MealDBBlocked(Exception):
    """API ücret, yetki veya limit engeli gösterdi; içe aktarma durdurulmalı."""


def fetch_all_meals(pause_seconds: float = 0.3) -> list[dict]:
    """Tüm tarifleri harf harf çeker. Ücret/yetki/limit belirtisinde MealDBBlocked fırlatır."""
    import string

    meals: dict[str, dict] = {}
    with httpx.Client(timeout=30) as client:
        for letter in string.ascii_lowercase + string.digits:
            response = client.get(f"{BASE_URL}/search.php", params={"f": letter})
            _raise_if_blocked(response)
            for meal in response.json().get("meals") or []:
                meals[meal["idMeal"]] = meal
            time.sleep(pause_seconds)
    return list(meals.values())


_PAYMENT_HINTS = ("patreon", "premium", "supporter", "subscribe", "upgrade", "payment", "paid")


def _raise_if_blocked(response: httpx.Response) -> None:
    if response.status_code in (401, 402, 403):
        raise MealDBBlocked(f"API erişimi reddetti (HTTP {response.status_code}); ücretli anahtar isteniyor olabilir.")
    if response.status_code == 429:
        raise MealDBBlocked("API istek limitine ulaşıldı (HTTP 429).")
    if response.status_code != 200:
        raise RuntimeError(f"Beklenmeyen API yanıtı: HTTP {response.status_code}")
    try:
        data = response.json()
    except ValueError:
        data = None
    if not isinstance(data, dict) or "meals" not in data:
        body = response.text[:300].lower()
        if any(hint in body for hint in _PAYMENT_HINTS):
            raise MealDBBlocked(f"API ücret/abonelik uyarısı döndürdü: {response.text[:200]!r}")
        raise RuntimeError(f"Beklenmeyen API içeriği: {response.text[:200]!r}")


# --- malzeme adları ---------------------------------------------------------

INGREDIENT_NAMES = {
    "salt": "Tuz", "sea salt": "Tuz",
    "garlic": "Sarımsak", "garlic clove": "Sarımsak", "garlic cloves": "Sarımsak", "garlic powder": "Sarımsak tozu",
    "onion": "Soğan", "onions": "Soğan", "brown onion": "Soğan", "white onion": "Soğan", "yellow onion": "Soğan",
    "red onion": "Kırmızı soğan", "red onions": "Kırmızı soğan",
    "spring onions": "Taze soğan", "spring onion": "Taze soğan", "scallions": "Taze soğan", "green onions": "Taze soğan",
    "butter": "Tereyağı", "unsalted butter": "Tereyağı", "salted butter": "Tereyağı",
    "olive oil": "Zeytinyağı", "extra virgin olive oil": "Zeytinyağı",
    "vegetable oil": "Sıvı yağ", "oil": "Sıvı yağ", "sunflower oil": "Sıvı yağ", "canola oil": "Sıvı yağ",
    "rapeseed oil": "Sıvı yağ", "groundnut oil": "Sıvı yağ",
    "sugar": "Şeker", "caster sugar": "Şeker", "granulated sugar": "Şeker", "white sugar": "Şeker",
    "brown sugar": "Esmer şeker", "light brown soft sugar": "Esmer şeker", "icing sugar": "Pudra şekeri",
    "water": "Su", "cold water": "Su", "hot water": "Su", "warm water": "Su", "boiling water": "Su",
    "milk": "Süt", "whole milk": "Süt", "semi-skimmed milk": "Süt",
    "egg": "Yumurta", "eggs": "Yumurta", "large eggs": "Yumurta", "free-range eggs": "Yumurta",
    "egg yolks": "Yumurta sarısı", "egg yolk": "Yumurta sarısı", "egg white": "Yumurta akı", "egg whites": "Yumurta akı",
    "pepper": "Karabiber", "black pepper": "Karabiber", "ground black pepper": "Karabiber",
    "white pepper": "Beyaz biber", "cayenne pepper": "Acı toz biber",
    "red pepper": "Kırmızı biber", "red bell pepper": "Kırmızı biber", "green pepper": "Yeşil biber",
    "green bell pepper": "Yeşil biber", "yellow pepper": "Sarı biber",
    "red chilli": "Kırmızı acı biber", "chilli": "Acı biber", "green chilli": "Yeşil acı biber",
    "chilli powder": "Acı toz biber", "chili powder": "Acı toz biber", "paprika": "Toz kırmızı biber",
    "smoked paprika": "Füme toz kırmızı biber",
    "parsley": "Maydanoz", "flat-leaf parsley": "Maydanoz", "fresh parsley": "Maydanoz",
    "flour": "Un", "plain flour": "Un", "all purpose flour": "Un", "all-purpose flour": "Un",
    "self-raising flour": "Kabartma tozlu un", "bread flour": "Un", "strong white flour": "Un",
    "potatoes": "Patates", "potato": "Patates", "new potatoes": "Patates", "sweet potato": "Tatlı patates",
    "carrots": "Havuç", "carrot": "Havuç",
    "soy sauce": "Soya sosu", "light soy sauce": "Soya sosu", "dark soy sauce": "Soya sosu",
    "coriander": "Kişniş", "fresh coriander": "Kişniş", "coriander leaves": "Kişniş", "ground coriander": "Kişniş tohumu",
    "baking powder": "Kabartma tozu", "baking soda": "Karbonat", "bicarbonate of soda": "Karbonat",
    "lime": "Misket limonu", "lemon": "Limon", "lemon juice": "Limon suyu", "lime juice": "Misket limonu suyu",
    "ginger": "Zencefil", "fresh ginger": "Zencefil", "ginger paste": "Zencefil",
    "thyme": "Kekik", "dried thyme": "Kekik", "oregano": "Kekik", "dried oregano": "Kekik",
    "tomato puree": "Salça", "tomato paste": "Salça",
    "chicken stock": "Tavuk suyu", "beef stock": "Et suyu", "vegetable stock": "Sebze suyu", "fish stock": "Balık suyu",
    "vanilla extract": "Vanilya", "vanilla": "Vanilya",
    "cinnamon": "Tarçın", "ground cinnamon": "Tarçın", "cinnamon stick": "Tarçın",
    "tomato": "Domates", "tomatoes": "Domates", "chopped tomatoes": "Domates", "tinned tomatoes": "Domates",
    "plum tomatoes": "Domates", "cherry tomatoes": "Domates", "canned tomatoes": "Domates",
    "bay leaf": "Defne yaprağı", "bay leaves": "Defne yaprağı",
    "coconut milk": "Hindistan cevizi sütü",
    "cornstarch": "Mısır nişastası", "cornflour": "Mısır nişastası", "corn flour": "Mısır nişastası",
    "mint": "Nane", "fresh mint": "Nane", "dried mint": "Nane",
    "cumin": "Kimyon", "ground cumin": "Kimyon", "cumin seeds": "Kimyon",
    "fish sauce": "Balık sosu",
    "rice": "Pirinç", "basmati rice": "Pirinç", "long-grain rice": "Pirinç", "white rice": "Pirinç",
    "beef": "Dana eti", "minced beef": "Kıyma", "ground beef": "Kıyma", "beef mince": "Kıyma", "lamb mince": "Kıyma",
    "minced lamb": "Kıyma", "lamb": "Kuzu eti", "lamb shoulder": "Kuzu eti", "lamb leg": "Kuzu eti",
    "double cream": "Krema", "heavy cream": "Krema", "cream": "Krema", "single cream": "Krema",
    "whipping cream": "Krema", "sour cream": "Ekşi krema",
    "celery": "Kereviz sapı", "almonds": "Badem", "flaked almonds": "Badem", "ground almonds": "Badem",
    "walnuts": "Ceviz", "honey": "Bal", "pistachios": "Antep fıstığı",
    "yogurt": "Yoğurt", "yoghurt": "Yoğurt", "natural yoghurt": "Yoğurt", "greek yogurt": "Yoğurt",
    "plain yogurt": "Yoğurt", "natural yogurt": "Yoğurt", "greek yoghurt": "Yoğurt",
    "chickpeas": "Nohut", "tinned chickpeas": "Nohut", "canned chickpeas": "Nohut",
    "red lentils": "Kırmızı mercimek", "lentils": "Mercimek", "green lentils": "Yeşil mercimek",
    "chicken": "Tavuk", "chicken breast": "Tavuk göğsü", "chicken breasts": "Tavuk göğsü",
    "chicken thighs": "Tavuk but", "chicken legs": "Tavuk but",
    "salmon": "Somon", "aubergine": "Patlıcan", "aubergines": "Patlıcan", "courgette": "Kabak", "zucchini": "Kabak",
    "green beans": "Taze fasulye", "pasta": "Makarna", "spaghetti": "Spagetti", "penne": "Makarna",
    "bulgur wheat": "Bulgur", "bulgur": "Bulgur", "couscous": "Kuskus", "tahini": "Tahin",
    "feta": "Beyaz peynir", "feta cheese": "Beyaz peynir", "parmesan": "Parmesan", "cheddar cheese": "Çedar peyniri",
    "mozzarella": "Mozzarella", "lemon zest": "Limon kabuğu", "orange": "Portakal", "orange juice": "Portakal suyu",
    "cucumber": "Salatalık", "spinach": "Ispanak", "mushrooms": "Mantar", "peas": "Bezelye", "cabbage": "Lahana",
    "raisins": "Kuru üzüm", "dates": "Hurma", "breadcrumbs": "Galeta unu", "bread": "Ekmek",
    "yeast": "Maya", "dried yeast": "Maya", "double-cream": "Krema", "fresh dill": "Dereotu", "dill": "Dereotu",
    "cardamom": "Kakule", "turmeric": "Zerdeçal", "nutmeg": "Muskat", "cloves": "Karanfil", "chocolate": "Çikolata",
    "dark chocolate": "Bitter çikolata", "cocoa": "Kakao", "cocoa powder": "Kakao", "sesame seeds": "Susam",
    "rice vermicelli": "Şehriye", "vermicelli": "Şehriye", "pine nuts": "Çam fıstığı", "hazelnuts": "Fındık",
}


def canonical_ingredient(name: str) -> str:
    key = re.sub(r"\s+", " ", name.strip().lower())
    if key in INGREDIENT_NAMES:
        return INGREDIENT_NAMES[key]
    return (key[:1].upper() + key[1:])[:150]


# --- ölçüler ----------------------------------------------------------------

_FRACTIONS = {"½": " 1/2", "¼": " 1/4", "¾": " 3/4", "⅓": " 1/3", "⅔": " 2/3", "⅛": " 1/8"}
_NUMBER = r"\d+\s+\d+/\d+|\d+/\d+|\d+(?:[.,]\d+)?"
_MEASURE_RE = re.compile(rf"^({_NUMBER})(?:\s*(?:-|–|to)\s*({_NUMBER}))?\s*(.*)$")

_UNITS: dict[str, tuple[Decimal, str]] = {}


def _register(names: str, factor: float, unit: str) -> None:
    for name in names.split():
        _UNITS[name] = (Decimal(str(factor)), unit)


_register("g gr gram grams", 1, "g")
_register("kg kilo kilos kilogram kilograms", 1000, "g")
_register("ml mls millilitre millilitres milliliter milliliters", 1, "ml")
_register("cl", 10, "ml")
_register("dl", 100, "ml")
_register("l litre litres liter liters", 1000, "ml")
_register("tsp tsps teaspoon teaspoons tspn ts", 1, "ck")
_register("tbsp tbsps tbs tblsp tbl tbls tb tablespoon tablespoons tblspn", 1, "yk")
_register("cup cups", 1, "su bardağı")
_register("oz ounce ounces", 28.35, "g")
_register("lb lbs pound pounds", 453.6, "g")
_register("pinch pinches dash dashes splash", 1, "tutam")
_register("handful handfuls", 1, "avuç")
_register("bunch bunches", 1, "demet")
_register("clove cloves", 1, "diş")
_register("slice slices", 1, "dilim")
_register("can cans tin tins tinned", 1, "kutu")
_register("sprig sprigs", 1, "dal")
_register("stalk stalks stick sticks", 1, "sap")
_register("packet packets pack packs package", 1, "paket")
_register("jar jars", 1, "kavanoz")
_register("bottle bottles", 1, "şişe")

_QUANTITYLESS = {"pinch", "dash", "splash", "handful", "bunch"}
_MAX_QUANTITY = Decimal("9999999")


def _to_number(text: str) -> Decimal:
    total = Decimal(0)
    for part in text.replace(",", ".").split():
        if "/" in part:
            numerator, denominator = part.split("/")
            if Decimal(denominator) != 0:
                total += Decimal(numerator) / Decimal(denominator)
        else:
            total += Decimal(part)
    return total


def parse_measure(measure: str | None) -> tuple[Decimal | None, str | None]:
    """'1 1/2 cups' -> (1.5, 'su bardağı'). Ayrıştırılamayan ('to taste', boş) için (None, None)."""
    text = (measure or "").strip().lower()
    for char, replacement in _FRACTIONS.items():
        text = text.replace(char, replacement)
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return None, None

    match = _MEASURE_RE.match(text)
    if match is None:
        first = re.match(r"[a-zçğıöşü]+", text)
        if first and first.group(0) in _QUANTITYLESS:
            return Decimal(1), _UNITS[first.group(0)][1]
        return None, None

    low, high, rest = match.groups()
    quantity = _to_number(high or low)
    word = re.match(r"[a-zçğıöşü]+", rest)
    factor, unit = _UNITS.get(word.group(0), (Decimal(1), "adet")) if word else (Decimal(1), "adet")
    quantity = (quantity * factor).quantize(Decimal("0.001"))
    if unit == "g" and factor != 1:
        quantity = quantity.quantize(Decimal("1"))
    if quantity <= 0 or quantity > _MAX_QUANTITY:
        return None, None
    return quantity, unit


# --- kategori ve filtre kuralları -------------------------------------------

CATEGORY_BY_SOURCE = {
    "Beef": "et", "Lamb": "et", "Goat": "et", "Chicken": "tavuk", "Seafood": "balik",
    "Pasta": "pilav-makarna", "Vegetarian": "sebze", "Vegan": "sebze", "Dessert": "tatli", "Breakfast": "kahvalti",
}
_SOUP = re.compile(r"\b(soup|chowder|bisque|chorba|corba|broth)\b", re.I)
_SALAD = re.compile(r"\bsalad\b", re.I)
_RICE_PASTA = re.compile(r"\b(rice|pilaf|pilau|risotto|couscous|noodles?|spaghetti|pasta|lasagne|macaroni|biryani)\b", re.I)
_LEGUME = re.compile(
    r"\b(lentils?|chickpeas?|garbanzo|kidney beans?|black beans?|white beans?|haricot|cannellini|borlotti|"
    r"butter beans?|broad beans?|fava|pinto|black-eyed|split peas?|dal|dhal)\b",
    re.I,
)
_NOT_A_LEGUME_PRODUCT = re.compile(r"sauce|paste|vinegar|oil|flour", re.I)
_PORK = re.compile(
    r"\b(pork|bacon|ham|prosciutto|pancetta|chorizo|lard|lardons?|sausages?|gammon|pepperoni|salami|guanciale)\b", re.I
)
_ALCOHOL = re.compile(
    r"\b(wine|beer|rum|brandy|vodka|whisky|whiskey|sake|sherry|marsala|gin|bourbon|stout|lager|ale|kirsch|"
    r"cognac|amaretto|liqueur|mirin|champagne|prosecco|vermouth|tequila|cider)\b",
    re.I,
)
_NOT_ALCOHOL = re.compile(r"vinegar|jelly|non-alcoholic", re.I)
_NOT_A_MEAL = re.compile(
    r"\b(sauce|oil|bread|breads|dip|dressing|chutney|relish|jam|gravy|paste|stock|seasoning|marinade|"
    r"puddings|dough|batter|syrup|spread)\s*$",
    re.I,
)
_HEAD_SPLIT = re.compile(r"\s+(?:with|in|and|on|over|for)\s+|\s+&\s+", re.I)


def _is_not_a_meal(title: str) -> bool:
    """Adın ana kısmı (with/in öncesi) sos, ekmek, yağ gibi bir şeyse yemek sayılmaz.
    'Chicken in Orange Sauce' yemektir, 'Creamy green sauce' değildir."""
    title = re.sub(r"\s+recipe\b", "", title, flags=re.I)
    parts = [re.sub(r"\s*\([^)]*\)", "", title)] + re.findall(r"\(([^)]*)\)", title)
    return any(_NOT_A_MEAL.search(_HEAD_SPLIT.split(part.strip(), maxsplit=1)[0]) for part in parts)


@dataclass
class ParsedMeal:
    external_id: str
    name: str
    image_url: str | None
    instructions: str | None
    source_url: str | None
    category_slugs: set = field(default_factory=set)
    ingredients: list = field(default_factory=list)  # [(ad, miktar, birim)]


def _raw_ingredients(meal: dict) -> list[tuple[str, str]]:
    result = []
    for i in range(1, 21):
        name = (meal.get(f"strIngredient{i}") or "").strip()
        if name:
            result.append((name, (meal.get(f"strMeasure{i}") or "").strip()))
    return result


def exclusion_reason(meal: dict) -> str | None:
    raw = _raw_ingredients(meal)
    name = meal.get("strMeal") or ""
    if not raw:
        return "malzeme yok"
    if EXCLUDE_PORK and (meal.get("strCategory") == "Pork" or _PORK.search(name) or any(_PORK.search(n) for n, _ in raw)):
        return "domuz"
    if EXCLUDE_ALCOHOL and any(_ALCOHOL.search(n) and not _NOT_ALCOHOL.search(n) for n, _ in raw):
        return "alkol"
    return None


def map_categories(meal: dict) -> set[str] | None:
    """Kaynak yemeği bizim kategori slug'larına eşler; içe aktarılmaması gerekiyorsa None döner."""
    source_category = meal.get("strCategory")
    name = meal.get("strMeal") or ""
    slugs: set[str] = set()
    if source_category in CATEGORY_BY_SOURCE:
        slugs.add(CATEGORY_BY_SOURCE[source_category])
    if source_category in ("Dessert", "Breakfast"):
        return slugs

    if _SOUP.search(name):
        slugs.add("corba")
    if _SALAD.search(name):
        slugs.add("salata")
    if _RICE_PASTA.search(name):
        slugs.add("pilav-makarna")
    if any(_LEGUME.search(n) and not _NOT_A_LEGUME_PRODUCT.search(n) for n, _ in _raw_ingredients(meal)):
        slugs.add("baklagil")

    if source_category in ("Side", "Starter") and not (slugs & {"corba", "salata"}):
        return None
    return slugs


def parse_meal(meal: dict) -> tuple[ParsedMeal | None, str | None]:
    """(ParsedMeal, None) ya da (None, atlama nedeni) döner."""
    reason = exclusion_reason(meal)
    if reason:
        return None, reason
    slugs = map_categories(meal)
    if slugs is None:
        return None, "yan yemek/başlangıç"
    if not (slugs & {"tatli", "kahvalti"}) and _is_not_a_meal(meal["strMeal"] or ""):
        return None, "yemek değil (sos/ekmek/yağ)"

    merged: dict[str, tuple[Decimal | None, str | None]] = {}
    for raw_name, measure in _raw_ingredients(meal):
        name = canonical_ingredient(raw_name)
        quantity, unit = parse_measure(measure)
        if name not in merged:
            merged[name] = (quantity, unit)
            continue
        old_quantity, old_unit = merged[name]
        if old_unit == unit and quantity is not None and old_quantity is not None:
            merged[name] = (old_quantity + quantity, unit)

    instructions = (meal.get("strInstructions") or "").replace("\r\n", "\n").strip() or None
    return (
        ParsedMeal(
            external_id=meal["idMeal"],
            name=(meal["strMeal"] or "").strip()[:200],
            image_url=meal.get("strMealThumb") or None,
            instructions=instructions,
            source_url=meal.get("strSource") or None,
            category_slugs=slugs,
            ingredients=[(n, q, u) for n, (q, u) in merged.items()],
        ),
        None,
    )
