"""AuditLedgerPort as a simulated immutable ledger (HC-191). MOCKED.

Not a blockchain and not a real ledger: an append-only list in this process's memory,
lost on restart (`durable` is false), with no consensus, signature, or replication.
Immutable only in that nothing here changes or removes a proof once anchored: an event
is anchored once, and anchoring it again with another payload is a ProofConflict. Each
proof holds its payload's SHA-256 hash (HC-192), computed here by the Node itself: not
signed, and not anchored anywhere else.

At startup it reads the fictional simulated proofs of demo-data/governance.json, and
checks that each anchors exactly the minimized payload of the audit event it names,
with that payload's hash. A file not marked fictional, a proof not marked simulated,
or an inconsistent proof stops startup.
"""

import json
import re
import threading
from collections.abc import Callable, Iterable
from datetime import datetime
from pathlib import Path

from adapters.outbound.in_memory_hospital_applications import SeedError
from application.audit import AuditTrail
from application.ledger import ProofConflict
from domain.audit import AuditOutcome
from domain.ledger import (
    HASH_ALGORITHM,
    LedgerProof,
    NotAnchorable,
    ProofPayload,
    hash_payload,
    proof_payload,
)

# The ledger name of the demo proofs; never the name of a real ledger.
LEDGER_NAME = "local-simulation"
_NUMBERED = re.compile(r"proof-(\d+)")
# The only fields a proof anchors (domain.ledger.ProofPayload), as the seed names them.
_PAYLOAD_FIELDS = {
    "eventId",
    "decisionId",
    "outcome",
    "decidedAt",
    "organizationIds",
    "version",
}


class SimulatedAuditLedger:
    simulated = True
    durable = False

    def __init__(
        self, clock: Callable[[], datetime], proofs: Iterable[LedgerProof] = ()
    ) -> None:
        self._clock = clock
        self._proofs: list[LedgerProof] = []
        self._by_event: dict[str, LedgerProof] = {}
        self._lock = threading.Lock()
        for proof in proofs:
            if proof.payload.event_ref in self._by_event:
                raise SeedError(f"{proof.payload.event_ref} is anchored twice")
            if any(p.proof_ref == proof.proof_ref for p in self._proofs):
                raise SeedError(f"{proof.proof_ref} is recorded twice")
            self._store(proof)

    @classmethod
    def load(
        cls, path: Path, trail: AuditTrail, clock: Callable[[], datetime]
    ) -> "SimulatedAuditLedger":
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if data.get("fictional") is not True:
                raise SeedError(f"{path} is not marked fictional")
            return cls(clock, [_proof(raw, trail) for raw in data["ledgerProofs"]])
        except SeedError:
            raise
        except (OSError, ValueError, KeyError, TypeError) as error:
            raise SeedError(f"Cannot load ledger proofs {path}: {error}") from error

    def anchor(self, payload: ProofPayload) -> LedgerProof:
        with self._lock:
            existing = self._by_event.get(payload.event_ref)
            if existing is not None:
                if existing.payload != payload:
                    raise ProofConflict(payload.event_ref)
                return existing
            numbers = [
                int(m.group(1))
                for proof in self._proofs
                if (m := _NUMBERED.fullmatch(proof.proof_ref))
            ]
            proof = LedgerProof(
                proof_ref=f"proof-{max(numbers, default=0) + 1:03d}",
                payload=payload,
                ledger=LEDGER_NAME,
                anchored_at=self._clock(),
                payload_hash=hash_payload(payload),
            )
            self._store(proof)
            return proof

    def proof(self, event_ref: str) -> LedgerProof | None:
        with self._lock:
            return self._by_event.get(event_ref)

    def proofs(self) -> list[LedgerProof]:
        with self._lock:
            return list(self._proofs)

    def _store(self, proof: LedgerProof) -> None:
        self._proofs.append(proof)
        self._by_event[proof.payload.event_ref] = proof


def _time(raw: str, where: str) -> datetime:
    value = datetime.fromisoformat(raw)
    if value.tzinfo is None:
        raise SeedError(f"{where} has a time without UTC offset")
    return value


def _proof(raw: dict, trail: AuditTrail) -> LedgerProof:
    ref = raw["id"]
    if raw.get("simulated") is not True or raw["ledger"] != LEDGER_NAME:
        raise SeedError(f"{ref} is not a {LEDGER_NAME} simulated proof")
    anchored = raw["anchoredPayload"]
    # Exactly the payload fields: nothing else may reach the ledger.
    if set(anchored) != _PAYLOAD_FIELDS:
        raise SeedError(f"{ref} anchors other fields than the proof payload")
    payload = ProofPayload(
        event_ref=anchored["eventId"],
        decision_ref=anchored["decisionId"],
        outcome=AuditOutcome(anchored["outcome"]),
        decided_at=_time(anchored["decidedAt"], ref),
        organization_refs=tuple(anchored["organizationIds"]),
        version=anchored["version"],
    )
    event = trail.event(raw["auditEventId"])
    if event is None or event.event_ref != payload.event_ref:
        raise SeedError(f"{ref} does not anchor the audit event it names")
    try:
        expected = proof_payload(event)
    except NotAnchorable as error:
        raise SeedError(f"{ref}: {error}") from error
    if payload != expected:
        raise SeedError(f"{ref} does not anchor the payload of {event.event_ref}")
    if raw["hashAlgorithm"] != HASH_ALGORITHM or raw["hash"] != hash_payload(payload):
        raise SeedError(f"{ref} does not hold the {HASH_ALGORITHM} hash of its payload")
    return LedgerProof(
        proof_ref=ref,
        payload=payload,
        ledger=LEDGER_NAME,
        anchored_at=_time(raw["anchoredAt"], ref),
        payload_hash=raw["hash"],
    )
