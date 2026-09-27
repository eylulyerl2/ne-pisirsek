from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.schemas.auth import check_password_length


class PasswordResetCreated(BaseModel):
    token: str
    code: str = Field(description="Tek kullanımlık şifre; yalnızca bu yanıtta bir kez görünür")
    expires_at: datetime
    member_name: str


class PasswordResetPreview(BaseModel):
    full_name: str
    username: str | None = None
    status: Literal["pending", "used", "locked", "expired"]
    usable: bool
    expires_at: datetime


class PasswordResetComplete(BaseModel):
    token: str = Field(min_length=1, max_length=64)
    code: str = Field(min_length=1, max_length=20)
    new_password: str = Field(min_length=8)

    _password = field_validator("new_password")(check_password_length)


class PasswordChange(BaseModel):
    current_password: str = Field(min_length=1)
    new_password: str = Field(min_length=8)

    _password = field_validator("new_password")(check_password_length)
