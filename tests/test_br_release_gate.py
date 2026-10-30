from datetime import date, timedelta
from factory.br_release_gate import GATES, evaluate


def evidence():
    return {name: {"approved_by": "Revisor Responsável", "reference": "REF-123",
                   "approved_on": date.today().isoformat()} for name in GATES}


def test_no_evidence_always_blocks_market_release():
    report = evaluate(None)
    assert report["status"] == "NAO_LIBERADO"
    assert len(report["pending"]) == len(GATES)
    assert "não comprova" in report["disclaimer"]


def test_missing_or_invalid_human_review_blocks():
    data = evidence()
    del data["eca_digital_assessment"]
    data["human_release_approval"]["approved_by"] = ""
    report = evaluate(data)
    missing = {item["code"] for item in report["pending"]}
    assert missing == {"eca_digital_assessment", "human_release_approval"}


def test_future_dated_evidence_is_not_accepted():
    data = evidence()
    data["security_assessment"]["approved_on"] = (date.today() + timedelta(days=1)).isoformat()
    report = evaluate(data)
    assert report["status"] == "NAO_LIBERADO"
    assert [x["code"] for x in report["pending"]] == ["security_assessment"]


def test_complete_reference_set_is_only_documented_not_legal_certificate():
    result = evaluate(evidence())
    assert result["status"] == "EVIDENCIAS_DOCUMENTADAS"
    assert result["pending"] == []
    assert "merge/deploy" in result["disclaimer"]
