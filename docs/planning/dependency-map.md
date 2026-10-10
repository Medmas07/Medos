# Dependency Map

The backlog is intentionally front-loaded toward visible value. Arrows mean “unlocks or materially informs,” not a runtime import dependency.

## Demo-first delivery

```mermaid
flowchart LR
    Decisions[HC-001 to HC-003<br/>Technology ADRs] --> Design[HC-004<br/>Visual system]
    Decisions --> Shells[Product shells]
    Data[HC-005<br/>Fictional dataset] --> Patient[Patient experience]
    Data --> Clinician[Clinician experience]
    Data --> Hospital[Hospital onboarding]
    Data --> Governance[Governance experience]
    Data --> Research[Research experience]
    Design --> Patient
    Design --> Clinician
    Design --> Hospital
    Design --> Governance
    Design --> Research
    Shells --> Patient
    Shells --> Clinician
    Shells --> Hospital
    Shells --> Governance
    Shells --> Research
    Patient --> Demo[Canonical demo]
    Clinician --> Demo
    Hospital --> Demo
    Governance --> Demo
    Research --> Demo
```

## Cross-product demo state

```mermaid
flowchart LR
    Grant[HC-015<br/>Grant access] --> AuthPatients[HC-033<br/>Authorized patients]
    Timeline[HC-012<br/>Patient timeline] --> ClinTimeline[HC-034<br/>Clinician history]
    Consult[HC-035 to HC-038<br/>Consultation and review] --> Warning[HC-040<br/>Medication warning]
    Consult --> UpdatedTimeline[Updated patient timeline]
    HospitalReview[HC-051 to HC-058] --> GovernanceApproval[HC-072]
    SyncReview[HC-073] --> Audit[HC-075 and HC-076]
    ResearchRequest[HC-092 to HC-096] --> ResearchApproval[HC-074]
    ResearchApproval --> Workspace[HC-097]
    Workspace --> Compute[HC-098]
    Workspace --> SciAgentsUI[HC-099]
```

## Contract and runtime dependencies

```mermaid
flowchart TD
    BackendADR[HC-003<br/>Backend strategy] --> HospitalSkeleton[HC-113]
    BackendADR --> GovernanceSkeleton[HC-114]
    BackendADR --> AISkeleton[HC-130]
    API[HC-110<br/>API conventions] --> PatientAPI[HC-115]
    API --> GovernanceAPI[HC-116]
    API --> ResearchAPI[HC-117]
    FederationContract[HC-112] --> MockFederation[HC-170]
    FederationContract --> Registry[HC-171]
    Registry --> NodeIdentity[HC-172]
    NodeIdentity --> SyncAuth[HC-173]
    SyncAuth --> NodeCommunication[HC-174]
    NodeCommunication --> CrossNodeQuery[HC-175]
    SciContract[HC-150] --> SciAdapter[HC-151]
    SciAdapter --> SciUI[HC-152]
    DMIPort[HC-190] --> MockDMI[HC-191]
    MockDMI --> LegacyAdapter[HC-192]
```

## Governance, ledger, and compute-to-data

```mermaid
flowchart TD
    Auth[HC-290<br/>Authentication] --> RBAC[HC-291]
    OrgIdentity[HC-292] --> SignedAuth[HC-293]
    Policy[HC-230] --> TempTokens[HC-232]
    Consent[HC-231] --> TempTokens
    PersistentAudit[HC-233] --> LedgerPort[HC-234]
    LedgerPort --> SimLedger[HC-235]
    LedgerPort --> RealLedger[HC-236]
    JobContract[HC-250] --> MockExecution[HC-251]
    JobContract --> Orchestrator[HC-252]
    TempTokens --> Orchestrator
    Orchestrator --> HospitalAgent[HC-253]
    HospitalAgent --> Isolation[HC-254]
    Isolation --> OutputValidation[HC-255]
```

The real ledger adapter never precedes `AuditLedgerPort`; research execution never bypasses governance authorization; and no dependency permits direct access to another component's persistence.
