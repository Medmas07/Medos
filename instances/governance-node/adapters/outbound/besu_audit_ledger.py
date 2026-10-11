"""AuditLedgerPort on a permissioned Hyperledger Besu (QBFT) ledger (HC-194, ADR-0007).

Each recorded decision's canonical minimized payload (domain.ledger.canonical_payload)
is anchored in the AuditAnchor contract (ledger/AuditAnchor.sol) by a transaction that
the Governance Node signs with its ledger account. The contract computes the payload's
SHA-256, keeps the payload, the hash, and the block time, and refuses a second anchor
for the same event and any anchor from another account. Proofs are read back from the
chain, so the hash served is the one the chain holds, not one the Node recomputed.

Not simulated (`simulated` is false), and durable for as long as the chain is. What it
does not give is in ADR-0007: on the local dev chain, the Governance Node runs the only
validator, so the ledger gives no assurance independent of the Governance Node; the
account key is a local file; and nothing is signed beyond the transaction. Node errors,
timeouts, and any refusal other than an event already anchored are LedgerUnavailable.
"""

import json
import threading
from datetime import UTC, datetime
from pathlib import Path

from requests.exceptions import RequestException
from web3 import Web3
from web3.contract.contract import ContractConstructor, ContractFunction
from web3.exceptions import Web3Exception

from adapters.outbound.in_memory_hospital_applications import SeedError
from application.ledger import LedgerUnavailable, ProofConflict
from domain.audit import AuditOutcome
from domain.ledger import LedgerProof, ProofPayload, canonical_payload

ARTIFACT = Path(__file__).resolve().parents[2] / "ledger" / "AuditAnchor.json"
# How long a transaction may take to be in a block before the ledger is unavailable.
RECEIPT_TIMEOUT_SECONDS = 15.0
RPC_TIMEOUT_SECONDS = 5.0
# A fixed limit, not an estimate: a refused anchor is then mined as a failed
# transaction on any node, rather than failing in a node-specific way when estimated.
# Well above what a minimized payload costs; the dev chain's gas price is zero.
ANCHOR_GAS = 3_000_000
# What the node or its connection can raise: all mean nothing could be read or written.
_NODE_ERRORS = (Web3Exception, RequestException, OSError)
_PAYLOAD_FIELDS = {
    "eventId",
    "decisionId",
    "outcome",
    "decidedAt",
    "organizationIds",
    "version",
}


def _artifact() -> dict:
    return json.loads(ARTIFACT.read_text(encoding="utf-8"))


def _transact(
    web3: Web3,
    key: str,
    call: ContractFunction | ContractConstructor,
    gas: int | None = None,
):
    """Sign and send the call from the key's account; its receipt once in a block.
    Without `gas`, the node estimates it."""
    account = web3.eth.account.from_key(key)
    fields = {
        "from": account.address,
        "nonce": web3.eth.get_transaction_count(account.address, "pending"),
        "chainId": web3.eth.chain_id,
        # Legacy pricing: the node's price, zero on the dev chain. Fee-market fields
        # would need a base fee, which a Berlin-genesis chain has not.
        "gasPrice": web3.eth.gas_price,
    }
    if gas is not None:
        fields["gas"] = gas
    transaction = call.build_transaction(fields)
    signed = account.sign_transaction(transaction)
    sent = web3.eth.send_raw_transaction(signed.raw_transaction)
    return web3.eth.wait_for_transaction_receipt(
        sent, timeout=RECEIPT_TIMEOUT_SECONDS, poll_latency=0.2
    )


def node_client(rpc_url: str) -> Web3:
    """A JSON-RPC client that does not retry: anchoring runs while a decision is
    recorded, so an unreachable node must be unavailable at once, not after backoff."""
    return Web3(
        Web3.HTTPProvider(
            rpc_url,
            request_kwargs={"timeout": RPC_TIMEOUT_SECONDS},
            exception_retry_configuration=None,
        )
    )


