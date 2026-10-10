"""HC-172 HTTP boundary consumed by the Research Portal."""

from typing import Any, Protocol
from uuid import UUID

from fastapi import APIRouter, FastAPI, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from .client import SciAgentsAdapterError


class InvestigationPort(Protocol):
    def submit(self, request: dict[str, Any]) -> dict[str, Any]: ...

    def get(self, investigation_id: str) -> dict[str, Any]: ...


class Concept(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label: str = Field(min_length=1, max_length=200)


class InvestigationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project_ref: str = Field(min_length=1, max_length=100, pattern=r"^[A-Za-z0-9._:-]+$")
    requested_by: str = Field(min_length=1, max_length=100, pattern=r"^[A-Za-z0-9._:-]+$")
    question: str = Field(min_length=1, max_length=2000)
    language: str | None = Field(default=None, pattern=r"^[A-Za-z]{2,3}(-[A-Za-z0-9]{2,8})*$")
    concepts: list[Concept] = Field(min_length=2, max_length=2)


def problem(status_code: int, title: str, code: str, detail: str | None = None) -> JSONResponse:
    content: dict[str, Any] = {
        "type": "about:blank",
        "title": title,
        "status": status_code,
        "code": code,
    }
    if detail:
        content["detail"] = detail
    return JSONResponse(
        status_code=status_code,
        content=content,
        media_type="application/problem+json",
    )


def configure_contract_errors(app: FastAPI) -> None:
    @app.exception_handler(RequestValidationError)
    async def invalid_request(_request: Request, _error: RequestValidationError) -> JSONResponse:
        return problem(400, "Invalid investigation request", "invalid_request")


def create_router(client: InvestigationPort) -> APIRouter:
    router = APIRouter(prefix="/v1/investigations", tags=["sciagents"])

    @router.post("", status_code=status.HTTP_202_ACCEPTED, response_model=None)
    def submit(request: InvestigationRequest, response: Response) -> dict[str, Any] | JSONResponse:
        try:
            investigation = client.submit(request.model_dump(exclude_none=True))
        except SciAgentsAdapterError as error:
            if error.code == "rejected_by_upstream":
                return problem(400, "Invalid investigation request", "invalid_request", str(error))
            return problem(503, "SciAgents unavailable", "sciagents_unavailable", str(error))
        response.headers["Location"] = f"/v1/investigations/{investigation['investigation_id']}"
        return investigation

    @router.get("/{investigation_id}", response_model=None)
    def read(investigation_id: UUID) -> dict[str, Any] | JSONResponse:
        try:
            return client.get(str(investigation_id))
        except KeyError:
            return problem(404, "Investigation not found", "investigation_not_found")

    return router
