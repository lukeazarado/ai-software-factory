"""Offline tests: mock OIDC exchange but exercise real session, CSRF, owner isolation and AES-GCM."""
import base64
import os
from pathlib import Path
import sqlite3
import time
from urllib.parse import urlparse, parse_qs

import pytest
from fastapi.testclient import TestClient

from apps.agenda_atleta.app import create_app

CLIENT_ID = "google-client-test"
SECRET = "google-secret-test"
LOCAL_URI = "http://127.0.0.1:8000/auth/google/callback"


def key():
    return base64.urlsafe_b64encode(os.urandom(32)).decode()


@pytest.fixture
def setup(tmp_path):
    db = tmp_path / "secure.sqlite3"
    secret = key()
    claims = {"sub": "google-person-1", "nonce": ""}

    def exchange(code, verifier):
        assert code == "verified-code"
        assert len(verifier) > 30
        return {"id_token": "verified-token"}

    def verify(token, aud):
        assert token == "verified-token"
        assert aud == CLIENT_ID
        return claims.copy()

    app = create_app(db, encryption_key=secret, client_id=CLIENT_ID, client_secret=SECRET,
                     redirect_uri=LOCAL_URI, token_exchange=exchange, token_verifier=verify)
    return app, db, secret, claims


def sign_in(client, db, claims, sub):
    claims["sub"] = sub
    response = client.get("/auth/google/start", follow_redirects=False)
    assert response.status_code == 302
    url = urlparse(response.headers["location"])
    assert url.hostname == "accounts.google.com"
    args = parse_qs(url.query)
    assert args["code_challenge_method"] == ["S256"]
    assert args["scope"] == ["openid email"]
    state = args["state"][0]
    with sqlite3.connect(db) as conn:
        claims["nonce"] = conn.execute("SELECT nonce FROM login_flows").fetchone()[0]
    callback = client.get("/auth/google/callback", params={"code": "verified-code", "state": state}, follow_redirects=False)
    assert callback.status_code == 303, callback.text
    assert callback.headers["location"] == "/"
    assert "HttpOnly" in callback.headers["set-cookie"]
    assert "samesite=lax" in callback.headers["set-cookie"].lower()
    return client.get("/api/auth/me").json()["csrfToken"]


def sample_item(item_id="item-1", **kwargs):
    return {"id": item_id, "title": "Consulta particular 123", "type": "training",
            "school": "Escola privada 123", "day": 2, "start": "15:00", "end": "16:00",
            "location": "Endereço privado 123", "notes": "Anotação pessoal 123", "catalogId": "t2-ter", **kwargs}


def test_required_security_config(tmp_path):
    with pytest.raises(RuntimeError, match="APP_ENCRYPTION_KEY"):
        create_app(tmp_path / "x.db", encryption_key="short", client_id=CLIENT_ID, client_secret=SECRET, redirect_uri=LOCAL_URI)
    with pytest.raises(RuntimeError, match="GOOGLE_CLIENT"):
        create_app(tmp_path / "x.db", encryption_key=key(), redirect_uri=LOCAL_URI)
    with pytest.raises(RuntimeError, match="HTTPS"):
        create_app(tmp_path / "x.db", encryption_key=key(), client_id=CLIENT_ID,
                   client_secret=SECRET, redirect_uri="http://example.org/auth/google/callback")


def test_requires_google_session(setup):
    app, db, _, claims = setup
    with TestClient(app) as client:
        assert client.get("/").status_code == 200  # redirects to safe login page
        assert client.get("/api/athletes").status_code == 401
        assert client.post("/api/athletes", json={"name": "X"}).status_code == 401
        assert client.get("/favicon.ico").status_code == 204
        assert client.get("/login").status_code == 200
        csrf = sign_in(client, db, claims, "user-1")
        assert client.get("/").status_code == 200
        assert "id=\"athleteSelect\"" in client.get("/").text
        assert "logoutBtn" in client.get("/").text
        assert csrf


