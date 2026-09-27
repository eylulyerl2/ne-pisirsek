from sqlalchemy import Column, Integer, Text, TIMESTAMP, ForeignKey, UniqueConstraint, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid
from app.database import Base


class MealRating(Base):
    __tablename__ = "meal_ratings"
    __table_args__ = (
        UniqueConstraint("user_id", "meal_id", name="uq_meal_ratings_user_meal"),
        CheckConstraint("rating BETWEEN 1 AND 5", name="ck_meal_ratings_rating"),
    )

    rating_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("profiles.user_id", ondelete="CASCADE"), nullable=False)
    meal_id = Column(UUID(as_uuid=True), ForeignKey("meals.meal_id", ondelete="CASCADE"), nullable=False, index=True)
    rating = Column(Integer, nullable=False)
    comment = Column(Text)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
