"""Regression tests for Google's Requests transport and safe OAuth diagnostics."""
import base64
import logging
import os
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest
from fastapi.testclient import TestClient

from apps.agenda_atleta.app import create_app


def test_google_requests_transport_explicitly_installed():
    # The production verifier uses google.auth.transport.requests.Request,
    # which requires third-party 'requests' (not provided by google-auth itself).
    requirements = Path("apps/agenda_atleta/requirements.txt").read_text(encoding="utf-8")
    assert any(line.strip().startswith("requests>=") for line in requirements.splitlines())
    from google.auth.transport.requests import Request
    transport = Request()
    assert transport.session is not None
    transport.session.close()


@pytest.mark.parametrize("failing_stage", ["token_exchange", "id_token_verification"])
def test_callback_logs_only_safe_failure_category(tmp_path, caplog, failing_stage):
    def exchange(code, verifier):
        if failing_stage == "token_exchange":
            raise RuntimeError("secret-value-must-never-be-logged")
        return {"id_token": "private-id-token"}

    def verify(token, audience):
        raise RuntimeError("secret-value-must-never-be-logged")

    key = base64.urlsafe_b64encode(os.urandom(32)).decode()
    app = create_app(
        db_path=tmp_path / "oauth.sqlite3", encryption_key=key,
        client_id="client-id-for-test", client_secret="client-secret-for-test",
        redirect_uri="http://127.0.0.1:8000/auth/google/callback",
        token_exchange=exchange, token_verifier=verify,
    )
    with TestClient(app) as client, caplog.at_level(logging.WARNING, logger="apps.agenda_atleta.app"):
        started = client.get("/auth/google/start", follow_redirects=False)
        assert started.status_code == 302
        state = parse_qs(urlparse(started.headers["location"]).query)["state"][0]
        response = client.get(
            "/auth/google/callback",
            params={"state": state, "code": "private-auth-code"},
            follow_redirects=False,
        )
        assert response.status_code == 401
        assert response.json() == {"detail": "Falha ao verificar identidade Google"}
        entries = [record.getMessage() for record in caplog.records if record.name == "apps.agenda_atleta.app"]
        assert len(entries) == 1
        assert f"stage={failing_stage}" in entries[0]
        assert "exception=RuntimeError" in entries[0]
        for sensitive in ("secret-value", "private-id-token", "private-auth-code", "client-secret-for-test"):
            assert sensitive not in entries[0]
