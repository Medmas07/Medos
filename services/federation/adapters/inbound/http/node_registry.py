"""HTTP adapter for contracts/federation/node-registry.v1.yaml."""

from typing import Annotated

from fastapi import APIRouter, Path, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator

from adapters.inbound.http.federated_query import OpaqueRef, problem
from application.node_registry import (
    NodeNotFound,
    NodeRegistry,
    OrganizationAlreadyRegistered,
    RegistrationRequest,
)
from domain.node_registration import (
    REGISTRY_NOTICE,
    InvalidRegistration,
    NodeRegistration,
)

PATH = "/v1/registry/nodes"
NodeRefPath = Annotated[
    str, Path(pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$", max_length=128)
]


class RegistrationBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    organization_ref: OpaqueRef
    base_url: Annotated[str, Field(min_length=1, max_length=2048)]
    contract_versions: Annotated[
        list[Annotated[str, Field(pattern=r"^[0-9]+\.[0-9]+$")]], Field(min_length=1)
    ]
    approval_decision_ref: OpaqueRef

    @field_validator("contract_versions")
    @classmethod
    def _unique(cls, versions: list[str]) -> list[str]:
        if len(set(versions)) != len(versions):
            raise ValueError("items must be unique")
        return versions


def to_wire(registration: NodeRegistration) -> dict:
    return {
        "node_ref": registration.node_ref,
        "organization_ref": registration.organization_ref,
        "base_url": registration.base_url,
        "contract_versions": sorted(registration.contract_versions),
        "approval": {
            "decision_ref": registration.approval_decision_ref,
            "verified": False,
        },
        "registered_at": registration.registered_at.isoformat(),
        "updated_at": registration.updated_at.isoformat(),
    }


def not_found(node_ref: str) -> JSONResponse:
    return problem(
        404, "Node not found", "node_not_found", f"{node_ref} is not registered."
    )


def create_router(registry: NodeRegistry) -> APIRouter:
    router = APIRouter()

    @router.get(PATH)
    def list_nodes() -> JSONResponse:
        return JSONResponse(
            {
                "notice": REGISTRY_NOTICE,
                "nodes": [to_wire(r) for r in registry.list()],
            }
        )

    @router.get(PATH + "/{node_ref}")
    def get_node(node_ref: NodeRefPath) -> JSONResponse:
        try:
            return JSONResponse(to_wire(registry.get(node_ref)))
        except NodeNotFound:
            return not_found(node_ref)

    @router.put(PATH + "/{node_ref}")
    def register_node(node_ref: NodeRefPath, body: RegistrationBody) -> JSONResponse:
        try:
            registration, created = registry.register(
                RegistrationRequest(
                    node_ref=node_ref,
                    organization_ref=body.organization_ref,
                    base_url=body.base_url,
                    contract_versions=frozenset(body.contract_versions),
                    approval_decision_ref=body.approval_decision_ref,
                )
            )
        except InvalidRegistration as error:
            return problem(
                400, "Invalid node registration", "invalid_request", str(error)
            )
        except OrganizationAlreadyRegistered as error:
            return problem(
                409,
                "Organization already registered",
                "organization_already_registered",
                str(error),
            )
        return JSONResponse(to_wire(registration), status_code=201 if created else 200)

    @router.delete(PATH + "/{node_ref}", status_code=204)
    def deregister_node(node_ref: NodeRefPath) -> Response:
        try:
            registry.deregister(node_ref)
        except NodeNotFound:
            return not_found(node_ref)
        return Response(status_code=204)

    return router