def test_tenant_isolation_for_all_athlete_routes(setup):
    app, db, _, claims = setup
    with TestClient(app) as alice:
        csrf_a = sign_in(alice, db, claims, "google-alice")
        aid = alice.get("/api/athletes").json()[0]["id"]
        save = alice.put(f"/api/athletes/{aid}/state", headers={"X-CSRF-Token": csrf_a},
                         json={"revision": 0, "events": [sample_item()], "available": []})
        assert save.status_code == 200, save.text
        with TestClient(app) as bob:
            csrf_b = sign_in(bob, db, claims, "google-bob")
            b_id = bob.get("/api/athletes").json()[0]["id"]
            assert b_id != aid
            assert aid not in [x["id"] for x in bob.get("/api/athletes").json()]
            assert bob.get(f"/api/athletes/{aid}/state").status_code == 404
            assert bob.put(f"/api/athletes/{aid}/state", headers={"X-CSRF-Token": csrf_b},
                           json={"revision": 0, "events": [], "available": []}).status_code == 404
            assert bob.patch(f"/api/athletes/{aid}", headers={"X-CSRF-Token": csrf_b},
                             json={"name": "Invasão"}).status_code == 404
            assert bob.delete(f"/api/athletes/{aid}", headers={"X-CSRF-Token": csrf_b}).status_code == 404
            assert bob.get(f"/api/athletes/{b_id}/state").json()["events"] == []
        assert len(alice.get(f"/api/athletes/{aid}/state").json()["events"]) == 1


def test_all_sensitive_columns_encrypted_and_roundtrip(setup):
    app, db, _, claims = setup
    with TestClient(app) as client:
        csrf = sign_in(client, db, claims, "google-account-2")
        aid = client.post("/api/athletes", headers={"X-CSRF-Token": csrf},
                          json={"name": "Atleta Sigiloso 123"}).json()["id"]
        data = {"revision": 0, "events": [sample_item()], "available": [sample_item("item-2")]}
        response = client.put(f"/api/athletes/{aid}/state", headers={"X-CSRF-Token": csrf}, json=data)
        assert response.status_code == 200, response.text
        state = client.get(f"/api/athletes/{aid}/state").json()
        assert state["events"] == data["events"]
        assert state["available"] == data["available"]
        assert state["revision"] == 1
        assert any(x["name"] == "Atleta Sigiloso 123" for x in client.get("/api/athletes").json())
    raw = db.read_bytes()
    for private in (b"Atleta Sigiloso 123", b"Consulta particular 123", b"Escola privada 123", b"Endere\xc3\xa7o privado 123", b"Anota\xc3\xa7\xc3\xa3o pessoal 123"):
        assert private not in raw
    with sqlite3.connect(db) as conn:
        assert conn.execute("SELECT name_enc FROM athletes WHERE id=?", (aid,)).fetchone()[0].startswith("enc:v1:")
        assert conn.execute("SELECT title_enc FROM items LIMIT 1").fetchone()[0].startswith("enc:v1:")
        assert "name" not in {x[1] for x in conn.execute("PRAGMA table_info(athletes)")}


def test_csrf_and_logout(setup):
    app, db, _, claims = setup
    with TestClient(app) as client:
        csrf = sign_in(client, db, claims, "google-csrf")
        for method, path, json in [("POST", "/api/athletes", {"name": "Outro"}),
                                   ("PUT", "/api/athletes/fake/state", {"revision": 0, "events": [], "available": []}),
                                   ("PATCH", "/api/athletes/fake", {"name": "Outro"}),
                                   ("DELETE", "/api/athletes/fake", None),
                                   ("POST", "/api/auth/logout", None)]:
            assert client.request(method, path, json=json).status_code == 403
            assert client.request(method, path, headers={"X-CSRF-Token": "invalid"}, json=json).status_code == 403
        assert client.post("/api/auth/logout", headers={"X-CSRF-Token": csrf}).status_code == 204
        assert client.get("/api/athletes").status_code == 401


