# ADR-0007: Permissioned audit ledger — Hyperledger Besu (QBFT) behind `AuditLedgerPort`

## Status

Accepted — 2026-10-11, chosen by the HC-194 assignee during HC-194 ([#157](https://github.com/Medmas07/Hackcure_hackathon/issues/157)), from the options of the [HC-193 evaluation](../research/2026-10-11-permissioned-ledger-evaluation.md); subject to pull-request review. The Immutable Audit Ledger itself stays OPTIONAL.

## Context

The Governance Node's `AuditLedgerPort` (HC-190) anchors the six-field minimized payload of each recorded decision, and holds its SHA-256 hash (HC-192). Its only adapter was a simulated in-memory ledger (HC-191, MOCKED). HC-194 asks for a real permissioned ledger behind the port.

The HC-193 evaluation showed that the choice depends on one question: who should be unable to rewrite the proofs.

- **A.** If only the Governance / Ethics Authority operates the ledger, consensus between nodes it controls adds no independent assurance, and a blockchain is not justified.
- **B.** If independent organizations co-operate the ledger (Hospital Nodes, a second authority, a regulator), Byzantine-fault-tolerant consensus prevents any single operator, Governance included, from rewriting or dropping proofs.

Forces:

- **Trust:** proofs about Governance decisions are most useful when Governance alone cannot rewrite them.
- **Python 3.12** in an outbound adapter only (ADR-0003); no ledger library in Domain or Application.
- **Data minimization:** nothing personal or clinical may reach a ledger, where it can never be erased (AGENTS.md, blockchain rules).
- **Team operating cost** in a two-day hackathon; no paid service.
- **Honesty of status:** a ledger operated only by the team must not be presented as independent assurance.

## Decision

1. **Trust model B.** The intended ledger is co-operated: the Governance / Ethics Authority and independent organizations each run validators. This is the target, not what runs today (see Consequences). Who those organizations are, and on what terms, is still OPEN.
2. **Technology: Hyperledger Besu, QBFT consensus, permissioned.** It is the actively maintained permissioned blockchain from the evaluation with a mature Python client, and runs as one process per node.
3. **Contract:** [`AuditAnchor.sol`](../../instances/governance-node/ledger/AuditAnchor.sol) (Solidity 0.8.26, EVM Berlin), append-only. It accepts anchors only from the account that deployed it, the Governance Node's, refuses a second anchor for the same event, computes the payload's SHA-256 itself, and keeps the payload, the hash, and the block time. The compiled artifact is committed with its source's hash, and a test detects drift between them.
4. **What is anchored: the full six-field canonical payload** (`canonical_payload`), not only its hash and references as HC-193 recommendation 4 proposed. All six fields are allowed proof data (references, an outcome, a time, organization identifiers, a version). Keeping them on the chain lets any reader of the chain recompute the hash without trusting the Governance Node's audit trail. It also lets the adapter detect an event anchored with another payload, even after the Node's in-memory trail has restarted and reused event references. The cost is that co-operators see each decision's outcome, time, and organizations.
5. **Adapter:** `BesuAuditLedger` in the Governance Node's outbound adapters, using `web3` (7.16.0). It implements the existing port unchanged, reports `simulated: false`, signs transactions with a local key file, maps node errors, timeouts, and refused transactions to `LedgerUnavailable`, and maps a different payload for an anchored event to `ProofConflict`. The client does not retry, so an unreachable node makes the decision stand unanchored at once.
6. **Selection by environment, simulated by default:** `GOVERNANCE_LEDGER=simulated|besu`, `GOVERNANCE_LEDGER_RPC_URL`, `GOVERNANCE_LEDGER_KEY_FILE`, and optionally `GOVERNANCE_LEDGER_CONTRACT`. Without a contract address, the Node deploys a new contract at startup, so its proofs start empty, like its in-memory audit trail. The simulated ledger stays the default so the demo runs without Besu, and it stays labelled MOCKED.
7. **Local chain:** a single-validator QBFT chain with zero gas price, generated and started by [`ledger/dev_chain.py`](../../instances/governance-node/ledger/dev_chain.py) from the Besu distribution (Java 21). Keys and chain data stay in a gitignored folder. No container runtime is adopted by this decision.

## Alternatives considered

- **Trust model A, with a signed hash-chained log and outside witnesses (Tessera model):** the right answer if Governance operates alone. It was not chosen because HC-194 asks for a permissioned ledger, and because proofs that Governance alone cannot rewrite are the stronger target.
- **immudb:** low operating cost, but a single operator and weak Python client maintenance signals.
- **Hyperledger Fabric:** the strongest per-organization read control, but no maintained Python Gateway client, and the highest operating cost. It is the fallback if read control on the ledger becomes a requirement.
- **Anchoring only the hash and references (HC-193 recommendation 4):** co-operators would see less. It was not chosen because the chain could no longer be checked on its own, and conflict detection would depend on the Node's in-memory audit trail.
- **GoQuorum, Corda, CCF / Azure Confidential Ledger, Amazon QLDB:** rejected in the evaluation (unmaintained, poor fit, paid or TEE-dependent, retired).

## Consequences

### Positive

- Decision proofs can live outside the Governance Node's process. They are durable for as long as the chain is, and the chain itself computes the hash.
- The port, the domain, the use cases, and the proof payload are unchanged; the layer test keeps `web3` out of Domain and Application.
- The proofs API stays at version 1 (1.2.0): `simulated: false`, a different notice, and a ledger name and proof reference that locate the proof in its contract.
- The adapter and the compiled contract are tested together in an in-process EVM (py-evm through eth-tester), without a Besu node.

### Negative

- **No independent assurance as run today.** The local chain has one validator, run by whoever runs the Governance Node. Until other organizations run validators, it protects against no one that the Governance Node operator could not overrule. The proofs API notice says so.
- **Not VALIDATED against a running Besu node.** At acceptance, the adapter had been run against the contract only in an in-process EVM, and `dev_chain.py` and its genesis had not been run. An opt-in live test exists for that check.
- Co-operators can read every decision's outcome, time, and organizations, and an anchor can never be erased. Whether that is acceptable for real decisions is OPEN with the erasure-versus-immutability question.
- Anchoring is synchronous and waits for a block (one second on the dev chain, up to 15 seconds before it is unavailable). A slow chain slows decision recording; asynchronous anchoring and retrying unanchored decisions are OPEN.
- A new contract per Node start leaves earlier contracts on the chain, unread by the Node.
- The ledger account key is a plain local file. Key management, validator onboarding, and node permissioning between organizations do not exist.

## Follow-up

- Validate the adapter against a running Besu chain (`python ledger/dev_chain.py`, then the opt-in live test and a decision recorded through the API), and record the result.
- Decide which organizations run validators, and how they join; until then, trust model B is a target only.
- Decide asynchronous anchoring and retry, signing beyond the transaction, key management, and who may read the chain.
- The Governance Portal's proof explorer (HC-080) still shows the MOCKED fixtures, not the Node's proofs.
