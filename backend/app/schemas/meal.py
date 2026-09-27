import uuid

from pydantic import BaseModel, ConfigDict, computed_field

from app.constants import REGIONS


class CategoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    category_id: uuid.UUID
    name: str
    slug: str


class NutritionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    calories: float | None = None
    protein_grams: float | None = None
    carbohydrate_grams: float | None = None
    fat_grams: float | None = None
    fiber_grams: float | None = None


class IngredientResponse(BaseModel):
    name: str
    quantity: float | None = None
    unit: str | None = None
    is_optional: bool = False


class MealSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    meal_id: uuid.UUID
    name: str
    description: str | None = None
    image_url: str | None = None
    preparation_time_minutes: int | None = None
    cooking_time_minutes: int | None = None
    servings: int
    estimated_cost: float | None = None
    currency: str
    region: str | None = None
    has_recipe: bool = False
    categories: list[CategoryResponse] = []
    nutrition: NutritionResponse | None = None

    @computed_field
    @property
    def total_time_minutes(self) -> int:
        return (self.preparation_time_minutes or 0) + (self.cooking_time_minutes or 0)

    @computed_field
    @property
    def region_name(self) -> str | None:
        return REGIONS.get(self.region) if self.region else None


class RegionResponse(BaseModel):
    slug: str
    name: str


class MealDetail(MealSummary):
    instructions: str | None = None
    source_type: str
    source_url: str | None = None
    ingredients: list[IngredientResponse] = []
    average_rating: float | None = None
    rating_count: int = 0


class MealListResponse(BaseModel):
    items: list[MealSummary]
    total: int
    limit: int
    offset: int
