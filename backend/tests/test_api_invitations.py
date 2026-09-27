"""Aile daveti (bağlantı + tek kullanımlık şifre) ve e-postasız hesaplar. Gerçek veritabanına yazar (bkz. conftest)."""
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.database import SessionLocal
from app.models import FamilyInvitation
from tests.conftest import unique

pytestmark = pytest.mark.integration

PASSWORD = "guclusifre123"


def invite(client, family, label=None):
    body = {"label": label} if label is not None else None
    response = client.post(f"/families/{family['family_id']}/invitations", headers=family["owner"]["headers"], json=body)
    assert response.status_code == 201, response.text
    return response.json()


def join(client, invitation, code=None, username=None, **extra):
    payload = {
        "token": invitation["token"],
        "code": code or invitation["code"],
        "full_name": "Elif Yılmaz",
        "username": username or unique("kid"),
        "password": PASSWORD,
        **extra,
    }
    return client.post("/invitations/join", json=payload)


def wrong_code(invitation):
    return "000000" if invitation["code"] != "000000" else "111111"


def set_db(invitation_id, **fields):
    db = SessionLocal()
    try:
        row = db.get(FamilyInvitation, invitation_id)
        for key, value in fields.items():
            setattr(row, key, value)
        db.commit()
    finally:
        db.close()


class TestCreating:
    def test_creates_link_and_one_time_code_shown_once(self, client, family):
        created = invite(client, family, label="  Elif (kızım) ")
        assert re.fullmatch(r"\d{6}", created["code"])
        assert created["label"] == "Elif (kızım)"
        assert created["status"] == "pending" and len(created["token"]) >= 30

        listed = client.get(f"/families/{family['family_id']}/invitations", headers=family["owner"]["headers"]).json()
        assert [i["invitation_id"] for i in listed] == [created["invitation_id"]]
        assert all(i["code"] is None for i in listed), "şifre listede tekrar gösterilmemeli"
        assert "code_hash" not in listed[0]

    def test_each_invitation_has_a_different_token_and_code_space(self, client, family):
        tokens = {invite(client, family)["token"] for _ in range(3)}
        assert len(tokens) == 3

    def test_only_admins_can_create_list_regenerate_or_revoke(self, client, family, make_user):
        member = make_user("member")
        created = invite(client, family)
        assert join_as_existing(client, family, member, created).status_code == 200

        base = f"/families/{family['family_id']}/invitations"
        assert client.post(base, headers=member["headers"], json={}).status_code == 403
        assert client.get(base, headers=member["headers"]).status_code == 403
        assert client.post(f"{base}/{created['invitation_id']}/regenerate", headers=member["headers"]).status_code == 403
        assert client.delete(f"{base}/{created['invitation_id']}", headers=member["headers"]).status_code == 403

    def test_outsiders_cannot_see_the_family_at_all(self, client, family, make_user):
        outsider = make_user("outsider")
        assert client.post(f"/families/{family['family_id']}/invitations", headers=outsider["headers"], json={}).status_code == 404

    def test_limits_the_number_of_open_invitations(self, client, family, monkeypatch):
        monkeypatch.setattr("app.routers.invitations.MAX_OPEN_INVITATIONS", 2)
        invite(client, family)
        invite(client, family)
        blocked = client.post(f"/families/{family['family_id']}/invitations", headers=family["owner"]["headers"], json={})
        assert blocked.status_code == 409 and "iptal" in blocked.json()["detail"]


def join_as_existing(client, family, user, invitation, code=None):
    return client.post(
        "/invitations/accept",
        headers=user["headers"],
        json={"token": invitation["token"], "code": code or invitation["code"]},
    )


