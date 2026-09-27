from sqlalchemy import Column, String, Integer, Boolean, Date, TIMESTAMP, ForeignKey, UniqueConstraint, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
from app.database import Base


class WeeklyPlan(Base):
    __tablename__ = "weekly_plans"
    __table_args__ = (
        CheckConstraint(
            "(user_id IS NOT NULL AND family_id IS NULL) OR (user_id IS NULL AND family_id IS NOT NULL)",
            name="ck_weekly_plans_single_owner",
        ),
        CheckConstraint("status IN ('draft', 'active', 'completed', 'archived')", name="ck_weekly_plans_status"),
        UniqueConstraint("user_id", "week_start_date", name="uq_weekly_plans_user_week"),
        UniqueConstraint("family_id", "week_start_date", name="uq_weekly_plans_family_week"),
    )

    plan_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("profiles.user_id", ondelete="CASCADE"), index=True)
    family_id = Column(UUID(as_uuid=True), ForeignKey("families.family_id", ondelete="CASCADE"), index=True)
    week_start_date = Column(Date, nullable=False)
    status = Column(String(20), nullable=False, default="draft")
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())

    planned_meals = relationship("PlannedMeal", back_populates="plan", cascade="all, delete-orphan")
    shopping_list = relationship("ShoppingList", back_populates="plan", uselist=False, cascade="all, delete-orphan")


class PlannedMeal(Base):
    __tablename__ = "planned_meals"
    __table_args__ = (
        CheckConstraint("day_of_week BETWEEN 1 AND 7", name="ck_planned_meals_day_of_week"),
        CheckConstraint("meal_type IN ('breakfast', 'lunch', 'dinner', 'snack')", name="ck_planned_meals_meal_type"),
        CheckConstraint("course IN ('main', 'soup', 'side', 'salad')", name="ck_planned_meals_course"),
    )

    planned_meal_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    plan_id = Column(UUID(as_uuid=True), ForeignKey("weekly_plans.plan_id", ondelete="CASCADE"), nullable=False, index=True)
    meal_id = Column(UUID(as_uuid=True), ForeignKey("meals.meal_id", ondelete="RESTRICT"), nullable=False, index=True)
    day_of_week = Column(Integer, nullable=False)
    meal_type = Column(String(20), nullable=False, default="dinner")
    course = Column(String(20), nullable=False, default="main", server_default="main")
    servings = Column(Integer, nullable=False, default=1)
    is_completed = Column(Boolean, nullable=False, default=False)

    plan = relationship("WeeklyPlan", back_populates="planned_meals")
    meal = relationship("Meal")
