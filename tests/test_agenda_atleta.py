import base64
from pathlib import Path
import sqlite3

from fastapi.testclient import TestClient
import pytest

from apps.agenda_atleta.app import create_app

PASSWORD = "senha-de-teste-longa"


@pytest.fixture
def client(tmp_path):
    app = create_app(db_path=tmp_path / "dados.sqlite3", password=PASSWORD)
    with TestClient(app) as http:
        http.headers["Authorization"] = "Basic " + base64.b64encode(f"admin:{PASSWORD}".encode()).decode()
        yield http


def first_athlete(client):
    result = client.get("/api/athletes")
    assert result.status_code == 200
    return result.json()[0]["id"]


def sample_item(id="evento-01", day=1, end="18:00"):
    return {"id": id, "title": "Treino Sub-8", "type": "training", "school": "Gol de Placa", "day": day,
            "start": "17:00", "end": end, "location": "Campo 1", "notes": "", "sourceId": "treino-10"}


def test_password_required(tmp_path):
    with pytest.raises(RuntimeError, match="APP_PASSWORD"):
        create_app(tmp_path / "x.sqlite3", password="curta")


def test_protection_includes_html_and_api(client):
    assert client.get("/", headers={"Authorization": ""}).status_code == 401
    denied = client.get("/api/athletes", headers={"Authorization": ""})
    assert denied.status_code == 401
    assert "Basic" in denied.headers["www-authenticate"]
    home = client.get("/")
    assert home.status_code == 200
    assert "Agenda do Atleta Pro" in home.text
    assert "Minha semana" in home.text
    assert home.headers["cache-control"] == "no-store"


def test_create_save_reload_and_isolation(client):
    first = first_athlete(client)
    second_result = client.post("/api/athletes", json={"name": "Atleta B"})
    assert second_result.status_code == 201
    second = second_result.json()["id"]
    payload = {"revision": 0, "events": [sample_item()], "available": [sample_item("treino-10", 3)]}
    saved = client.put(f"/api/athletes/{first}/state", json=payload)
    assert saved.status_code == 200, saved.text
    assert saved.json()["revision"] == 1
    state = client.get(f"/api/athletes/{first}/state").json()
    assert state["events"] == [sample_item()]
    assert state["available"] == [sample_item("treino-10", 3)]
    assert client.get(f"/api/athletes/{second}/state").json()["events"] == []
    another_save = client.put(f"/api/athletes/{second}/state", json={"revision": 0, "events": [], "available": []})
    assert another_save.status_code == 200
    assert client.get(f"/api/athletes/{first}/state").json()["revision"] == 1


def test_revision_conflict_keeps_data(client):
    athlete = first_athlete(client)
    first = {"revision": 0, "events": [sample_item()], "available": []}
    assert client.put(f"/api/athletes/{athlete}/state", json=first).status_code == 200
    stale = client.put(f"/api/athletes/{athlete}/state", json={"revision": 0, "events": [], "available": []})
    assert stale.status_code == 409
    assert len(client.get(f"/api/athletes/{athlete}/state").json()["events"]) == 1


@pytest.mark.parametrize("item", [
    sample_item(end="16:00"), sample_item(day=7), sample_item(end="33:00"),
    {**sample_item(), "title": "x" * 81}, {**sample_item(), "type": "unknown"},
])
def test_reject_invalid_items(client, item):
    athlete = first_athlete(client)
    response = client.put(f"/api/athletes/{athlete}/state", json={"revision": 0, "events": [item], "available": []})
    assert response.status_code == 422
    assert client.get(f"/api/athletes/{athlete}/state").json()["revision"] == 0


def test_reject_duplicate_ids(client):
    athlete = first_athlete(client)
    response = client.put(f"/api/athletes/{athlete}/state", json={"revision": 0, "events": [sample_item(), sample_item()], "available": []})
    assert response.status_code == 422


def test_rename_delete_and_last_athlete_guard(client):
    first = first_athlete(client)
    assert client.delete(f"/api/athletes/{first}").status_code == 409
    added = client.post("/api/athletes", json={"name": "Bia"}).json()["id"]
    assert client.patch(f"/api/athletes/{added}", json={"name": "  Bianca  "}).json()["name"] == "Bianca"
    assert client.delete(f"/api/athletes/{first}").status_code == 200
    assert len(client.get("/api/athletes").json()) == 1
    assert client.get(f"/api/athletes/{first}/state").status_code == 404


def test_sqlite_persistence_survives_restart(tmp_path):
    db = tmp_path / "agenda.sqlite3"
    first = create_app(db, password=PASSWORD)
    headers = {"Authorization": "Basic " + base64.b64encode(f"admin:{PASSWORD}".encode()).decode()}
    with TestClient(first) as http:
        who = http.get("/api/athletes", headers=headers).json()[0]["id"]
        response = http.put(f"/api/athletes/{who}/state", headers=headers, json={"revision": 0, "events": [sample_item()], "available": []})
        assert response.status_code == 200
    second = create_app(db, password=PASSWORD)
    with TestClient(second) as http:
        assert http.get(f"/api/athletes/{who}/state", headers=headers).json()["events"][0]["title"] == "Treino Sub-8"
    with sqlite3.connect(db) as conn:
        assert conn.execute("SELECT COUNT(*) FROM items").fetchone()[0] == 1


def test_html_keeps_original_sections_and_server_persistence(client):
    text = client.get("/").text
    for marker in ('id="section-overview"', 'id="section-library"', 'id="section-week"',
                   'id="section-academy"', 'id="section-summary"',
                   'id="academyCatalog"', 'id="importBtn"', 'id="exportBtn"',
                   'id="athleteSelect"', 'id="weekGrid"'):
        assert marker in text
    assert 'localStorage.setItem(KEY' not in text
    assert "/api/athletes" in text
    assert 'Salvo no banco' in text