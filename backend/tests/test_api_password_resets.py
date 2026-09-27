"""Şifre sıfırlama bağlantısı (yönetici üretir) ve giriş yapmış kullanıcının şifre değiştirmesi. Gerçek veritabanına yazar."""
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.database import SessionLocal
from app.models import PasswordReset
from tests.conftest import unique

pytestmark = pytest.mark.integration

PASSWORD = "guclusifre123"
NEW_PASSWORD = "yepyeni-sifre-77"


def invite_and_join(client, family, *, existing_user=None):
    """Aile yöneticisinin daveti üzerinden katılan bir üye döndürür (e-postasız yeni hesap ya da mevcut hesap)."""
    invitation = client.post(f"/families/{family['family_id']}/invitations", headers=family["owner"]["headers"], json={"label": "Çocuk"}).json()
    if existing_user:
        response = client.post("/invitations/accept", headers=existing_user["headers"], json={"token": invitation["token"], "code": invitation["code"]})
        assert response.status_code == 200, response.text
        return existing_user
    username = unique("kid")
    response = client.post(
        "/invitations/join",
        json={"token": invitation["token"], "code": invitation["code"], "full_name": "Elif Yılmaz", "username": username, "password": PASSWORD},
    )
    assert response.status_code == 201, response.text
    token = response.json()["access_token"]
    me = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"}).json()
    return {"username": username, "user_id": me["user_id"], "headers": {"Authorization": f"Bearer {token}"}}


def create_reset(client, family, member):
    response = client.post(
        f"/families/{family['family_id']}/members/{member['user_id']}/password-reset", headers=family["owner"]["headers"]
    )
    assert response.status_code == 201, response.text
    return response.json()


def complete(client, reset, code=None, password=NEW_PASSWORD):
    return client.post(
        "/password-resets/complete", json={"token": reset["token"], "code": code or reset["code"], "new_password": password}
    )


def wrong(reset):
    return "000000" if reset["code"] != "000000" else "111111"


def login(client, identifier, password):
    return client.post("/auth/login", data={"username": identifier, "password": password})


def member_flags(client, family, headers, user_id):
    detail = client.get(f"/families/{family['family_id']}", headers=headers).json()
    member = next(m for m in detail["members"] if m["user_id"] == user_id)
    return member["can_reset_password"], member["reset_pending"]


def set_db(reset_token, **fields):
    db = SessionLocal()
    try:
        row = db.query(PasswordReset).filter(PasswordReset.token == reset_token).one()
        for key, value in fields.items():
            setattr(row, key, value)
        db.commit()
    finally:
        db.close()


class TestCreatingAResetLink:
    def test_admin_gets_a_link_and_one_time_code_for_a_family_created_account(self, client, family):
        kid = invite_and_join(client, family)
        created = create_reset(client, family, kid)
        assert re.fullmatch(r"\d{6}", created["code"]) and len(created["token"]) >= 30
        assert created["member_name"] == "Elif Yılmaz"

    def test_password_does_not_change_until_the_owner_completes_it(self, client, family):
        kid = invite_and_join(client, family)
        create_reset(client, family, kid)
        assert login(client, kid["username"], PASSWORD).status_code == 200

    def test_member_list_flags_who_can_be_reset_and_who_is_pending(self, client, family):
        kid = invite_and_join(client, family)
        assert member_flags(client, family, family["owner"]["headers"], kid["user_id"]) == (True, False)
        create_reset(client, family, kid)
        assert member_flags(client, family, family["owner"]["headers"], kid["user_id"]) == (True, True)
        assert member_flags(client, family, kid["headers"], kid["user_id"]) == (False, False), "üye kendi için ya da bekleyen bilgisi görmez"

    def test_a_new_link_kills_the_previous_one(self, client, family):
        kid = invite_and_join(client, family)
        first = create_reset(client, family, kid)
        second = create_reset(client, family, kid)
        assert first["token"] != second["token"]
        assert complete(client, first).status_code == 404
        assert complete(client, second).status_code == 200


