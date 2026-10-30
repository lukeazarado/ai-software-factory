"""Fail-closed operational release checklist for Agenda do Atleta in Brazil.

This verifies documented evidence exists; it NEVER certifies legal compliance.
Execution has no access to secrets or production and does not merge or deploy.
"""
from __future__ import annotations

import argparse
from datetime import date
import json
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


def main():
    parser = argparse.ArgumentParser(description="Gate conservador de prontidão comercial BR")
    parser.add_argument("--evidence", type=Path, help="JSON de referências de aprovações, fora do repositório")
    args = parser.parse_args()
    entries = None
    if args.evidence:
        entries = json.loads(args.evidence.read_text(encoding="utf-8"))
    report = evaluate(entries)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    raise SystemExit(0 if report["status"] == "EVIDENCIAS_DOCUMENTADAS" else 2)


if __name__ == "__main__":
    main()
