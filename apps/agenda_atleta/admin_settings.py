"""Single-DB, typed configuration registry for the Agenda do Atleta.

All editable settings and obligation metadata live in the app SQLite database.
OAuth credentials, encryption keys and permission grants are NEVER database settings.
"""
from __future__ import annotations

from datetime import date
import json
import re
import sqlite3

from factory.br_release_gate import GATES

BASE_DEFINITIONS = {
    "brand.product_name": ("Marca e produto", "Nome público do produto", "text", "Agenda do Atleta Pro", 100),
    "brand.support_email": ("Marca e produto", "E-mail público de suporte", "email", "", 160),
    "supplier.legal_name": ("Fornecedor", "Razão social / nome do fornecedor", "text", "", 180),
    "supplier.registration": ("Fornecedor", "CNPJ / CPF comercial do fornecedor", "text", "", 24),
    "supplier.address": ("Fornecedor", "Endereço de atendimento comercial", "textarea", "", 500),
    "supplier.contact_url": ("Fornecedor", "Página pública de contato", "url", "", 300),
    "legal.privacy_notice": ("Documentos legais", "Aviso de privacidade (rascunho até revisão)", "textarea", "", 12000),
    "legal.terms_of_service": ("Documentos legais", "Termos de uso (rascunho até revisão)", "textarea", "", 12000),
    "legal.consumer_cancellation": ("Documentos legais", "Orientações de cancelamento / arrependimento", "textarea", "", 8000),
    "privacy.retention_days": ("Privacidade", "Prazo de retenção planejado (dias)", "integer", 365, 0),
    "privacy.audience": ("Privacidade", "Público da conta", "choice", "adult_administrator", 50),
    "operations.incident_contact": ("Operação", "Canal de incidentes de segurança", "email", "", 160),
    "operations.backup_policy": ("Operação", "Procedimento de backup / restauração", "textarea", "", 4000),
}
CHOICES = {"privacy.audience": {"adult_administrator"}}
OBLIGATION_PREFIX = "obligation."
ALL_DEFINITIONS = {
    key: {"key":key, "group":group, "label":label, "kind":kind,"default":default,"max_length":max_len}
    for key,(group,label,kind,default,max_len) in BASE_DEFINITIONS.items()
}
for key,label in GATES.items():
    full_key = OBLIGATION_PREFIX + key
    ALL_DEFINITIONS[full_key] = {
        "key":full_key, "group":"Obrigações Brasil", "label":label,
        "kind":"obligation", "default":{"status":"pending","owner":"","evidence_reference":"","reviewed_on":""},
        "max_length":600,
    }

def validate_value(key: str, value):
    definition = ALL_DEFINITIONS.get(key)
    if definition is None:
        raise ValueError("Parâmetro não permitido")
    kind = definition["kind"]
    if kind == "integer":
        if type(value) is not int or not 30 <= value <= 3650:
            raise ValueError("A retenção deve ser um número inteiro entre 30 e 3650 dias")
        return value
    if kind == "obligation":
        if not isinstance(value,dict) or set(value) != {"status","owner","evidence_reference","reviewed_on"}:
            raise ValueError("Formato inválido da obrigação")
        status = value["status"]
        if status not in ("pending","in_review","evidence_recorded"):
            raise ValueError("Situação da obrigação inválida")
        for field,limit in (("owner",160),("evidence_reference",600),("reviewed_on",10)):
            if not isinstance(value[field],str) or len(value[field]) > limit:
                raise ValueError("Campo da obrigação inválido")
        if status == "evidence_recorded":
            if not value["owner"].strip() or not value["evidence_reference"].strip():
                raise ValueError("Responsável e referência são obrigatórios")
            try:
                reviewed_date = date.fromisoformat(value["reviewed_on"])
            except (TypeError,ValueError):
                raise ValueError("Data da revisão inválida") from None
            if reviewed_date > date.today():
                raise ValueError("Data de revisão futura não permitida")
        elif value["reviewed_on"]:
            try: date.fromisoformat(value["reviewed_on"])
            except ValueError: raise ValueError("Data inválida") from None
        return {field:value[field].strip() if field!="status" else status for field in value}
    if not isinstance(value,str) or len(value) > definition["max_length"]:
        raise ValueError("Texto inválido ou muito longo")
    if "\x00" in value:
        raise ValueError("Texto contém caracteres inválidos")
    value = value.strip()
    if kind == "email" and value and (not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+",value)):
        raise ValueError("E-mail inválido")
    if kind == "url" and value and not re.fullmatch(r"https://[^\s]+",value):
        raise ValueError("URL pública precisa utilizar HTTPS")
    if kind == "choice" and value not in CHOICES.get(key,set()):
        raise ValueError("Opção não permitida")
    return value

def ensure_settings(conn: sqlite3.Connection):
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS app_settings (
            key TEXT PRIMARY KEY, value_json TEXT NOT NULL,
            revision INTEGER NOT NULL DEFAULT 0,
            updated_by TEXT, updated_at INTEGER
        );
        CREATE TABLE IF NOT EXISTS app_settings_audit (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key TEXT NOT NULL,
            revision INTEGER NOT NULL, actor_id TEXT NOT NULL,
            updated_at INTEGER NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_settings_audit_key ON app_settings_audit(key,id);
    """)
    conn.executemany(
        "INSERT OR IGNORE INTO app_settings(key,value_json,revision) VALUES(?,?,0)",
        [(key,json.dumps(d["default"],ensure_ascii=False)) for key,d in ALL_DEFINITIONS.items()],
    )

def fetch_settings(conn:sqlite3.Connection):
    result = []
    for row in conn.execute("SELECT key,value_json,revision,updated_at FROM app_settings ORDER BY key"):
        definition = ALL_DEFINITIONS.get(row["key"])
        if definition is None:
            continue
        result.append({**{k:v for k,v in definition.items() if k!="default"},
                       "value":json.loads(row["value_json"]),
                       "revision":row["revision"],"updated_at":row["updated_at"]})
    return result
