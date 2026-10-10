"""contracts/federation/sync-authorization-check.v1.yaml, provider side (HC-132).

Answers the Federation Service's question before each exchange under a synchronization
decision: does it authorize this request now? A denial is a 200 result; only a request
outside the contract is a 400. actor_ref is accepted but not recorded yet: the
governance audit trail is PLANNED (HC-134).
"""

from collections.abc import Callable
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from adapters.inbound.http.problems import OPAQUE_REF, problem
from adapters.inbound.http.synchronization_requests import Ref, ScopeField
from application.synchronization import SynchronizationStore, check_sync_authorization
from domain.synchronization import ExchangeAsk, ScopeItem


class CheckRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    requester_organization_ref: Ref
    actor_ref: Ref
    patient_ref: Ref
    scope: ScopeField
    purpose: Annotated[str, Field(min_length=1, max_length=200)]


def _invalid(fields: set[str]) -> JSONResponse:
    return problem(
        400,
        "Invalid authorization check",
        "invalid_request",
        "Invalid or missing fields: " + ", ".join(sorted(fields)),
    )


def create_router(
    store: SynchronizationStore, clock: Callable[[], datetime]
) -> APIRouter:
    router = APIRouter(tags=["synchronization"])

    @router.post("/v1/synchronization-authorizations/{decision_ref}/checks")
    async def check(decision_ref: str, request: Request) -> JSONResponse:
        if not OPAQUE_REF.fullmatch(decision_ref):
            return _invalid({"decision_ref"})
        try:
            body = CheckRequest.model_validate_json(await request.body())
        except ValidationError as error:
            # Malformed JSON has no field location.
            fields = {str(e["loc"][0]) for e in error.errors() if e["loc"]}
            return _invalid(fields or {"body"})
        result = check_sync_authorization(
            decision_ref,
            ExchangeAsk(
                body.requester_organization_ref,
                body.actor_ref,
                body.patient_ref,
                frozenset(ScopeItem(item) for item in body.scope),
                body.purpose,
            ),
            store,
            clock,
        )
        return JSONResponse(
            {
                "decision_ref": result.decision_ref,
                "outcome": "authorized" if result.authorized else "denied",
                "reason": result.reason.value if result.reason else None,
                "target_organization_refs": list(result.target_organization_refs),
                "scope": sorted(item.value for item in result.scope),
                "purpose": result.purpose,
                "valid_until": result.valid_until.isoformat()
                if result.valid_until
                else None,
                "checked_at": result.checked_at.isoformat(),
            }
        )

    return router