def test_validation_revision_catalog_and_isolation(setup):
    app, db, _, claims = setup
    with TestClient(app) as client:
        csrf = sign_in(client, db, claims, "google-verified")
        aid = client.get("/api/athletes").json()[0]["id"]
        headers = {"X-CSRF-Token": csrf}
        assert client.put(f"/api/athletes/{aid}/state", headers=headers,
                          json={"revision": 0, "events": [sample_item("bad", day=8)], "available": []}).status_code == 422
        saved = client.put(f"/api/athletes/{aid}/state", headers=headers,
                           json={"revision": 0, "events": [sample_item()], "available": []})
        assert saved.status_code == 200
        assert client.get(f"/api/athletes/{aid}/state").json()["events"][0]["catalogId"] == "t2-ter"
        assert client.put(f"/api/athletes/{aid}/state", headers=headers,
                          json={"revision": 0, "events": [], "available": []}).status_code == 409
        assert len(client.get(f"/api/athletes/{aid}/state").json()["events"]) == 1


def test_last_athlete_guard_and_delete_scope(setup):
    app, db, _, claims = setup
    with TestClient(app) as client:
        csrf = sign_in(client, db, claims, "google-1")
        headers = {"X-CSRF-Token": csrf}
        first = client.get("/api/athletes").json()[0]["id"]
        assert client.delete(f"/api/athletes/{first}", headers=headers).status_code == 409
        second = client.post("/api/athletes", headers=headers, json={"name": "B"}).json()["id"]
        assert client.patch(f"/api/athletes/{second}", headers=headers, json={"name": "C"}).status_code == 200
        assert client.delete(f"/api/athletes/{first}", headers=headers).status_code == 200
        assert client.get(f"/api/athletes/{first}/state").status_code == 404


def test_restart_with_same_key_preserves_data(setup):
    app, db, secret, claims = setup
    with TestClient(app) as c:
        sign_in(c, db, claims, "stable-google-sub")
        aid = c.get("/api/athletes").json()[0]["id"]
    app2 = create_app(db, encryption_key=secret, client_id=CLIENT_ID, client_secret=SECRET,
                      redirect_uri=LOCAL_URI, token_exchange=lambda *x: {"id_token": "t"},
                      token_verifier=lambda *x: {"sub": "stable-google-sub", "nonce": claims["nonce"]})
    with TestClient(app2) as c2:
        sign_in(c2, db, claims, "stable-google-sub")
        assert c2.get("/api/athletes").json()[0]["id"] == aid


def test_legacy_database_refuses_implicit_claim(tmp_path):
    db = tmp_path / "legacy.sqlite3"
    with sqlite3.connect(db) as conn:
        conn.execute("CREATE TABLE athletes (id TEXT PRIMARY KEY, name TEXT NOT NULL)")
        conn.execute("INSERT INTO athletes VALUES ('legacy', 'Personal Data - Secret')")
    with pytest.raises(RuntimeError, match="Banco legado"):
        create_app(db, encryption_key=key(), client_id=CLIENT_ID, client_secret=SECRET,
                   redirect_uri=LOCAL_URI)
    with sqlite3.connect(db) as conn:
        assert conn.execute("SELECT name FROM athletes").fetchone()[0] == "Personal Data - Secret"


def test_oauth_state_reuse_invalid_nonce_and_no_access(setup):
    app, db, _, claims = setup
    with TestClient(app) as c:
        assert c.get("/auth/google/callback", params={"code": "verified-code", "state": "unknown"}).status_code == 400
        start = c.get("/auth/google/start", follow_redirects=False)
        state = parse_qs(urlparse(start.headers["location"]).query)["state"][0]
        with sqlite3.connect(db) as conn:
            real_nonce = conn.execute("SELECT nonce FROM login_flows").fetchone()[0]
        claims["sub"] = "u1"
        claims["nonce"] = "wrong-nonce"
        assert c.get("/auth/google/callback", params={"code": "verified-code", "state": state}).status_code == 401
        assert c.get("/api/athletes").status_code == 401
        claims["nonce"] = real_nonce
        assert c.get("/auth/google/callback", params={"code": "verified-code", "state": state}).status_code == 400


