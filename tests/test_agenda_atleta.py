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


def test_academy_catalog_item_is_saved_and_returned(client):
    """Regression: Gol de Placa uses catalogId, previously rejected with HTTP 422."""
    athlete = first_athlete(client)
    slot = {**sample_item(), "id": "catalog-event-1", "catalogId": "t2-ter"}
    response = client.put(f"/api/athletes/{athlete}/state", json={
        "revision": 0, "events": [slot], "available": []
    })
    assert response.status_code == 200, response.text
    saved = client.get(f"/api/athletes/{athlete}/state").json()
    assert saved["revision"] == 1
    assert saved["events"] == [slot]
    # A later ordinary save must also work after the catalog item was persisted.
    more = client.put(f"/api/athletes/{athlete}/state", json={
        "revision": 1, "events": [slot, sample_item("after-catalog")], "available": []
    })
    assert more.status_code == 200, more.text
    reloaded = client.get(f"/api/athletes/{athlete}/state").json()
    assert reloaded["events"][0]["catalogId"] == "t2-ter"
    assert len(reloaded["events"]) == 2


def test_existing_sqlite_schema_is_migrated_without_data_loss(tmp_path):
    """Migrates the published MVP schema while retaining events and athletes."""
    db = tmp_path / "old.sqlite3"
    with sqlite3.connect(db) as conn:
        conn.executescript("""
        CREATE TABLE athletes (id TEXT PRIMARY KEY, name TEXT NOT NULL, revision INTEGER NOT NULL DEFAULT 0);
        CREATE TABLE items (
            athlete_id TEXT NOT NULL REFERENCES athletes(id) ON DELETE CASCADE,
            collection TEXT NOT NULL CHECK(collection IN ('events', 'available')),
            id TEXT NOT NULL, position INTEGER NOT NULL, title TEXT NOT NULL,
            type TEXT NOT NULL, school TEXT NOT NULL, day INTEGER NOT NULL,
            start TEXT NOT NULL, end TEXT NOT NULL, location TEXT NOT NULL,
            notes TEXT NOT NULL, source_id TEXT,
            PRIMARY KEY(athlete_id, collection, id));
        INSERT INTO athletes (id,name,revision) VALUES ('legacy','Atleta Antigo',1);
        INSERT INTO items VALUES ('legacy','events','old',0,'Treino existente','training','Escola',1,'17:00','18:00','','',NULL);
        """)
    app = create_app(db, password=PASSWORD)
    auth = {"Authorization": "Basic " + base64.b64encode(f"admin:{PASSWORD}".encode()).decode()}
    with TestClient(app) as http:
        original = http.get("/api/athletes/legacy/state", headers=auth)
        assert original.status_code == 200
        assert original.json()["events"][0]["title"] == "Treino existente"
        assert original.json()["revision"] == 1
        old = original.json()["events"][0]
        new = {**sample_item("new"), "catalogId": "t2-ter"}
        response = http.put("/api/athletes/legacy/state", headers=auth,
                            json={"revision": 1, "events": [old, new], "available": []})
        assert response.status_code == 200, response.text
        persisted = http.get("/api/athletes/legacy/state", headers=auth).json()
        assert len(persisted["events"]) == 2
        assert persisted["events"][1]["catalogId"] == "t2-ter"
    with sqlite3.connect(db) as conn:
        assert "catalog_id" in {row[1] for row in conn.execute("PRAGMA table_info(items)")}
        assert conn.execute("SELECT COUNT(*) FROM athletes").fetchone()[0] == 1


def test_invalid_catalog_id_remains_rejected(client):
    athlete = first_athlete(client)
    invalid = {**sample_item(), "catalogId": "x" * 101}
    response = client.put(f"/api/athletes/{athlete}/state", json={
        "revision": 0, "events": [invalid], "available": []})
    assert response.status_code == 422