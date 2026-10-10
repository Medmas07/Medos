"""ResearchStore in memory, seeded from fictional demo data (HC-133).

Explicit D2 storage: the Governance Node holds these requests and decisions itself, but
only in memory, so requests and decisions recorded through the API are lost on restart.
Persistence is OPEN. At startup it reads the research access requests and their
decisions from demo-data/governance.json, and each request's project content (title,
investigator, participating organizations, structured data scope, protocol reference)
from demo-data/research.json, as the Research Portal would submit it. A file not marked
fictional, or inconsistent, stops startup.
"""

import json
import re
import threading
from collections.abc import Callable
from datetime import date, datetime
from pathlib import Path

from adapters.outbound.in_memory_hospital_applications import SeedError
from domain.hospital_approval import Outcome
from domain.research import (
    DataScope,
    NotUnderReview,
    Population,
    ResearchDecision,
    ResearchRequest,
)

_NUMBERED = re.compile(r"rar-(\d+)")


class InMemoryResearchStore:
    def __init__(
        self, requests: list[ResearchRequest], decisions: list[ResearchDecision]
    ) -> None:
        self._requests = {r.request_ref: r for r in requests}
        self._decisions = {d.decision_ref: d for d in decisions}
        self._lock = threading.Lock()
        for request in requests:
            decision = self._decisions.get(request.decision_ref or "")
            if request.decision_ref and (
                decision is None or decision.request_ref != request.request_ref
            ):
                raise SeedError(
                    f"{request.request_ref} cites a decision that is not its own"
                )

    @classmethod
    def load(
        cls, governance_path: Path, research_path: Path
    ) -> "InMemoryResearchStore":
        try:
            governance = json.loads(governance_path.read_text(encoding="utf-8"))
            research = json.loads(research_path.read_text(encoding="utf-8"))
            for path, data in (
                (governance_path, governance),
                (research_path, research),
            ):
                if data.get("fictional") is not True:
                    raise SeedError(f"{path} is not marked fictional")
            projects = {p["id"]: p for p in research["projects"]}
            raw_requests = governance["researchAccessRequests"]
            requests = [_request(r, projects[r["projectId"]]) for r in raw_requests]
            decisions = [
                _decision(d)
                for d in governance["decisions"]
                if d["subjectType"] == "research_access_request"
            ]
            outcomes = {d.decision_ref: d.outcome.value for d in decisions}
            for raw in raw_requests:
                decided = raw["status"] in ("approved", "rejected")
                if decided != (raw["decisionId"] is not None):
                    raise SeedError(f"{raw['id']} status and decision disagree")
                if decided and outcomes.get(raw["decisionId"]) != raw["status"]:
                    raise SeedError(f"{raw['id']} status differs from its decision")
            return cls(requests, decisions)
        except SeedError:
            raise
        except (OSError, ValueError, KeyError, TypeError) as error:
            raise SeedError(f"Cannot load research requests: {error}") from error

    def requests(self) -> list[ResearchRequest]:
        with self._lock:
            return list(self._requests.values())

    def request(self, request_ref: str) -> ResearchRequest | None:
        with self._lock:
            return self._requests.get(request_ref)

    def decision(self, decision_ref: str) -> ResearchDecision | None:
        with self._lock:
            return self._decisions.get(decision_ref)

    def submit(self, new_request: Callable[[str], ResearchRequest]) -> ResearchRequest:
        with self._lock:
            numbers = [
                int(m.group(1))
                for ref in self._requests
                if (m := _NUMBERED.fullmatch(ref))
            ]
            request = new_request(f"rar-{max(numbers, default=0) + 1:03d}")
            self._requests[request.request_ref] = request
            return request

    def record(self, decided: ResearchRequest, decision: ResearchDecision) -> None:
        with self._lock:
            current = self._requests[decided.request_ref]
            if (
                current.decision_ref is not None
                or decision.decision_ref in self._decisions
            ):
                raise NotUnderReview(
                    f"Request {decided.request_ref} was decided in the meantime."
                )
            self._requests[decided.request_ref] = decided
            self._decisions[decision.decision_ref] = decision


def _population(raw: dict) -> Population:
    def day(key: str) -> date | None:
        return date.fromisoformat(raw[key]) if key in raw else None

    return Population(
        age_min=raw.get("ageMin"),
        age_max=raw.get("ageMax"),
        encounter_from=day("encounterFrom"),
        encounter_to=day("encounterTo"),
    )


def _request(raw: dict, project: dict) -> ResearchRequest:
    scope = project["dataScope"]
    protocol = project.get("protocolDocument")
    return ResearchRequest(
        request_ref=raw["id"],
        project_ref=project["id"],
        project_title=project["title"],
        research_organization_ref=project["organizationId"],
        principal_investigator_ref=project["principalInvestigatorId"],
        submitted_by_ref=raw["submittedById"],
        purpose=project["summary"],
        participating_organization_refs=tuple(project["participatingOrganizationIds"]),
        data_scope=DataScope(
            _population(scope["population"]), tuple(scope["variables"])
        ),
        protocol_document_ref=protocol["id"] if protocol else None,
        submitted_at=datetime.fromisoformat(raw["submittedAt"]),
        decision_ref=raw["decisionId"],
    )


def _decision(raw: dict) -> ResearchDecision:
    decided_at = datetime.fromisoformat(raw["decidedAt"])
    valid_until = (
        datetime.fromisoformat(raw["validUntil"]) if raw["validUntil"] else None
    )
    if decided_at.tzinfo is None or (valid_until and valid_until.tzinfo is None):
        raise SeedError(f"{raw['id']} has a time without UTC offset")
    authorization = raw.get("researchAuthorization") or {}
    return ResearchDecision(
        decision_ref=raw["id"],
        request_ref=raw["subjectId"],
        outcome=Outcome(raw["outcome"]),
        decided_by_ref=raw["decidedById"],
        decided_at=decided_at,
        rationale=raw["rationale"],
        conditions=tuple(raw["conditions"]),
        approved_organization_refs=tuple(
            authorization.get("approvedOrganizationIds", ())
        ),
        approved_variables=tuple(authorization.get("approvedVariables", ())),
        minimum_cell_size=authorization.get("minimumCellSize"),
        valid_until=valid_until,
    )
