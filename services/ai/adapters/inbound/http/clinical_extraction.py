"""HTTP adapter for contracts/api/ai/clinical-extraction.v1.yaml."""

from datetime import datetime
from typing import Annotated, Literal

from fastapi import APIRouter, FastAPI, Request
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from application.extract_clinical_information import (
    ExtractClinicalInformation,
    ExtractionRequest,
    ExtractionUnavailable,
)
from domain.clinical_extraction import (
    MAX_SOURCE_LENGTH,
    ExtractionDraft,
    ExtractionSource,
    InvalidExtraction,
    ItemCategory,
    ExtractorKind,
    SourceType,
)

PATH = "/v1/clinical-extractions"
CONTRACT_VERSION = "1.0"

OpaqueRef = Annotated[str, Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")]


class SourceBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: SourceType
    text: Annotated[str, Field(min_length=1, max_length=MAX_SOURCE_LENGTH)]
    language: (
        Annotated[str, Field(pattern=r"^[A-Za-z]{2,3}(-[A-Za-z0-9]{2,8})*$")] | None
    ) = None


class ExtractionRequestBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    patient_ref: OpaqueRef
    encounter_ref: OpaqueRef | None = None
    requested_by: OpaqueRef
    source: SourceBody


class EvidenceBody(BaseModel):
    quote: str
    start: int
    end: int


class ExtractedItemBody(BaseModel):
    item_id: str
    category: ItemCategory
    text: str
    value: float | None
    unit: str | None
    abnormal: bool | None
    confidence: float | None
    evidence: EvidenceBody


class MissingInformationBody(BaseModel):
    topic: str
    prompt: str


class ExtractorBody(BaseModel):
    kind: ExtractorKind
    name: str
    version: str


class ProvenanceBody(BaseModel):
    extractor: ExtractorBody
    mocked: bool
    generated_at: datetime
    source_type: SourceType


class ExtractionDraftBody(BaseModel):
    extraction_id: str
    contract_version: Literal["1.0"]
    patient_ref: str
    encounter_ref: str | None = None
    requested_by: str
    review_status: Literal["pending_clinician_review"]
    advisory: Literal[True]
    notice: str
    items: list[ExtractedItemBody]
    missing_information: list[MissingInformationBody]
    provenance: ProvenanceBody


class ProblemBody(BaseModel):
    type: str
    title: str
    status: int
    detail: str | None = None
    code: Literal["invalid_request", "extraction_unavailable"]


def _to_body(draft: ExtractionDraft) -> ExtractionDraftBody:
    extractor = draft.provenance.extractor
    return ExtractionDraftBody(
        extraction_id=draft.extraction_id,
        contract_version=CONTRACT_VERSION,
        patient_ref=draft.patient_ref,
        encounter_ref=draft.encounter_ref,
        requested_by=draft.requested_by,
        review_status=draft.review_status.value,
        advisory=True,
        notice=draft.notice,
        items=[
            ExtractedItemBody(
                item_id=item.item_id,
                category=item.category,
                text=item.text,
                value=item.value,
                unit=item.unit,
                abnormal=item.abnormal,
                confidence=item.confidence,
                evidence=EvidenceBody(
                    quote=item.evidence.quote,
                    start=item.evidence.start,
                    end=item.evidence.end,
                ),
            )
            for item in draft.items
        ],
        missing_information=[
            MissingInformationBody(topic=m.topic, prompt=m.prompt)
            for m in draft.missing_information
        ],
        provenance=ProvenanceBody(
            extractor=ExtractorBody(
                kind=extractor.kind, name=extractor.name, version=extractor.version
            ),
            mocked=extractor.mocked,
            generated_at=draft.provenance.generated_at,
            source_type=draft.provenance.source_type,
        ),
    )


def _problem(
    detail: str,
    status: int = 400,
    title: str = "Invalid clinical extraction request",
    code: Literal["invalid_request", "extraction_unavailable"] = "invalid_request",
) -> JSONResponse:
    problem = ProblemBody(
        type="about:blank", title=title, status=status, detail=detail, code=code
    )
    return JSONResponse(
        problem.model_dump(), status_code=status, media_type="application/problem+json"
    )


def create_router(extract: ExtractClinicalInformation) -> APIRouter:
    router = APIRouter()

    @router.post(
        PATH,
        response_model=ExtractionDraftBody,
        responses={400: {"model": ProblemBody}, 503: {"model": ProblemBody}},
    )
    def create_clinical_extraction(body: ExtractionRequestBody) -> JSONResponse:
        try:
            source = ExtractionSource(
                type=body.source.type,
                text=body.source.text,
                language=body.source.language,
            )
            draft = extract(
                ExtractionRequest(
                    patient_ref=body.patient_ref,
                    encounter_ref=body.encounter_ref,
                    requested_by=body.requested_by,
                    source=source,
                )
            )
        except InvalidExtraction as error:
            return _problem(str(error))
        except ExtractionUnavailable as error:
            return _problem(
                str(error),
                status=503,
                title="Clinical extraction unavailable",
                code="extraction_unavailable",
            )
        exclude = {"encounter_ref"} if draft.encounter_ref is None else set()
        return JSONResponse(_to_body(draft).model_dump(mode="json", exclude=exclude))

    return router


def register_problem_handler(app: FastAPI) -> None:
    @app.exception_handler(RequestValidationError)
    async def invalid_request(request: Request, error: RequestValidationError):
        if request.url.path != PATH:
            return await request_validation_exception_handler(request, error)
        fields = sorted(
            {
                ".".join(str(part) for part in e["loc"][1:]) or "body"
                for e in error.errors()
            }
        )
        return _problem("Invalid or missing fields: " + ", ".join(fields))
