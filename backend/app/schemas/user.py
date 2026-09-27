from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ProfileUpdate(BaseModel):
    full_name: str | None = Field(None, max_length=100)
    avatar_url: str | None = Field(None, max_length=2048)
    preferred_language: Literal["tr", "en"] | None = None

    @field_validator("full_name")
    @classmethod
    def strip_full_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("Ad soyad boş olamaz")
        return value

    @model_validator(mode="after")
    def reject_null_required_fields(self):
        for name in ("full_name", "preferred_language"):
            if name in self.model_fields_set and getattr(self, name) is None:
                raise ValueError(f"{name} boş bırakılamaz")
        return self


class PreferenceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    daily_calorie_target: int | None = None
    calorie_tolerance_percent: float
    protein_target_grams: float | None = None
    carbohydrate_target_grams: float | None = None
    fat_target_grams: float | None = None
    servings_per_meal: int
    soup_frequency_per_week: int
    vegetable_frequency_per_week: int
    legume_frequency_per_week: int
    max_preparation_time_minutes: int | None = None
    weekly_budget: float | None = None
    currency: str


class PreferenceUpdate(BaseModel):
    daily_calorie_target: int | None = Field(None, ge=500, le=10000)
    calorie_tolerance_percent: float | None = Field(None, ge=0, le=100)
    protein_target_grams: float | None = Field(None, ge=0, le=9999)
    carbohydrate_target_grams: float | None = Field(None, ge=0, le=9999)
    fat_target_grams: float | None = Field(None, ge=0, le=9999)
    servings_per_meal: int | None = Field(None, ge=1, le=20)
    soup_frequency_per_week: int | None = Field(None, ge=0, le=7)
    vegetable_frequency_per_week: int | None = Field(None, ge=0, le=7)
    legume_frequency_per_week: int | None = Field(None, ge=0, le=7)
    max_preparation_time_minutes: int | None = Field(None, ge=1, le=1440)
    weekly_budget: float | None = Field(None, ge=0, le=99999999)
    currency: str | None = Field(None, pattern=r"^[A-Z]{3}$")

    @model_validator(mode="after")
    def reject_null_required_fields(self):
        required = (
            "calorie_tolerance_percent",
            "servings_per_meal",
            "soup_frequency_per_week",
            "vegetable_frequency_per_week",
            "legume_frequency_per_week",
            "currency",
        )
        for name in required:
            if name in self.model_fields_set and getattr(self, name) is None:
                raise ValueError(f"{name} boş bırakılamaz")
        return self
