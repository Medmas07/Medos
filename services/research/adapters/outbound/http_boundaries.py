"""HTTP adapters for Governance and Hospital Node Compute-to-Data boundaries."""

import httpx

from domain.research_job import (
    AuthorizationDecision,
    ExecutionStatus,
    JobError,
    NodeExecution,
    ResearchJob,
)


class HttpGovernanceAuthorization:
    def __init__(self, base_url: str | None, timeout: float = 5.0) -> None:
        self.base_url = base_url.rstrip("/") if base_url else None
        self.timeout = timeout

    def check(self, job: ResearchJob) -> AuthorizationDecision:
        if not self.base_url:
            raise RuntimeError("Governance endpoint is not configured")
        response = httpx.post(
            f"{self.base_url}/v1/research-authorizations/check",
            json={
                "decision_ref": job.authorization_decision_ref,
                "project_ref": job.project_ref,
                "requested_by": job.requested_by,
                "purpose": job.purpose,
                "target_organization_refs": list(job.target_organizations),
                "data_scope": job.data_scope,
            },
            timeout=self.timeout,
        )
        response.raise_for_status()
        document = response.json()
        return AuthorizationDecision(
            decision_ref=document["decision_ref"],
            approved=document["status"] == "approved",
            approved_organization_refs=tuple(
                document.get("approved_organization_refs", [])
            ),
            approved_variables=tuple(document.get("approved_variables", [])),
            authority_organization_ref=document["authority_organization_ref"],
            valid_until=document.get("valid_until"),
            reason_code=document.get("reason_code"),
        )


class HttpHospitalExecution:
    def __init__(self, node_urls: dict[str, str], timeout: float = 5.0) -> None:
        self.node_urls = {key: value.rstrip("/") for key, value in node_urls.items()}
        self.timeout = timeout

    def submit(
        self,
        job: ResearchJob,
        organization_ref: str,
        authorization: AuthorizationDecision,
    ) -> NodeExecution:
        base_url = self._base_url(organization_ref)
        execution_id = f"{job.job_ref}-exec-{organization_ref}"
        response = httpx.post(
            f"{base_url}/v1/research-executions",
            json={
                "execution_id": execution_id,
                "job_ref": job.job_ref,
                "project_ref": job.project_ref,
                "target": {
                    "node_ref": organization_ref.replace("org-", "node-"),
                    "organization_ref": organization_ref,
                },
                "submitted_by": {
                    "organization_ref": "org-platform",
                    "actor_ref": job.requested_by,
                },
                "purpose": job.purpose,
                "authorization": {
                    "decision_ref": authorization.decision_ref,
                    "authority_organization_ref": authorization.authority_organization_ref,
                    "valid_until": authorization.valid_until,
                    "approved_organization_refs": list(
                        authorization.approved_organization_refs
                    ),
                    "approved_variables": list(authorization.approved_variables),
                },
                "data_scope": job.data_scope,
                "algorithm": job.algorithm,
                "output_policy": job.output_policy,
            },
            timeout=self.timeout,
        )
        response.raise_for_status()
        return self._execution(response.json(), organization_ref)

    def read(self, execution: NodeExecution) -> NodeExecution:
        base_url = self._base_url(execution.organization_ref)
        response = httpx.get(
            f"{base_url}/v1/research-executions/{execution.execution_id}",
            timeout=self.timeout,
        )
        response.raise_for_status()
        return self._execution(response.json(), execution.organization_ref)

    def _base_url(self, organization_ref: str) -> str:
        try:
            return self.node_urls[organization_ref]
        except KeyError as error:
            raise RuntimeError(
                f"No endpoint configured for {organization_ref}"
            ) from error

    @staticmethod
    def _execution(document: dict, organization_ref: str) -> NodeExecution:
        raw_error = document.get("error")
        error = JobError(**raw_error) if raw_error else None
        return NodeExecution(
            execution_id=document["execution_id"],
            organization_ref=document.get("organization_ref", organization_ref),
            status=ExecutionStatus(document["status"]),
            result=document.get("result"),
            error=error,
        )