def test_expired_session_denied(setup):
    app, db, _, claims = setup
    with TestClient(app) as c:
        sign_in(c, db, claims, "expiring-user")
        with sqlite3.connect(db) as conn:
            conn.execute("UPDATE sessions SET expires=?", (int(time.time()) - 1,))
        assert c.get("/api/athletes").status_code == 401


def test_secure_cookie_for_https(tmp_path):
    db = tmp_path / "secure.db"
    claims = {"sub": "person", "nonce": ""}
    app = create_app(db, encryption_key=key(), client_id=CLIENT_ID, client_secret=SECRET,
                     redirect_uri="https://app.example.org/auth/google/callback",
                     token_exchange=lambda *x: {"id_token": "t"}, token_verifier=lambda *x: claims.copy())
    with TestClient(app, base_url="https://app.example.org") as c:
        r = c.get("/auth/google/start", follow_redirects=False)
        assert "Secure" in r.headers["set-cookie"]
        state = parse_qs(urlparse(r.headers["location"]).query)["state"][0]
        with sqlite3.connect(db) as conn:
            claims["nonce"] = conn.execute("SELECT nonce FROM login_flows").fetchone()[0]
        r = c.get("/auth/google/callback", params={"code": "verified-code", "state": state}, follow_redirects=False)
        assert "Secure" in r.headers["set-cookie"]
        assert r.headers["strict-transport-security"]


def test_wrong_encryption_key_refuses_database(setup):
    _, db, _, _ = setup
    with pytest.raises(RuntimeError, match="APP_ENCRYPTION_KEY não corresponde"):
        create_app(db, encryption_key=key(), client_id=CLIENT_ID,
                   client_secret=SECRET, redirect_uri=LOCAL_URI)


def test_owner_cannot_reuse_other_owners_csrf(setup):
    app, db, _, claims = setup
    with TestClient(app) as first:
        csrf1 = sign_in(first, db, claims, "owner1")
        with TestClient(app) as second:
            csrf2 = sign_in(second, db, claims, "owner2")
            assert first.post("/api/athletes", headers={"X-CSRF-Token": csrf2}, json={"name": "A"}).status_code == 403
            assert second.post("/api/athletes", headers={"X-CSRF-Token": csrf1}, json={"name": "B"}).status_code == 403
            assert first.post("/api/athletes", headers={"X-CSRF-Token": csrf1}, json={"name": "A"}).status_code == 201


def test_source_and_catalog_id_saved_after_restart(setup):
    app, db, secret, claims = setup
    with TestClient(app) as c:
        csrf = sign_in(c, db, claims, "catalog-user")
        aid = c.get("/api/athletes").json()[0]["id"]
        event = {**sample_item(), "sourceId": "abc-123"}
        assert c.put(f"/api/athletes/{aid}/state", headers={"X-CSRF-Token": csrf},
                     json={"revision": 0, "events": [event], "available": []}).status_code == 200
    app2 = create_app(db, encryption_key=secret, client_id=CLIENT_ID, client_secret=SECRET,
                      redirect_uri=LOCAL_URI, token_exchange=lambda *x: {"id_token": "verified-token"},
                      token_verifier=lambda *x: claims.copy())
    with TestClient(app2) as c2:
        sign_in(c2, db, claims, "catalog-user")
        assert c2.get(f"/api/athletes/{aid}/state").json()["events"] == [event]
def test_owner_export_contains_only_own_athletes(setup):
    app, db, _, claims = setup
    with TestClient(app) as alice:
        csrf = sign_in(alice, db, claims, "export-alice")
        aid = alice.get("/api/athletes").json()[0]["id"]
        saved = alice.put(
            f"/api/athletes/{aid}/state", headers={"X-CSRF-Token": csrf},
            json={"revision": 0, "events": [sample_item()], "available": []},
        )
        assert saved.status_code == 200, saved.text
        with TestClient(app) as bob:
            sign_in(bob, db, claims, "export-bob")
            response = bob.get("/api/account/export")
            assert response.status_code == 200
            assert aid not in response.text
            assert "Consulta particular 123" not in response.text
        exported = alice.get("/api/account/export")
        assert exported.status_code == 200
        assert exported.headers["cache-control"] == "no-store"
        payload = exported.json()
        assert payload["format"] == "account-export-v1"
        assert payload["athletes"][0]["events"][0]["title"] == "Consulta particular 123"
        assert payload["athletes"][0]["id"] == aid
        assert "google-person-1" not in exported.text


