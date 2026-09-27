from sqlalchemy import Column, String, Numeric, Boolean, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from app.database import Base


class Ingredient(Base):
    __tablename__ = "ingredients"

    ingredient_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(150), nullable=False, unique=True)
    default_unit = Column(String(20))


class MealIngredient(Base):
    __tablename__ = "meal_ingredients"
    __table_args__ = (
        UniqueConstraint("meal_id", "ingredient_id", name="uq_meal_ingredients_meal_ingredient"),
    )

    meal_ingredient_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    meal_id = Column(UUID(as_uuid=True), ForeignKey("meals.meal_id", ondelete="CASCADE"), nullable=False)
    ingredient_id = Column(UUID(as_uuid=True), ForeignKey("ingredients.ingredient_id", ondelete="RESTRICT"), nullable=False, index=True)
    quantity = Column(Numeric(10, 3))
    unit = Column(String(20))
    is_optional = Column(Boolean, nullable=False, default=False)

    ingredient = relationship("Ingredient")
