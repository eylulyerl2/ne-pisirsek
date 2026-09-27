import re
import uuid

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.security import MAX_PASSWORD_BYTES

USERNAME_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{2,29}$")


def check_password_length(value: str) -> str:
    if len(value.encode("utf-8")) > MAX_PASSWORD_BYTES:
        raise ValueError(f"Şifre en fazla {MAX_PASSWORD_BYTES} bayt olabilir")
    return value


def clean_full_name(value: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError("Ad soyad boş olamaz")
    return value


def clean_username(value: str) -> str:
    value = value.strip().lower()
    if not USERNAME_RE.match(value):
        raise ValueError("Kullanıcı adı 3-30 karakter olmalı; yalnızca küçük harf (a-z), rakam, nokta, tire ve alt çizgi içerebilir")
    return value


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    full_name: str = Field(min_length=1, max_length=100)

    _password = field_validator("password")(check_password_length)
    _full_name = field_validator("full_name")(clean_full_name)


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: uuid.UUID
    email: EmailStr | None = None
    username: str | None = None
    full_name: str
    avatar_url: str | None = None
    preferred_language: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
