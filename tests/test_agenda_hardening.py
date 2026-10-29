"""Regressões TL-01/TL-03/TL-05: ativos locais, rate limiting, backup/restore."""
import base64
import os
from pathlib import Path
import sqlite3
import time
from urllib.parse import parse_qs, urlparse

import pytest
from fastapi.testclient import TestClient

from apps.agenda_atleta.app import create_app, LOGIN_LIMIT, LOGIN_MAX_PENDING, LOGIN_WINDOW
from apps.agenda_atleta.backup import create_backup


@pytest.fixture
def secure_app(tmp_path):
    db = tmp_path / "test.sqlite3"
    secret = base64.urlsafe_b64encode(os.urandom(32)).decode()
    claims = {"sub": "runner-user", "nonce": ""}
    def exchange(code, verifier):
        assert code == "test-code"
        assert verifier
        return {"id_token": "id-token"}
    def verify(token, aud):
        assert token == "id-token"
        assert aud == "test-client-id"
        return claims.copy()
    def app_for(path):
        return create_app(path, encryption_key=secret, client_id="test-client-id", client_secret="test-client-secret",
                          redirect_uri="http://127.0.0.1:8000/auth/google/callback",
                          token_exchange=exchange, token_verifier=verify)
    return app_for, db, claims


def login(client, db, claims):
    resp = client.get("/auth/google/start", follow_redirects=False)
    assert resp.status_code == 302
    state = parse_qs(urlparse(resp.headers["location"]).query)["state"][0]
    with sqlite3.connect(db) as conn:
        claims["nonce"] = conn.execute("SELECT nonce FROM login_flows WHERE state_hash=(SELECT state_hash FROM login_flows ORDER BY rowid DESC LIMIT 1)").fetchone()[0]
    resp = client.get("/auth/google/callback", params={"state": state, "code": "test-code"}, follow_redirects=False)
    assert resp.status_code == 303, resp.text
    return client.get("/api/auth/me").json()["csrfToken"]


def test_strict_csp_and_local_assets(secure_app):
    make, db, claims = secure_app
    with TestClient(make(db)) as client:
        login_page = client.get("/login")
        assert login_page.status_code == 200
        assert 'href="/static/login.css"' in login_page.text
        assert "style=" not in login_page.text
        assert client.get("/static/login.css").status_code == 200
        assert client.get("/static/app.js").status_code == 401
        assert client.get("/static/app.css").status_code == 401
        csrf = login(client, db, claims)
        page = client.get("/")
        assert page.status_code == 200
        assert '<script defer src="/static/app.js"></script>' in page.text
        assert '<link rel="stylesheet" href="/static/app.css">' in page.text
        assert '<script>' not in page.text and '<style>' not in page.text
        assert "cdn.tailwindcss.com" not in page.text
        assert "style=" not in page.text
        csp = page.headers["content-security-policy"]
        assert "script-src 'self'" in csp and "style-src 'self'" in csp
        assert "unsafe-inline" not in csp and "https://" not in csp
        assert "script-src 'self'" in login_page.headers["content-security-policy"]
        js = client.get("/static/app.js")
        css = client.get("/static/app.css")
        assert js.status_code == 200 and "javascript" in js.headers["content-type"]
        assert css.status_code == 200 and "css" in css.headers["content-type"]
        assert "school-color-0" in css.text and "academy-color-0" in css.text
        assert "@tailwind" not in css.text and "@import" not in css.text
        assert "style=\"" not in js.text
        assert csrf


def test_rate_limit_and_retry_after_ignores_forwarded_headers(secure_app):
    make, db, _ = secure_app
    with TestClient(make(db)) as client:
        for i in range(LOGIN_LIMIT):
            resp = client.get("/auth/google/start", headers={"X-Forwarded-For": f"10.0.0.{i+1}"}, follow_redirects=False)
            assert resp.status_code == 302
        denied = client.get("/auth/google/start", headers={"X-Forwarded-For": "1.1.1.1"}, follow_redirects=False)
        assert denied.status_code == 429
        assert 0 < int(denied.headers["retry-after"]) <= LOGIN_WINDOW
        with sqlite3.connect(db) as conn:
            assert conn.execute("SELECT SUM(attempts) FROM login_attempts").fetchone()[0] == LOGIN_LIMIT
            assert conn.execute("SELECT COUNT(*) FROM login_flows").fetchone()[0] == LOGIN_LIMIT
            conn.execute("UPDATE login_attempts SET window_start=?", (int(time.time()) - LOGIN_WINDOW - 1,))
        assert client.get("/auth/google/start", follow_redirects=False).status_code == 302


def test_global_oauth_flow_cap(secure_app):
    make, db, _ = secure_app
    with TestClient(make(db)) as client:
        with sqlite3.connect(db) as conn:
            conn.executemany("INSERT INTO login_flows(state_hash,verifier,nonce,expires) VALUES (?,?,?,?)",
                             ((f"flow{i}", "verifier", "nonce", int(time.time())+300) for i in range(LOGIN_MAX_PENDING)))
        res = client.get("/auth/google/start", follow_redirects=False)
        assert res.status_code == 503
        assert res.headers["retry-after"] == "60"
        with sqlite3.connect(db) as conn:
            assert conn.execute("SELECT COUNT(*) FROM login_flows").fetchone()[0] == LOGIN_MAX_PENDING


def test_consistent_sqlite_backup_and_restore_with_same_key(secure_app, tmp_path):
    make, db, claims = secure_app
    app = make(db)
    with TestClient(app) as client:
        csrf = login(client, db, claims)
        aid = client.get("/api/athletes").json()[0]["id"]
        entry = {"id": "my-entry", "title": "Segredo pessoal", "type": "training", "school": "Clube", "day": 4,
                 "start": "18:00", "end": "19:00", "location": "Endereço particular", "notes": "Notas privadas"}
        assert client.put(f"/api/athletes/{aid}/state", headers={"X-CSRF-Token": csrf}, json={"revision": 0, "events": [entry], "available": []}).status_code == 200
        out = tmp_path / "backup.sqlite3"
        create_backup(db, out)
        assert out.read_bytes() and b"Segredo pessoal" not in out.read_bytes()
        assert b"Endere\xc3\xa7o particular" not in out.read_bytes()
        with pytest.raises(FileExistsError):
            create_backup(db, out)
        with pytest.raises(ValueError):
            create_backup(db, db)
    restored_db = tmp_path / "restored.sqlite3"
    restored_db.write_bytes(out.read_bytes())
    with TestClient(make(restored_db)) as restored:
        claims["sub"] = "runner-user"
        login(restored, restored_db, claims)
        assert restored.get("/api/athletes").json()[0]["id"] == aid
        assert restored.get(f"/api/athletes/{aid}/state").json()["events"] == [entry]