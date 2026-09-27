import secrets
import uuid
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user, require_family_admin
from app.models import Family, FamilyInvitation, FamilyMember, Profile
from app.routers.families import family_summary
from app.schemas.family import (
    AcceptRequest,
    FamilySummary,
    InvitationCreate,
    InvitationPreview,
    InvitationResponse,
    JoinRequest,
    JoinResult,
)
from app.security import create_access_token, hash_password
from app.services.accounts import AccountConflict, add_profile
from app.services.codes import new_code, now_utc, verify_one_time_code

router = APIRouter(tags=["invitations"])

INVITATION_TTL = timedelta(days=7)
MAX_OPEN_INVITATIONS = 20


def _response(invitation: FamilyInvitation, code: str | None = None) -> InvitationResponse:
    expired = invitation.status == "pending" and invitation.expires_at <= now_utc()
    return InvitationResponse(
        invitation_id=invitation.invitation_id,
        family_id=invitation.family_id,
        label=invitation.label,
        token=invitation.token,
        status="expired" if expired else invitation.status,
        failed_attempts=invitation.failed_attempts,
        expires_at=invitation.expires_at,
        created_at=invitation.created_at,
        code=code,
    )


# --- Yönetici tarafı ------------------------------------------------------------


@router.post("/families/{family_id}/invitations", response_model=InvitationResponse, status_code=status.HTTP_201_CREATED)
def create_invitation(
    family_id: uuid.UUID,
    payload: InvitationCreate | None = None,
    current_user: Profile = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Bağlantı ve tek kullanımlık şifre üretir. Şifre yalnızca bu yanıtta görünür."""
    require_family_admin(db, family_id, current_user)
    open_count = (
        db.query(FamilyInvitation)
        .filter(
            FamilyInvitation.family_id == family_id,
            FamilyInvitation.status.in_(("pending", "locked")),
            FamilyInvitation.expires_at > now_utc(),
        )
        .count()
    )
    if open_count >= MAX_OPEN_INVITATIONS:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Çok fazla açık davet var, önce bazılarını iptal edin")

    code = new_code()
    invitation = FamilyInvitation(
        family_id=family_id,
        invited_by=current_user.user_id,
        label=(payload.label if payload else None),
        token=secrets.token_urlsafe(32),
        code_hash=hash_password(code),
        expires_at=now_utc() + INVITATION_TTL,
    )
    db.add(invitation)
    db.commit()
    db.refresh(invitation)
    return _response(invitation, code)


@router.get("/families/{family_id}/invitations", response_model=list[InvitationResponse])
def list_family_invitations(
    family_id: uuid.UUID,
    current_user: Profile = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    require_family_admin(db, family_id, current_user)
    rows = (
        db.query(FamilyInvitation)
        .filter(
            FamilyInvitation.family_id == family_id,
            FamilyInvitation.status.in_(("pending", "locked")),
            FamilyInvitation.expires_at > now_utc(),
        )
        .order_by(FamilyInvitation.created_at.desc())
        .all()
    )
    return [_response(row) for row in rows]


@router.post("/families/{family_id}/invitations/{invitation_id}/regenerate", response_model=InvitationResponse)
def regenerate_invitation_code(
    family_id: uuid.UUID,
    invitation_id: uuid.UUID,
    current_user: Profile = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Yeni şifre üretir (eskisi geçersiz olur), kilidi açar ve süreyi yeniler."""
    require_family_admin(db, family_id, current_user)
    invitation = (
        db.query(FamilyInvitation)
        .filter(FamilyInvitation.invitation_id == invitation_id, FamilyInvitation.family_id == family_id)
        .with_for_update()
        .first()
    )
    if invitation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Davet bulunamadı")
    if invitation.status == "accepted":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Bu davet zaten kullanılmış")
    code = new_code()
    invitation.code_hash = hash_password(code)
    invitation.failed_attempts = 0
    invitation.status = "pending"
    invitation.expires_at = now_utc() + INVITATION_TTL
    db.commit()
    db.refresh(invitation)
    return _response(invitation, code)


@router.delete("/families/{family_id}/invitations/{invitation_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_invitation(
    family_id: uuid.UUID,
    invitation_id: uuid.UUID,
    current_user: Profile = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    require_family_admin(db, family_id, current_user)
    deleted = (
        db.query(FamilyInvitation)
        .filter(FamilyInvitation.invitation_id == invitation_id, FamilyInvitation.family_id == family_id)
        .delete(synchronize_session=False)
    )
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Davet bulunamadı")
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# --- Davet edilen taraf (bağlantıyı açan) ---------------------------------------


@router.get("/invitations/preview", response_model=InvitationPreview)
def preview_invitation(token: str = Query(min_length=1, max_length=64), db: Session = Depends(get_db)):
    """Herkese açık: bağlantıyı açan kişiye hangi aileye katılacağını ve davetin durumunu gösterir."""
    row = (
        db.query(FamilyInvitation, Family.name, Profile.full_name)
        .join(Family, Family.family_id == FamilyInvitation.family_id)
        .join(Profile, Profile.user_id == FamilyInvitation.invited_by)
        .filter(FamilyInvitation.token == token)
        .first()
    )
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Davet bulunamadı")
    invitation, family_name, inviter_name = row
    current = _response(invitation)
    return InvitationPreview(
        family_name=family_name,
        inviter_name=inviter_name,
        label=invitation.label,
        status=current.status,
        usable=current.status == "pending",
        expires_at=invitation.expires_at,
    )


def _verify_invitation(db: Session, token: str, code: str) -> FamilyInvitation:
    """Bağlantı ve şifreyi doğrular. Yanlış şifre denemesi sayılır; sınırda davet kilitlenir."""
    invitation = db.query(FamilyInvitation).filter(FamilyInvitation.token == token).with_for_update().first()
    if invitation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Davet bulunamadı")
    verify_one_time_code(
        db,
        invitation,
        code,
        done_status="accepted",
        used_message="Bu davet daha önce kullanılmış",
        locked_message="Çok fazla yanlış şifre denendiği için davet kilitlendi. Aile yöneticisinden yeni bir şifre isteyin",
        expired_message="Davetin süresi dolmuş, aile yöneticisinden yenisini isteyin",
    )
    return invitation


def _consume(invitation: FamilyInvitation, user_id: uuid.UUID) -> None:
    invitation.status = "accepted"
    invitation.used_by = user_id
    invitation.used_at = now_utc()


@router.post("/invitations/accept", response_model=FamilySummary)
def accept_invitation(
    payload: AcceptRequest,
    current_user: Profile = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Hesabı olan kişi bağlantıdaki şifreyle aileye katılır."""
    invitation = _verify_invitation(db, payload.token, payload.code)
    already = (
        db.query(FamilyMember.member_id)
        .filter(FamilyMember.family_id == invitation.family_id, FamilyMember.user_id == current_user.user_id)
        .first()
    )
    if already:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Zaten bu ailenin üyesisiniz")
    db.add(FamilyMember(family_id=invitation.family_id, user_id=current_user.user_id, role="member"))
    _consume(invitation, current_user.user_id)
    family_id = invitation.family_id
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Zaten bu ailenin üyesisiniz")
    return family_summary(db, db.get(Family, family_id), "member")


@router.post("/invitations/join", response_model=JoinResult, status_code=status.HTTP_201_CREATED)
def join_with_new_account(payload: JoinRequest, db: Session = Depends(get_db)):
    """Hesabı olmayan kişi (e-postası olmasa da) bağlantıdaki şifreyle hesap açıp aileye katılır."""
    invitation = _verify_invitation(db, payload.token, payload.code)
    try:
        user = add_profile(
            db,
            full_name=payload.full_name,
            password=payload.password,
            email=payload.email,
            username=payload.username,
            created_via_family_id=invitation.family_id,
        )
        db.add(FamilyMember(family_id=invitation.family_id, user_id=user.user_id, role="member"))
        _consume(invitation, user.user_id)
        db.commit()
    except (AccountConflict, IntegrityError) as error:
        db.rollback()
        message = error.message if isinstance(error, AccountConflict) else "Bu kullanıcı adı veya e-posta zaten kayıtlı"
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=message)
    return JoinResult(
        access_token=create_access_token(str(user.user_id)),
        family=family_summary(db, db.get(Family, invitation.family_id), "member"),
    )