class BesuAuditLedger:
    simulated = False
    durable = True

    def __init__(self, web3: Web3, contract_address: str, key: str) -> None:
        self._web3 = web3
        self._key = key
        address = Web3.to_checksum_address(contract_address)
        self._contract = web3.eth.contract(address=address, abi=_artifact()["abi"])
        # The name every proof carries: the contract holding it.
        self.ledger = f"besu-qbft:{address}"
        self._lock = threading.Lock()

    @classmethod
    def deploy(cls, web3: Web3, key: str) -> "BesuAuditLedger":
        """Deploy a new AuditAnchor contract, owned by the key's account."""
        artifact = _artifact()
        factory = web3.eth.contract(abi=artifact["abi"], bytecode=artifact["bytecode"])
        try:
            receipt = _transact(web3, key, factory.constructor())
        except _NODE_ERRORS as error:
            raise LedgerUnavailable(
                f"Cannot deploy the audit contract: {error}"
            ) from error
        if receipt["status"] != 1:
            raise LedgerUnavailable("The audit contract deployment was reverted")
        return cls(web3, receipt["contractAddress"], key)

    @classmethod
    def connect(
        cls, rpc_url: str, key_file: Path, contract_address: str | None
    ) -> "BesuAuditLedger":
        """The contract at `contract_address`, or a new one if none is given: its proofs
        then start empty, like the Node's in-memory audit trail. A missing key or a
        failed deployment stops startup."""
        try:
            key = key_file.read_text(encoding="utf-8").strip()
        except OSError as error:
            raise SeedError(
                f"Cannot read the ledger key {key_file}: {error}"
            ) from error
        web3 = node_client(rpc_url)
        if contract_address:
            return cls(web3, contract_address, key)
        try:
            return cls.deploy(web3, key)
        except LedgerUnavailable as error:
            raise SeedError(f"Besu ledger at {rpc_url}: {error}") from error

    def anchor(self, payload: ProofPayload) -> LedgerProof:
        with self._lock:
            try:
                existing = self._find(payload.event_ref)
                if existing is None:
                    receipt = _transact(
                        self._web3,
                        self._key,
                        self._contract.functions.anchor(
                            payload.event_ref, canonical_payload(payload)
                        ),
                        gas=ANCHOR_GAS,
                    )
                    # A failed transaction: anchored meanwhile, or not our contract.
                    existing = self._find(payload.event_ref)
                    if existing is None:
                        raise LedgerUnavailable(
                            f"{payload.event_ref} was not anchored"
                            + (
                                ""
                                if receipt["status"] == 1
                                else ": refused by the contract"
                            )
                        )
            except _NODE_ERRORS as error:
                raise LedgerUnavailable(str(error)) from error
        if existing.payload != payload:
            raise ProofConflict(payload.event_ref)
        return existing

    def proof(self, event_ref: str) -> LedgerProof | None:
        try:
            return self._find(event_ref)
        except _NODE_ERRORS as error:
            raise LedgerUnavailable(str(error)) from error

    def proofs(self) -> list[LedgerProof]:
        try:
            count = self._contract.functions.count().call()
            return [self._at(index) for index in range(count)]
        except _NODE_ERRORS as error:
            raise LedgerUnavailable(str(error)) from error

    def _find(self, event_ref: str) -> LedgerProof | None:
        found, index = self._contract.functions.find(event_ref).call()
        return self._at(index) if found else None

    def _at(self, index: int) -> LedgerProof:
        event_ref, payload, payload_hash, anchored_at = (
            self._contract.functions.anchorAt(index).call()
        )
        return LedgerProof(
            proof_ref=f"{self._contract.address}:{index}",
            payload=_payload(payload, event_ref),
            ledger=self.ledger,
            anchored_at=datetime.fromtimestamp(anchored_at, UTC),
            payload_hash=payload_hash.hex(),
        )


def _payload(raw: str, event_ref: str) -> ProofPayload:
    """The payload the chain holds, read back from its canonical form. Anything else
    there is an unreadable ledger, not a proof."""
    try:
        data = json.loads(raw)
        if set(data) != _PAYLOAD_FIELDS or data["eventId"] != event_ref:
            raise ValueError("not a proof payload")
        decided_at = datetime.fromisoformat(data["decidedAt"])
        if decided_at.tzinfo is None:
            raise ValueError("a time without UTC offset")
        return ProofPayload(
            event_ref=data["eventId"],
            decision_ref=data["decisionId"],
            outcome=AuditOutcome(data["outcome"]),
            decided_at=decided_at,
            organization_refs=tuple(data["organizationIds"]),
            version=data["version"],
        )
    except (ValueError, TypeError) as error:
        raise LedgerUnavailable(f"Unreadable proof for {event_ref}: {error}") from error
