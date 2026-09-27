from sqlalchemy import Column, String, Integer, Text, Boolean, Numeric, TIMESTAMP, DATE, ForeignKey, UniqueConstraint, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
from app.database import Base

class Profile(Base):
    __tablename__ = "profiles"
    __table_args__ = (
        CheckConstraint("email IS NOT NULL OR username IS NOT NULL", name="ck_profiles_login_identifier"),
    )

    user_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, index=True)
    username = Column(String(30), unique=True, index=True)
    created_via_family_id = Column(
        UUID(as_uuid=True), ForeignKey("families.family_id", ondelete="SET NULL", use_alter=True, name="fk_profiles_created_via_family")
    )
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(100), nullable=False)
    avatar_url = Column(Text)
    preferred_language = Column(String(10), nullable=False, default="tr")
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())


class UserPreference(Base):
    __tablename__ = "user_preferences"

    preference_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("profiles.user_id", ondelete="CASCADE"), nullable=False, unique=True)
    daily_calorie_target = Column(Integer)
    calorie_tolerance_percent = Column(Numeric(5, 2), default=10.00)
    protein_target_grams = Column(Numeric(7, 2))
    carbohydrate_target_grams = Column(Numeric(7, 2))
    fat_target_grams = Column(Numeric(7, 2))
    servings_per_meal = Column(Integer, nullable=False, default=2)
    soup_frequency_per_week = Column(Integer, nullable=False, default=2)
    vegetable_frequency_per_week = Column(Integer, nullable=False, default=2)
    legume_frequency_per_week = Column(Integer, nullable=False, default=1)
    max_preparation_time_minutes = Column(Integer)
    weekly_budget = Column(Numeric(10, 2))
    currency = Column(String(3), nullable=False, default="TRY")
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())

class PasswordReset(Base):
    __tablename__ = "password_resets"
    __table_args__ = (
        CheckConstraint("status IN ('pending', 'used', 'locked', 'expired')", name="ck_password_resets_status"),
    )

    reset_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("profiles.user_id", ondelete="CASCADE"), nullable=False, index=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("profiles.user_id", ondelete="SET NULL"))
    token = Column(String(64), nullable=False, unique=True)
    code_hash = Column(String(255), nullable=False)
    failed_attempts = Column(Integer, nullable=False, default=0, server_default="0")
    status = Column(String(20), nullable=False, default="pending")
    expires_at = Column(TIMESTAMP(timezone=True), nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    used_at = Column(TIMESTAMP(timezone=True))
