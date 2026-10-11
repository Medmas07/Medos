"""contracts/api/governance/governance-ledger-proofs.v1.yaml (HC-191).

Reads the proofs the Governance Node anchored in its audit ledger: today the simulated
ledger only (MOCKED), so every answer says `simulated: true`. Readers are not
authenticated, as for the audit trail.
"""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from adapters.inbound.http.problems import problem
from application.audit import AuditTrail, EventNotFound, get_event
from application.ledger import (
    AuditLedgerPort,
    LedgerUnavailable,
    ProofNotFound,
    get_proof,
    list_proofs,
)
from domain.ledger import LedgerProof
from domain.node_identity import NodeIdentity

NOTICE = (
    "MOCKED BLOCKCHAIN. Fictional demo proofs held by the Governance Node's simulated "
    "immutable ledger: an append-only list in memory, not a blockchain or a real "
    "ledger; proofs anchored at runtime are lost on restart and payloads are not "
    "hashed. Only a decision's minimized payload is anchored, never clinical content."
)


def _wire(proof: LedgerProof) -> dict:
    payload = proof.payload
    return {
        "proof_ref": proof.proof_ref,
        "ledger": proof.ledger,
        "anchored_at": proof.anchored_at.isoformat(),
        "payload": {
            "event_ref": payload.event_ref,
            "decision_ref": payload.decision_ref,
            "outcome": payload.outcome.value,
            "decided_at": payload.decided_at.isoformat(),
            "organization_refs": list(payload.organization_refs),
            "version": payload.version,
        },
    }


def _unavailable() -> JSONResponse:
    return problem(
        503,
        "Ledger unavailable",
        "ledger_unavailable",
        "The audit ledger cannot be read now.",
    )


def create_router(
    identity: NodeIdentity, ledger: AuditLedgerPort, trail: AuditTrail
) -> APIRouter:
    router = APIRouter(tags=["ledger"])

    def envelope(**content: object) -> dict:
        return {
            "node_ref": identity.node_ref,
            "organization_ref": identity.organization_ref,
            "simulated": ledger.simulated,
            "notice": NOTICE,
            **content,
        }

    @router.get("/v1/ledger/proofs")
    def list_ledger_proofs() -> JSONResponse:
        try:
            proofs = list_proofs(ledger)
        except LedgerUnavailable:
            return _unavailable()
        return JSONResponse(envelope(proofs=[_wire(p) for p in proofs]))

    @router.get("/v1/audit/events/{event_ref}/proof")
    def get_ledger_proof(event_ref: str) -> JSONResponse:
        try:
            get_event(event_ref, trail)
            return JSONResponse(envelope(proof=_wire(get_proof(event_ref, ledger))))
        except EventNotFound:
            return problem(
                404,
                "Event not found",
                "event_not_found",
                f"No governance audit event {event_ref}.",
            )
        except ProofNotFound:
            return problem(
                404,
                "Proof not found",
                "proof_not_found",
                f"Audit event {event_ref} is not anchored in the ledger.",
            )
        except LedgerUnavailable:
            return _unavailable()

    return router
