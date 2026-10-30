"""Agenda do Atleta: Google OIDC, owner-scoped APIs and field-level AES-GCM at rest.

The legacy unowned SQLite database is NEVER opened/migrated by this app.
"""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from urllib.parse import urlencode, urlparse
import base64
import hmac
import json
import logging
import os
import re
import secrets
import sqlite3
import time
import uuid

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, RedirectResponse, Response
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

WEB_DIR = Path(__file__).resolve().parent / "web"
WEB_FILE = WEB_DIR / "index.html"
LOGIN_WINDOW = 10 * 60
LOGIN_LIMIT = 10
LOGIN_MAX_PENDING = 500
TIME = re.compile(r"^(?:[01][0-9]|2[0-3]):[0-5][0-9]$")
SESSION_TTL = 12 * 60 * 60
OAUTH_TTL = 10 * 60


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
    catalogId: str | None = Field(default=None, max_length=100)

    @field_validator("type")
    @classmethod
    def valid_type(cls, value):
        if value not in ("training", "game", "other"):
            raise ValueError("Tipo inválido")
        return value

    @model_validator(mode="after")
    def valid_time(self):
        if not TIME.fullmatch(self.start):
            raise ValueError("Hora inicial inválida")
        if self.end and (not TIME.fullmatch(self.end) or self.end <= self.start):
            raise ValueError("Hora final deve ser posterior à inicial")
        return self


class State(BaseModel):
    model_config = ConfigDict(extra="forbid")
    revision: int = Field(ge=0)
    events: list[Item]
    available: list[Item]

    @model_validator(mode="after")
    def unique_items(self):
        if len(self.events) + len(self.available) > 20_000:
            raise ValueError("Limite de itens excedido")
        for collection in (self.events, self.available):
            ids = [x.id for x in collection]
            if len(ids) != len(set(ids)):
                raise ValueError("IDs duplicados")
        return self


NOTICE_VERSION = "2026-10-30-draft-1"


class PrivacyAcknowledgement(BaseModel):
    model_config = ConfigDict(extra="forbid")
    read_notice: bool
    responsible_adult: bool


class AccountDeletionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    confirmation: str


class AthleteName(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=80)

    @field_validator("name")
    @classmethod
    def trim_name(cls, value):
        value = value.strip()
        if not value:
            raise ValueError("Nome obrigatório")
        return value


def parse_key(value: str) -> bytes:
    try:
        key = base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))
    except (ValueError, base64.binascii.Error) as exc:
        raise RuntimeError("APP_ENCRYPTION_KEY inválida") from exc
    if len(key) != 32:
        raise RuntimeError("APP_ENCRYPTION_KEY precisa codificar 32 bytes")
    return key


