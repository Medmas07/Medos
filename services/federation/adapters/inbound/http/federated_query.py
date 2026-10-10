"""HTTP adapter for contracts/federation/federated-patient-query.v1.yaml."""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator

from application.federate_patient_query import (
    AuthorizationExpired,
    FederatedQueryRequest,
    FederatePatientQuery,
    RegistryUnavailable,
    UnknownTargets,
)
from domain.federated_query import (
    Authorization,
    AuthorizationBasis,
    FederatedResult,
    Requester,
    ScopeItem,
)

PATH = "/v1/federated-queries"
CONTRACT_VERSION = "1.0"

OpaqueRef = Annotated[str, Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")]


class RequesterBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    organization_ref: OpaqueRef
    actor_ref: OpaqueRef


class AuthorizationBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    basis: AuthorizationBasis
    ref: OpaqueRef
    expires_at: AwareDatetime


def _unique(values: list) -> list:
    if len(set(values)) != len(values):
        raise ValueError("items must be unique")
    return values


class FederatedQueryBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    patient_ref: OpaqueRef
    scope: Annotated[list[ScopeItem], Field(min_length=1)]
    purpose: Annotated[str, Field(min_length=1, max_length=200)]
    requested_by: RequesterBody
    authorization: AuthorizationBody
    target_organization_refs: (
        Annotated[list[OpaqueRef], Field(min_length=1, max_length=50)] | None
    ) = None

    _unique_scope = field_validator("scope")(_unique)
    _unique_targets = field_validator("target_organization_refs")(
        lambda v: v if v is None else _unique(v)
    )


def _problem(status: int, title: str, code: str, detail: str) -> JSONResponse:
    return JSONResponse(
        {
            "type": "about:blank",
            "title": title,
            "status": status,
            "detail": detail,
            "code": code,
        },
        status_code=status,
        media_type="application/problem+json",
    )


def _timestamp(value: datetime) -> str:
    return value.isoformat()


def _to_wire(result: FederatedResult) -> dict:
    return {
        "query_id": result.query_id,
        "contract_version": CONTRACT_VERSION,
        "patient_ref": result.patient_ref,
        "scope": sorted(item.value for item in result.scope),
        "completeness": result.completeness.value,
        "notice": result.notice,
        "node_results": [
            {
                "organization_ref": r.node.organization_ref,
                "node_ref": r.node.node_ref,
                "status": r.status.value,
                "entry_count": len(r.entries),
                "problem_code": r.problem_code,
            }
            for r in result.node_results
        ],
        "entries": [
            {
                "entry_ref": e.entry_ref,
                "record_type": e.record_type.value,
                "occurred_at": _timestamp(e.occurred_at),
                "source": {
                    "organization_ref": e.source.organization_ref,
                    "node_ref": e.source.node_ref,
                },
                e.record_type.value: dict(e.details),
            }
            for e in result.entries
        ],
        "provenance": {
            "mocked": result.mocked,
            "aggregated_at": _timestamp(result.aggregated_at),
        },
    }


def create_router(federate: FederatePatientQuery) -> APIRouter:
    router = APIRouter()

    @router.post(PATH)
    def create_federated_query(body: FederatedQueryBody) -> JSONResponse:
        request = FederatedQueryRequest(
            patient_ref=body.patient_ref,
            scope=frozenset(body.scope),
            purpose=body.purpose,
            requested_by=Requester(**body.requested_by.model_dump()),
            authorization=Authorization(**body.authorization.model_dump()),
            target_organization_refs=(
                tuple(body.target_organization_refs)
                if body.target_organization_refs
                else None
            ),
        )
        try:
            result = federate(request)
        except AuthorizationExpired:
            return _problem(
                403,
                "Federated query not authorized",
                "authorization_denied",
                f"The authorization expired on {body.authorization.expires_at.date()}.",
            )
        except UnknownTargets as error:
            return _problem(
                400,
                "Invalid federated query",
                "invalid_request",
                f"Not an approved node: {', '.join(error.organization_refs)}",
            )
        except RegistryUnavailable:
            return _problem(
                503,
                "Federation unavailable",
                "federation_unavailable",
                "The Federation Service cannot reach the node registry.",
            )
        return JSONResponse(_to_wire(result))

    return router


def register_problem_handler(app: FastAPI) -> None:
    @app.exception_handler(RequestValidationError)
    async def invalid_request(request: Request, error: RequestValidationError):
        fields = sorted(
            {".".join(str(p) for p in e["loc"][1:]) or "body" for e in error.errors()}
        )
        return _problem(
            400,
            "Invalid federated query",
            "invalid_request",
            f"Invalid or missing fields: {', '.join(fields)}",
        )
