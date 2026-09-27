from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import Profile, UserPreference
from app.schemas.auth import UserResponse
from app.security import hash_password, verify_password
from app.schemas.password_reset import PasswordChange
from app.schemas.user import PreferenceResponse, PreferenceUpdate, ProfileUpdate

router = APIRouter(prefix="/users/me", tags=["users"])


def _get_or_create_preferences(db: Session, user: Profile) -> UserPreference:
    prefs = db.query(UserPreference).filter(UserPreference.user_id == user.user_id).first()
    if prefs is None:
        prefs = UserPreference(user_id=user.user_id)
        db.add(prefs)
        db.commit()
        db.refresh(prefs)
    return prefs


@router.get("", response_model=UserResponse)
def get_profile(current_user: Profile = Depends(get_current_user)):
    return current_user


@router.patch("", response_model=UserResponse)
def update_profile(
    payload: ProfileUpdate,
    current_user: Profile = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(current_user, field, value)
    db.commit()
    db.refresh(current_user)
    return current_user


@router.get("/preferences", response_model=PreferenceResponse)
def get_preferences(current_user: Profile = Depends(get_current_user), db: Session = Depends(get_db)):
    return _get_or_create_preferences(db, current_user)


@router.patch("/preferences", response_model=PreferenceResponse)
def update_preferences(
    payload: PreferenceUpdate,
    current_user: Profile = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    prefs = _get_or_create_preferences(db, current_user)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(prefs, field, value)
    db.commit()
    db.refresh(prefs)
    return prefs


@router.post("/password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(
    payload: PasswordChange,
    current_user: Profile = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not verify_password(payload.current_password, current_user.password_hash):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Mevcut şifre hatalı")
    current_user.password_hash = hash_password(payload.new_password)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