class TestPreview:
    def test_is_public_and_shows_family_and_inviter(self, client, family):
        created = invite(client, family, label="Elif")
        preview = client.get("/invitations/preview", params={"token": created["token"]})
        assert preview.status_code == 200
        body = preview.json()
        assert body["family_name"] == "Test Ailesi" and body["inviter_name"] == "Test owner"
        assert body["label"] == "Elif" and body["usable"] is True and body["status"] == "pending"
        assert "code" not in body and "token" not in body

    def test_unknown_token_is_404(self, client):
        assert client.get("/invitations/preview", params={"token": "yok"}).status_code == 404

    def test_reports_expired_and_used_and_locked(self, client, family):
        expired = invite(client, family)
        set_db(expired["invitation_id"], expires_at=datetime.now(timezone.utc) - timedelta(minutes=1))
        assert client.get("/invitations/preview", params={"token": expired["token"]}).json()["status"] == "expired"

        used = invite(client, family)
        assert join(client, used).status_code == 201
        preview = client.get("/invitations/preview", params={"token": used["token"]}).json()
        assert preview["status"] == "accepted" and preview["usable"] is False


class TestJoiningWithANewAccount:
    def test_child_without_email_can_join_and_log_in_with_username(self, client, family):
        created = invite(client, family)
        username = unique("elif")
        response = join(client, created, username=username.upper())
        assert response.status_code == 201, response.text
        body = response.json()
        assert body["family"]["family_id"] == family["family_id"] and body["family"]["role"] == "member"

        me = client.get("/auth/me", headers={"Authorization": f"Bearer {body['access_token']}"}).json()
        assert me["email"] is None and me["username"] == username, "kullanıcı adı küçük harfe çevrilir"

        for identifier in (username, username.upper(), f"  {username} "):
            login = client.post("/auth/login", data={"username": identifier, "password": PASSWORD})
            assert login.status_code == 200, identifier
        assert client.post("/auth/login", data={"username": username, "password": "yanlis-sifre"}).status_code == 401

    def test_member_appears_in_the_family_with_username(self, client, family):
        created = invite(client, family)
        username = unique("elif")
        join(client, created, username=username)
        detail = client.get(f"/families/{family['family_id']}", headers=family["owner"]["headers"]).json()
        assert detail["member_count"] == 2
        member = next(m for m in detail["members"] if m["username"] == username)
        assert member["full_name"] == "Elif Yılmaz" and member["role"] == "member"

    def test_optional_email_is_stored_and_usable_for_login(self, client, family):
        created = invite(client, family)
        email = f"{unique('mail')}@example.com"
        assert join(client, created, email=email).status_code == 201
        assert client.post("/auth/login", data={"username": email, "password": PASSWORD}).status_code == 200

    def test_the_code_works_only_once(self, client, family):
        created = invite(client, family)
        assert join(client, created).status_code == 201
        again = join(client, created)
        assert again.status_code == 409 and "kullanılmış" in again.json()["detail"]

    def test_code_may_be_typed_with_spaces_or_dashes(self, client, family):
        created = invite(client, family)
        spaced = f"{created['code'][:3]} {created['code'][3:]}"
        assert join(client, created, code=spaced).status_code == 201
        second = invite(client, family)
        assert join(client, second, code=f"{second['code'][:3]}-{second['code'][3:]}").status_code == 201

    def test_taken_username_or_email_does_not_burn_the_invitation(self, client, family, make_user):
        taken = make_user("taken")
        created = invite(client, family)
        by_email = join(client, created, email=taken["email"])
        assert by_email.status_code == 409 and "e-posta" in by_email.json()["detail"]

        first = join(client, created)
        assert first.status_code == 201
        second_invite = invite(client, family)
        username = unique("same")
        assert join(client, second_invite, username=username).status_code == 201
        third_invite = invite(client, family)
        clash = join(client, third_invite, username=username)
        assert clash.status_code == 409 and "kullanıcı adı" in clash.json()["detail"]
        retry = join(client, third_invite)
        assert retry.status_code == 201, "çakışma davet hakkını tüketmemeli"
        db = SessionLocal()
        try:
            assert db.get(FamilyInvitation, third_invite["invitation_id"]).failed_attempts == 0
        finally:
            db.close()

    @pytest.mark.parametrize(
        "username, fragment",
        [("ab", "3-30"), ("Elif Yilmaz", "3-30"), ("elif@mail", "3-30"), ("çocuk", "3-30"), ("a" * 31, "3-30"), ("-elif", "3-30")],
    )
    def test_rejects_invalid_usernames_in_turkish(self, client, family, username, fragment):
        created = invite(client, family)
        response = join(client, created, username=username)
        assert response.status_code == 422
        assert fragment in response.text and "Kullanıcı adı" in response.text

    def test_rejects_short_passwords_and_bad_email_without_using_the_code(self, client, family):
        created = invite(client, family)
        assert join(client, created, password="kisa").status_code == 422
        assert join(client, created, email="gecersiz").status_code == 422
        assert join(client, created).status_code == 201

    def test_two_people_racing_for_one_code_only_one_wins(self, client, family):
        created = invite(client, family)

        def attempt(_):
            with TestClient(client.app) as other:
                return join(other, created).status_code

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = sorted(pool.map(attempt, range(2)))
        assert results == [201, 409]
        detail = client.get(f"/families/{family['family_id']}", headers=family["owner"]["headers"]).json()
        assert detail["member_count"] == 2


