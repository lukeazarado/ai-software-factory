"""Fail-closed operational release checklist for Agenda do Atleta in Brazil.

This verifies documented evidence exists; it NEVER certifies legal compliance.
Execution has no access to secrets or production and does not merge or deploy.
"""
from __future__ import annotations

import argparse
from datetime import date
import json
import sqlite3
from pathlib import Path

GATES = {
    "controller_and_contact": "Fornecedor/controlador identificado, canal de contato e atendimento",
    "legal_basis_and_minor_ripd": "Bases legais, melhor interesse e avaliação do impacto em menores",
    "eca_digital_assessment": "Análise de aplicabilidade do ECA Digital e medidas exigíveis",
    "privacy_terms_approved": "Política de privacidade e termos comerciais aprovados",
    "consumer_rules": "Informações do fornecedor, atendimento, cancelamento e arrependimento",
    "guardian_safeguards": "Controle adequado de adultos responsáveis e minimização de dados de menores",
    "security_assessment": "Auditoria de autenticação, autorização, criptografia, logs e incidentes",
    "https_secrets_and_backups": "HTTPS, segregação de segredos, backup e restauração comprovados",
    "e2e_accessibility": "E2E desktop/mobile, acessibilidade e testes com dados fictícios",
    "incident_response": "Procedimento de resposta, canal ANPD e responsáveis definidos",
    "human_release_approval": "Aprovação humana explícita para deploy público e custo",
}


def evaluate(evidence: dict | None) -> dict:
    evidence = evidence if isinstance(evidence, dict) else {}
    blocked = []
    for code, requirement in GATES.items():
        entry = evidence.get(code)
        if not isinstance(entry, dict):
            blocked.append({"code": code, "requirement": requirement, "reason": "Sem evidência"})
            continue
        approver = str(entry.get("approved_by", "")).strip()
        reference = str(entry.get("reference", "")).strip()
        raw_date = str(entry.get("approved_on", "")).strip()
        try:
            when = date.fromisoformat(raw_date)
            if when > date.today():
                raise ValueError("future")
        except ValueError:
            when = None
        if not approver or not reference or when is None:
            blocked.append({"code": code, "requirement": requirement,
                            "reason": "Exige responsável, referência e data válida"})
    return {"status": "EVIDENCIAS_DOCUMENTADAS" if not blocked else "NAO_LIBERADO",
            "total_gates": len(GATES), "pending": blocked,
            "disclaimer": "Checklist não comprova adequação jurídica nem autoriza merge/deploy."}


def evidence_from_database(db_path: Path) -> dict:
    """Read only generic obligation settings from the existing application DB.

    This never makes a database, updates values, reads athlete data or decrypts fields.
    """
    if not db_path.is_file():
        return {}
    result = {}
    with sqlite3.connect(f"file:{db_path.resolve().as_posix()}?mode=ro", uri=True) as conn:
        try:
            records = conn.execute("SELECT key,value_json FROM app_settings WHERE key LIKE 'obligation.%'").fetchall()
        except sqlite3.OperationalError:
            return {}
        for key, value_json in records:
            code = key.removeprefix("obligation.")
            if code not in GATES:
                continue
            try:
                item = json.loads(value_json)
            except (ValueError,TypeError):
                continue
            if not isinstance(item,dict) or item.get("status") != "evidence_recorded":
                continue
            result[code] = {"approved_by":item.get("owner",""),
                            "reference":item.get("evidence_reference",""),
                            "approved_on":item.get("reviewed_on","")}
    return result


def main():
    parser = argparse.ArgumentParser(description="Gate conservador de prontidão comercial BR")
    parser.add_argument("--evidence", type=Path, help="JSON de evidências (modo legado)")
    parser.add_argument("--db", type=Path, default=Path("data/agenda_atleta_secure.sqlite3"),
                        help="SQLite único contendo app_settings/obrigações")
    args = parser.parse_args()
    entries = (json.loads(args.evidence.read_text(encoding="utf-8"))
               if args.evidence else evidence_from_database(args.db))
    report = evaluate(entries)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    raise SystemExit(0 if report["status"] == "EVIDENCIAS_DOCUMENTADAS" else 2)


if __name__ == "__main__":
    main()
