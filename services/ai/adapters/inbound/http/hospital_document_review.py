"""HTTP adapter for contracts/api/ai/hospital-document-review.v1.yaml (HC-154).

The body is parsed here, strictly, so this route answers its own 400 problems without
changing the clinical extraction route's validation handler. The review itself runs in
the threadpool: provider adapters are synchronous and may start their own event loop
(the Claude Agent SDK adapter calls asyncio.run).
"""

from typing import Annotated, Literal

from fastapi import APIRouter, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, StrictBool, ValidationError

from application.review_hospital_documents import (
    ReviewHospitalDocuments,
    ReviewRequest,
    ReviewUnavailable,
)
from domain.document_review import (
    MAX_DOCUMENT_TEXT_LENGTH,
    MAX_DOCUMENTS,
    MAX_FIELD_VALUE_LENGTH,
    MAX_FIELDS,
    DocumentReview,
    Dossier,
    DossierDocument,
    DossierField,
    InvalidDossier,
)

PATH = "/v1/hospital-document-reviews"
CONTRACT_VERSION = "1.0"
NOTICE = (
    "Advisory review of an onboarding dossier by an AI assistant. It points out what "
    "the human reviewer should check; it does not approve, reject, or score the "
    "application. The Governance / Ethics Authority decides."
)

OpaqueRef = Annotated[str, Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")]
Value = (
    Annotated[str, Field(max_length=MAX_FIELD_VALUE_LENGTH)]
    | StrictBool
    | int
    | float
    | None
)


class FieldBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: Annotated[
        str, Field(pattern=r"^[a-z][a-z0-9_]*(\.[a-z0-9_]+)*$", max_length=200)
    ]
    value: Value


class DocumentBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    document_ref: OpaqueRef
    type: Annotated[str, Field(min_length=1, max_length=200)]
    title: Annotated[str, Field(min_length=1, max_length=200)]
    status: Annotated[str, Field(min_length=1, max_length=200)]
    text: (
        Annotated[str, Field(min_length=1, max_length=MAX_DOCUMENT_TEXT_LENGTH)] | None
    ) = None


class ReviewRequestBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    application_ref: OpaqueRef
    requested_by: OpaqueRef
    fields: Annotated[list[FieldBody], Field(min_length=1, max_length=MAX_FIELDS)]
    documents: Annotated[list[DocumentBody], Field(max_length=MAX_DOCUMENTS)] = []


def _problem(
    detail: str,
    status: int = 400,
    title: str = "Invalid hospital document review request",
    code: Literal["invalid_request", "review_unavailable"] = "invalid_request",
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


def _wire(review: DocumentReview) -> dict:
    reviewer = review.reviewer
    return {
        "review_id": review.review_id,
        "contract_version": CONTRACT_VERSION,
        "application_ref": review.application_ref,
        "requested_by": review.requested_by,
        "review_status": review.review_status.value,
        "advisory": True,
        "notice": NOTICE,
        "findings": [
            {
                "finding_id": f.finding_id,
                "category": f.category.value,
                "message": f.message,
                "field_paths": list(f.field_paths),
                "evidence": {
                    "document_ref": f.evidence.document_ref,
                    "quote": f.evidence.quote,
                }
                if f.evidence
                else None,
            }
            for f in review.findings
        ],
        "unverified_findings_dropped": review.unverified_findings_dropped,
        "uncertainty_notes": list(review.uncertainty_notes),
        "provenance": {
            "reviewer": {
                "kind": reviewer.kind.value,
                "name": reviewer.name,
                "version": reviewer.version,
            },
            "mocked": reviewer.mocked,
            "generated_at": review.generated_at.isoformat(),
        },
    }


def create_router(review: ReviewHospitalDocuments) -> APIRouter:
    router = APIRouter()

    @router.post(PATH)
    async def create_hospital_document_review(request: Request) -> JSONResponse:
        try:
            body = ReviewRequestBody.model_validate_json(await request.body())
            dossier = Dossier(
                fields=tuple(DossierField(f.path, f.value) for f in body.fields),
                documents=tuple(
                    DossierDocument(d.document_ref, d.type, d.title, d.status, d.text)
                    for d in body.documents
                ),
            )
        except ValidationError as error:
            fields = sorted(
                {".".join(str(p) for p in e["loc"]) or "body" for e in error.errors()}
            )
            return _problem("Invalid or missing fields: " + ", ".join(fields))
        except InvalidDossier as error:
            return _problem(str(error))
        try:
            result = await run_in_threadpool(
                review, ReviewRequest(body.application_ref, body.requested_by, dossier)
            )
        except ReviewUnavailable as error:
            return _problem(
                str(error),
                status=503,
                title="Hospital document review unavailable",
                code="review_unavailable",
            )
        return JSONResponse(_wire(result))

    return router
