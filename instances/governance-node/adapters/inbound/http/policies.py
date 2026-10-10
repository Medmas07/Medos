"""contracts/api/governance/governance-policies.v1.yaml (HC-135).

Lists and reads the governance policy versions with their status now. Read-only: the
policy is the Authority's data, read at startup; how a new version is written and
approved is OPEN. Readers are not authenticated.
"""

from collections.abc import Callable
from datetime import datetime

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from adapters.inbound.http.problems import problem
from application.policy import PolicyNotFound, get_policy, list_policies
from domain.policy import GovernancePolicy, PolicyHistory, PolicyStatus

NOTICE = (
    "Fictional demo governance policy, read by the Governance Node at startup. It is "
    "demo policy, not a validated legal or ethical framework."
)


def _wire(policy: GovernancePolicy, status: PolicyStatus) -> dict:
    return {
        "policy_ref": policy.policy_ref,
        "version": policy.version,
        "effective_from": policy.effective_from.isoformat(),
        "status": status.value,
        "title": policy.title,
        "rules": {
            "review": {"minimum_rationale_length": policy.minimum_rationale_length},
            "synchronization": {
                "maximum_duration_days": policy.maximum_sync_duration_days,
                "consent_bases": {
                    basis: mode.value for basis, mode in policy.consent_bases
                },
            },
            "research": {
                "maximum_validity_months": policy.maximum_research_validity_months,
                "minimum_cell_size": policy.minimum_cell_size,
            },
        },
    }


def create_router(policies: PolicyHistory, clock: Callable[[], datetime]) -> APIRouter:
    router = APIRouter(prefix="/v1/policies", tags=["policy"])

    @router.get("")
    def list_governance_policies() -> JSONResponse:
        rows = list_policies(policies, clock())
        return JSONResponse(
            {"notice": NOTICE, "policies": [_wire(*row) for row in rows]}
        )

    @router.get("/{policy_ref}")
    def get_governance_policy(policy_ref: str) -> JSONResponse:
        try:
            return JSONResponse(_wire(*get_policy(policy_ref, policies, clock())))
        except PolicyNotFound:
            return problem(
                404,
                "Policy not found",
                "policy_not_found",
                f"No governance policy {policy_ref}.",
            )

    return router