class TestWhoMayBeReset:
    def test_accounts_the_family_did_not_create_cannot_be_reset(self, client, family, make_user):
        adult = make_user("adult")
        invite_and_join(client, family, existing_user=adult)
        response = client.post(f"/families/{family['family_id']}/members/{adult['user_id']}/password-reset", headers=family["owner"]["headers"])
        assert response.status_code == 403 and "hesap sahibi" in response.json()["detail"]
        assert member_flags(client, family, family["owner"]["headers"], adult["user_id"]) == (False, False)

    def test_admin_cannot_reset_their_own_password_this_way(self, client, family):
        response = client.post(
            f"/families/{family['family_id']}/members/{family['owner']['user_id']}/password-reset", headers=family["owner"]["headers"]
        )
        assert response.status_code == 400 and "Tercihler" in response.json()["detail"]

    def test_a_promoted_admin_cannot_take_over_the_founder(self, client, family):
        kid = invite_and_join(client, family)
        client.patch(f"/families/{family['family_id']}/members/{kid['user_id']}", headers=family["owner"]["headers"], json={"role": "admin"})
        response = client.post(f"/families/{family['family_id']}/members/{family['owner']['user_id']}/password-reset", headers=kid["headers"])
        assert response.status_code == 403

    def test_regular_members_and_outsiders_are_refused(self, client, family, make_user):
        kid = invite_and_join(client, family)
        other_kid = invite_and_join(client, family)
        outsider = make_user("outsider")
        url = f"/families/{family['family_id']}/members/{kid['user_id']}/password-reset"
        assert client.post(url, headers=other_kid["headers"]).status_code == 403
        assert client.post(url, headers=outsider["headers"]).status_code == 404

    def test_target_must_belong_to_the_family(self, client, family, make_user):
        stranger = make_user("stranger")
        response = client.post(f"/families/{family['family_id']}/members/{stranger['user_id']}/password-reset", headers=family["owner"]["headers"])
        assert response.status_code == 404

    def test_admin_of_another_family_cannot_reset_the_account(self, client, family, make_user):
        kid = invite_and_join(client, family)
        other_owner = make_user("other-owner")
        other_family = client.post("/families", headers=other_owner["headers"], json={"name": "Başka Aile"}).json()["family_id"]
        response = client.post(f"/families/{other_family}/members/{kid['user_id']}/password-reset", headers=other_owner["headers"])
        assert response.status_code == 404, "başka ailenin yöneticisi bu hesabı göremez bile"


class TestOpeningAndCompleting:
    def test_preview_is_public_and_shows_only_the_account_name(self, client, family):
        kid = invite_and_join(client, family)
        created = create_reset(client, family, kid)
        body = client.get("/password-resets/preview", params={"token": created["token"]}).json()
        assert body["full_name"] == "Elif Yılmaz" and body["username"] == kid["username"] and body["usable"] is True
        assert "code" not in body and "token" not in body
        assert client.get("/password-resets/preview", params={"token": "yok"}).status_code == 404

    def test_correct_code_sets_the_new_password_and_signs_in(self, client, family):
        kid = invite_and_join(client, family)
        created = create_reset(client, family, kid)
        done = complete(client, created)
        assert done.status_code == 200, done.text
        me = client.get("/auth/me", headers={"Authorization": f"Bearer {done.json()['access_token']}"}).json()
        assert me["user_id"] == kid["user_id"]
        assert login(client, kid["username"], NEW_PASSWORD).status_code == 200
        assert login(client, kid["username"], PASSWORD).status_code == 401

    def test_code_may_be_typed_with_a_space(self, client, family):
        kid = invite_and_join(client, family)
        created = create_reset(client, family, kid)
        spaced = f"{created['code'][:3]} {created['code'][3:]}"
        assert complete(client, created, code=spaced).status_code == 200

    def test_a_link_works_only_once(self, client, family):
        kid = invite_and_join(client, family)
        created = create_reset(client, family, kid)
        assert complete(client, created).status_code == 200
        again = complete(client, created, password="baska-sifre-123")
        assert again.status_code == 409 and "daha önce kullanılmış" in again.json()["detail"]
        assert login(client, kid["username"], NEW_PASSWORD).status_code == 200, "ikinci deneme şifreyi değiştirmemeli"
        assert client.get("/password-resets/preview", params={"token": created["token"]}).json()["status"] == "used"

    def test_weak_passwords_are_rejected_without_using_the_code(self, client, family):
        kid = invite_and_join(client, family)
        created = create_reset(client, family, kid)
        assert complete(client, created, password="kisa").status_code == 422
        assert complete(client, created, password="ş" * 40).status_code == 422
        assert complete(client, created).status_code == 200

    def test_two_people_racing_with_the_same_code_only_one_wins(self, client, family):
        kid = invite_and_join(client, family)
        created = create_reset(client, family, kid)

        def attempt(password):
            with TestClient(client.app) as other:
                return complete(other, created, password=password).status_code

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = sorted(pool.map(attempt, ["ilk-sifre-1234", "ikinci-sifre-1234"]))
        assert results == [200, 409]


