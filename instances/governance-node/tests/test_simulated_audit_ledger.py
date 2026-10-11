import json
import threading
from dataclasses import replace
from datetime import timedelta

import pytest

from adapters.outbound.in_memory_audit_trail import InMemoryAuditTrail
from adapters.outbound.in_memory_hospital_applications import SeedError
from adapters.outbound.simulated_audit_ledger import LEDGER_NAME, SimulatedAuditLedger
from application.ledger import ProofConflict, anchor_decision
from domain.audit import AuditOutcome
from domain.ledger import hash_payload, proof_payload
from tests.conftest import DEMO_DATA, DEMO_NOW
from tests.test_ledger import decision_event

GOVERNANCE = DEMO_DATA / "governance.json"


def ledger(path=GOVERNANCE) -> SimulatedAuditLedger:
    return SimulatedAuditLedger.load(
        path, InMemoryAuditTrail.load(GOVERNANCE), lambda: DEMO_NOW
    )


def test_seeds_the_simulated_demo_proofs_with_their_audit_events_payloads():
    seeded = ledger()
    trail = InMemoryAuditTrail.load(GOVERNANCE)

    assert seeded.simulated is True and seeded.durable is False
    assert [(p.proof_ref, p.payload.event_ref) for p in seeded.proofs()] == [
        ("proof-003", "evt-003"),
        ("proof-004", "evt-004"),
    ]
    for proof in seeded.proofs():
        assert proof.ledger == LEDGER_NAME
        assert proof.payload == proof_payload(trail.event(proof.payload.event_ref))
        assert proof.hash_algorithm == "SHA-256"
        assert proof.payload_hash == hash_payload(proof.payload)
    assert seeded.proof("evt-001") is None


def test_anchors_a_new_payload_with_the_next_reference_at_the_clock_time():
    seeded = ledger()

    proof = seeded.anchor(proof_payload(decision_event()))

    assert proof.proof_ref == "proof-005"
    assert proof.anchored_at == DEMO_NOW
    assert proof.ledger == LEDGER_NAME
    assert proof.payload_hash == hash_payload(proof_payload(decision_event()))
    assert seeded.proof("evt-042") == proof
    assert seeded.proofs()[-1] == proof


def test_a_proof_is_never_changed_once_anchored():
    seeded = ledger()
    first = seeded.anchor(proof_payload(decision_event()))

    # The same payload again is the same proof; another payload is refused.
    assert seeded.anchor(proof_payload(decision_event())) == first
    with pytest.raises(ProofConflict):
        seeded.anchor(proof_payload(decision_event(outcome=AuditOutcome.REJECTED)))
    with pytest.raises(ProofConflict):
        seeded.anchor(replace(seeded.proof("evt-003").payload, version=2))

    assert seeded.proof("evt-042") == first
    assert len(seeded.proofs()) == 3


def test_proofs_are_a_copy_of_the_ledger():
    seeded = ledger()

    seeded.proofs().clear()

    assert len(seeded.proofs()) == 2


def test_anchor_decision_through_the_simulated_ledger():
    seeded = ledger()
    later = decision_event(recorded_at=DEMO_NOW + timedelta(minutes=1))

    proof = anchor_decision(seeded, later)

    assert proof.payload.decided_at == later.recorded_at
    assert anchor_decision(seeded, later) == proof


def test_concurrent_anchors_get_distinct_references_and_one_proof_per_event():
    seeded = ledger()
    payloads = [
        proof_payload(decision_event(event_ref=f"evt-{100 + n}")) for n in range(20)
    ]
    threads = [
        threading.Thread(target=seeded.anchor, args=(payload,))
        for payload in payloads + payloads
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    refs = [p.proof_ref for p in seeded.proofs()]
    assert len(refs) == len(set(refs)) == 22


def write(tmp_path, change):
    data = json.loads(GOVERNANCE.read_text(encoding="utf-8"))
    change(data)
    path = tmp_path / "governance.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def _payload(data, **fields):
    data["ledgerProofs"][0]["anchoredPayload"].update(fields)


@pytest.mark.parametrize(
    "change",
    [
        lambda d: d.update(fictional=False),
        lambda d: d["ledgerProofs"][0].update(simulated=False),
        lambda d: d["ledgerProofs"][0].update(ledger="mainnet"),
        lambda d: d["ledgerProofs"][0].update(anchoredAt="2025-12-12T14:30:05"),
        lambda d: d["ledgerProofs"][0].update(auditEventId="evt-004"),
        lambda d: d["ledgerProofs"][0].update(auditEventId="evt-999"),
        lambda d: d["ledgerProofs"][0].update(hash="0" * 64),
        lambda d: d["ledgerProofs"][0].update(hashAlgorithm="MD5"),
        lambda d: d["ledgerProofs"][0].pop("hash"),
        lambda d: _payload(d, patientId="pat-a"),
        lambda d: _payload(d, outcome="rejected"),
        lambda d: _payload(d, organizationIds=["org-governance"]),
        lambda d: _payload(d, decidedAt="2025-12-12T14:31:00+01:00"),
        lambda d: _payload(d, version=2),
        lambda d: _payload(d, eventId="evt-007", decisionId="sync-001"),
        lambda d: d["ledgerProofs"].append(d["ledgerProofs"][0]),
        lambda d: d["ledgerProofs"][1].update(id="proof-003"),
        lambda d: d.pop("ledgerProofs"),
    ],
)
def test_refuses_an_unusable_seed(tmp_path, change):
    with pytest.raises(SeedError):
        ledger(write(tmp_path, change))


def test_refuses_a_seed_proof_of_an_event_that_is_not_a_decision(tmp_path):
    def change(data):
        proof = data["ledgerProofs"][0]
        proof["auditEventId"] = "evt-007"
        proof["anchoredPayload"]["eventId"] = "evt-007"

    with pytest.raises(SeedError, match="not a recorded decision"):
        ledger(write(tmp_path, change))
