"""This node's side of contracts/federation/hospital-node-federation.v1.yaml (HC-114).

GET /v1/federation/node describes the node; POST /v1/federation/queries answers an
authorized, scoped query about one patient's history from the records this node holds.
Requests are parsed strictly; anything outside the contract is a 400 invalid_request.
"""

import uuid
from collections.abc import Callable
from datetime import UTC, datetime, time
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

from application.authorization_verifier import AuthorizationVerifier
from application.clinical_repository import ClinicalRepository
from application.get_patient_history import AuthorizationDenied, get_patient_history
from domain.clinical_record import Encounter, LabReport, Medication
from domain.node_identity import NodeIdentity
from domain.patient_history import (
    Authorization,
    AuthorizationBasis,
    HistoryQuery,
    InvalidHistoryQuery,
    PatientHistory,
    Requester,
    ScopeItem,
)

CONTRACT_VERSION = "1.0"
SUPPORTED_SCOPES = [item.value for item in ScopeItem]


def _uuid(value: str) -> str:
    uuid.UUID(value)
    return value  # Echoed back unchanged, so the caller can match its query_id.


def _unique(items: list[str]) -> list[str]:
    if len(set(items)) != len(items):
        raise ValueError("scope items must be unique")
    return items


Ref = Annotated[str, Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")]


class _Wire(BaseModel):
    model_config = ConfigDict(extra="forbid")


class _Requester(_Wire):
    organization_ref: Ref
    actor_ref: Ref


class _Authorization(_Wire):
    basis: Literal["patient_access_grant", "synchronization_decision"]
    ref: Ref
    expires_at: AwareDatetime


class NodeQueryRequest(_Wire):
    query_id: Annotated[str, AfterValidator(_uuid)]
    patient_ref: Ref
    scope: Annotated[
        list[Literal["encounters", "medications", "lab_reports"]],
        Field(min_length=1),
        AfterValidator(_unique),
    ]
    purpose: Annotated[str, Field(min_length=1, max_length=200)]
    requested_by: _Requester
    authorization: _Authorization

    def to_query(self) -> HistoryQuery:
        return HistoryQuery(
            query_id=self.query_id,
            patient_ref=self.patient_ref,
            scope=frozenset(ScopeItem(item) for item in self.scope),
            purpose=self.purpose,
            requested_by=Requester(
                self.requested_by.organization_ref, self.requested_by.actor_ref
            ),
            authorization=Authorization(
                AuthorizationBasis(self.authorization.basis),
                self.authorization.ref,
                self.authorization.expires_at,
            ),
        )


class NodeDescriptor(BaseModel):
    node_ref: str
    organization_ref: str
    contract_versions: list[str]
    status: Literal["online", "degraded"]
    supported_scopes: list[str]
    mocked: bool


def _problem(status: int, title: str, code: str, detail: str) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        media_type="application/problem+json",
        content={
            "type": "about:blank",
            "title": title,
            "status": status,
            "detail": detail,
            "code": code,
        },
    )


def _invalid(fields: set[str]) -> JSONResponse:
    detail = "Invalid or missing fields: " + ", ".join(sorted(fields))
    return _problem(400, "Invalid federation query", "invalid_request", detail)


def _entries(history: PatientHistory, source: dict) -> list[dict]:
    def entry(record, record_type: str, occurred_at: datetime, details: dict) -> dict:
        return {
            "entry_ref": record.record_ref,
            "record_type": record_type,
            "occurred_at": occurred_at.isoformat(),
            "source": source,
            record_type: {k: v for k, v in details.items() if v is not None},
        }

    def encounter(e: Encounter) -> dict:
        return entry(
            e,
            "encounter",
            e.started_at,
            {
                "type": e.type,
                "title": e.title,
                "reason": e.reason,
                "summary": e.summary,
                "clinician_ref": e.clinician_ref,
            },
        )

    def medication(m: Medication) -> dict:
        # A medication has only a start date; it is placed at midnight UTC.
        details = entry(
            m,
            "medication",
            datetime.combine(m.start_date, time(), tzinfo=UTC),
            {
                "code": m.code,
                "dosage": m.dosage,
                "status": m.status.value,
                "start_date": m.start_date.isoformat(),
                "prescribed_by_ref": m.prescribed_by_ref,
            },
        )
        # Required but nullable in the contract.
        details["medication"]["end_date"] = (
            m.end_date.isoformat() if m.end_date else None
        )
        return details

    def lab_report(r: LabReport) -> dict:
        results = []
        for x in r.results:
            result = {
                "test": x.test,
                "value": x.value,
                "unit": x.unit,
                "flag": x.flag.value,
            }
            if x.reference_range:
                result["reference_range"] = {
                    "low": x.reference_range.low,
                    "high": x.reference_range.high,
                }
            results.append(result)
        return entry(
            r, "lab_report", r.collected_at, {"title": r.title, "results": results}
        )

    records = history.records
    return (
        [encounter(e) for e in records.encounters]
        + [medication(m) for m in records.medications]
        + [lab_report(r) for r in records.lab_reports]
    )


def create_router(
    identity: NodeIdentity,
    repository: ClinicalRepository,
    verifier: AuthorizationVerifier,
    clock: Callable[[], datetime],
) -> APIRouter:
    router = APIRouter(prefix="/v1/federation", tags=["federation"])
    source = {
        "organization_ref": identity.organization_ref,
        "node_ref": identity.node_ref,
    }

    @router.get("/node")
    def describe_node() -> NodeDescriptor:
        return NodeDescriptor(
            node_ref=identity.node_ref,
            organization_ref=identity.organization_ref,
            contract_versions=[CONTRACT_VERSION],
            # Records are in memory, so the node always reaches them (HC-113).
            status="online",
            supported_scopes=SUPPORTED_SCOPES,
            mocked=repository.summary().mocked,
        )

    @router.post("/queries")
    async def query_node(request: Request) -> JSONResponse:
        try:
            query = NodeQueryRequest.model_validate_json(
                await request.body()
            ).to_query()
        except ValidationError as error:
            # Malformed JSON has no field location.
            fields = {".".join(map(str, e["loc"])) for e in error.errors() if e["loc"]}
            return _invalid(fields or {"body"})
        except InvalidHistoryQuery as error:
            return _invalid({str(error).split(" ")[0]})
        try:
            history = get_patient_history(query, repository, verifier, clock)
        except AuthorizationDenied:
            return _problem(
                403,
                "Federation query not authorized",
                "authorization_denied",
                "The authorization does not cover this query.",
            )
        return JSONResponse(
            {
                "query_id": history.query_id,
                "contract_version": CONTRACT_VERSION,
                "node_ref": identity.node_ref,
                "organization_ref": identity.organization_ref,
                "patient_ref": history.patient_ref,
                # Same answer for an unknown patient as for nothing inside the scope.
                "entries": _entries(history, source),
                "provenance": {
                    "mocked": history.mocked,
                    "answered_at": history.answered_at.isoformat(),
                },
            }
        )

    return router
