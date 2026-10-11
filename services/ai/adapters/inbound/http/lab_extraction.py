"""HTTP adapter for contracts/api/ai/lab-extraction.v1.yaml (HC-155).

The body is parsed here, strictly, so this route answers its own 400 problems. The
extraction runs in the threadpool: provider adapters are synchronous and may start their
own event loop (the Claude Agent SDK adapter calls asyncio.run).
"""

from typing import Annotated, Literal

from fastapi import APIRouter, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from application.extract_lab_results import (
    ExtractLabResults,
    LabExtractionRequest,
    LabExtractionUnavailable,
)
from domain.lab_extraction import MAX_REPORT_LENGTH, LabExtractionDraft

PATH = "/v1/lab-extractions"
CONTRACT_VERSION = "1.0"
NOTICE = (
    "Draft lab results extracted by an AI assistant for clinician review. Each value is "
    "checked against the report text, and flags are computed from the reference range "
    "printed in the report, never by the model. Not clinically validated; a clinician "
    "confirms or corrects every result before it is used."
)

OpaqueRef = Annotated[str, Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")]


class SourceBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: Annotated[str, Field(min_length=1, max_length=MAX_REPORT_LENGTH)]


class LabExtractionBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    patient_ref: OpaqueRef
    encounter_ref: OpaqueRef | None = None
    requested_by: OpaqueRef
    source: SourceBody


def _problem(
    detail: str,
    status: int = 400,
    title: str = "Invalid lab extraction request",
    code: Literal["invalid_request", "extraction_unavailable"] = "invalid_request",
) -> JSONResponse:
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


def _wire(draft: LabExtractionDraft) -> dict:
    extractor = draft.extractor
    return {
        "extraction_id": draft.extraction_id,
        "contract_version": CONTRACT_VERSION,
        "patient_ref": draft.patient_ref,
        "encounter_ref": draft.encounter_ref,
        "requested_by": draft.requested_by,
        "review_status": draft.review_status.value,
        "advisory": True,
        "notice": NOTICE,
        "results": [
            {
                "result_id": r.result_id,
                "test": r.test,
                "value": r.value,
                "unit": r.unit,
                "reference_range": {
                    "low": r.reference_range.low,
                    "high": r.reference_range.high,
                }
                if r.reference_range
                else None,
                "flag": r.flag.value if r.flag else None,
                "flag_basis": r.flag_basis.value,
                "evidence": {
                    "quote": r.evidence.quote,
                    "start": r.evidence.start,
                    "end": r.evidence.end,
                },
            }
            for r in draft.results
        ],
        "unverified_results_dropped": draft.unverified_results_dropped,
        "uncertainty_notes": list(draft.uncertainty_notes),
        "provenance": {
            "extractor": {
                "kind": extractor.kind.value,
                "name": extractor.name,
                "version": extractor.version,
            },
            "mocked": extractor.mocked,
            "generated_at": draft.generated_at.isoformat(),
        },
    }


def create_router(extract: ExtractLabResults) -> APIRouter:
    router = APIRouter()

    @router.post(PATH)
    async def create_lab_extraction(request: Request) -> JSONResponse:
        try:
            body = LabExtractionBody.model_validate_json(await request.body())
        except ValidationError as error:
            fields = sorted(
                {".".join(str(p) for p in e["loc"]) or "body" for e in error.errors()}
            )
            return _problem("Invalid or missing fields: " + ", ".join(fields))
        try:
            draft = await run_in_threadpool(
                extract,
                LabExtractionRequest(
                    body.patient_ref,
                    body.requested_by,
                    body.source.text,
                    body.encounter_ref,
                ),
            )
        except LabExtractionUnavailable as error:
            return _problem(
                str(error),
                status=503,
                title="Lab extraction unavailable",
                code="extraction_unavailable",
            )
        return JSONResponse(_wire(draft))

    return router