def create_app(db_path=None, *, encryption_key=None, client_id=None, client_secret=None,
               redirect_uri=None, token_exchange=None, token_verifier=None) -> FastAPI:
    """Mocks accepted only as Python callables supplied by tests, never via HTTP."""
    key_value = encryption_key or os.environ.get("APP_ENCRYPTION_KEY", "")
    key = parse_key(key_value) if isinstance(key_value, str) else key_value
    if not isinstance(key, bytes) or len(key) != 32:
        raise RuntimeError("Configure APP_ENCRYPTION_KEY com 32 bytes em base64 URL-safe")
    client_id = client_id or os.environ.get("GOOGLE_CLIENT_ID", "")
    client_secret = client_secret or os.environ.get("GOOGLE_CLIENT_SECRET", "")
    redirect_uri = redirect_uri or os.environ.get("GOOGLE_REDIRECT_URI", "")
    if not client_id or not client_secret or not redirect_uri:
        raise RuntimeError("Configure GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET e GOOGLE_REDIRECT_URI")
    target = urlparse(redirect_uri)
    if target.path != "/auth/google/callback" or target.query or target.fragment or not target.hostname:
        raise RuntimeError("GOOGLE_REDIRECT_URI inválida")
    if target.scheme != "https" and not (target.scheme == "http" and target.hostname in ("localhost", "127.0.0.1")):
        raise RuntimeError("HTTPS é obrigatório fora de localhost")
    secure_cookie = target.scheme == "https"
    db = Path(db_path or os.getenv("APP_DB_PATH", "data/agenda_atleta_secure.sqlite3")).resolve()
    db.parent.mkdir(parents=True, exist_ok=True)
    aes = AESGCM(key)

    def encrypted(value, aad):
        nonce = secrets.token_bytes(12)
        payload = nonce + aes.encrypt(nonce, value.encode("utf-8"), aad.encode("utf-8"))
        return "enc:v1:" + base64.urlsafe_b64encode(payload).decode("ascii")

    def decrypted(value, aad):
        if not value.startswith("enc:v1:"):
            raise RuntimeError("Dado não criptografado no banco seguro")
        payload = base64.urlsafe_b64decode(value[7:])
        return aes.decrypt(payload[:12], payload[12:], aad.encode("utf-8")).decode("utf-8")

    def owner_key(sub):
        return hmac.new(key, b"google-sub:" + sub.encode(), sha256).hexdigest()

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
        # Refuse accidental access to the legacy shared/unowned database; no automatic migration.
        existing = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='athletes'").fetchone()
        if existing:
            columns = {x[1] for x in conn.execute("PRAGMA table_info(athletes)")}
            if "owner_id" not in columns or "name_enc" not in columns or "name" in columns:
                raise RuntimeError("Banco legado detectado: mantenha-o intacto; use um APP_DB_PATH novo e importe backups JSON")
        existing_items = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='items'").fetchone()
        if existing_items:
            item_columns = {x[1] for x in conn.execute("PRAGMA table_info(items)")}
            if not {"title_enc", "school_enc", "location_enc", "notes_enc"}.issubset(item_columns) or "title" in item_columns:
                raise RuntimeError("Tabela de atividades legada detectada: faça backup e use um banco seguro novo")
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (id TEXT PRIMARY KEY);
        CREATE TABLE IF NOT EXISTS athletes (
            id TEXT PRIMARY KEY, owner_id TEXT NOT NULL REFERENCES users(id),
            name_enc TEXT NOT NULL, revision INTEGER NOT NULL DEFAULT 0
        );
        CREATE INDEX IF NOT EXISTS idx_athletes_owner ON athletes(owner_id);
        CREATE TABLE IF NOT EXISTS items (
            athlete_id TEXT NOT NULL REFERENCES athletes(id) ON DELETE CASCADE,
            collection TEXT NOT NULL CHECK(collection IN ('events','available')),
            id TEXT NOT NULL, position INTEGER NOT NULL,
            title_enc TEXT NOT NULL, school_enc TEXT NOT NULL,
            location_enc TEXT NOT NULL, notes_enc TEXT NOT NULL,
            type TEXT NOT NULL, schedule_enc TEXT NOT NULL,
            source_id TEXT, catalog_id TEXT,
            PRIMARY KEY (athlete_id, collection, id)
        );
        CREATE TABLE IF NOT EXISTS app_config (key TEXT PRIMARY KEY, value TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS login_flows (
            state_hash TEXT PRIMARY KEY, verifier TEXT NOT NULL,
            nonce TEXT NOT NULL, expires INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS login_attempts (
            ip_hash TEXT PRIMARY KEY, window_start INTEGER NOT NULL,
            attempts INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS privacy_ack (
            owner_id TEXT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
            notice_version TEXT NOT NULL,
            acknowledged_at INTEGER NOT NULL,
            adult_statement INTEGER NOT NULL CHECK(adult_statement IN (0,1))
        );
        CREATE TABLE IF NOT EXISTS sessions (
            token_hash TEXT PRIMARY KEY, owner_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            csrf TEXT NOT NULL, expires INTEGER NOT NULL
        );
        """)
        key_test = conn.execute("SELECT value FROM app_config WHERE key='encryption_check'").fetchone()
        if key_test:
            try:
                if decrypted(key_test["value"], "app_config:encryption_check") != "configured":
                    raise RuntimeError("Chave de criptografia incompatível")
            except Exception as exc:
                raise RuntimeError("APP_ENCRYPTION_KEY não corresponde ao banco existente") from exc
        else:
            conn.execute("INSERT INTO app_config(key,value) VALUES(?,?)",
                         ("encryption_check", encrypted("configured", "app_config:encryption_check")))
        # V2: encrypt day/start/end, which can reveal the routines of minors.
        # Migrate older owned databases only AFTER verifying the encryption key.
        cols = {col[1] for col in conn.execute("PRAGMA table_info(items)")}
        if "schedule_enc" not in cols:
            if not {"day", "start", "end"}.issubset(cols):
                raise RuntimeError("Esquema de horários incompatível; restaure backup e revise migração")
            conn.execute("BEGIN IMMEDIATE")
            try:
                conn.execute("""CREATE TABLE items_schedule_v2 (
                    athlete_id TEXT NOT NULL REFERENCES athletes(id) ON DELETE CASCADE,
                    collection TEXT NOT NULL CHECK(collection IN ('events','available')),
                    id TEXT NOT NULL, position INTEGER NOT NULL,
                    title_enc TEXT NOT NULL, school_enc TEXT NOT NULL,
                    location_enc TEXT NOT NULL, notes_enc TEXT NOT NULL,
                    type TEXT NOT NULL, schedule_enc TEXT NOT NULL,
                    source_id TEXT, catalog_id TEXT,
                    PRIMARY KEY (athlete_id, collection, id)
                )""")
                legacy_rows = conn.execute("SELECT * FROM items").fetchall()
                for row in legacy_rows:
                    schedule = json.dumps({"day": row["day"], "start": row["start"], "end": row["end"]},
                                          separators=(",", ":"), ensure_ascii=False)
                    aad = f"items:{row['athlete_id']}:{row['collection']}:{row['id']}:schedule"
                    conn.execute("""INSERT INTO items_schedule_v2 (
                        athlete_id,collection,id,position,title_enc,school_enc,location_enc,notes_enc,
                        type,schedule_enc,source_id,catalog_id
                    ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""", (
                        row["athlete_id"], row["collection"], row["id"], row["position"],
                        row["title_enc"], row["school_enc"], row["location_enc"], row["notes_enc"],
                        row["type"], encrypted(schedule, aad), row["source_id"], row["catalog_id"]
                    ))
                conn.execute("DROP TABLE items")
                conn.execute("ALTER TABLE items_schedule_v2 RENAME TO items")
                conn.commit()
            except Exception:
                conn.rollback()
                raise
        elif {"day", "start", "end"} & cols:
            raise RuntimeError("Esquema híbrido pode expor horários; revisão manual necessária")
    if os.name == "posix":
        os.chmod(db, 0o600)

    def exchange_code(code, verifier):
        import httpx
        r = httpx.post("https://oauth2.googleapis.com/token", data={
            "client_id": client_id, "client_secret": client_secret,
            "grant_type": "authorization_code", "code": code,
            "redirect_uri": redirect_uri, "code_verifier": verifier,
        }, timeout=10)
        r.raise_for_status()
        return r.json()

    def verify_id_token(id_token_value, audience):
        # Standard Google library performs signature, expiry, issuer and audience validation.
        from google.oauth2 import id_token
        from google.auth.transport import requests as google_requests
        return id_token.verify_oauth2_token(id_token_value, google_requests.Request(), audience)

    token_exchange = token_exchange or exchange_code
    token_verifier = token_verifier or verify_id_token

    app = FastAPI(title="Agenda do Atleta Pro - Seguro", docs_url=None, redoc_url=None, openapi_url=None)

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers.update({
            "Cache-Control": "no-store", "Pragma": "no-cache",
            "X-Content-Type-Options": "nosniff", "X-Frame-Options": "DENY",
            "Referrer-Policy": "no-referrer", "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
            # No third-party executable code and no inline scripts/styles in HTML.
            "Content-Security-Policy": "default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self' data:; font-src 'self'; connect-src 'self'; base-uri 'none'; object-src 'none'; frame-ancestors 'none'; form-action 'self'",
        })
        if secure_cookie:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response

    def session_for(request: Request):
        token = request.cookies.get("ada_session", "")
        if not token:
            raise HTTPException(401, "Faça login com sua conta Google")
        hashed = sha256(token.encode()).hexdigest()
        with connection() as conn:
            row = conn.execute("SELECT owner_id, csrf FROM sessions WHERE token_hash=? AND expires>?", (hashed, int(time.time()))).fetchone()
        if row is None:
            raise HTTPException(401, "Sessão expirada")
        return {"owner_id": row["owner_id"], "csrf": row["csrf"]}

    def csrf_guard(request: Request, session=Depends(session_for)):
        if not secrets.compare_digest(request.headers.get("X-CSRF-Token", ""), session["csrf"]):
            raise HTTPException(403, "Token CSRF ausente ou inválido")
        return session

    def athlete_for(conn, aid, owner):
        row = conn.execute("SELECT id,name_enc,revision FROM athletes WHERE id=? AND owner_id=?", (aid, owner)).fetchone()
        if row is None:
            raise HTTPException(404, "Atleta não encontrado")
        return row

    @app.get("/login", include_in_schema=False)
    def login_page():
        return FileResponse(WEB_DIR / "login.html", media_type="text/html; charset=utf-8")

    @app.get("/static/login.css", include_in_schema=False)
    def login_styles():
        return FileResponse(WEB_DIR / "login.css", media_type="text/css; charset=utf-8")

    @app.get("/static/app.css", include_in_schema=False)
    def app_styles(session=Depends(session_for)):
        return FileResponse(WEB_DIR / "app.css", media_type="text/css; charset=utf-8")

    @app.get("/static/app.js", include_in_schema=False)
    def app_javascript(session=Depends(session_for)):
        return FileResponse(WEB_DIR / "app.js", media_type="text/javascript; charset=utf-8")

    @app.get("/account", include_in_schema=False)
    def account_page(session=Depends(session_for)):
        return FileResponse(WEB_DIR / "account.html", media_type="text/html; charset=utf-8")

    @app.get("/static/account.js", include_in_schema=False)
    def account_javascript(session=Depends(session_for)):
        return FileResponse(WEB_DIR / "account.js", media_type="text/javascript; charset=utf-8")

    @app.get("/static/account.css", include_in_schema=False)
    def account_styles(session=Depends(session_for)):
        return FileResponse(WEB_DIR / "account.css", media_type="text/css; charset=utf-8")

    @app.get("/auth/google/start")
    def login_start(request: Request):
        # Bound OAuth flow creation at the authoritative socket peer, never X-Forwarded-For.
        # A shared proxy address can aggregate users: also enforce limits at the trusted edge.
        peer = request.client.host if request.client else "unknown"
        ip_hash = hmac.new(key, b"login-peer:" + peer.encode(), sha256).hexdigest()
        now = int(time.time())
        state = secrets.token_urlsafe(32)
        verifier = secrets.token_urlsafe(48)
        nonce = secrets.token_urlsafe(32)
        challenge = base64.urlsafe_b64encode(sha256(verifier.encode()).digest()).decode().rstrip("=")
        with connection() as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                conn.execute("DELETE FROM login_flows WHERE expires <= ?", (now,))
                conn.execute("DELETE FROM login_attempts WHERE window_start <= ?", (now - LOGIN_WINDOW,))
                attempt = conn.execute("SELECT window_start,attempts FROM login_attempts WHERE ip_hash=?", (ip_hash,)).fetchone()
                if attempt is not None and attempt["attempts"] >= LOGIN_LIMIT:
                    remaining = max(1, attempt["window_start"] + LOGIN_WINDOW - now)
                    raise HTTPException(429, "Muitas tentativas de login. Aguarde para tentar novamente.", headers={"Retry-After": str(remaining)})
                if conn.execute("SELECT COUNT(*) FROM login_flows").fetchone()[0] >= LOGIN_MAX_PENDING:
                    raise HTTPException(503, "Login temporariamente indisponível", headers={"Retry-After": "60"})
                conn.execute("""INSERT INTO login_attempts(ip_hash,window_start,attempts) VALUES(?,?,1)
                    ON CONFLICT(ip_hash) DO UPDATE SET attempts=attempts+1""", (ip_hash, now))
                conn.execute("INSERT INTO login_flows(state_hash,verifier,nonce,expires) VALUES(?,?,?,?)",
                             (sha256(state.encode()).hexdigest(), verifier, nonce, now + OAUTH_TTL))
                conn.commit()
            except Exception:
                conn.rollback()
                raise
        params = {"client_id": client_id, "redirect_uri": redirect_uri,
                  "response_type": "code", "scope": "openid email", "state": state,
                  "nonce": nonce, "code_challenge": challenge, "code_challenge_method": "S256"}
        response = RedirectResponse("https://accounts.google.com/o/oauth2/v2/auth?" + urlencode(params), status_code=302)
        response.set_cookie("ada_oauth_state", state, max_age=OAUTH_TTL, httponly=True, secure=secure_cookie, samesite="lax", path="/auth/google")
        return response

    @app.get("/auth/google/callback")
    def login_callback(request: Request, state: str = "", code: str = ""):
        cookie_state = request.cookies.get("ada_oauth_state", "")
        if not state or not cookie_state or not secrets.compare_digest(state, cookie_state) or not code:
            raise HTTPException(400, "Estado OAuth inválido")
        with connection() as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                flow = conn.execute("SELECT verifier,nonce FROM login_flows WHERE state_hash=? AND expires>?",
                                    (sha256(state.encode()).hexdigest(), int(time.time()))).fetchone()
                if flow is None:
                    raise HTTPException(400, "Login expirado ou já utilizado")
                conn.execute("DELETE FROM login_flows WHERE state_hash=?", (sha256(state.encode()).hexdigest(),))
                conn.commit()
            except Exception:
                conn.rollback()
                raise
        stage = "token_exchange"
        try:
            tokens = token_exchange(code, flow["verifier"])
            stage = "id_token_verification"
            claims = token_verifier(tokens["id_token"], client_id)
            if not isinstance(claims, dict) or not isinstance(claims.get("sub"), str) or not claims["sub"] or not secrets.compare_digest(str(claims.get("nonce", "")), flow["nonce"]):
                raise ValueError("Token sem identidade ou nonce válido")
        except Exception as exc:
            # Report only the phase and exception class. Never log codes, tokens, claims or secrets.
            logging.getLogger(__name__).warning(
                "Google OAuth callback failed: stage=%s exception=%s",
                stage, type(exc).__name__,
            )
            raise HTTPException(401, "Falha ao verificar identidade Google") from exc
        owner_id = owner_key(claims["sub"])
        token = secrets.token_urlsafe(48)
        csrf = secrets.token_urlsafe(32)
        with connection() as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                conn.execute("INSERT OR IGNORE INTO users(id) VALUES (?)", (owner_id,))
                if not conn.execute("SELECT 1 FROM athletes WHERE owner_id=? LIMIT 1", (owner_id,)).fetchone():
                    aid = uuid.uuid4().hex
                    conn.execute("INSERT INTO athletes(id,owner_id,name_enc) VALUES(?,?,?)",
                                 (aid, owner_id, encrypted("Atleta principal", f"athletes:{aid}:name")))
                conn.execute("INSERT INTO sessions(token_hash,owner_id,csrf,expires) VALUES (?,?,?,?)",
                             (sha256(token.encode()).hexdigest(), owner_id, csrf, int(time.time()) + SESSION_TTL))
                conn.commit()
            except Exception:
                conn.rollback()
                raise
        response = RedirectResponse("/", status_code=303)
        response.delete_cookie("ada_oauth_state", path="/auth/google")
        response.set_cookie("ada_session", token, max_age=SESSION_TTL, secure=secure_cookie,
                            httponly=True, samesite="lax", path="/")
        return response

    @app.get("/", include_in_schema=False)
    def home(request: Request):
        try:
            session_for(request)
        except HTTPException:
            return RedirectResponse("/login", status_code=303)
        return FileResponse(WEB_FILE, media_type="text/html; charset=utf-8")

    @app.get("/favicon.ico", include_in_schema=False)
    def no_favicon():
        return Response(status_code=204)

    @app.get("/api/auth/me")
    def me(session=Depends(session_for)):
        return {"authenticated": True, "csrfToken": session["csrf"]}

    @app.post("/api/auth/logout")
    def logout(request: Request, session=Depends(csrf_guard)):
        with connection() as conn:
            conn.execute("DELETE FROM sessions WHERE token_hash=?", (sha256(request.cookies["ada_session"].encode()).hexdigest(),))
        response = Response(status_code=204)
        response.delete_cookie("ada_session", path="/")
        return response

    @app.get("/api/privacy")
    def privacy_notice(session=Depends(session_for)):
        return {
            "version": NOTICE_VERSION, "status": "draft_pending_legal_review",
            "audience": "Conta administrada por pessoa adulta; acesso direto por menores nao previsto.",
            "data_categories": ["identificador Google derivado", "nome do atleta",
                                "escola, local, atividade, observacoes", "dia e horario"],
            "purpose": "Organizacao privada de atividades de atletas pelo responsavel da conta.",
            "third_party_login": "Google OAuth para autenticacao; o email nao e armazenado.",
            "export": "/api/account/export", "deletion": "/api/account",
            "warning": "Aviso informativo de homologacao: nao substitui politica de privacidade juridicamente aprovada.",
        }

    @app.get("/api/privacy/ack")
    def get_privacy_ack(session=Depends(session_for)):
        with connection() as conn:
            row = conn.execute(
                "SELECT notice_version,acknowledged_at,adult_statement FROM privacy_ack WHERE owner_id=?",
                (session["owner_id"],),
            ).fetchone()
        return {"acknowledged": row is not None, "notice_version": row["notice_version"] if row else None,
                "adult_statement": bool(row["adult_statement"]) if row else False}

    @app.post("/api/privacy/ack")
    def acknowledge_privacy(data: PrivacyAcknowledgement, session=Depends(csrf_guard)):
        if not data.read_notice or not data.responsible_adult:
            raise HTTPException(400, "Exige-se declaracao expressa de leitura e responsabilidade adulta")
        with connection() as conn:
            conn.execute(
                """INSERT INTO privacy_ack(owner_id,notice_version,acknowledged_at,adult_statement)
                   VALUES (?,?,?,1) ON CONFLICT(owner_id)
                   DO UPDATE SET notice_version=excluded.notice_version,
                                 acknowledged_at=excluded.acknowledged_at,adult_statement=1""",
                (session["owner_id"], NOTICE_VERSION, int(time.time())),
            )
        return {"acknowledged": True, "notice_version": NOTICE_VERSION,
                "note": "Autodeclaracao registrada; nao comprova tutela nem consentimento juridico."}

    @app.get("/api/account/export")
    def export_account(session=Depends(session_for)):
        """Return only the logged-in owner's account data, decrypted for download."""
        owner = session["owner_id"]
        result = []
        with connection() as conn:
            athletes = conn.execute(
                "SELECT id,name_enc,revision FROM athletes WHERE owner_id=? ORDER BY id", (owner,)
            ).fetchall()
            for athlete in athletes:
                aid = athlete["id"]
                data = {"id": aid, "name": decrypted(athlete["name_enc"], f"athletes:{aid}:name"),
                        "revision": athlete["revision"], "events": [], "available": []}
                for row in conn.execute(
                    "SELECT * FROM items WHERE athlete_id=? ORDER BY collection,position", (aid,)
                ):
                    aad = lambda field: f"items:{aid}:{row['collection']}:{row['id']}:{field}"
                    item = {"id": row["id"], "type": row["type"], "day": row["day"],
                            "start": row["start"], "end": row["end"],
                            "title": decrypted(row["title_enc"], aad("title")),
                            "school": decrypted(row["school_enc"], aad("school")),
                            "location": decrypted(row["location_enc"], aad("location")),
                            "notes": decrypted(row["notes_enc"], aad("notes"))}
                    if row["source_id"]:
                        item["sourceId"] = row["source_id"]
                    if row["catalog_id"]:
                        item["catalogId"] = row["catalog_id"]
                    data[row["collection"]].append(item)
                result.append(data)
        return {"app": "Agenda do Atleta", "format": "account-export-v1", "athletes": result}

    @app.delete("/api/account")
    def delete_account(data: AccountDeletionRequest, session=Depends(csrf_guard)):
        """Remove current account and its athletes; backups remain independently managed."""
        if data.confirmation != "EXCLUIR_MINHA_CONTA_E_ATLETAS":
            raise HTTPException(400, "Confirmação de exclusão inválida")
        owner = session["owner_id"]
        with connection() as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                conn.execute("DELETE FROM items WHERE athlete_id IN (SELECT id FROM athletes WHERE owner_id=?)", (owner,))
                conn.execute("DELETE FROM athletes WHERE owner_id=?", (owner,))
                conn.execute("DELETE FROM sessions WHERE owner_id=?", (owner,))
                conn.execute("DELETE FROM users WHERE id=?", (owner,))
                conn.commit()
            except Exception:
                conn.rollback()
                raise
        response = Response(status_code=204)
        response.delete_cookie("ada_session", path="/")
        return response

    @app.get("/api/athletes")
    def list_athletes(session=Depends(session_for)):
        owner = session["owner_id"]
        with connection() as conn:
            return [{"id": x["id"], "name": decrypted(x["name_enc"], f"athletes:{x['id']}:name")}
                    for x in conn.execute("SELECT id,name_enc FROM athletes WHERE owner_id=? ORDER BY id", (owner,))]

    @app.post("/api/athletes", status_code=201)
    def add_athlete(data: AthleteName, session=Depends(csrf_guard)):
        aid = uuid.uuid4().hex
        with connection() as conn:
            conn.execute("INSERT INTO athletes(id,owner_id,name_enc) VALUES (?,?,?)",
                         (aid, session["owner_id"], encrypted(data.name, f"athletes:{aid}:name")))
        return {"id": aid, "name": data.name}

    @app.patch("/api/athletes/{aid}")
    def rename_athlete(aid: str, data: AthleteName, session=Depends(csrf_guard)):
        with connection() as conn:
            athlete_for(conn, aid, session["owner_id"])
            conn.execute("UPDATE athletes SET name_enc=? WHERE id=? AND owner_id=?",
                         (encrypted(data.name, f"athletes:{aid}:name"), aid, session["owner_id"]))
        return {"id": aid, "name": data.name}

    @app.delete("/api/athletes/{aid}")
    def delete_athlete(aid: str, session=Depends(csrf_guard)):
        with connection() as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                athlete_for(conn, aid, session["owner_id"])
                count = conn.execute("SELECT COUNT(*) FROM athletes WHERE owner_id=?", (session["owner_id"],)).fetchone()[0]
                if count <= 1:
                    raise HTTPException(409, "Não é possível excluir o último atleta")
                conn.execute("DELETE FROM athletes WHERE id=? AND owner_id=?", (aid, session["owner_id"]))
                conn.commit()
            except Exception:
                conn.rollback()
                raise
        return {"deleted": True}

    @app.get("/api/athletes/{aid}/state")
    def read_state(aid: str, session=Depends(session_for)):
        with connection() as conn:
            athlete = athlete_for(conn, aid, session["owner_id"])
            result = {"revision": athlete["revision"], "events": [], "available": []}
            for row in conn.execute("SELECT * FROM items WHERE athlete_id=? ORDER BY collection,position", (aid,)):
                aad = lambda field: f"items:{aid}:{row['collection']}:{row['id']}:{field}"
                item = {"id": row["id"], "type": row["type"], "day": row["day"],
                        "start": row["start"], "end": row["end"],
                        "title": decrypted(row["title_enc"], aad("title")),
                        "school": decrypted(row["school_enc"], aad("school")),
                        "location": decrypted(row["location_enc"], aad("location")),
                        "notes": decrypted(row["notes_enc"], aad("notes"))}
                if row["source_id"]:
                    item["sourceId"] = row["source_id"]
                if row["catalog_id"]:
                    item["catalogId"] = row["catalog_id"]
                result[row["collection"]].append(item)
            return result

    @app.put("/api/athletes/{aid}/state")
    def write_state(aid: str, data: State, session=Depends(csrf_guard)):
        with connection() as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                athlete = athlete_for(conn, aid, session["owner_id"])
                if data.revision != athlete["revision"]:
                    raise HTTPException(409, "Agenda alterada em outra sessão. Recarregue a página.")
                conn.execute("DELETE FROM items WHERE athlete_id=?", (aid,))
                for collection in ("events", "available"):
                    for index, item in enumerate(getattr(data, collection)):
                        aad = lambda field: f"items:{aid}:{collection}:{item.id}:{field}"
                        conn.execute("""INSERT INTO items(athlete_id,collection,id,position,title_enc,school_enc,
                            location_enc,notes_enc,type,day,start,end,source_id,catalog_id)
                            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (
                            aid, collection, item.id, index, encrypted(item.title, aad("title")),
                            encrypted(item.school, aad("school")), encrypted(item.location, aad("location")),
                            encrypted(item.notes, aad("notes")), item.type, item.day, item.start,
                            item.end, item.sourceId, item.catalogId,
                        ))
                revision = athlete["revision"] + 1
                conn.execute("UPDATE athletes SET revision=? WHERE id=? AND owner_id=?", (revision, aid, session["owner_id"]))
                conn.commit()
            except Exception:
                conn.rollback()
                raise
        return {"revision": revision, "saved": True}

    return app


def app_factory():
    return create_app()