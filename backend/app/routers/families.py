import uuid

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import collate, func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user, get_membership, require_family_admin
from app.models import Family, FamilyMember, PasswordReset, Profile
from app.schemas.family import (
    FamilyCreate,
    FamilyDetail,
    FamilySummary,
    FamilyUpdate,
    MemberResponse,
    MemberRoleUpdate,
)

router = APIRouter(tags=["families"])

TR_COLLATION = "tr-TR-x-icu"


def _member_count(db: Session, family_id: uuid.UUID) -> int:
    return db.query(func.count(FamilyMember.member_id)).filter(FamilyMember.family_id == family_id).scalar()


def admin_count(db: Session, family_id: uuid.UUID) -> int:
    return (
        db.query(func.count(FamilyMember.member_id))
        .filter(FamilyMember.family_id == family_id, FamilyMember.role == "admin")
        .scalar()
    )


def family_summary(db: Session, family: Family, role: str) -> FamilySummary:
    return FamilySummary(
        family_id=family.family_id,
        name=family.name,
        role=role,
        created_by=family.created_by,
        member_count=_member_count(db, family.family_id),
        created_at=family.created_at,
    )


def _get_family(db: Session, family_id: uuid.UUID) -> Family:
    family = db.get(Family, family_id)
    if family is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Aile bulunamadı")
    return family


@router.post("/families", response_model=FamilySummary, status_code=status.HTTP_201_CREATED)
def create_family(
    payload: FamilyCreate,
    current_user: Profile = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    family = Family(name=payload.name, created_by=current_user.user_id)
    db.add(family)
    db.flush()
    db.add(FamilyMember(family_id=family.family_id, user_id=current_user.user_id, role="admin"))
    db.commit()
    db.refresh(family)
    return family_summary(db, family, "admin")


@router.get("/families", response_model=list[FamilySummary])
def list_my_families(current_user: Profile = Depends(get_current_user), db: Session = Depends(get_db)):
    my_family_ids = select(FamilyMember.family_id).where(FamilyMember.user_id == current_user.user_id)
    counts = (
        select(FamilyMember.family_id, func.count().label("n"))
        .where(FamilyMember.family_id.in_(my_family_ids))
        .group_by(FamilyMember.family_id)
        .subquery()
    )
    rows = (
        db.query(Family, FamilyMember.role, counts.c.n)
        .join(FamilyMember, FamilyMember.family_id == Family.family_id)
        .join(counts, counts.c.family_id == Family.family_id)
        .filter(FamilyMember.user_id == current_user.user_id)
        .order_by(collate(Family.name, TR_COLLATION))
        .all()
    )
    return [
        FamilySummary(
            family_id=f.family_id, name=f.name, role=role, created_by=f.created_by, member_count=n, created_at=f.created_at
        )
        for f, role, n in rows
    ]


@router.get("/families/{family_id}", response_model=FamilyDetail)
def get_family(
    family_id: uuid.UUID,
    current_user: Profile = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    membership = get_membership(db, family_id, current_user)
    family = _get_family(db, family_id)
    rows = (
        db.query(FamilyMember, Profile)
        .join(Profile, Profile.user_id == FamilyMember.user_id)
        .filter(FamilyMember.family_id == family_id)
        .order_by(FamilyMember.joined_at)
        .all()
    )
    is_admin = membership.role == "admin"
    pending_reset_users = set()
    if is_admin:
        pending_reset_users = {
            user_id
            for (user_id,) in db.query(PasswordReset.user_id).filter(
                PasswordReset.user_id.in_([p.user_id for _, p in rows]),
                PasswordReset.status == "pending",
                PasswordReset.expires_at > datetime.now(timezone.utc),
            )
        }
    members = [
        MemberResponse(
            user_id=p.user_id,
            full_name=p.full_name,
            username=p.username,
            avatar_url=p.avatar_url,
            role=m.role,
            joined_at=m.joined_at,
            can_reset_password=is_admin and p.created_via_family_id == family_id and p.user_id != current_user.user_id,
            reset_pending=p.user_id in pending_reset_users,
        )
        for m, p in rows
    ]
    summary = family_summary(db, family, membership.role)
    return FamilyDetail(**summary.model_dump(), members=members)


@router.patch("/families/{family_id}", response_model=FamilySummary)
def rename_family(
    family_id: uuid.UUID,
    payload: FamilyUpdate,
    current_user: Profile = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    membership = require_family_admin(db, family_id, current_user)
    family = _get_family(db, family_id)
    family.name = payload.name
    db.commit()
    db.refresh(family)
    return family_summary(db, family, membership.role)


@router.delete("/families/{family_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_family(
    family_id: uuid.UUID,
    current_user: Profile = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    get_membership(db, family_id, current_user)
    family = _get_family(db, family_id)
    if family.created_by != current_user.user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Aileyi yalnızca kurucusu silebilir")
    db.delete(family)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.patch("/families/{family_id}/members/{user_id}", response_model=MemberResponse)
def update_member_role(
    family_id: uuid.UUID,
    user_id: uuid.UUID,
    payload: MemberRoleUpdate,
    current_user: Profile = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    require_family_admin(db, family_id, current_user)
    target = (
        db.query(FamilyMember).filter(FamilyMember.family_id == family_id, FamilyMember.user_id == user_id).first()
    )
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Üye bulunamadı")
    if target.role == "admin" and payload.role == "member" and admin_count(db, family_id) <= 1:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Ailede en az bir yönetici kalmalı")
    target.role = payload.role
    db.commit()
    profile = db.get(Profile, user_id)
    return MemberResponse(
        user_id=user_id,
        full_name=profile.full_name,
        username=profile.username,
        avatar_url=profile.avatar_url,
        role=target.role,
        joined_at=target.joined_at,
    )


@router.delete("/families/{family_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_member(
    family_id: uuid.UUID,
    user_id: uuid.UUID,
    current_user: Profile = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    me = get_membership(db, family_id, current_user)
    if user_id != current_user.user_id and me.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Bu işlem için aile yöneticisi olmalısınız")
    target = (
        db.query(FamilyMember).filter(FamilyMember.family_id == family_id, FamilyMember.user_id == user_id).first()
    )
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Üye bulunamadı")
    if target.role == "admin" and admin_count(db, family_id) <= 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ailedeki tek yönetici çıkarılamaz. Önce başka bir yönetici atayın veya aileyi silin",
        )
    db.delete(target)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
