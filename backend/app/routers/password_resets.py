import secrets
import uuid
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user, require_family_admin
from app.models import FamilyMember, PasswordReset, Profile
from app.schemas.auth import Token
from app.schemas.password_reset import (
    PasswordResetComplete,
    PasswordResetCreated,
    PasswordResetPreview,
)
from app.security import create_access_token, hash_password
from app.services.codes import new_code, now_utc, verify_one_time_code

router = APIRouter(tags=["password-resets"])

RESET_TTL = timedelta(hours=24)


def _issue_reset(db: Session, *, user_id: uuid.UUID, created_by: uuid.UUID | None) -> tuple[PasswordReset, str]:
    """Önceki bekleyen/kilitli sıfırlamaları iptal edip yenisini oluşturur. Commit etmez."""
    db.query(PasswordReset).filter(PasswordReset.user_id == user_id, PasswordReset.status.in_(("pending", "locked"))).delete(
        synchronize_session=False
    )
    code = new_code()
    reset = PasswordReset(
        user_id=user_id,
        created_by=created_by,
        token=secrets.token_urlsafe(32),
        code_hash=hash_password(code),
        expires_at=now_utc() + RESET_TTL,
    )
    db.add(reset)
    return reset, code


@router.post(
    "/families/{family_id}/members/{user_id}/password-reset",
    response_model=PasswordResetCreated,
    status_code=status.HTTP_201_CREATED,
)
def create_password_reset(
    family_id: uuid.UUID,
    user_id: uuid.UUID,
    current_user: Profile = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Ailenin açtığı bir hesap için sıfırlama bağlantısı ve tek kullanımlık şifre üretir.

    Şifre henüz değişmez; hesap sahibi bağlantıyı açıp şifreyi girince yeni şifresini kendisi belirler.
    """
    require_family_admin(db, family_id, current_user)
    if user_id == current_user.user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Kendi şifrenizi Tercihler sayfasından değiştirebilirsiniz")
    is_member = (
        db.query(FamilyMember.member_id)
        .filter(FamilyMember.family_id == family_id, FamilyMember.user_id == user_id)
        .first()
    )
    profile = db.get(Profile, user_id) if is_member else None
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Üye bulunamadı")
    if profile.created_via_family_id != family_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bu hesabı aile açmadığı için şifresini yalnızca hesap sahibi değiştirebilir",
        )

    reset, code = _issue_reset(db, user_id=user_id, created_by=current_user.user_id)
    db.commit()
    return PasswordResetCreated(token=reset.token, code=code, expires_at=reset.expires_at, member_name=profile.full_name)


@router.delete("/families/{family_id}/members/{user_id}/password-reset", status_code=status.HTTP_204_NO_CONTENT)
def cancel_password_reset(
    family_id: uuid.UUID,
    user_id: uuid.UUID,
    current_user: Profile = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    require_family_admin(db, family_id, current_user)
    is_member = (
        db.query(FamilyMember.member_id)
        .filter(FamilyMember.family_id == family_id, FamilyMember.user_id == user_id)
        .first()
    )
    deleted = 0
    if is_member:
        deleted = (
            db.query(PasswordReset)
            .filter(PasswordReset.user_id == user_id, PasswordReset.status.in_(("pending", "locked")))
            .delete(synchronize_session=False)
        )
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bekleyen şifre sıfırlama yok")
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/password-resets/preview", response_model=PasswordResetPreview)
def preview_password_reset(token: str = Query(min_length=1, max_length=64), db: Session = Depends(get_db)):
    """Herkese açık: bağlantıyı açan kişiye hangi hesap için sıfırlama yapılacağını ve durumunu gösterir."""
    row = (
        db.query(PasswordReset, Profile)
        .join(Profile, Profile.user_id == PasswordReset.user_id)
        .filter(PasswordReset.token == token)
        .first()
    )
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Şifre sıfırlama bağlantısı bulunamadı")
    reset, profile = row
    current = "expired" if reset.status == "pending" and reset.expires_at <= now_utc() else reset.status
    return PasswordResetPreview(
        full_name=profile.full_name,
        username=profile.username,
        status=current,
        usable=current == "pending",
        expires_at=reset.expires_at,
    )


@router.post("/password-resets/complete", response_model=Token)
def complete_password_reset(payload: PasswordResetComplete, db: Session = Depends(get_db)):
    """Bağlantıdaki şifreyi doğrular, yeni şifreyi kaydeder ve kişiyi giriş yapmış hâle getirir."""
    reset = db.query(PasswordReset).filter(PasswordReset.token == payload.token).with_for_update().first()
    if reset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Şifre sıfırlama bağlantısı bulunamadı")

    verify_one_time_code(
        db,
        reset,
        payload.code,
        done_status="used",
        used_message="Bu şifre sıfırlama bağlantısı daha önce kullanılmış",
        locked_message="Çok fazla yanlış şifre denendiği için bağlantı kilitlendi. Lütfen aile yöneticisinden yenisini isteyin",
        expired_message="Şifre sıfırlama bağlantısının süresi dolmuş, lütfen aile yöneticisinden yenisini isteyin",
    )
    profile = db.get(Profile, reset.user_id)

    still_managed = (
        profile.created_via_family_id is not None
        and db.query(FamilyMember.member_id)
        .filter(FamilyMember.family_id == profile.created_via_family_id, FamilyMember.user_id == profile.user_id)
        .first()
        is not None
    )
    if not still_managed:
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Bu bağlantı artık geçerli değil, hesap aileden ayrılmış")

    profile.password_hash = hash_password(payload.new_password)
    reset.status = "used"
    reset.used_at = now_utc()
    db.commit()
    return Token(access_token=create_access_token(str(profile.user_id)))
