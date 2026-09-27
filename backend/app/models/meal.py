from sqlalchemy import Column, String, Integer, Text, Boolean, Numeric, TIMESTAMP, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
from app.database import Base

class Meal(Base):
    __tablename__ = "meals"
    __table_args__ = (UniqueConstraint("source_type", "external_id", name="uq_meals_source_external"),)

    meal_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    image_url = Column(Text)
    preparation_time_minutes = Column(Integer)
    cooking_time_minutes = Column(Integer)
    servings = Column(Integer, nullable=False, default=1)
    estimated_cost = Column(Numeric(10, 2))
    currency = Column(String(3), nullable=False, default="TRY")
    source_type = Column(String(20), nullable=False, default="external")
    external_id = Column(String(50))
    instructions = Column(Text)
    source_url = Column(Text)
    region = Column(String(30), index=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())

    categories = relationship("Category", secondary="meal_categories", order_by="Category.name")
    ingredients = relationship("MealIngredient", cascade="all, delete-orphan")
    nutrition = relationship("MealNutrition", uselist=False, cascade="all, delete-orphan")

    @property
    def has_recipe(self) -> bool:
        return bool(self.instructions)