class TestWrongCodesAndLocking:
    def test_counts_down_attempts_and_locks_after_five(self, client, family):
        created = invite(client, family)
        bad = wrong_code(created)
        messages = []
        for _ in range(4):
            response = join(client, created, code=bad)
            assert response.status_code == 403
            messages.append(response.json()["detail"])
        assert messages == [f"Şifre hatalı. Kalan deneme hakkı: {n}" for n in (4, 3, 2, 1)]

        locked = join(client, created, code=bad)
        assert locked.status_code == 423 and "kilitlendi" in locked.json()["detail"]

        even_correct = join(client, created)
        assert even_correct.status_code == 423, "kilitliyken doğru şifre de kabul edilmez"
        assert client.get("/invitations/preview", params={"token": created["token"]}).json()["status"] == "locked"

    def test_correct_code_within_the_limit_still_works(self, client, family):
        created = invite(client, family)
        for _ in range(4):
            join(client, created, code=wrong_code(created))
        assert join(client, created).status_code == 201

    def test_admin_can_unlock_with_a_new_code_and_the_old_one_dies(self, client, family):
        created = invite(client, family)
        for _ in range(5):
            join(client, created, code=wrong_code(created))
        listed = client.get(f"/families/{family['family_id']}/invitations", headers=family["owner"]["headers"]).json()
        assert listed[0]["status"] == "locked" and listed[0]["failed_attempts"] == 5

        renewed = client.post(
            f"/families/{family['family_id']}/invitations/{created['invitation_id']}/regenerate", headers=family["owner"]["headers"]
        ).json()
        assert re.fullmatch(r"\d{6}", renewed["code"]) and renewed["status"] == "pending" and renewed["failed_attempts"] == 0
        assert renewed["token"] == created["token"], "bağlantı değişmez, şifre değişir"

        if renewed["code"] != created["code"]:
            old = join(client, created, code=created["code"])
            assert old.status_code == 403
        assert join(client, renewed).status_code == 201

    def test_cannot_regenerate_a_used_invitation(self, client, family):
        created = invite(client, family)
        join(client, created)
        response = client.post(
            f"/families/{family['family_id']}/invitations/{created['invitation_id']}/regenerate", headers=family["owner"]["headers"]
        )
        assert response.status_code == 409

    def test_unknown_token_is_404_not_a_password_hint(self, client):
        response = client.post("/invitations/join", json={"token": "yok", "code": "123456", "full_name": "A", "username": unique("x"), "password": PASSWORD})
        assert response.status_code == 404


class TestExpiryAndRevoking:
    def test_expired_invitation_is_refused_and_regenerating_renews_it(self, client, family):
        created = invite(client, family)
        set_db(created["invitation_id"], expires_at=datetime.now(timezone.utc) - timedelta(minutes=1))
        refused = join(client, created)
        assert refused.status_code == 410 and "süresi dolmuş" in refused.json()["detail"]
        assert client.get(f"/families/{family['family_id']}/invitations", headers=family["owner"]["headers"]).json() == []

        renewed = client.post(
            f"/families/{family['family_id']}/invitations/{created['invitation_id']}/regenerate", headers=family["owner"]["headers"]
        ).json()
        assert join(client, renewed).status_code == 201

    def test_revoked_invitation_no_longer_works(self, client, family):
        created = invite(client, family)
        url = f"/families/{family['family_id']}/invitations/{created['invitation_id']}"
        assert client.delete(url, headers=family["owner"]["headers"]).status_code == 204
        assert client.delete(url, headers=family["owner"]["headers"]).status_code == 404
        assert join(client, created).status_code == 404


