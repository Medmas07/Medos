# Dependency Map

Real `Blocked by` and `Blocks` references live in the GitHub issues linked from [the backlog](backlog.md). These diagrams retain stable HC IDs. Arrows mean “unlocks or materially informs,” not a runtime import dependency.

## Demo-first delivery

```mermaid
flowchart LR
    Decisions[HC-001 to HC-003<br/>Technology ADRs] --> Design[HC-004<br/>Design system]
    Fixtures[HC-005<br/>Canonical fixtures] --> Patient[HC-010 to HC-022<br/>Patient App]
    Fixtures --> Clinician[HC-030 to HC-044<br/>Clinician App]
    Fixtures --> Hospital[HC-050 to HC-063<br/>Hospital Portal]
    Fixtures --> Governance[HC-070 to HC-080<br/>Governance Portal]
    Fixtures --> Research[HC-090 to HC-102<br/>Research Portal]
    Design --> Patient
    Design --> Clinician
    Design --> Hospital
    Design --> Governance
    Design --> Research
    Patient --> Demo[HC-240 to HC-247<br/>End-to-End Demo]
    Clinician --> Demo
    Hospital --> Demo
    Governance --> Demo
    Research --> Demo
```

## Patient and clinician upgrade paths

```mermaid
flowchart LR
    Timeline[HC-012<br/>D1 timeline] --> MockAggregation[HC-141<br/>D2 mock aggregation]
    MockAggregation --> NodeComms[HC-145<br/>D3 Node communication]
    NodeComms --> CrossQuery[HC-146<br/>D3 cross-node query]
    Warning[HC-042<br/>D1 warning] --> Fixtures[HC-161<br/>demo interactions]
    Fixtures --> Engine[HC-162<br/>deterministic engine]
    Engine --> Source[HC-163<br/>validated source]
    Engine --> Explanation[HC-164<br/>AI explanation]
```

## Runtime and integration boundaries

```mermaid
flowchart TD
    BackendADR[HC-003] --> HospitalNode[HC-110]
    BackendADR --> GovernanceNode[HC-130]
    BackendADR --> AI[HC-150]
    DMIPort[HC-120<br/>Hospital-local port] --> MockDMI[HC-121]
    DMIPort --> Mapping[HC-122]
    MockDMI --> HospitalAdapter[HC-123]
    FederationContract[HC-140] --> MockFederation[HC-141]
    FederationContract --> Registry[HC-142]
    Registry --> Identity[HC-143]
    Identity --> Authorization[HC-144]
    Authorization --> NodeCommunication[HC-145]
    SciContract[HC-170] --> SciAdapter[HC-171]
    SciAdapter --> SciPortal[HC-172]
```

## Compute-to-Data and immutable audit

```mermaid
flowchart TD
    JobContract[HC-180] --> MockExecution[HC-181]
    JobContract --> Orchestrator[HC-182]
    Orchestrator --> HospitalAgent[HC-183]
    HospitalAgent --> Aggregation[HC-184]
    Aggregation --> OutputValidation[HC-185]
    HospitalAgent --> Sandbox[HC-186]
    LedgerPort[HC-190<br/>Governance boundary] --> SimLedger[HC-191]
    LedgerPort --> Hashing[HC-192]
    LedgerResearch[HC-193] --> RealLedger[HC-194]
    LedgerPort --> RealLedger
```

The DMI Adapter remains inside each Hospital Node; the ledger remains inside Governance and excludes raw clinical data; SciAgents remains external; and visual D1 tickets do not depend on D3/D4 infrastructure.
