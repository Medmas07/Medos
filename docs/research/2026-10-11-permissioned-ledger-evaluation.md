# Permissioned ledger technologies for the Governance audit ledger (HC-193)

- **Issue:** [HC-193 — Evaluate permissioned ledger technologies (#156)](https://github.com/Medmas07/Hackcure_hackathon/issues/156), depth D0
- **Date:** 2026-10-11
- **Status:** research note. This note is evidence for a decision, not a decision. The ledger technology stays **OPEN** until an ADR accepts one; the Immutable Audit Ledger itself stays **OPTIONAL**. No code, dependency, or runtime was added, and no candidate was installed, prototyped, or benchmarked.
- **Unblocks:** [HC-194 — Implement real blockchain/ledger adapter (#157)](https://github.com/Medmas07/Hackcure_hackathon/issues/157), once an ADR records the choice.
- **Outcome:** [ADR-0007](../decisions/ADR-0007-permissioned-audit-ledger.md) accepted trust model B and Besu (QBFT), and anchors the full six-field payload rather than recommendation 4's hash and references.

## 1. Question

Which permissioned ledger, if any, should implement the Governance Node's `AuditLedgerPort` in place of the simulated ledger, so that governance decision proofs are tamper-evident without placing medical data on a ledger?

## 2. What the ledger has to do, from the code as IMPLEMENTED

The port and its use cases already exist ([HC-190 to HC-192](../../instances/governance-node/README.md#audit-ledger-port-hc-190)). Any candidate is evaluated against them, not against the product vision alone:

| Requirement | Source |
|---|---|
| Anchor a **six-field minimized payload** of a recorded decision: event ref, decision ref, outcome, time decided, organization refs, payload version. No actor, patient reference, purpose, rationale, data scope, or clinical content. | [`domain/ledger.py`](../../instances/governance-node/domain/ledger.py) |
| Hold the payload's **SHA-256 hash** of a fixed canonical JSON form, and let a reader recompute it. | `hash_payload`, HC-192 |
| **Append-only**, one proof per event; the same payload again returns the same proof; another payload for the same event is a conflict. | `anchor_decision` in [`application/ledger.py`](../../instances/governance-node/application/ledger.py) |
| Look proofs up **by event ref** and list them **in anchoring order**. | `proof`, `proofs` |
| Report **unavailability** as `LedgerUnavailable`; the decision stands if anchoring fails. | `anchor_recorded` |
| Say whether it is simulated (`simulated`), so a simulation is never shown as a real ledger. | `AuditLedgerPort.simulated` |
| Be reachable from **Python 3.12** in an outbound adapter only; no ledger library in Domain or Application. | [ADR-0003](../decisions/ADR-0003-backend-runtime-strategy.md), [AGENTS.md](../../AGENTS.md#blockchain-rules) |

Anchoring is called synchronously while a decision is recorded, so a ledger whose writes take more than a few seconds to be final would need an asynchronous anchoring step. That step does not exist today, and retrying an unanchored decision is OPEN.

## 3. The decisive question: who should be unable to rewrite the proofs?

A ledger is only worth its operating cost when it protects against someone the Governance Node alone cannot be trusted to check. Two answers lead to different technologies:

- **A. Only the Governance / Ethics Authority operates the ledger.** Every ledger node then belongs to the party being audited. Consensus between nodes it controls adds no independent assurance. A signed, hash-chained log gives the same guarantee, and gives more if its checkpoints are published to outside witnesses. A blockchain is not justified.
- **B. Independent organizations co-operate the ledger**, for example participating Hospital Nodes, a second authority, or a regulator, each running a validator or peer. Then Byzantine-fault-tolerant consensus means no single operator, Governance included, can rewrite or drop proofs. This is the case a permissioned blockchain is for.

Nothing in the [product vision](../product/FEDERATED_HEALTHCARE_ECOSYSTEM.md#10-blockchain--immutable-ledger) or [architecture](../architecture.md#9-blockchain--immutable-ledger-boundary) says which of A or B is intended, or who would run ledger nodes. It is recorded in [OPEN_QUESTIONS.md](../OPEN_QUESTIONS.md). **The ADR that unblocks HC-194 must answer it first.** It is a governance and operating decision, not a library choice.

## 4. Criteria

1. **Trust fit:** does it give independent assurance under answer A or B?
2. **Python integration:** maintained client usable from the Governance Node's outbound adapter.
3. **Data minimization:** can it anchor only hashes and references, and who can read what is anchored?
4. **Operating cost for this team:** number of processes, containers, certificates, and concepts; whether a local demo is realistic.
5. **Maintenance and licensing:** active upstream, open-source licence, no paid service required (ADR-0003 constraint).
6. **Verifiability:** can a third party check a proof without trusting the Governance Node?

## 5. Candidates

### Hyperledger Besu (permissioned Ethereum, QBFT)

- Java Ethereum client under LF Decentralized Trust, Apache-2.0. Private networks use QBFT (BFT, typically 4 or more validators to tolerate one faulty node), with gas price set to zero and node allowlists for permissioning.
- **Python:** `web3.py` is the mature, widely used Ethereum client; a small anchoring contract (map `eventRef -> payloadHash`, emit an event, refuse a second write) covers the port's semantics.
- **Minimization:** every validator sees every transaction. Besu's Tessera private transactions were deprecated in 24.12.0 and **removed in 25.6.0**, together with on-chain permissioning ([Besu 25.6.0 release](https://newreleases.io/project/github/besu-eth/besu/release/25.6.0), [LF Decentralized Trust](https://lfdecentralizedtrust.org/blog/sunsetting-tessera-and-simplifying-hyperledger-besu)). Anchor only the hash and references, so that co-operators see which organizations had decisions and when, but no content.
- **Operations:** one image per node; a single-node dev chain for local work, four validators in Compose for a BFT demo. Block finality is a block period, typically a few seconds.
- **Fit:** good under answer B; no benefit under answer A.

### Hyperledger Fabric

- Permissioned ledger designed for consortia, Apache-2.0. Organizations, MSPs, channels, and private data collections give fine-grained read control. Fabric 3.x adds a BFT ordering service.
- **Python:** the Fabric Gateway client API, the recommended application API since v2.4, is official only for **Go, Node.js, and Java**. The Python SDK (`fabric-sdk-py`) predates the Gateway model and shows no sign of current support ([Fabric docs](https://hlf.readthedocs.io/en/latest/sdk_chaincode.html), [hfc-py on PyPI](https://pypi.org/project/hfc-py)). The Governance Node would need a Node/Go/Java gateway process or hand-written gRPC calls to the Gateway. A gateway process is an extra component that AGENTS.md asks us not to add without justification.
- **Operations:** certificate authorities, orderers, peers per organization, channel configuration, and a chaincode lifecycle. This is the heaviest candidate to run and to explain.
- **Fit:** strongest read-control model under answer B, and the usual choice for healthcare consortia. Its Python integration and operating cost are poor for this team.

### R3 Corda

- JVM, point-to-point permissioned ledger aimed at financial agreements between parties. No Python client; heavy runtime. Its sharing model (only the parties to a state see it) does not match a public-to-members audit trail. **Not recommended.**

### GoQuorum

- ConsenSys's Ethereum fork for permissioned networks. Besu removed its GoQuorum compatibility features in the 23.x releases, and a Hyperledger governance report describes the Quorum features as no longer maintained by Consensys ([Besu 23.4.0](https://newreleases.io/project/github/besu-eth/besu/release/23.4.0)). **Not recommended:** Besu covers the same need with an active upstream.

### Microsoft CCF / Azure Confidential Ledger

- CCF is an open-source (Apache-2.0) framework for confidential, BFT-replicated ledgers on trusted execution environments. Azure Confidential Ledger is its managed form and has a Python client.
- Strong verifiability (signed receipts), but the managed service is a paid cloud dependency, and running CCF itself needs TEE-capable hardware for its guarantees. The hosting decision is OPEN. **Not recommended** until a hosting ADR exists.

### Amazon QLDB

- **Retired:** end of support was 31 July 2025 ([Classmethod](https://dev.classmethod.jp/articles/amazon-qldb-eos-announcement/), [Tutorials Dojo](https://tutorialsdojo.com/amazon-quantum-ledger-database-qldb/)). **Excluded.**

### immudb (verifiable database, not a blockchain)

- Codenotary's immutable database, Apache-2.0, single container, with client-side verification of inclusion and consistency. Official Python client `immudb-py`, though its maintenance signals are weak ([PyPI](https://pypi.org/project/immudb-py)).
- One operator, so it fits **answer A** as a durable, tamper-evident store. It gives no independence from the Governance operator unless its state roots are published elsewhere.

### Transparency log (Trillian Tessera, C2SP tlog-tiles)

- Merkle-tree append-only log with inclusion and consistency proofs, plus **witnesses**: independent parties that co-sign checkpoints so a log operator cannot show different histories to different readers. Trillian is in maintenance mode, and Tessera is its recommended successor at v1.0 ([transparency.dev](https://blog.transparency.dev/tessera-v1-0-is-here)). Apache-2.0.
- **Python:** Tessera is a Go library, so a log server would be a separate Go process. Verifying proofs is simple hashing and can stay in Python.
- Best fit for **answer A with outside verification**: Hospital Nodes or a regulator act as witnesses without running consensus.

### Public-chain timestamping (for example OpenTimestamps)

- Anchors a hash of a batch of proofs on a public chain. It is permissionless, so it is outside this ticket's premise. Listed only because it is cheap and well suited to answer A, if the team ever relaxes that premise.

## 6. Matrix

Ratings are qualitative and come from documentation and the sources above, not measurement.

| Candidate | Trust fit | Python | Minimization | Operating cost | Maintained / licence | Third-party verifiable |
|---|---|---|---|---|---|---|
| Besu (QBFT) | B: good · A: none | Good (`web3.py`) | Hash-only; all validators read all | Medium | Active, Apache-2.0 | Yes, if co-operated |
| Fabric | B: very good · A: none | Poor (no official Gateway client) | Channels / private data | High | Active, Apache-2.0 | Yes, if co-operated |
| Corda | Poor model fit | None | Party-scoped | High | Active, mixed | Parties only |
| GoQuorum | B | Good (`web3.py`) | Hash-only | Medium | Effectively unmaintained | — |
| CCF / Azure CL | A and B | Good (Azure) | Confidential | High / paid | Active | Signed receipts |
| QLDB | — | — | — | — | **Retired 2025-07-31** | — |
| immudb | A | Fair (weak signals) | Hash-only | Low | Active, Apache-2.0 | Only with external roots |
| Tessera log + witnesses | A, plus witnesses | Verify in Python; Go server | Hash-only | Medium | Active (v1.0), Apache-2.0 | Yes, via witnesses |

## 7. Recommendation (PROPOSED, for the HC-194 ADR)

1. **Decide the trust model first** (section 3) and record it in the ADR. Without that decision, no candidate can be justified.
2. **Under answer B (independent co-operators): Hyperledger Besu with QBFT.** Use a minimal anchoring contract and a `web3.py` outbound adapter at `instances/governance-node/adapters/outbound/`. Besu is the only actively maintained permissioned blockchain here with a mature Python client, and it runs as one image per node. Fabric is the runner-up if per-organization read control on the ledger becomes a requirement. Its integration and operating costs are the reason it is second.
3. **Under answer A (Governance operates alone): do not adopt a blockchain.** Prefer a hash-chained, signed append-only log whose checkpoints are co-signed by witnesses (Tessera model). immudb is a lower-cost fallback if durability matters more than independent verification. Both are ledgers, but neither is a blockchain, and the documentation should say so.
4. **Whatever is chosen, anchor only the payload hash and references** (`event_ref`, `decision_ref`, `payload_hash`, `hash_algorithm`, `version`). Keep the full six-field payload in the Governance audit trail, which already lets anyone recompute the hash. That way co-operators see the least possible, and nothing personal is placed where it can never be erased.

## 8. Consequences for HC-194 if Besu is accepted

- The adapter implements the existing port unchanged and reports `simulated: false`. Node errors and timeouts map to `LedgerUnavailable`. A contract revert on a second write to the same event maps to the existing conflict rule.
- `ProofPayload` and the canonical hash are unchanged. The contract stores what `hash_payload` already computes.
- New pinned runtime dependency (`web3`) in the Governance Node only. The existing layer test keeps it out of `domain/` and `application/`.
- A Compose definition for one or four validators, a genesis file, and validator keys (never committed; `.env.example` names only).
- Anchoring latency is a block period. If it is too slow for a synchronous `anchor_recorded`, an asynchronous anchoring step with a retry needs its own decision.
- The proofs API contract would need a ledger-specific locator, for example a transaction hash and block number. That is a contract version change.
- No cross-organization node operation, key management, or onboarding process exists. Those are part of answer B and are not in scope at D4 without an accepted issue.

## 9. Limits of this note

- No candidate was run. Operating cost, latency, and client quality are judged from documentation, not tested.
- Maintenance status was checked by web search on 2026-10-11 and can change. Re-check release pages before the ADR is accepted.
- Legal questions (erasure versus immutability, cross-border operators) are not answered here. They are OPEN in [OPEN_QUESTIONS.md](../OPEN_QUESTIONS.md).

## Sources

- [Besu 25.6.0 release notes](https://newreleases.io/project/github/besu-eth/besu/release/25.6.0) and [Besu 23.4.0 release notes](https://newreleases.io/project/github/besu-eth/besu/release/23.4.0)
- [LF Decentralized Trust: Sunsetting Tessera and simplifying Hyperledger Besu](https://lfdecentralizedtrust.org/blog/sunsetting-tessera-and-simplifying-hyperledger-besu)
- [Besu docs: private transaction processing (deprecated)](https://besu.hyperledger.org/private-networks/concepts/privacy/private-transactions/processing)
- [Fabric: contract APIs and application APIs](https://hlf.readthedocs.io/en/latest/sdk_chaincode.html), [hfc-py (fabric-sdk-py) on PyPI](https://pypi.org/project/hfc-py)
- [Classmethod: Amazon QLDB end of support](https://dev.classmethod.jp/articles/amazon-qldb-eos-announcement/), [Tutorials Dojo: Amazon QLDB](https://tutorialsdojo.com/amazon-quantum-ledger-database-qldb/)
- [immudb-py on PyPI](https://pypi.org/project/immudb-py)
- [transparency.dev: Tessera v1.0](https://blog.transparency.dev/tessera-v1-0-is-here), [Introducing Trillian Tessera](https://blog.transparency.dev/introducing-trillian-tessera)