def test_account_deletion_requires_csrf_and_exact_confirmation(setup):
    app, db, _, claims = setup
    with TestClient(app) as alice:
        csrf = sign_in(alice, db, claims, "remove-alice")
        aid = alice.get("/api/athletes").json()[0]["id"]
        with TestClient(app) as bob:
            sign_in(bob, db, claims, "remove-bob")
            bob_id = bob.get("/api/athletes").json()[0]["id"]
            invalid = alice.request("DELETE", "/api/account", json={"confirmation": "EXCLUIR_MINHA_CONTA_E_ATLETAS"})
            assert invalid.status_code == 403
            invalid = alice.request("DELETE", "/api/account", headers={"X-CSRF-Token": csrf},
                                    json={"confirmation": "sim"})
            assert invalid.status_code == 400
            assert alice.get("/api/athletes").status_code == 200
            done = alice.request("DELETE", "/api/account", headers={"X-CSRF-Token": csrf},
                                 json={"confirmation": "EXCLUIR_MINHA_CONTA_E_ATLETAS"})
            assert done.status_code == 204
            assert alice.get("/api/account/export").status_code == 401
            assert bob.get("/api/athletes").json()[0]["id"] == bob_id
            assert bob.get(f"/api/athletes/{aid}/state").status_code == 404
            with sqlite3.connect(db) as conn:
                assert conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 1
                assert conn.execute("SELECT COUNT(*) FROM athletes").fetchone()[0] == 1

def test_privacy_notice_and_explicit_adult_acknowledgement(setup):
    app, db, _, claims = setup
    with TestClient(app) as client:
        assert client.get("/account").status_code == 401
        assert client.get("/api/privacy").status_code == 401
        csrf = sign_in(client, db, claims, "privacy-user")
        notice = client.get("/api/privacy")
        assert notice.status_code == 200
        assert notice.json()["status"] == "draft_pending_legal_review"
        assert client.get("/account").status_code == 200
        assert client.get("/static/account.js").status_code == 200
        assert client.get("/static/account.css").status_code == 200
        assert not client.get("/api/privacy/ack").json()["acknowledged"]
        invalid = client.post("/api/privacy/ack", json={"read_notice": True, "responsible_adult": True})
        assert invalid.status_code == 403
        invalid = client.post("/api/privacy/ack", headers={"X-CSRF-Token": csrf},
                              json={"read_notice": True, "responsible_adult": False})
        assert invalid.status_code == 400
        acknowledged = client.post("/api/privacy/ack", headers={"X-CSRF-Token": csrf},
                                    json={"read_notice": True, "responsible_adult": True})
        assert acknowledged.status_code == 200
        assert acknowledged.json()["acknowledged"]
        assert client.get("/api/privacy/ack").json()["adult_statement"] is True
        with sqlite3.connect(db) as conn:
            assert conn.execute("SELECT COUNT(*) FROM privacy_ack").fetchone()[0] == 1


def test_privacy_declaration_is_scoped_and_erased_with_owner(setup):
    app, db, _, claims = setup
    with TestClient(app) as alice:
        csrf_a = sign_in(alice, db, claims, "ack-alice")
        assert alice.post("/api/privacy/ack", headers={"X-CSRF-Token":csrf_a},
                          json={"read_notice":True,"responsible_adult":True}).status_code == 200
        with TestClient(app) as bob:
            sign_in(bob, db, claims, "ack-bob")
            assert not bob.get("/api/privacy/ack").json()["acknowledged"]
            assert alice.request("DELETE", "/api/account", headers={"X-CSRF-Token":csrf_a},
                                  json={"confirmation":"EXCLUIR_MINHA_CONTA_E_ATLETAS"}).status_code == 204
            with sqlite3.connect(db) as conn:
                assert conn.execute("SELECT COUNT(*) FROM privacy_ack").fetchone()[0] == 0
            assert bob.get("/api/athletes").status_code == 200

