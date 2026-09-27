import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import FamilyMember, Profile, WeeklyPlan
from app.security import decode_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> Profile:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Kimlik doğrulanamadı",
        headers={"WWW-Authenticate": "Bearer"},
    )
    subject = decode_access_token(token)
    if subject is None:
        raise credentials_error
    try:
        user_id = uuid.UUID(subject)
    except ValueError:
        raise credentials_error

    user = db.get(Profile, user_id)
    if user is None:
        raise credentials_error
    return user


def get_membership(db: Session, family_id: uuid.UUID, user: Profile) -> FamilyMember:
    membership = (
        db.query(FamilyMember)
        .filter(FamilyMember.family_id == family_id, FamilyMember.user_id == user.user_id)
        .first()
    )
    if membership is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Aile bulunamadı")
    return membership


def require_family_admin(db: Session, family_id: uuid.UUID, user: Profile) -> FamilyMember:
    membership = get_membership(db, family_id, user)
    if membership.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Bu işlem için aile yöneticisi olmalısınız")
    return membership


def get_plan_for_user(db: Session, plan_id: uuid.UUID, user: Profile, require_admin: bool = False) -> WeeklyPlan:
    not_found = HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan bulunamadı")
    plan = db.get(WeeklyPlan, plan_id)
    if plan is None:
        raise not_found
    if plan.user_id is not None:
        if plan.user_id != user.user_id:
            raise not_found
        return plan

    membership = (
        db.query(FamilyMember)
        .filter(FamilyMember.family_id == plan.family_id, FamilyMember.user_id == user.user_id)
        .first()
    )
    if membership is None:
        raise not_found
    if require_admin and membership.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Bu işlem için aile yöneticisi olmalısınız")
    return plan
