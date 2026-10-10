"""contracts/api/governance/governance-audit-events.v1.yaml (HC-134).

Lists and reads the Governance Node's own audit trail. Filters are parsed strictly; an
unknown, repeated, or invalid parameter is a 400 invalid_request. Readers are not
authenticated: who may read the trail is OPEN.
"""

from typing import Annotated

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from adapters.inbound.http.problems import OPAQUE_REF, problem
from application.audit import (
    DEFAULT_LIMIT,
    MAX_LIMIT,
    AuditTrail,
    EventNotFound,
    get_event,
    list_events,
)
from domain.audit import AuditAction, AuditDomain, AuditEvent, AuditFilter
from domain.node_identity import NodeIdentity

NOTICE = (
    "Fictional demo governance audit trail, held in memory by the Governance Node: "
    "events recorded at runtime are lost on restart, actors are declared, not "
    "authenticated, and no event is anchored in a ledger."
)

Ref = Annotated[str, Field(pattern=OPAQUE_REF.pattern)]


class _Filters(BaseModel):
    model_config = ConfigDict(extra="forbid")

    domain: AuditDomain | None = None
    action: AuditAction | None = None
    organization_ref: Ref | None = None
    subject_ref: Ref | None = None
    limit: Annotated[int, Field(ge=1, le=MAX_LIMIT)] = DEFAULT_LIMIT

    def to_filter(self) -> AuditFilter:
        return AuditFilter(
            domain=self.domain,
            action=self.action,
            organization_ref=self.organization_ref,
            subject_ref=self.subject_ref,
        )


def _invalid(fields: set[str]) -> JSONResponse:
    return problem(
        400,
        "Invalid audit query",
        "invalid_request",
        "Invalid or unknown parameters: " + ", ".join(sorted(fields)),
    )


def _wire(event: AuditEvent) -> dict:
    return {
        "event_ref": event.event_ref,
        "recorded_at": event.recorded_at.isoformat(),
        "action": event.action.value,
        "domain": event.domain.value,
        "actor_ref": event.actor_ref,
        "subject_type": event.subject_type.value,
        "subject_ref": event.subject_ref,
        "outcome": event.outcome.value if event.outcome else None,
        "reason": event.reason,
        "organization_refs": list(event.organization_refs),
    }


def create_router(identity: NodeIdentity, trail: AuditTrail) -> APIRouter:
    router = APIRouter(prefix="/v1/audit/events", tags=["audit"])

    def envelope(**content: object) -> dict:
        return {
            "node_ref": identity.node_ref,
            "organization_ref": identity.organization_ref,
            "durable": trail.durable,
            "notice": NOTICE,
            **content,
        }

    @router.get("")
    def list_audit_events(request: Request) -> JSONResponse:
        params = request.query_params
        repeated = {key for key in params if len(params.getlist(key)) > 1}
        if repeated:
            return _invalid(repeated)
        try:
            filters = _Filters.model_validate(dict(params))
        except ValidationError as error:
            return _invalid({str(e["loc"][0]) for e in error.errors() if e["loc"]})
        events = list_events(trail, filters.to_filter(), filters.limit)
        return JSONResponse(envelope(events=[_wire(e) for e in events]))

    @router.get("/{event_ref}")
    def get_audit_event(event_ref: str) -> JSONResponse:
        try:
            return JSONResponse(envelope(event=_wire(get_event(event_ref, trail))))
        except EventNotFound:
            return problem(
                404,
                "Event not found",
                "event_not_found",
                f"No governance audit event {event_ref}.",
            )

    return router
