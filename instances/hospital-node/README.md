# Hospital Node

An autonomous hospital-controlled runtime boundary, intended eventually to be packaged as a containerized deployable instance. Future concerns may include a local API, identity/RBAC, clinical data, a FHIR or canonical model, DMI integration, consent, audit, synchronization, notifications/events, local storage, and health checks.

It must expose explicit contracts and retain control of its persistence. No framework, database, FHIR server, or container service is initialized here.
