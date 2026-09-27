import uuid
import warnings

import pytest

warnings.filterwarnings("ignore", category=DeprecationWarning)

TEST_PREFIX = "pytest-"


def unique(label: str = "u") -> str:
    return f"{TEST_PREFIX}{label}-{uuid.uuid4().hex[:8]}"


@pytest.fixture(scope="session")
def _sweep_test_data():
    """Entegrasyon testleri gerçek veritabanına yazar; bittiğinde 'pytest-' önekli kayıtları siler."""
    yield
    from app.database import SessionLocal
    from app.models import Family, Profile

    db = SessionLocal()
    try:
        ids = [
            p.user_id
            for p in db.query(Profile).filter(
                (Profile.email.like(f"{TEST_PREFIX}%")) | (Profile.username.like(f"{TEST_PREFIX}%"))
            )
        ]
        if ids:
            db.query(Family).filter(Family.created_by.in_(ids)).delete(synchronize_session=False)
            db.query(Profile).filter(Profile.user_id.in_(ids)).delete(synchronize_session=False)
            db.commit()
    finally:
        db.close()


@pytest.fixture(scope="module")
def client(_sweep_test_data):
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def make_user(client):
    """E-postalı kullanıcı kaydeder ve giriş başlıklarını döndürür."""

    def _make(label: str = "u"):
        tag = unique(label)
        email = f"{tag}@example.com"
        registered = client.post("/auth/register", json={"email": email, "password": "guclusifre123", "full_name": f"Test {label}"})
        assert registered.status_code == 201, registered.text
        token = client.post("/auth/login", data={"username": email, "password": "guclusifre123"}).json()["access_token"]
        return {"headers": {"Authorization": f"Bearer {token}"}, "email": email, "user_id": registered.json()["user_id"]}

    return _make


@pytest.fixture
def family(client, make_user):
    """Kurucu (A) ve ailesi."""
    owner = make_user("owner")
    created = client.post("/families", headers=owner["headers"], json={"name": "Test Ailesi"})
    assert created.status_code == 201, created.text
    return {"owner": owner, "family_id": created.json()["family_id"]}
