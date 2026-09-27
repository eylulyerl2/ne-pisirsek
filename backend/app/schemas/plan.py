import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field, computed_field, field_validator, model_validator

MealType = Literal["breakfast", "lunch", "dinner", "snack"]
Course = Literal["main", "soup", "side", "salad"]
PlanStatus = Literal["draft", "active", "completed", "archived"]

COURSE_NAMES = {"main": "Ana yemek", "soup": "Çorba", "side": "Yan yemek", "salad": "Salata"}
MEAL_TYPE_NAMES = {"breakfast": "Kahvaltı", "lunch": "Öğle yemeği", "dinner": "Akşam yemeği", "snack": "Ara öğün"}


class PlanCreate(BaseModel):
    week_start_date: date
    family_id: uuid.UUID | None = None

    @field_validator("week_start_date")
    @classmethod
    def must_be_monday(cls, value: date) -> date:
        if value.weekday() != 0:
            raise ValueError("Hafta başlangıcı Pazartesi olmalı")
        return value


class PlanStatusUpdate(BaseModel):
    status: PlanStatus


class GenerateRequest(BaseModel):
    meal_types: list[MealType] = Field(default_factory=lambda: ["dinner"], min_length=1)
    seed: int | None = None
    compose: bool = Field(True, description="Açıksa öğün ana yemek + çorba/yan yemek/salata olarak kurulur")
    exclude_meal_ids: list[uuid.UUID] = Field(default_factory=list, max_length=200)


class ReplaceRequest(BaseModel):
    meal_id: uuid.UUID | None = Field(None, description="Boşsa en uygun alternatif otomatik seçilir")
    seed: int | None = None


class PlannedMealCreate(BaseModel):
    meal_id: uuid.UUID
    day_of_week: int = Field(ge=1, le=7)
    meal_type: MealType = "dinner"
    course: Course = "main"
    servings: int | None = Field(None, ge=1, le=50)


class PlannedMealUpdate(BaseModel):
    meal_id: uuid.UUID | None = None
    day_of_week: int | None = Field(None, ge=1, le=7)
    meal_type: MealType | None = None
    servings: int | None = Field(None, ge=1, le=50)
    is_completed: bool | None = None

    @model_validator(mode="after")
    def reject_nulls(self):
        for name in self.model_fields_set:
            if getattr(self, name) is None:
                raise ValueError(f"{name} boş bırakılamaz")
        return self


class MealBrief(BaseModel):
    meal_id: uuid.UUID
    name: str
    image_url: str | None = None
    region: str | None = None
    total_time_minutes: int
    calories_per_serving: float | None = None
    categories: list[str] = []
    has_recipe: bool = False


class AlternativeMeal(MealBrief):
    estimated_cost: float | None = None


class PlannedMealResponse(BaseModel):
    planned_meal_id: uuid.UUID
    day_of_week: int
    meal_type: MealType
    course: Course
    servings: int
    is_completed: bool
    estimated_cost: float | None = None
    meal: MealBrief

    @computed_field
    @property
    def course_name(self) -> str:
        return COURSE_NAMES[self.course]


class MealSlot(BaseModel):
    meal_type: MealType
    dishes: list[PlannedMealResponse]

    @computed_field
    @property
    def meal_type_name(self) -> str:
        return MEAL_TYPE_NAMES[self.meal_type]


class DayPlan(BaseModel):
    day_of_week: int
    meals: list[MealSlot]


class PlanSummary(BaseModel):
    plan_id: uuid.UUID
    user_id: uuid.UUID | None = None
    family_id: uuid.UUID | None = None
    week_start_date: date
    status: PlanStatus
    created_at: datetime | None = None


class PlanDetail(PlanSummary):
    planned_meals: list[PlannedMealResponse]
    days: list[DayPlan] = []
    estimated_total_cost: float | None = None


class GenerateResponse(BaseModel):
    plan: PlanDetail
    warnings: list[str]
