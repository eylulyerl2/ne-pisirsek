from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import Profile
from app.schemas.auth import RegisterRequest, Token, UserResponse
from app.security import create_access_token, verify_dummy_password, verify_password
from app.services.accounts import AccountConflict, add_profile

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    try:
        user = add_profile(db, full_name=payload.full_name, password=payload.password, email=payload.email, username=None)
        db.commit()
    except (AccountConflict, IntegrityError) as error:
        db.rollback()
        message = error.message if isinstance(error, AccountConflict) else "Bu e-posta adresi zaten kayıtlı"
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=message)
    db.refresh(user)
    return user


@router.post("/login", response_model=Token)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """Giriş: 'username' alanına e-posta adresi ya da kullanıcı adı yazılır."""
    identifier = form.username.strip().lower()
    user = db.query(Profile).filter(or_(Profile.email == identifier, Profile.username == identifier)).first()
    if user is None:
        verify_dummy_password(form.password)
    if user is None or not verify_password(form.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="E-posta/kullanıcı adı veya şifre hatalı",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return Token(access_token=create_access_token(str(user.user_id)))


@router.get("/me", response_model=UserResponse)
def me(current_user: Profile = Depends(get_current_user)):
    return current_user
