"""SynchronizationStore in memory, seeded from fictional demo data (HC-132).

Explicit D2 storage: the Governance Node holds these requests and decisions itself, but
only in memory, so requests and decisions recorded through the API are lost on restart.
Persistence is OPEN. At startup it reads the synchronization requests and their
decisions from demo-data/governance.json; a file not marked fictional, or inconsistent,
stops startup.
"""

import json
import re
import threading
from collections.abc import Callable
from datetime import datetime, timedelta
from pathlib import Path

from adapters.outbound.in_memory_hospital_applications import SeedError
from domain.hospital_approval import Outcome
from domain.synchronization import (
    Consent,
    ConsentBasis,
    NotPending,
    ScopeItem,
    SynchronizationDecision,
    SynchronizationRequest,
)

# The demo data names record categories in camelCase.
FIXTURE_SCOPE = {
    "encounters": ScopeItem.ENCOUNTERS,
    "medications": ScopeItem.MEDICATIONS,
    "labReports": ScopeItem.LAB_REPORTS,
}
_NUMBERED = re.compile(r"sync-(\d+)")


class InMemorySynchronizationStore:
    def __init__(
        self,
        requests: list[SynchronizationRequest],
        decisions: list[SynchronizationDecision],
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
    def load(cls, path: Path) -> "InMemorySynchronizationStore":
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if data.get("fictional") is not True:
                raise SeedError(f"{path} is not marked fictional")
            raw_requests = data["synchronizationRequests"]
            requests = [_request(r) for r in raw_requests]
            decisions = [
                _decision(d)
                for d in data["decisions"]
                if d["subjectType"] == "synchronization_request"
            ]
            for raw in raw_requests:
                decided = raw["status"] in ("approved", "rejected")
                if decided != (raw["decisionId"] is not None):
                    raise SeedError(f"{raw['id']} status and decision disagree")
                outcome = next(
                    (
                        d.outcome.value
                        for d in decisions
                        if d.decision_ref == raw["decisionId"]
                    ),
                    None,
                )
                if decided and outcome != raw["status"]:
                    raise SeedError(f"{raw['id']} status differs from its decision")
            return cls(requests, decisions)
        except SeedError:
            raise
        except (OSError, ValueError, KeyError, TypeError) as error:
            raise SeedError(
                f"Cannot load synchronization requests {path}: {error}"
            ) from error

    def requests(self) -> list[SynchronizationRequest]:
        with self._lock:
            return list(self._requests.values())

    def request(self, request_ref: str) -> SynchronizationRequest | None:
        with self._lock:
            return self._requests.get(request_ref)

    def decision(self, decision_ref: str) -> SynchronizationDecision | None:
        with self._lock:
            return self._decisions.get(decision_ref)

    def submit(
        self, new_request: Callable[[str], SynchronizationRequest]
    ) -> SynchronizationRequest:
        with self._lock:
            numbers = [
                int(m.group(1))
                for ref in self._requests
                if (m := _NUMBERED.fullmatch(ref))
            ]
            request = new_request(f"sync-{max(numbers, default=0) + 1:03d}")
            self._requests[request.request_ref] = request
            return request

    def record(
        self, decided: SynchronizationRequest, decision: SynchronizationDecision
    ) -> None:
        with self._lock:
            current = self._requests[decided.request_ref]
            if (
                current.decision_ref is not None
                or decision.decision_ref in self._decisions
            ):
                raise NotPending(
                    f"Request {decided.request_ref} was decided in the meantime."
                )
            self._requests[decided.request_ref] = decided
            self._decisions[decision.decision_ref] = decision


def _request(raw: dict) -> SynchronizationRequest:
    consent = raw["consent"]
    return SynchronizationRequest(
        request_ref=raw["id"],
        requester_organization_ref=raw["requesterOrganizationId"],
        target_organization_ref=raw["targetOrganizationId"],
        patient_ref=raw["patientId"],
        purpose=raw["purpose"],
        scope=frozenset(FIXTURE_SCOPE[item] for item in raw["scope"]),
        duration_days=raw["durationDays"],
        consent=Consent(ConsentBasis(consent["basis"]), consent["accessGrantId"]),
        submitted_at=datetime.fromisoformat(raw["submittedAt"]),
        decision_ref=raw["decisionId"],
    )


def _decision(raw: dict) -> SynchronizationDecision:
    decided_at = datetime.fromisoformat(raw["decidedAt"])
    valid_until = (
        datetime.fromisoformat(raw["validUntil"]) if raw["validUntil"] else None
    )
    if decided_at.tzinfo is None or (valid_until and valid_until.tzinfo is None):
        raise SeedError(f"{raw['id']} has a time without UTC offset")
    approved_days = (
        round((valid_until - decided_at) / timedelta(days=1)) if valid_until else None
    )
    return SynchronizationDecision(
        decision_ref=raw["id"],
        request_ref=raw["subjectId"],
        outcome=Outcome(raw["outcome"]),
        decided_by_ref=raw["decidedById"],
        decided_at=decided_at,
        rationale=raw["rationale"],
        conditions=tuple(raw["conditions"]),
        approved_days=approved_days,
        valid_until=valid_until,
    )
