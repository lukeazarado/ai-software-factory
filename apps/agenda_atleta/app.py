"""Single-tenant, password-protected sports scheduling API with SQLite persistence."""
from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
import base64
import binascii
import os
import re
import secrets
import sqlite3
import uuid

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

WEB_FILE = Path(__file__).resolve().parent / "web" / "index.html"
TIME = re.compile(r"^(?:[01][0-9]|2[0-3]):[0-5][0-9]$")


class Item(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(min_length=1, max_length=100)
    title: str = Field(min_length=1, max_length=80)
    type: str
    school: str = Field(default="", max_length=100)
    day: int = Field(ge=0, le=6)
    start: str
    end: str = ""
    location: str = Field(default="", max_length=100)
    notes: str = Field(default="", max_length=300)
    sourceId: str | None = Field(default=None, max_length=100)

    @field_validator("type")
    @classmethod
    def kind(cls, value: str) -> str:
        if value not in ("training", "game", "other"):
            raise ValueError("Tipo de atividade inválido")
        return value

    @model_validator(mode="after")
    def valid_time(self):
        if not TIME.fullmatch(self.start):
            raise ValueError("Horário inicial inválido")
        if self.end and (not TIME.fullmatch(self.end) or self.end <= self.start):
            raise ValueError("O horário final precisa ser posterior ao inicial")
        return self


class State(BaseModel):
    model_config = ConfigDict(extra="forbid")
    revision: int = Field(ge=0)
    events: list[Item]
    available: list[Item]

    @model_validator(mode="after")
    def unique_items(self):
        if len(self.events) + len(self.available) > 20000:
            raise ValueError("Limite de 20.000 itens excedido")
        for group in (self.events, self.available):
            ids = [item.id for item in group]
            if len(ids) != len(set(ids)):
                raise ValueError("IDs repetidos na coleção")
        return self


class AthleteName(BaseModel):
    name: str = Field(min_length=1, max_length=80)

    @field_validator("name")
    @classmethod
    def trim_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Nome do atleta obrigatório")
        return value


def create_app(db_path: str | Path | None = None, password: str | None = None) -> FastAPI:
    """Require an explicit password even for local development. No embedded secrets."""
    password = password if password is not None else os.getenv("APP_PASSWORD", "")
    if len(password) < 12:
        raise RuntimeError("Defina APP_PASSWORD com pelo menos 12 caracteres no ambiente")
    db = Path(db_path or os.getenv("APP_DB_PATH", "data/agenda_atleta.sqlite3")).resolve()
    db.parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def connection():
        conn = sqlite3.connect(db, timeout=10, isolation_level=None)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA busy_timeout=10000")
        try:
            yield conn
        finally:
            conn.close()

    with connection() as conn:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS athletes (
            id TEXT PRIMARY KEY, name TEXT NOT NULL, revision INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS items (
            athlete_id TEXT NOT NULL REFERENCES athletes(id) ON DELETE CASCADE,
            collection TEXT NOT NULL CHECK(collection IN ('events', 'available')),
            id TEXT NOT NULL, position INTEGER NOT NULL, title TEXT NOT NULL,
            type TEXT NOT NULL, school TEXT NOT NULL, day INTEGER NOT NULL,
            start TEXT NOT NULL, end TEXT NOT NULL, location TEXT NOT NULL,
            notes TEXT NOT NULL, source_id TEXT,
            PRIMARY KEY(athlete_id, collection, id)
        );
        CREATE INDEX IF NOT EXISTS idx_items_athlete ON items(athlete_id, collection, position);
        """)
        if not conn.execute("SELECT 1 FROM athletes LIMIT 1").fetchone():
            conn.execute("INSERT INTO athletes (id, name) VALUES (?, ?)", (uuid.uuid4().hex, "Atleta principal"))

    app = FastAPI(title="Agenda do Atleta Pro API", docs_url=None, redoc_url=None, openapi_url=None)

    @app.middleware("http")
    async def no_cache(request: Request, call_next):
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        return response

    def authorize(request: Request):
        header = request.headers.get("Authorization", "")
        if header.startswith("Basic "):
            try:
                decoded = base64.b64decode(header[6:], validate=True).decode("utf-8")
                username, supplied = decoded.split(":", 1)
                if secrets.compare_digest(username, "admin") and secrets.compare_digest(supplied, password):
                    return
            except (ValueError, UnicodeDecodeError, binascii.Error):
                pass
        raise HTTPException(status_code=401, detail="Autenticação necessária", headers={"WWW-Authenticate": 'Basic realm="Agenda do Atleta", charset="UTF-8"'})

    def ensure_athlete(conn, athlete_id: str):
        row = conn.execute("SELECT id,name,revision FROM athletes WHERE id=?", (athlete_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Atleta não encontrado")
        return row

    @app.get("/", dependencies=[Depends(authorize)], include_in_schema=False)
    def home():
        return FileResponse(WEB_FILE, media_type="text/html; charset=utf-8")

    @app.get("/api/athletes", dependencies=[Depends(authorize)])
    def list_athletes():
        with connection() as conn:
            return [dict(x) for x in conn.execute("SELECT id,name FROM athletes ORDER BY name COLLATE NOCASE, id")]

    @app.post("/api/athletes", status_code=201, dependencies=[Depends(authorize)])
    def add_athlete(data: AthleteName):
        athlete_id = uuid.uuid4().hex
        with connection() as conn:
            conn.execute("INSERT INTO athletes (id,name) VALUES (?,?)", (athlete_id, data.name))
        return {"id": athlete_id, "name": data.name}

    @app.patch("/api/athletes/{athlete_id}", dependencies=[Depends(authorize)])
    def rename_athlete(athlete_id: str, data: AthleteName):
        with connection() as conn:
            ensure_athlete(conn, athlete_id)
            conn.execute("UPDATE athletes SET name=? WHERE id=?", (data.name, athlete_id))
        return {"id": athlete_id, "name": data.name}

    @app.delete("/api/athletes/{athlete_id}", dependencies=[Depends(authorize)])
    def delete_athlete(athlete_id: str):
        with connection() as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                ensure_athlete(conn, athlete_id)
                if conn.execute("SELECT COUNT(*) FROM athletes").fetchone()[0] <= 1:
                    raise HTTPException(409, "Não é possível excluir o último atleta")
                conn.execute("DELETE FROM athletes WHERE id=?", (athlete_id,))
                conn.commit()
            except Exception:
                conn.rollback()
                raise
        return {"deleted": True}

    @app.get("/api/athletes/{athlete_id}/state", dependencies=[Depends(authorize)])
    def read_state(athlete_id: str):
        with connection() as conn:
            athlete = ensure_athlete(conn, athlete_id)
            result = {"revision": athlete["revision"], "events": [], "available": []}
            rows = conn.execute("SELECT * FROM items WHERE athlete_id=? ORDER BY collection,position", (athlete_id,))
            for row in rows:
                item = dict(id=row["id"], title=row["title"], type=row["type"], school=row["school"],
                            day=row["day"], start=row["start"], end=row["end"],
                            location=row["location"], notes=row["notes"])
                if row["source_id"]:
                    item["sourceId"] = row["source_id"]
                result[row["collection"]].append(item)
            return result

    @app.put("/api/athletes/{athlete_id}/state", dependencies=[Depends(authorize)])
    def write_state(athlete_id: str, data: State):
        with connection() as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                athlete = ensure_athlete(conn, athlete_id)
                if athlete["revision"] != data.revision:
                    raise HTTPException(409, "Agenda alterada em outra sessão. Recarregue a página antes de editar novamente.")
                conn.execute("DELETE FROM items WHERE athlete_id=?", (athlete_id,))
                for collection in ("events", "available"):
                    for position, item in enumerate(getattr(data, collection)):
                        conn.execute("""INSERT INTO items
                            (athlete_id,collection,id,position,title,type,school,day,start,end,location,notes,source_id)
                            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                            (athlete_id, collection, item.id, position, item.title, item.type, item.school,
                             item.day, item.start, item.end, item.location, item.notes, item.sourceId))
                new_revision = athlete["revision"] + 1
                conn.execute("UPDATE athletes SET revision=? WHERE id=?", (new_revision, athlete_id))
                conn.commit()
            except Exception:
                conn.rollback()
                raise
        return {"revision": new_revision, "saved": True}

    return app


# For uvicorn, configuration is required in the process environment.
# Initialization is deferred so importing this module in unit tests has no side effects.
def app_factory():
    return create_app()