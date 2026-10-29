from unittest.mock import patch
import pytest
from factory.tech_lead import (
    MAX_PR_FILES, collect_pr, gate_status, parse_verdict, validate_repo,
)


def test_verdict_only_one_line_is_accepted():
    assert parse_verdict("Achado: OK\nVEREDITO: APROVADO\n") == "APROVADO"
    assert parse_verdict("VEREDITO: AJUSTES_OBRIGATORIOS") == "AJUSTES_OBRIGATORIOS"
    assert parse_verdict("VEREDITO: APROVADO\nVEREDITO: AJUSTES_OBRIGATORIOS") == "NAO_VERIFICADO"
    assert parse_verdict("Recomendo aprovar") == "NAO_VERIFICADO"


def test_fail_closed_gate():
    assert gate_status("APROVADO", "PASSOU: verificações básicas") == "AGUARDANDO_REVISAO_HUMANA"
    assert gate_status("APROVADO", "FALHOU: index ausente") == "AJUSTES_OBRIGATORIOS"
    assert gate_status("AJUSTES_OBRIGATORIOS", "PASSOU: verificação") == "AJUSTES_OBRIGATORIOS"
    assert gate_status("NAO_VERIFICADO", "PASSOU: verificação") == "REVISAO_INCONCLUSIVA"


@pytest.mark.parametrize("repo", ["../foo", "org/repo/extra", "https://github.com/o/r", "..//r", "x/..", "", "a/b?c"])
def test_disallow_invalid_repo(repo):
    with pytest.raises(ValueError):
        validate_repo(repo, 1)


def test_disallow_invalid_pr():
    with pytest.raises(ValueError):
        validate_repo("owner/name", 0)


def test_collect_pr_reads_real_patch_data_without_writing():
    pr = {"title": "Feature", "body": "Descrição", "head": {"sha": "abc"}, "base": {"ref": "main"}}
    patches = [{"filename": "src/app.py", "status": "modified", "patch": "@@ -1 +1 @@\n-x\n+y"}]
    with patch("factory.tech_lead.github_json", side_effect=[pr, patches]) as fetch:
        result = collect_pr("owner/project", 4, "secret")
    assert result["head_sha"] == "abc"
    assert result["files"] == [{"path": "src/app.py", "status": "modified", "patch": "@@ -1 +1 @@\n-x\n+y"}]
    assert fetch.call_count == 2


def test_collect_pr_refuses_unavailable_binary_patch():
    pr = {"head": {"sha": "abc"}, "base": {"ref": "main"}}
    with patch("factory.tech_lead.github_json", side_effect=[pr, [{"filename": "logo.png"}]]):
        with pytest.raises(RuntimeError, match="Diff indisponível"):
            collect_pr("owner/project", 4, "secret")


def test_collect_pr_refuses_oversized_batch():
    pr = {"head": {"sha": "abc"}}
    patches = [{"filename": f"f{i}.py", "patch": "+pass"} for i in range(MAX_PR_FILES + 1)]
    with patch("factory.tech_lead.github_json", side_effect=[pr, patches]):
        with pytest.raises(RuntimeError, match="excede limites"):
            collect_pr("owner/project", 4, "secret")


def test_no_token_no_fetch():
    with pytest.raises(ValueError, match="GITHUB_TOKEN"):
        collect_pr("owner/project", 4, "")