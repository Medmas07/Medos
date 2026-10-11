"""The Besu ledger adapter (HC-194) against the compiled AuditAnchor contract.

The contract runs in py-evm through eth-tester, an in-process EVM: the same bytecode
and the same adapter code as on Besu, without a Besu node. That checks the adapter and
the contract, not Besu's consensus or networking, which are checked by hand (README).
"""

import hashlib
import json
import os
from dataclasses import replace
from datetime import timedelta
from pathlib import Path

import pytest
from eth_account import Account
from fastapi.testclient import TestClient
from web3 import Web3

from adapters.outbound.besu_audit_ledger import ARTIFACT, BesuAuditLedger, node_client
from adapters.outbound.in_memory_audit_trail import InMemoryAuditTrail
from adapters.outbound.in_memory_hospital_applications import SeedError
from application.ledger import (
    LedgerUnavailable,
    ProofConflict,
    anchor_decision,
    anchor_recorded,
    verify_proof,
)
from domain.audit import AuditOutcome
from domain.ledger import ProofPayload, ProofVerification, hash_payload
from main import create_app
from tests.conftest import DEMO_DATA, DEMO_NOW
from tests.test_ledger_proofs_http import DETAIL, LIST, PROOFS, decision_event
from tests.test_synchronization_http import APPROVE_001, Clock, check, example

PAYLOAD = ProofPayload(
    event_ref="evt-104",
    decision_ref="dec-sync-104",
    outcome=AuditOutcome.APPROVED,
    decided_at=DEMO_NOW,
    organization_refs=("org-governance", "org-hospital-a", "org-hospital-b"),
)
# Nothing listens there.
UNREACHABLE = "http://127.0.0.1:9"


def funded_key(web3: Web3) -> str:
    """A new account with test ether: eth-tester's chain charges gas."""
    account = Account.create()
    web3.eth.send_transaction(
        {"from": web3.eth.accounts[0], "to": account.address, "value": 10**18}
    )
    return account.key.hex()


@pytest.fixture
def web3() -> Web3:
    return Web3(Web3.EthereumTesterProvider())


@pytest.fixture
def ledger(web3) -> BesuAuditLedger:
    return BesuAuditLedger.deploy(web3, funded_key(web3))


def test_the_artifact_is_compiled_from_the_committed_contract():
    artifact = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    source = (ARTIFACT.parent / artifact["source"]).read_text(encoding="utf-8")

    assert (
        artifact["sourceSha256"]
        == hashlib.sha256(source.replace("\r\n", "\n").encode("utf-8")).hexdigest()
    )


def test_anchors_a_payload_and_reads_back_the_hash_the_chain_computed(ledger):
    proof = ledger.anchor(PAYLOAD)

    assert ledger.simulated is False
    assert proof.payload == PAYLOAD
    assert proof.payload_hash == hash_payload(PAYLOAD)
    assert proof.ledger == ledger.ledger
    assert ledger.ledger.startswith("besu-qbft:0x")
    assert proof.proof_ref == f"{ledger.ledger.removeprefix('besu-qbft:')}:0"
    assert proof.anchored_at.utcoffset() == timedelta(0)
    assert ledger.proof("evt-104") == proof
    assert ledger.proofs() == [proof]


def test_an_event_is_anchored_once(ledger):
    first = ledger.anchor(PAYLOAD)

    assert ledger.anchor(PAYLOAD) == first
    with pytest.raises(ProofConflict):
        ledger.anchor(replace(PAYLOAD, outcome=AuditOutcome.REJECTED))
    assert ledger.proofs() == [first]


def test_lists_proofs_in_the_order_anchored(ledger):
    later = replace(PAYLOAD, event_ref="evt-105", decision_ref="dec-sync-105")
    ledger.anchor(PAYLOAD)
    ledger.anchor(later)

    assert [p.payload for p in ledger.proofs()] == [PAYLOAD, later]
    assert ledger.proof("evt-999") is None


