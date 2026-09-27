from sqlalchemy.orm import Session

from app.models import Profile, UserPreference
from app.security import hash_password


class AccountConflict(Exception):
    """E-posta veya kullanıcı adı zaten kayıtlı."""

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


def check_available(db: Session, email: str | None, username: str | None) -> None:
    if email and db.query(Profile.user_id).filter(Profile.email == email).first():
        raise AccountConflict("Bu e-posta adresi zaten kayıtlı")
    if username and db.query(Profile.user_id).filter(Profile.username == username).first():
        raise AccountConflict("Bu kullanıcı adı alınmış")


def add_profile(
    db: Session,
    *,
    full_name: str,
    password: str,
    email: str | None,
    username: str | None,
    created_via_family_id=None,
) -> Profile:
    """Profili ve varsayılan tercihlerini ekler (flush eder, commit çağırana aittir)."""
    check_available(db, email, username)
    profile = Profile(
        full_name=full_name,
        email=email.lower() if email else None,
        username=username,
        password_hash=hash_password(password),
        created_via_family_id=created_via_family_id,
    )
    db.add(profile)
    db.flush()
    db.add(UserPreference(user_id=profile.user_id))
    return profile
