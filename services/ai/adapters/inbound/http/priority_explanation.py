"""HTTP adapter for contracts/api/ai/priority-queue-explanation.v1.yaml (HC-157).

The body is parsed here, strictly. The explanation runs in the threadpool, because
provider adapters may start their own event loop (the Claude adapter calls asyncio.run).
"""

from typing import Annotated

from fastapi import APIRouter, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from application.explain_priority_entry import (
    ExplainPriorityEntry,
    PriorityExplanationResult,
)
from domain.priority_explanation import (
    MAX_FACTORS,
    FactorType,
    InvalidQueueEntry,
    Level,
    MethodKind,
    PriorityFactor,
    PriorityMethod,
    QueueEntry,
)

PATH = "/v1/priority-queue-explanations"
CONTRACT_VERSION = "1.0"
NOTICE = (
    "Advisory explanation of a priority queue entry. The rank and the priority come "
    "from a deterministic priority method, never from AI; this text only puts them in "
    "words and changes neither. It is not a clinical triage. The clinician decides."
)

OpaqueRef = Annotated[str, Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")]
Number = Annotated[float, Field(ge=0, le=1_000_000)]


class FactorBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    factor_id: OpaqueRef
    type: FactorType
    label: Annotated[str, Field(min_length=1, max_length=200)]
    severity: Level
    weight: Number | None = None


class MethodBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: MethodKind
    name: Annotated[str, Field(min_length=1, max_length=200)]
    version: Annotated[str, Field(min_length=1, max_length=100)]
    description: Annotated[str, Field(max_length=500)] | None = None


class EntryBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    entry_id: OpaqueRef
    rank: Annotated[int, Field(ge=1, strict=True)]
    priority: Level
    score: Number | None = None
    factors: Annotated[list[FactorBody], Field(min_length=1, max_length=MAX_FACTORS)]
    method: MethodBody


class ExplanationRequestBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    requested_by: OpaqueRef
    entry: EntryBody


def _problem(detail: str) -> JSONResponse:
    return JSONResponse(
        {
            "type": "about:blank",
            "title": "Invalid priority queue explanation request",
            "status": 400,
            "detail": detail,
            "code": "invalid_request",
        },
        status_code=400,
        media_type="application/problem+json",
    )


def _wire(result: PriorityExplanationResult) -> dict:
    explanation = result.explanation
    by = explanation.generated_by
    return {
        "explanation_id": result.explanation_id,
        "contract_version": CONTRACT_VERSION,
        "entry_id": result.entry_id,
        "advisory": True,
        "review_status": "pending_clinician_review",
        "notice": NOTICE,
        "explanation": {
            "text": explanation.text,
            "advisory": True,
            "generated_by": {
                "kind": by.kind.value,
                "name": by.name,
                "version": by.version,
                "mocked": by.mocked,
            },
            "generated_at": explanation.generated_at.isoformat(),
        },
        "rejected_reasons": list(result.rejected_reasons),
        "uncertainty_notes": list(result.uncertainty_notes),
    }


def create_router(explain: ExplainPriorityEntry) -> APIRouter:
    router = APIRouter()

    @router.post(PATH)
    async def create_priority_queue_explanation(request: Request) -> JSONResponse:
        try:
            body = ExplanationRequestBody.model_validate_json(await request.body())
            e = body.entry
            entry = QueueEntry(
                entry_id=e.entry_id,
                rank=e.rank,
                priority=e.priority,
                score=e.score,
                factors=tuple(
                    PriorityFactor(f.factor_id, f.type, f.label, f.severity, f.weight)
                    for f in e.factors
                ),
                method=PriorityMethod(
                    e.method.kind, e.method.name, e.method.version, e.method.description
                ),
            )
        except ValidationError as error:
            fields = sorted(
                {".".join(str(p) for p in e["loc"]) or "body" for e in error.errors()}
            )
            return _problem("Invalid or missing fields: " + ", ".join(fields))
        except InvalidQueueEntry as error:
            return _problem(str(error))
        result = await run_in_threadpool(explain, entry)
        return JSONResponse(_wire(result))

    return router