def test_schedule_is_ciphertext_and_roundtrips(setup):
    app, db, _, claims = setup
    with TestClient(app) as client:
        csrf = sign_in(client, db, claims, "schedule-private")
        aid = client.get("/api/athletes").json()[0]["id"]
        saved = client.put(f"/api/athletes/{aid}/state", headers={"X-CSRF-Token": csrf},
                           json={"revision": 0, "events": [sample_item()], "available": []})
        assert saved.status_code == 200, saved.text
        assert client.get(f"/api/athletes/{aid}/state").json()["events"][0]["start"] == "15:00"
        assert client.get("/api/account/export").json()["athletes"][0]["events"][0]["day"] == 2
    with sqlite3.connect(db) as conn:
        names = {row[1] for row in conn.execute("PRAGMA table_info(items)")}
        assert "schedule_enc" in names
        assert not {"day", "start", "end"} & names
        assert conn.execute("SELECT schedule_enc FROM items LIMIT 1").fetchone()[0].startswith("enc:v1:")
    assert b"15:00" not in db.read_bytes()


def test_owned_database_schedule_migrates_transactionally(setup):
    app, db, secret, claims = setup
    with TestClient(app) as client:
        csrf = sign_in(client, db, claims, "schedule-migration")
        aid = client.get("/api/athletes").json()[0]["id"]
        assert client.put(f"/api/athletes/{aid}/state", headers={"X-CSRF-Token": csrf},
                          json={"revision": 0, "events": [sample_item()], "available": []}).status_code == 200
    # Rebuild a copy of the old owned-DB schema to reproduce an existing installation.
    with sqlite3.connect(db) as conn:
        conn.executescript("""
            ALTER TABLE items RENAME TO items_encrypted_old;
            CREATE TABLE items (
                athlete_id TEXT NOT NULL REFERENCES athletes(id) ON DELETE CASCADE,
                collection TEXT NOT NULL CHECK(collection IN ('events','available')),
                id TEXT NOT NULL, position INTEGER NOT NULL,
                title_enc TEXT NOT NULL, school_enc TEXT NOT NULL,
                location_enc TEXT NOT NULL, notes_enc TEXT NOT NULL,
                type TEXT NOT NULL, day INTEGER NOT NULL, start TEXT NOT NULL, end TEXT NOT NULL,
                source_id TEXT, catalog_id TEXT,
                PRIMARY KEY (athlete_id, collection, id)
            );
            INSERT INTO items(athlete_id,collection,id,position,title_enc,school_enc,
                             location_enc,notes_enc,type,day,start,end,source_id,catalog_id)
                SELECT athlete_id,collection,id,position,title_enc,school_enc,
                       location_enc,notes_enc,type,2,'15:00','16:00',source_id,catalog_id
                FROM items_encrypted_old;
            DROP TABLE items_encrypted_old;
        """)
    migrated = create_app(db, encryption_key=secret, client_id=CLIENT_ID, client_secret=SECRET,
                          redirect_uri=LOCAL_URI, token_exchange=lambda *args: {"id_token":"verified-token"},
                          token_verifier=lambda *args: claims.copy())
    with TestClient(migrated) as client:
        sign_in(client, db, claims, "schedule-migration")
        state = client.get(f"/api/athletes/{aid}/state").json()
        assert state["events"][0]["start"] == "15:00"
        assert state["events"][0]["title"] == "Consulta particular 123"
        assert state["revision"] == 1
    with sqlite3.connect(db) as conn:
        columns = {row[1] for row in conn.execute("PRAGMA table_info(items)")}
        assert "schedule_enc" in columns and "start" not in columns
        assert conn.execute("SELECT COUNT(*) FROM items").fetchone()[0] == 1
