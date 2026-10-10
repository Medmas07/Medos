# Federation Contracts

Versioned communication between Hospital Nodes, the Federation Service, and their consumers. File names carry the major version (`<name>.v<major>.yaml`); a breaking change creates a new file instead of editing the old one. Cryptography, transport, node identity, and token formats remain OPEN.

| Contract | Provider | Status |
|---|---|---|
| [`hospital-node-federation.v1.yaml`](hospital-node-federation.v1.yaml) | Every Hospital Node | IMPLEMENTED as OpenAPI 3.1 with fictional examples (HC-140); no Node provides it yet, only simulated nodes inside the Federation Service (HC-141) |
| [`federated-patient-query.v1.yaml`](federated-patient-query.v1.yaml) | Federation Service | IMPLEMENTED as OpenAPI 3.1 with fictional examples (HC-140); served by [`services/federation/`](../../services/federation/README.md) with MOCKED nodes (HC-141) |
| [`node-registry.v1.yaml`](node-registry.v1.yaml) | Federation Service | IMPLEMENTED as OpenAPI 3.1 with fictional examples; served by [`services/federation/`](../../services/federation/README.md) (HC-142). Approval references are not verified |

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
- **Authorization is a Governance-backed basis:** a patient access grant or an approved synchronization decision, with its expiry. The same query serves both cases. Verification with the Governance Node and the token format are OPEN (HC-144).
- **Partial results are explicit.** Every node asked appears in `node_results` with `ok`, `denied`, `unavailable`, or `timeout`. A result is `complete` only if every node answered `ok`. Empty entries never mean "no history".
- **Every entry names the organization and node that hold it.** Entries are an authorized-view wire shape, not a storage model. FHIR mapping is OPEN.

The two files share most component schemas (`Entry`, `Authorization`, `Scope`, `Problem`, and others). They are duplicated so each file stands alone, and the [contract tests](../../tests/contracts/) fail if they drift apart.

The node registry lists which node serves which organization, where to reach it, and the Governance decision it cites. It routes; it does not approve. Organization approval belongs to the Governance Node, and the registry reports each approval reference as `verified: false` until a Governance approval API exists (HC-131).

Not in v1: capability discovery (HC-143), Governance verification of the authorization (HC-144), audit event format, and research Compute-to-Data execution, which has its own boundary.
