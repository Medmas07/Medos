import json
from pathlib import Path

import httpx
import yaml
from jsonschema import Draft202012Validator, FormatChecker

from sciagents_adapter import SciAgentsClient

ROOT = Path(__file__).resolve().parents[3]
CONTRACT_PATH = ROOT / "contracts/api/sciagents/scientific-investigation.v1.yaml"


def validator_for(reference):
    contract = yaml.safe_load(CONTRACT_PATH.read_text(encoding="utf-8"))
    return Draft202012Validator(
        {"$ref": reference, "components": contract["components"]},
        format_checker=FormatChecker(),
    )


def test_adapter_states_match_the_hc170_contract():
    upstream_state = {
        "proposal": {"hypothesis": "A fictional research lead."},
        "grounding": {"citations": []},
        "evaluation": {"passed_quality_gate": True},
        "error": None,
    }

    def handler(request):
        if request.method == "POST":
            return httpx.Response(202, json={"run_id": "run-contract"})
        return httpx.Response(200, json=upstream_state)

    http = httpx.Client(
        base_url="https://sciagents.invalid", transport=httpx.MockTransport(handler)
    )
    adapter = SciAgentsClient(
        "https://sciagents.invalid",
        http_client=http,
        id_factory=lambda: "0b6f5a1e-3c2d-4e7f-9a8b-1c2d3e4f5a6b",
    )
    queued = adapter.submit(
        {
            "project_ref": "proj-001",
            "requested_by": "usr-aymen",
            "question": "Question fictive.",
            "concepts": [{"label": "Metformin"}, {"label": "Diabetes"}],
        }
    )
    completed = adapter.get(queued["investigation_id"])
    schema = validator_for("#/components/schemas/Investigation")

    assert schema.is_valid(json.loads(json.dumps(queued)))
    assert schema.is_valid(json.loads(json.dumps(completed)))


def test_no_external_sciagents_implementation_is_imported():
    source = (ROOT / "integrations/sciagents/src/sciagents_adapter/client.py").read_text(
        encoding="utf-8"
    )
    assert "from sciagents" not in source
    assert "import sciagents" not in source
