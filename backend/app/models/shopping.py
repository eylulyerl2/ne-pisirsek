from sqlalchemy import Column, String, Boolean, Numeric, TIMESTAMP, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
from app.database import Base


class ShoppingList(Base):
    __tablename__ = "shopping_lists"

    list_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    plan_id = Column(UUID(as_uuid=True), ForeignKey("weekly_plans.plan_id", ondelete="CASCADE"), nullable=False, unique=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    plan = relationship("WeeklyPlan", back_populates="shopping_list")
    items = relationship("ShoppingItem", back_populates="shopping_list", cascade="all, delete-orphan")


class ShoppingItem(Base):
    __tablename__ = "shopping_items"

    item_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    list_id = Column(UUID(as_uuid=True), ForeignKey("shopping_lists.list_id", ondelete="CASCADE"), nullable=False, index=True)
    ingredient_id = Column(UUID(as_uuid=True), ForeignKey("ingredients.ingredient_id", ondelete="RESTRICT"), nullable=False)
    quantity = Column(Numeric(10, 3))
    unit = Column(String(20))
    estimated_price = Column(Numeric(10, 2))
    is_checked = Column(Boolean, nullable=False, default=False)

    shopping_list = relationship("ShoppingList", back_populates="items")
    ingredient = relationship("Ingredient")
