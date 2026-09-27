from sqlalchemy import Column, Numeric, ForeignKey, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.database import Base


class MealNutrition(Base):
    __tablename__ = "meal_nutrition"

    meal_id = Column(UUID(as_uuid=True), ForeignKey("meals.meal_id", ondelete="CASCADE"), primary_key=True)
    calories = Column(Numeric(8, 2))
    protein_grams = Column(Numeric(7, 2))
    carbohydrate_grams = Column(Numeric(7, 2))
    fat_grams = Column(Numeric(7, 2))
    fiber_grams = Column(Numeric(7, 2))
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
