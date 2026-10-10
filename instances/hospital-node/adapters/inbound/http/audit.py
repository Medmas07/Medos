"""GET /v1/audit/events of contracts/api/hospital-audit/hospital-audit-events.v1.yaml.

Lists this node's own audit trail (HC-116). Filters are parsed strictly; an unknown,
repeated, or invalid parameter is a 400 invalid_request. Callers are not authenticated:
who may read the trail is OPEN.
"""

import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import AfterValidator, BaseModel, ConfigDict, Field, ValidationError

from application.audit_log import AuditLog
from application.list_audit_events import list_audit_events
from domain.audit_event import MAX_LIMIT, AuditEvent, AuditOutcome, AuditQuery
from domain.node_identity import NodeIdentity


def _uuid(value: str) -> str:
    uuid.UUID(value)
    return value


class _Filters(BaseModel):
    model_config = ConfigDict(extra="forbid")

    patient_ref: (
        Annotated[str, Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")] | None
    ) = None
    query_id: Annotated[str, AfterValidator(_uuid)] | None = None
    outcome: Literal["disclosed", "denied"] | None = None
    limit: Annotated[int, Field(ge=1, le=MAX_LIMIT)] = 50

    def to_query(self) -> AuditQuery:
        return AuditQuery(
            patient_ref=self.patient_ref,
            query_id=self.query_id,
            outcome=AuditOutcome(self.outcome) if self.outcome else None,
            limit=self.limit,
        )


def _invalid(fields: set[str]) -> JSONResponse:
    return JSONResponse(
        status_code=400,
        media_type="application/problem+json",
        content={
            "type": "about:blank",
            "title": "Invalid audit query",
            "status": 400,
            "detail": "Invalid or unknown parameters: " + ", ".join(sorted(fields)),
            "code": "invalid_request",
        },
    )


def _to_wire(event: AuditEvent) -> dict:
    return {
        "event_id": event.event_id,
        "recorded_at": event.recorded_at.isoformat(),
        "action": event.action.value,
        "outcome": event.outcome.value,
        "query_id": event.query_id,
        "patient_ref": event.patient_ref,
        "requested_by": {
            "organization_ref": event.requested_by.organization_ref,
            "actor_ref": event.requested_by.actor_ref,
        },
        "purpose": event.purpose,
        "scope": sorted(item.value for item in event.scope),
        "authorization": {
            "basis": event.authorization_basis.value,
            "ref": event.authorization_ref,
        },
        "disclosed_entry_refs": list(event.disclosed_entry_refs),
    }


def create_router(identity: NodeIdentity, audit_log: AuditLog) -> APIRouter:
    router = APIRouter(prefix="/v1/audit", tags=["audit"])

    @router.get("/events")
    def list_events(request: Request) -> JSONResponse:
        params = request.query_params
        repeated = {key for key in params if len(params.getlist(key)) > 1}
        if repeated:
            return _invalid(repeated)
        try:
            query = _Filters.model_validate(dict(params)).to_query()
        except ValidationError as error:
            return _invalid({str(e["loc"][0]) for e in error.errors() if e["loc"]})
        return JSONResponse(
            {
                "node_ref": identity.node_ref,
                "organization_ref": identity.organization_ref,
                "durable": audit_log.durable,
                "events": [_to_wire(e) for e in list_audit_events(query, audit_log)],
            }
        )

    return router
