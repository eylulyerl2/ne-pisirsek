import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.schemas.auth import check_password_length, clean_full_name, clean_username


class FamilyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Aile adı boş olamaz")
        return value


class FamilyUpdate(FamilyCreate):
    pass


class MemberResponse(BaseModel):
    user_id: uuid.UUID
    full_name: str
    username: str | None = None
    avatar_url: str | None = None
    role: Literal["admin", "member"]
    joined_at: datetime | None = None
    can_reset_password: bool = False
    reset_pending: bool = False


class FamilySummary(BaseModel):
    family_id: uuid.UUID
    name: str
    role: Literal["admin", "member"]
    created_by: uuid.UUID
    member_count: int
    created_at: datetime | None = None


class FamilyDetail(FamilySummary):
    members: list[MemberResponse]


class MemberRoleUpdate(BaseModel):
    role: Literal["admin", "member"]


class InvitationCreate(BaseModel):
    label: str | None = Field(None, max_length=100, description="Davetin kimin için olduğu (isteğe bağlı)")

    @field_validator("label")
    @classmethod
    def blank_label_to_none(cls, value: str | None) -> str | None:
        return value.strip() or None if value else None


class InvitationResponse(BaseModel):
    invitation_id: uuid.UUID
    family_id: uuid.UUID
    label: str | None = None
    token: str
    status: str
    failed_attempts: int = 0
    expires_at: datetime
    created_at: datetime | None = None
    code: str | None = Field(None, description="Tek kullanımlık şifre; yalnızca oluşturma/yenileme yanıtında bir kez döner")


class InvitationPreview(BaseModel):
    family_name: str
    inviter_name: str
    label: str | None = None
    status: Literal["pending", "accepted", "expired", "locked"]
    usable: bool
    expires_at: datetime


class AcceptRequest(BaseModel):
    token: str = Field(min_length=1, max_length=64)
    code: str = Field(min_length=1, max_length=20)


class JoinRequest(AcceptRequest):
    full_name: str = Field(min_length=1, max_length=100)
    username: str
    password: str = Field(min_length=8)
    email: EmailStr | None = None

    _full_name = field_validator("full_name")(clean_full_name)
    _username = field_validator("username")(clean_username)
    _password = field_validator("password")(check_password_length)


class JoinResult(BaseModel):
    access_token: str
    token_type: str = "bearer"
    family: FamilySummary
