# Federation Contracts

Versioned communication between Hospital Nodes, the Federation Service, and their consumers. File names carry the major version (`<name>.v<major>.yaml`); a breaking change creates a new file instead of editing the old one. Cryptography, transport, node identity, and token formats remain OPEN.

| Contract | Provider | Status |
|---|---|---|
| [`hospital-node-federation.v1.yaml`](hospital-node-federation.v1.yaml) | Every Hospital Node | IMPLEMENTED as OpenAPI 3.1 with fictional examples (HC-140). Called by the Federation Service over real HTTP (HC-145, queries; HC-143, descriptor). Served by the [Hospital Node runtime](../../instances/hospital-node/README.md) (HC-114) with MOCKED records and MOCKED authorization, and by simulated nodes (HC-141) with `FEDERATION_NODES=simulated`. Version 1.0.2 updates this status only |
| [`federated-patient-query.v1.yaml`](federated-patient-query.v1.yaml) | Federation Service | IMPLEMENTED as OpenAPI 3.1 with fictional examples (HC-140); served by [`services/federation/`](../../services/federation/README.md) with MOCKED nodes (HC-141). Version 1.1 adds the Governance check for synchronization decisions (HC-144); 1.2 adds the `not_asked` node status for capability-aware routing (HC-146); 1.3 adds the `circuit_open` reason and documents retries (HC-147) |
| [`node-registry.v1.yaml`](node-registry.v1.yaml) | Federation Service | IMPLEMENTED as OpenAPI 3.1 with fictional examples; served by [`services/federation/`](../../services/federation/README.md) (HC-142). Approval references are not verified. Version 1.1 adds capability discovery (HC-143) |
| [`sync-authorization-check.v1.yaml`](sync-authorization-check.v1.yaml) | Governance Node | IMPLEMENTED as OpenAPI 3.1 with fictional examples (HC-144); called by the Federation Service over real HTTP. No Governance Node implements it yet (HC-130, HC-132) |

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
- **Authorization is a Governance-backed basis:** a patient access grant or an approved synchronization decision, with its expiry. The same query serves both cases. For a synchronization decision, the Federation Service first asks the Governance Node whether it authorizes this exact request ([`sync-authorization-check.v1.yaml`](sync-authorization-check.v1.yaml), HC-144) and then asks only the organizations Governance names. Each node still enforces on its own. Node-side verification and any token format are OPEN.
- **Partial results are explicit.** Every node asked appears in `node_results` with `ok`, `denied`, `unavailable`, or `timeout`. A result is `complete` only if every node answered `ok`. Empty entries never mean "no history".
- **Every entry names the organization and node that hold it.** Entries are an authorized-view wire shape, not a storage model. FHIR mapping is OPEN.

The two files share most component schemas (`Entry`, `Authorization`, `Scope`, `Problem`, and others). They are duplicated so each file stands alone, and the [contract tests](../../tests/contracts/) fail if they drift apart.

The node registry lists which node serves which organization, where to reach it, and the Governance decision it cites. It routes; it does not approve. Organization approval belongs to the Governance Node, and the registry reports each approval reference as `verified: false` until a Governance approval API exists (HC-131).

Capability discovery (registry 1.1) asks each registered node for its `GET /v1/federation/node` descriptor and keeps the latest self-reported result with an explicit outcome. A failed check never means "no data", and a node naming another identity is flagged `identity_mismatch`.

Not in v1: Governance verification of patient access grants, node-side verification, signed tokens, audit event format, and research Compute-to-Data execution, which has its own boundary.