class TestExistingAccountJoining:
    def test_logged_in_user_joins_with_the_code(self, client, family, make_user):
        member = make_user("member")
        created = invite(client, family)
        response = join_as_existing(client, family, member, created)
        assert response.status_code == 200 and response.json()["role"] == "member"
        assert [f["family_id"] for f in client.get("/families", headers=member["headers"]).json()] == [family["family_id"]]

    def test_requires_login_and_the_right_code(self, client, family, make_user):
        member = make_user("member")
        created = invite(client, family)
        assert client.post("/invitations/accept", json={"token": created["token"], "code": created["code"]}).status_code == 401
        wrong = join_as_existing(client, family, member, created, code=wrong_code(created))
        assert wrong.status_code == 403 and "Kalan deneme hakkı: 4" in wrong.json()["detail"]

    def test_existing_member_cannot_reuse_and_does_not_burn_the_invitation(self, client, family, make_user):
        member = make_user("member")
        first = invite(client, family)
        join_as_existing(client, family, member, first)
        second = invite(client, family)
        again = join_as_existing(client, family, member, second)
        assert again.status_code == 409 and "Zaten" in again.json()["detail"]
        assert join(client, second).status_code == 201, "boşa harcanmamalı"


class TestFoundersOnlyDeletion:
    def test_family_reports_its_founder(self, client, family):
        summary = client.get("/families", headers=family["owner"]["headers"]).json()[0]
        assert summary["created_by"] == family["owner"]["user_id"]
        detail = client.get(f"/families/{family['family_id']}", headers=family["owner"]["headers"]).json()
        assert detail["created_by"] == family["owner"]["user_id"]

    def test_a_promoted_admin_cannot_delete_but_the_founder_can(self, client, family, make_user):
        other = make_user("other")
        created = invite(client, family)
        join_as_existing(client, family, other, created)
        promote = client.patch(
            f"/families/{family['family_id']}/members/{other['user_id']}", headers=family["owner"]["headers"], json={"role": "admin"}
        )
        assert promote.status_code == 200

        refused = client.delete(f"/families/{family['family_id']}", headers=other["headers"])
        assert refused.status_code == 403 and "kurucusu" in refused.json()["detail"]
        assert client.get(f"/families/{family['family_id']}", headers=other["headers"]).status_code == 200
        assert client.delete(f"/families/{family['family_id']}", headers=family["owner"]["headers"]).status_code == 204
        assert client.get(f"/families/{family['family_id']}", headers=other["headers"]).status_code == 404


class TestAccounts:
    def test_public_registration_still_needs_an_email(self, client):
        response = client.post("/auth/register", json={"password": PASSWORD, "full_name": "A"})
        assert response.status_code == 422

    def test_email_login_is_case_insensitive_and_error_is_generic(self, client, make_user):
        user = make_user("mail")
        assert client.post("/auth/login", data={"username": user["email"].upper(), "password": PASSWORD}).status_code == 200
        unknown = client.post("/auth/login", data={"username": "kimse", "password": PASSWORD})
        wrong = client.post("/auth/login", data={"username": user["email"], "password": "yanlis-sifre"})
        assert unknown.status_code == wrong.status_code == 401
        assert unknown.json() == wrong.json(), "hangi kullanıcıların var olduğu sızdırılmamalı"

    def test_old_email_invitation_endpoints_are_gone(self, client, make_user):
        user = make_user("gone")
        assert client.get("/invitations/mine", headers=user["headers"]).status_code in (404, 405, 422)
        assert client.post("/invitations/decline", headers=user["headers"], json={"token": "x"}).status_code in (404, 405, 422)
