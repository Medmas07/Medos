import json

import httpx
import pytest

from adapters.outbound.http_sync_authorization_checker import (
    HttpSyncAuthorizationChecker,
)
from application.federate_patient_query import (
    GovernanceUnavailable,
    SyncAuthorizationDenied,
)
from domain.federated_query import Requester, ScopeItem
from domain.sync_authorization import DenialReason
from tests.conftest import contract, validator

CONTRACT = contract("sync-authorization-check.v1.yaml")
OPERATION = CONTRACT["paths"][
    "/v1/synchronization-authorizations/{decision_ref}/checks"
]["post"]
REQUEST = OPERATION["requestBody"]["content"]["application/json"]["examples"][
    "hospitalAAsksHospitalB"
]["value"]
RESULTS = OPERATION["responses"]["200"]["content"]["application/json"]["examples"]
AUTHORIZED = RESULTS["authorized"]["value"]
request_schema = validator(CONTRACT, "CheckRequest")


def check(handler, decision_ref="dec-sync-001"):
    checker = HttpSyncAuthorizationChecker(
        "http://localhost:8200/", transport=httpx.MockTransport(handler)
    )
    return checker.check(
        decision_ref=decision_ref,
        requested_by=Requester("org-hospital-a", "clin-x"),
        patient_ref="pat-a",
        scope=frozenset({ScopeItem.MEDICATIONS}),
        purpose=REQUEST["purpose"],
    )


def test_sends_the_contract_request_and_parses_an_authorization():
    seen = []

    def handler(request):
        seen.append((request.method, str(request.url), json.loads(request.content)))
        return httpx.Response(200, json=AUTHORIZED)

    authorization = check(handler)

    method, url, body = seen[0]
    assert (method, url) == (
        "POST",
        "http://localhost:8200/v1/synchronization-authorizations/dec-sync-001/checks",
    )
    assert body == REQUEST
    assert request_schema.is_valid(body)
    assert authorization.target_organization_refs == {"org-hospital-b"}
    assert authorization.scope == {ScopeItem.LAB_REPORTS, ScopeItem.MEDICATIONS}


@pytest.mark.parametrize(
    ("name", "reason"),
    [("expired", DenialReason.EXPIRED), ("rejected", DenialReason.NOT_APPROVED)],
)
def test_denials_carry_governance_reason(name, reason):
    value = RESULTS[name]["value"]
    with pytest.raises(SyncAuthorizationDenied) as error:
        check(lambda request: httpx.Response(200, json=value), value["decision_ref"])
    assert error.value.reason is reason


@pytest.mark.parametrize(
    "handler",
    [
        lambda request: (_ for _ in ()).throw(httpx.ConnectError("refused")),
        lambda request: (_ for _ in ()).throw(httpx.ReadTimeout("slow")),
        lambda request: httpx.Response(500),
        lambda request: httpx.Response(404),
        lambda request: httpx.Response(302, headers={"location": "http://elsewhere"}),
        lambda request: httpx.Response(200, text="yes"),
        lambda request: httpx.Response(
            200, json=AUTHORIZED | {"decision_ref": "dec-other"}
        ),
        lambda request: httpx.Response(200, json=AUTHORIZED | {"outcome": "maybe"}),
        lambda request: httpx.Response(
            200, json=AUTHORIZED | {"target_organization_refs": []}
        ),
        lambda request: httpx.Response(
            200, json=AUTHORIZED | {"valid_until": "2026-11-09T10:00:00"}
        ),
        lambda request: httpx.Response(200, json=AUTHORIZED | {"extra": 1}),
        lambda request: httpx.Response(
            200,
            json=RESULTS["expired"]["value"]
            | {"decision_ref": "dec-sync-001", "reason": "because"},
        ),
    ],
    ids=[
        "connect",
        "timeout",
        "server_error",
        "not_found",
        "redirect",
        "not_json",
        "other_decision",
        "unknown_outcome",
        "no_targets",
        "naive_valid_until",
        "extra_field",
        "unknown_reason",
    ],
)
def test_anything_else_denies_by_default(handler):
    with pytest.raises(GovernanceUnavailable):
        check(handler)