def test_a_ledger_owned_by_another_account_refuses_to_anchor(web3, ledger):
    contract = ledger.ledger.removeprefix("besu-qbft:")
    intruder = BesuAuditLedger(web3, contract, funded_key(web3))

    with pytest.raises(LedgerUnavailable, match="refused"):
        intruder.anchor(PAYLOAD)
    assert intruder.proofs() == []


def test_a_proof_read_from_the_chain_verifies_against_the_audit_trail(ledger):
    trail = InMemoryAuditTrail.load(DEMO_DATA / "governance.json")
    event = trail.event("evt-004")

    proof = anchor_decision(ledger, event)

    assert verify_proof(proof, trail) is ProofVerification.VERIFIED


def test_an_unreachable_node_is_unavailable_and_the_decision_stands():
    ledger = BesuAuditLedger(
        node_client(UNREACHABLE),
        "0x" + "11" * 20,
        Account.create().key.hex(),
    )
    trail = InMemoryAuditTrail.load(DEMO_DATA / "governance.json")

    for read in (
        ledger.proofs,
        lambda: ledger.proof("evt-004"),
        lambda: ledger.anchor(PAYLOAD),
    ):
        with pytest.raises(LedgerUnavailable):
            read()
    assert anchor_recorded(ledger, trail.event("evt-004")) is None


def test_startup_needs_a_readable_key_and_a_reachable_node(tmp_path: Path):
    with pytest.raises(SeedError, match="ledger key"):
        BesuAuditLedger.connect(UNREACHABLE, tmp_path / "missing.key", None)

    key_file = tmp_path / "anchor.key"
    key_file.write_text(Account.create().key.hex(), encoding="utf-8")
    with pytest.raises(SeedError, match="Cannot deploy"):
        BesuAuditLedger.connect(UNREACHABLE, key_file, None)


def test_a_decision_recorded_through_the_api_is_anchored_on_the_chain(ledger):
    client = TestClient(create_app(demo_data=DEMO_DATA, clock=Clock(), ledger=ledger))

    decided = client.post(
        "/v1/synchronization-requests/sync-001/decision", json=APPROVE_001
    )
    assert decided.status_code == 201

    event_ref = decision_event(client, decided.json()["decision_ref"])
    body = check(client.get(f"/v1/audit/events/{event_ref}/proof"), PROOFS, DETAIL, 200)
    expected = example(PROOFS, DETAIL, 200, "anchoredOnBesu")
    # Where and when it was anchored depend on the chain; everything else is the example.
    for answer in (body, expected):
        for key in ("proof_ref", "ledger", "anchored_at"):
            answer["proof"].pop(key)
    assert body == expected
    assert "MOCKED" not in body["notice"]
    # The simulated seed proofs are not on this chain.
    listed = check(client.get("/v1/ledger/proofs"), PROOFS, LIST, 200)["proofs"]
    assert [p["payload"]["event_ref"] for p in listed] == [event_ref]
    assert listed[0]["ledger"] == ledger.ledger


@pytest.mark.skipif(
    not os.environ.get("GOVERNANCE_LEDGER_LIVE_RPC"),
    reason="live Besu check is opt-in: set GOVERNANCE_LEDGER_LIVE_RPC and _KEY_FILE",
)
def test_live_besu_deploys_anchors_and_reads_back():
    """Against a running chain, such as ledger/dev_chain.py's: a new contract each run."""
    web3 = node_client(os.environ["GOVERNANCE_LEDGER_LIVE_RPC"])
    key = Path(os.environ["GOVERNANCE_LEDGER_LIVE_KEY_FILE"]).read_text().strip()
    live = BesuAuditLedger.deploy(web3, key)

    proof = live.anchor(PAYLOAD)

    assert proof.payload == PAYLOAD and proof.payload_hash == hash_payload(PAYLOAD)
    assert live.anchor(PAYLOAD) == proof
    with pytest.raises(ProofConflict):
        live.anchor(replace(PAYLOAD, outcome=AuditOutcome.REJECTED))
    assert live.proofs() == [proof]
