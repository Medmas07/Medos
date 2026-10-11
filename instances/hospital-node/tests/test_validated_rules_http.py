"""The medication safety check with the validated ONC snapshot (HC-163), over HTTP."""

from fastapi.testclient import TestClient

from infrastructure.config import load_config
from main import create_app
from tests.conftest import CONFIG_DIR, DEMO_NOW
from tests.test_medication_safety_http import PATH, problem, valid

client = TestClient(
    create_app(
        load_config(CONFIG_DIR / "hospital-a.onc-rules.json"), clock=lambda: DEMO_NOW
    )
)


def body(proposed, *current):
    return {
        "patient_ref": "pat-x",
        "requested_by": "clin-x",
        "proposed_medication": {"name": proposed, "code": None},
        "current_medications": [
            {
                "statement_ref": f"stmt-{i}",
                "medication": {"name": name, "code": None},
                "status": "active",
                "source": {"organization_ref": "org-hospital-b"},
            }
            for i, name in enumerate(current)
        ],
    }


def test_a_listed_pair_is_a_contraindicated_warning_from_a_validated_source():
    result = valid(
        client.post(PATH, json=body("Simvastatine", "Clarithromycine")).json()
    )

    [warning] = result["warnings"]
    assert warning["severity"] == "contraindicated"
    assert warning["rule_source"]["kind"] == "validated_source"
    assert warning["rule_source"]["rule_id"] == "onc-2012-row-25"
    assert "doi:10.1136/amiajnl-2011-000612" in warning["rule_source"]["reference"]
    assert warning["summary"].startswith(
        "Association contre-indiquée selon la liste ONC"
    )
    assert result["provenance"]["mocked"] is False
    assert result["provenance"]["engine"]["kind"] == "validated_source"
    assert "MOCKED" not in result["notice"]
    assert "non exhaustif" in result["notice"]


def test_no_warning_from_a_minimum_list_says_it_is_not_a_statement_of_safety():
    result = valid(
        client.post(PATH, json=body("simvastatine", "amlodipine", "ritonavir")).json()
    )

    # Ritonavir is listed with simvastatin; amlodipine is not in the list at all.
    assert [w["rule_source"]["rule_id"] for w in result["warnings"]] == [
        "onc-2012-row-25"
    ]
    assert [
        (u["statement_ref"], u["reason"]) for u in result["unevaluated_medications"]
    ] == [("stmt-0", "not_in_rule_source")]

    quiet = valid(client.post(PATH, json=body("simvastatine", "ezetimibe")).json())
    assert quiet["outcome"] == "no_warnings_found"
    assert "ne signifie pas que l'association est sûre" in quiet["notice"]


def test_a_medication_the_list_does_not_know_cannot_be_checked():
    # Fictional demo medicines are unknown to a real source: no check, never "safe".
    response = client.post(PATH, json=body("Dolorane", "Coagulix"))

    problem(response, 503, "safety_check_unavailable")
