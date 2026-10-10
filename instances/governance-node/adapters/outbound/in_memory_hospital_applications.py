"""HospitalApplicationStore in memory, seeded from fictional demo data (HC-131).

Explicit D2 storage, not a mock of another component: the Governance Node holds these
applications and decisions itself, but only in memory, so decisions recorded through
the API are lost on restart. Persistence is OPEN. At startup it reads the hospital
applications and their decisions from demo-data/governance.json; a file not marked
fictional, or inconsistent, stops startup.
"""

import json
import threading
from datetime import datetime
from pathlib import Path

from domain.hospital_application import (
    ApplicationStatus,
    Findings,
    HospitalApplication,
    MissingDocument,
)
from domain.hospital_approval import (
    HospitalApprovalDecision,
    NotAwaitingReview,
    Outcome,
)


class SeedError(RuntimeError):
    pass


class InMemoryHospitalApplicationStore:
    def __init__(
        self,
        applications: list[HospitalApplication],
        decisions: list[HospitalApprovalDecision],
    ) -> None:
        self._applications = {a.application_ref: a for a in applications}
        self._decisions = {d.decision_ref: d for d in decisions}
        self._lock = threading.Lock()
        for application in applications:
            if application.decision_ref is None:
                continue
            decision = self._decisions.get(application.decision_ref)
            if (
                decision is None
                or decision.application_ref != application.application_ref
            ):
                raise SeedError(
                    f"{application.application_ref} cites a decision that is not its own"
                )
            if decision.outcome.value != application.status.value:
                raise SeedError(
                    f"{application.application_ref} status differs from its decision"
                )

    @classmethod
    def load(cls, path: Path) -> "InMemoryHospitalApplicationStore":
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if data.get("fictional") is not True:
                raise SeedError(f"{path} is not marked fictional")
            decisions = [
                _decision(d, data["hospitalApplications"])
                for d in data["decisions"]
                if d["subjectType"] == "hospital_application"
            ]
            applications = [_application(a) for a in data["hospitalApplications"]]
            return cls(applications, decisions)
        except SeedError:
            raise
        except (OSError, ValueError, KeyError, TypeError) as error:
            raise SeedError(
                f"Cannot load hospital applications {path}: {error}"
            ) from error

    def applications(self) -> list[HospitalApplication]:
        with self._lock:
            return list(self._applications.values())

    def application(self, application_ref: str) -> HospitalApplication | None:
        with self._lock:
            return self._applications.get(application_ref)

    def decision(self, decision_ref: str) -> HospitalApprovalDecision | None:
        with self._lock:
            return self._decisions.get(decision_ref)

    def record(
        self, decided: HospitalApplication, decision: HospitalApprovalDecision
    ) -> None:
        with self._lock:
            current = self._applications[decided.application_ref]
            if not current.awaiting_review or decision.decision_ref in self._decisions:
                raise NotAwaitingReview(
                    f"Application {decided.application_ref} was decided in the meantime."
                )
            self._applications[decided.application_ref] = decided
            self._decisions[decision.decision_ref] = decision


def _findings(raw: dict) -> Findings:
    def step(name: str) -> tuple[str, ...]:
        for s in raw.get("reviewSteps", []):
            if s["step"] == name:
                return tuple(s.get("findings", []))
        return ()

    return Findings(
        missing_documents=tuple(
            MissingDocument(d["id"], d["type"], d["title"])
            for d in raw["documents"]
            if d["status"] != "received"
        ),
        unaccepted_agreements=tuple(
            a["code"] for a in raw["agreements"] if not a["accepted"]
        ),
        completeness_findings=step("completeness_check"),
        advisory_findings=step("assisted_review"),
    )


def _application(raw: dict) -> HospitalApplication:
    return HospitalApplication(
        application_ref=raw["id"],
        organization_ref=raw["organizationId"],
        status=ApplicationStatus(raw["status"]),
        submitted_at=datetime.fromisoformat(raw["submittedAt"]),
        findings=_findings(raw),
        decision_ref=raw["decisionId"],
    )


def _decision(raw: dict, applications: list[dict]) -> HospitalApprovalDecision:
    subject = next((a for a in applications if a["id"] == raw["subjectId"]), None)
    if subject is None:
        raise SeedError(f"{raw['id']} decides an unknown application")
    decided_at = datetime.fromisoformat(raw["decidedAt"])
    if decided_at.tzinfo is None:
        raise SeedError(f"{raw['id']} decidedAt has no UTC offset")
    return HospitalApprovalDecision(
        decision_ref=raw["id"],
        application_ref=raw["subjectId"],
        organization_ref=subject["organizationId"],
        outcome=Outcome(raw["outcome"]),
        decided_by_ref=raw["decidedById"],
        decided_at=decided_at,
        rationale=raw["rationale"],
        conditions=tuple(raw["conditions"]),
        policy_ref=raw["policyId"],
    )
