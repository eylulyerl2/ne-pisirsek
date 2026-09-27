import secrets
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.security import verify_password

MAX_CODE_ATTEMPTS = 5


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def new_code() -> str:
    return f"{secrets.randbelow(10**6):06d}"


def normalize_code(code: str) -> str:
    """'482 917' ve '482-917' gibi yazımları rakamlara indirger."""
    return "".join(ch for ch in code if ch.isdigit())


def verify_one_time_code(
    db: Session,
    record,
    code: str,
    *,
    done_status: str,
    used_message: str,
    locked_message: str,
    expired_message: str,
) -> None:
    """Davet ve şifre sıfırlama kayıtları için ortak doğrulama.

    Kayıt; status, failed_attempts, code_hash ve expires_at alanlarına sahip olmalı ve
    sorgulanırken satır kilidiyle (with_for_update) alınmış olmalıdır. Yanlış şifre denemesi
    sayılır ve commit edilir; sınıra ulaşınca kayıt kilitlenir.
    """
    if record.status == done_status:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=used_message)
    if record.status == "locked":
        raise HTTPException(status_code=status.HTTP_423_LOCKED, detail=locked_message)
    if record.expires_at <= now_utc():
        record.status = "expired"
        db.commit()
        raise HTTPException(status_code=status.HTTP_410_GONE, detail=expired_message)

    if not verify_password(normalize_code(code), record.code_hash):
        record.failed_attempts += 1
        remaining = MAX_CODE_ATTEMPTS - record.failed_attempts
        if remaining <= 0:
            record.status = "locked"
        db.commit()
        if remaining <= 0:
            raise HTTPException(status_code=status.HTTP_423_LOCKED, detail=locked_message)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Şifre hatalı. Kalan deneme hakkı: {remaining}")
