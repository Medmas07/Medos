# Federation Contracts

Versioned communication between Hospital Nodes, the Federation Service, and their consumers. File names carry the major version (`<name>.v<major>.yaml`); a breaking change creates a new file instead of editing the old one. The Governance-signed synchronization authorization format is decided by [ADR-0015](../../docs/decisions/ADR-0015-signed-federation-authorization.md) (HC-214); transport, service and node identity, and other token formats remain OPEN.

| Contract | Provider | Status |
|---|---|---|
| [`hospital-node-federation.v1.yaml`](hospital-node-federation.v1.yaml) | Every Hospital Node | IMPLEMENTED as OpenAPI 3.1 with fictional examples (HC-140). Called by the Federation Service over real HTTP (HC-145, queries; HC-143, descriptor). Served by the [Hospital Node runtime](../../instances/hospital-node/README.md) (HC-114) with MOCKED records and MOCKED authorization, and by simulated nodes (HC-141) with `FEDERATION_NODES=simulated`. Versions 1.0.2 and 1.0.3 update its status and point to the node's audit-event contract only. Version 1.1.0 adds the optional `signed_authorization` (HC-214), verified by a node configured with the Governance public key |
| [`federated-patient-query.v1.yaml`](federated-patient-query.v1.yaml) | Federation Service | IMPLEMENTED as OpenAPI 3.1 with fictional examples (HC-140); served by [`services/federation/`](../../services/federation/README.md), asking registered Hospital Nodes over real HTTP by default (HC-145), or MOCKED simulated nodes when opted in (HC-141). Version 1.1 adds the Governance check for synchronization decisions (HC-144); 1.2 adds the `not_asked` node status for capability-aware routing (HC-146); 1.3 adds the `circuit_open` reason and documents retries (HC-147); 1.3.1 notes the signed authorization passed to nodes (HC-214, wording only) |
| [`node-registry.v1.yaml`](node-registry.v1.yaml) | Federation Service | IMPLEMENTED as OpenAPI 3.1 with fictional examples; served by [`services/federation/`](../../services/federation/README.md) (HC-142). Approval references are not verified. Version 1.1 adds capability discovery (HC-143) |
| [`sync-authorization-check.v1.yaml`](sync-authorization-check.v1.yaml) | Governance Node | IMPLEMENTED as OpenAPI 3.1 with fictional examples (HC-144); called by the Federation Service over real HTTP, and served by the [Governance Node](../../instances/governance-node/README.md#synchronization-request-api-hc-132) for the synchronization decisions it holds in memory (HC-132); since version 1.1.0 (HC-136) it re-verifies the patient grant with the Hospital Node holding it, answering `revoked` once withdrawn there and `503` when that node cannot answer; version 1.2.0 (HC-214) adds `signed_authorization`, an Ed25519 compact JWS of the exact authorized exchange, when the Governance Node signs (opt-in) |

## How they fit together

```text
Clinician App / Patient App
  -> POST /v1/federated-queries        (Federation Service)
       -> POST /v1/federation/queries  (each Hospital Node, independently)
       <- entries from that node, or a refusal / failure
  <- transient timeline + one status per node
```

- **A node keeps control of its data.** It answers from its own storage and DMI Adapter, only inside the requested scope, and enforces the authorization itself. It denies by default.
- **The Federation Service is not a clinical database.** It asks the nodes, merges their answers for one response, and stores nothing. It never reads a node's database or DMI.
- **Authorization is a Governance-backed basis:** a patient access grant or an approved synchronization decision, with its expiry. The same query serves both cases. For a synchronization decision, the Federation Service first asks the Governance Node whether it authorizes this exact request ([`sync-authorization-check.v1.yaml`](sync-authorization-check.v1.yaml), HC-144) and then asks only the organizations Governance names. Each node still enforces on its own. When the Governance Node signs (HC-214), its answer carries a short-lived `signed_authorization` that the Federation Service passes on unchanged, and a node configured with the Governance public key verifies it on its own ([ADR-0015](../../docs/decisions/ADR-0015-signed-federation-authorization.md)).
- **Partial results are explicit.** Every node asked appears in `node_results` with `ok`, `denied`, `unavailable`, or `timeout`. A result is `complete` only if every node answered `ok`. Empty entries never mean "no history".
- **Every entry names the organization and node that hold it.** Entries are an authorized-view wire shape, not a storage model. FHIR mapping is OPEN.

The two files share most component schemas (`Entry`, `Authorization`, `Scope`, `Problem`, and others). They are duplicated so each file stands alone, and the [contract tests](../../tests/contracts/) fail if they drift apart.

The node registry lists which node serves which organization, where to reach it, and the Governance decision it cites. It routes; it does not approve. Organization approval belongs to the Governance Node, and the registry reports each approval reference as `verified: false`: the Governance Node serves `getHospitalApproval` ([`hospital-approval.v1.yaml`](../api/governance/hospital-approval.v1.yaml), HC-131), but the Federation Service does not call it yet.

Capability discovery (registry 1.1) asks each registered node for its `GET /v1/federation/node` descriptor and keeps the latest self-reported result with an explicit outcome. A failed check never means "no data", and a node naming another identity is flagged `identity_mismatch`.

Not in v1: Governance verification of patient access grants, signed patient access grants, service authentication, audit event format, and research Compute-to-Data execution, which has its own boundary.