class TestWrongCodesAndExpiry:
    def test_counts_down_and_locks_after_five_wrong_codes(self, client, family):
        kid = invite_and_join(client, family)
        created = create_reset(client, family, kid)
        messages = [complete(client, created, code=wrong(created)).json()["detail"] for _ in range(4)]
        assert messages == [f"Şifre hatalı. Kalan deneme hakkı: {n}" for n in (4, 3, 2, 1)]
        locked = complete(client, created, code=wrong(created))
        assert locked.status_code == 423 and "kilitlendi" in locked.json()["detail"]
        assert complete(client, created).status_code == 423, "kilitliyken doğru şifre de kabul edilmez"
        assert login(client, kid["username"], PASSWORD).status_code == 200, "şifre değişmemiş olmalı"

    def test_admin_unlocks_by_creating_a_new_link(self, client, family):
        kid = invite_and_join(client, family)
        locked = create_reset(client, family, kid)
        for _ in range(5):
            complete(client, locked, code=wrong(locked))
        renewed = create_reset(client, family, kid)
        assert complete(client, renewed).status_code == 200

    def test_expired_link_is_refused(self, client, family):
        kid = invite_and_join(client, family)
        created = create_reset(client, family, kid)
        set_db(created["token"], expires_at=datetime.now(timezone.utc) - timedelta(minutes=1))
        refused = complete(client, created)
        assert refused.status_code == 410 and "süresi dolmuş" in refused.json()["detail"]
        assert client.get("/password-resets/preview", params={"token": created["token"]}).json()["status"] == "expired"
        assert member_flags(client, family, family["owner"]["headers"], kid["user_id"])[1] is False

    def test_link_dies_when_the_account_is_removed_from_the_family(self, client, family):
        kid = invite_and_join(client, family)
        created = create_reset(client, family, kid)
        client.delete(f"/families/{family['family_id']}/members/{kid['user_id']}", headers=family["owner"]["headers"])
        response = complete(client, created)
        assert response.status_code == 410 and "aileden ayrılmış" in response.json()["detail"]
        assert login(client, kid["username"], PASSWORD).status_code == 200


class TestCancelling:
    def test_admin_can_cancel_a_pending_link(self, client, family):
        kid = invite_and_join(client, family)
        created = create_reset(client, family, kid)
        url = f"/families/{family['family_id']}/members/{kid['user_id']}/password-reset"
        assert client.delete(url, headers=family["owner"]["headers"]).status_code == 204
        assert complete(client, created).status_code == 404
        assert client.delete(url, headers=family["owner"]["headers"]).status_code == 404
        assert member_flags(client, family, family["owner"]["headers"], kid["user_id"]) == (True, False)

    def test_members_cannot_cancel(self, client, family):
        kid = invite_and_join(client, family)
        other = invite_and_join(client, family)
        create_reset(client, family, kid)
        response = client.delete(f"/families/{family['family_id']}/members/{kid['user_id']}/password-reset", headers=other["headers"])
        assert response.status_code == 403


class TestChangingYourOwnPassword:
    def test_changes_the_password_when_the_current_one_is_right(self, client, make_user):
        user = make_user("changer")
        response = client.post("/users/me/password", headers=user["headers"], json={"current_password": PASSWORD, "new_password": NEW_PASSWORD})
        assert response.status_code == 204
        assert login(client, user["email"], NEW_PASSWORD).status_code == 200
        assert login(client, user["email"], PASSWORD).status_code == 401

    def test_refuses_a_wrong_current_password_and_weak_new_one(self, client, make_user):
        user = make_user("changer")
        wrong_current = client.post("/users/me/password", headers=user["headers"], json={"current_password": "yanlis-sifre", "new_password": NEW_PASSWORD})
        assert wrong_current.status_code == 403 and wrong_current.json()["detail"] == "Mevcut şifre hatalı"
        assert client.post("/users/me/password", headers=user["headers"], json={"current_password": PASSWORD, "new_password": "kisa"}).status_code == 422
        assert login(client, user["email"], PASSWORD).status_code == 200

    def test_requires_login(self, client):
        assert client.post("/users/me/password", json={"current_password": "a", "new_password": NEW_PASSWORD}).status_code == 401
