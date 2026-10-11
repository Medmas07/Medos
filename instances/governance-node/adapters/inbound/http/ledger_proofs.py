"""contracts/api/governance/governance-ledger-proofs.v1.yaml (HC-191, HC-192, HC-194).

Reads the proofs the Governance Node anchored in its audit ledger: the simulated ledger
(MOCKED, `simulated: true`) by default, or the Besu ledger (`simulated: false`), each
with its own notice. Each proof is served with its payload's hash and the Node's
verification of that hash against its audit trail. Readers are not authenticated, as
for the audit trail.
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
    verify_proof,
)
from domain.ledger import LedgerProof
from domain.node_identity import NodeIdentity

SIMULATED_NOTICE = (
    "MOCKED BLOCKCHAIN. Fictional demo proofs held by the Governance Node's simulated "
    "immutable ledger: an append-only list in memory, not a blockchain or a real "
    "ledger; proofs anchored at runtime are lost on restart. Each payload's SHA-256 "
    "hash is computed by the Node itself, not signed, and anchored nowhere else. Only a "
    "decision's minimized payload is anchored, never clinical content."
)
LEDGER_NOTICE = (
    "Proofs anchored by the Governance Node's ledger account in a permissioned "
    "Hyperledger Besu (QBFT) ledger (ADR-0007), which computes and keeps each "
    "payload's SHA-256; its contract cannot change or remove an anchored proof. The "
    "ledger is independent of the Governance Node only if other organizations run its "
    "validators: the demo chain has one validator, run locally. Only a decision's "
    "minimized payload is anchored, never clinical content."
)


def _wire(proof: LedgerProof, trail: AuditTrail) -> dict:
    payload = proof.payload
    return {
        "proof_ref": proof.proof_ref,
        "ledger": proof.ledger,
        "anchored_at": proof.anchored_at.isoformat(),
        "hash_algorithm": proof.hash_algorithm,
        "payload_hash": proof.payload_hash,
        "verification": verify_proof(proof, trail).value,
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
            "notice": SIMULATED_NOTICE if ledger.simulated else LEDGER_NOTICE,
            **content,
        }

    @router.get("/v1/ledger/proofs")
    def list_ledger_proofs() -> JSONResponse:
        try:
            proofs = list_proofs(ledger)
        except LedgerUnavailable:
            return _unavailable()
        return JSONResponse(envelope(proofs=[_wire(p, trail) for p in proofs]))

    @router.get("/v1/audit/events/{event_ref}/proof")
    def get_ledger_proof(event_ref: str) -> JSONResponse:
        try:
            get_event(event_ref, trail)
            return JSONResponse(
                envelope(proof=_wire(get_proof(event_ref, ledger), trail))
            )
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
