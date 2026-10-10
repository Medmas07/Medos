# Hospital-Local DMI / HIS Adapter

## Purpose and status

PLANNED Hospital Node infrastructure-adapter boundary for its local legacy DMI/HIS. No port, mapping, fixture, configuration, or implementation exists. The future adapter translates hospital-specific representations into the canonical clinical model owned by that Hospital Node:

```text
Legacy DMI / HIS
        |
Hospital-specific DMI Adapter
        |
Hospital Node canonical clinical model
        |
FHIR / internal clinical representation
```

Each hospital may require a different adapter implementation, mapping, and local configuration. A central service must never connect directly to every hospital DMI; only the corresponding Hospital Node owns and operates this integration boundary.

## Communication boundaries

The adapter implements Hospital Node-owned inbound/outbound ports. DMI representations must not leak into the Node Domain or repository-level cross-component contracts.

## Non-responsibilities

This is not a shared central integration service and does not define a universal hospital schema.

## Expected contracts

Future validated work may add `ports/`, `mappings/`, and `implementations/` beneath this directory. Any port must preserve the Hospital Node's Clean/Hexagonal dependency direction.
