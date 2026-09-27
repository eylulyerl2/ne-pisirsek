import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class RatingUpsert(BaseModel):
    rating: int = Field(ge=1, le=5)
    comment: str | None = Field(None, max_length=1000)

    @field_validator("comment")
    @classmethod
    def blank_comment_to_none(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip() or None


class RatingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    rating_id: uuid.UUID
    meal_id: uuid.UUID
    rating: int
    comment: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class MyRatingResponse(RatingResponse):
    meal_name: str
