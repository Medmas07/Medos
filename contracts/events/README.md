# Event Contracts

Place validated, versioned asynchronous cross-component event specifications and envelopes here. File names carry the major version (`<name>.v<major>.yaml`); breaking changes require a new major version.

| Contract | Producers | Consumers | Status |
|---|---|---|---|
| [`notification-event.v1.yaml`](notification-event.v1.yaml) | Hospital Nodes, Governance Node, Research Service, AI Services | Notification Service (HC-202) | IMPLEMENTED as OpenAPI 3.1 specification with canonical fictional examples at depth D1 (HC-201). Received by the [Notification Service](../../services/notifications/README.md) (HC-202, HC-203); no producer emits it over the network yet. |

## Boundary invariants for event contracts

- **Payload minimization**: Events carry high-level summaries, localized titles, and opaque references. They must NEVER carry raw clinical records, consultation transcripts, diagnostic images, or SQL queries.
- **No autonomous clinical authority**: Clinical alerts are strictly advisory (`advisory: true`) and require clinician review.
- **Explicit recipient roles**: Every notification event targets an opaque recipient reference and specifies an authorized recipient role (`patient`, `relative`, `clinician`, `governance_reviewer`, `hospital_admin`, `researcher`).
- **Delivery isolation**: Delivery coordination and provider failures stay within the Notification Service; emitting services are decoupled from delivery channel infrastructure.
