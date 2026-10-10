"""contracts/api/patient-access/patient-access-grants.v1.yaml (HC-115).

Lists, records, and revokes one patient's access grants on this node. Requests are
parsed strictly; anything outside the contract is a 400 invalid_request. Callers are not
authenticated: who may manage a patient's grants is OPEN.
"""

import re
from collections.abc import Callable
from datetime import datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import (
    AfterValidator,
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
)

from application.manage_access_grants import (
    AccessGrantStore,
    GrantNotFound,
    grant_access,
    list_access_grants,
    revoke_access_grant,
)
from domain.access_grant import AccessGrant, InvalidAccessGrant
from domain.node_identity import NodeIdentity
from domain.patient_history import ScopeItem

_REF = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")


def _unique(items: list[str]) -> list[str]:
    if len(set(items)) != len(items):
        raise ValueError("scope items must be unique")
    return items


class NewAccessGrant(BaseModel):
    model_config = ConfigDict(extra="forbid")

    grantee_ref: Annotated[str, Field(pattern=_REF.pattern)]
    scope: Annotated[
        list[Literal["encounters", "medications", "lab_reports"]],
        Field(min_length=1),
        AfterValidator(_unique),
    ]
    purpose: Annotated[str, Field(min_length=1, max_length=200)]
    expires_at: AwareDatetime


def _problem(
    status: int, title: str, code: str, detail: str | None = None
) -> JSONResponse:
    content = {"type": "about:blank", "title": title, "status": status, "code": code}
    if detail:
        content["detail"] = detail
    return JSONResponse(
        status_code=status, media_type="application/problem+json", content=content
    )


def _invalid(fields: set[str]) -> JSONResponse:
    detail = "Invalid or missing fields: " + ", ".join(sorted(fields))
    return _problem(400, "Invalid access grant request", "invalid_request", detail)


def _not_found() -> JSONResponse:
    return _problem(404, "Access grant not found", "grant_not_found")


def _to_wire(grant: AccessGrant, at: datetime) -> dict:
    return {
        "grant_ref": grant.grant_ref,
        "patient_ref": grant.patient_ref,
        "grantee_ref": grant.grantee_ref,
        # In the contract's order.
        "scope": [item.value for item in ScopeItem if item in grant.scope],
        "purpose": grant.purpose,
        "status": grant.status(at).value,
        "granted_at": grant.granted_at.isoformat(),
        "expires_at": grant.expires_at.isoformat(),
        "revoked_at": grant.revoked_at.isoformat() if grant.revoked_at else None,
    }


def create_router(
    identity: NodeIdentity,
    store: AccessGrantStore,
    clock: Callable[[], datetime],
    new_grant_ref: Callable[[], str] | None = None,
) -> APIRouter:
    router = APIRouter(
        prefix="/v1/patients/{patient_ref}/access-grants", tags=["access grants"]
    )
    node = {
        "node_ref": identity.node_ref,
        "organization_ref": identity.organization_ref,
    }
    ref_options = {"new_grant_ref": new_grant_ref} if new_grant_ref else {}

    def record(grant: AccessGrant, at: datetime, status: int = 200) -> JSONResponse:
        return JSONResponse(
            {**node, "grant": _to_wire(grant, at), "mocked": store.mocked},
            status_code=status,
        )

    @router.get("")
    def list_grants(patient_ref: str) -> JSONResponse:
        if not _REF.fullmatch(patient_ref):
            return _invalid({"patient_ref"})
        now = clock()
        return JSONResponse(
            {
                **node,
                "patient_ref": patient_ref,
                "grants": [
                    _to_wire(g, now) for g in list_access_grants(patient_ref, store)
                ],
                "mocked": store.mocked,
            }
        )

    @router.post("")
    async def grant(patient_ref: str, request: Request) -> JSONResponse:
        if not _REF.fullmatch(patient_ref):
            return _invalid({"patient_ref"})
        try:
            body = NewAccessGrant.model_validate_json(await request.body())
        except ValidationError as error:
            # Malformed JSON has no field location.
            fields = {".".join(map(str, e["loc"])) for e in error.errors() if e["loc"]}
            return _invalid(fields or {"body"})
        try:
            created = grant_access(
                patient_ref,
                body.grantee_ref,
                frozenset(ScopeItem(item) for item in body.scope),
                body.purpose,
                body.expires_at,
                store,
                clock,
                **ref_options,
            )
        except InvalidAccessGrant as error:
            return _invalid({str(error).split(" ")[0]})
        return record(created, created.granted_at, status=201)

    @router.post("/{grant_ref}/revocation")
    def revoke(patient_ref: str, grant_ref: str) -> JSONResponse:
        invalid = {
            name
            for name, value in (("patient_ref", patient_ref), ("grant_ref", grant_ref))
            if not _REF.fullmatch(value)
        }
        if invalid:
            return _invalid(invalid)
        try:
            revoked = revoke_access_grant(patient_ref, grant_ref, store, clock)
        except GrantNotFound:
            return _not_found()
        return record(revoked, revoked.revoked_at)

    return router
