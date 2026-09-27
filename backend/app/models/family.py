from sqlalchemy import Column, String, Integer, TIMESTAMP, ForeignKey, UniqueConstraint, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
from app.database import Base


class Family(Base):
    __tablename__ = "families"

    family_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    created_by = Column(UUID(as_uuid=True), ForeignKey("profiles.user_id", ondelete="RESTRICT"), nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())

    members = relationship("FamilyMember", back_populates="family", cascade="all, delete-orphan")
    invitations = relationship("FamilyInvitation", back_populates="family", cascade="all, delete-orphan")


class FamilyMember(Base):
    __tablename__ = "family_members"
    __table_args__ = (
        UniqueConstraint("family_id", "user_id", name="uq_family_members_family_user"),
        CheckConstraint("role IN ('admin', 'member')", name="ck_family_members_role"),
    )

    member_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    family_id = Column(UUID(as_uuid=True), ForeignKey("families.family_id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("profiles.user_id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String(20), nullable=False, default="member")
    joined_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    family = relationship("Family", back_populates="members")


class FamilyInvitation(Base):
    __tablename__ = "family_invitations"
    __table_args__ = (
        CheckConstraint("status IN ('pending', 'accepted', 'expired', 'locked')", name="ck_family_invitations_status"),
    )

    invitation_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    family_id = Column(UUID(as_uuid=True), ForeignKey("families.family_id", ondelete="CASCADE"), nullable=False)
    invited_by = Column(UUID(as_uuid=True), ForeignKey("profiles.user_id", ondelete="CASCADE"), nullable=False)
    label = Column(String(100))
    token = Column(String(64), nullable=False, unique=True)
    code_hash = Column(String(255), nullable=False)
    failed_attempts = Column(Integer, nullable=False, default=0, server_default="0")
    status = Column(String(20), nullable=False, default="pending")
    expires_at = Column(TIMESTAMP(timezone=True), nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    used_by = Column(UUID(as_uuid=True), ForeignKey("profiles.user_id", ondelete="SET NULL"))
    used_at = Column(TIMESTAMP(timezone=True))

    family = relationship("Family", back_populates="invitations")
