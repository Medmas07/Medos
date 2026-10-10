# Milestones

Milestones express delivery intent, not a promise of production readiness. The order is demo-first; deterministic fixtures may unlock visible flows before their final adapters exist.

## Milestone 0 — Architecture Decisions

Decide the minimum technology and contract foundations before scaffolding runtimes.

- HC-001, HC-002, HC-003
- HC-110, HC-111, HC-112
- HC-150, HC-190, HC-250

Exit: accepted ADRs identify web, mobile, and backend strategies; initial contract conventions have owners and versioning direction.

## Milestone 1 — Visual Product

Build a coherent, attractive ecosystem from one fictional dataset.

- Foundation: HC-004, HC-005
- Patient: HC-010–HC-019
- Clinician: HC-030–HC-040
- Hospital onboarding: HC-050–HC-059
- Governance: HC-070–HC-076
- Research: HC-090–HC-099
- Shared notification experience: HC-210

Exit: the complete [canonical demo](demo-scenario.md) is navigable with clearly identified mock behavior.

## Milestone 2 — Demo Functional Layer

Replace isolated UI fixtures with explicit mock APIs and coordinated demo state.

- HC-115, HC-116, HC-117
- HC-170, HC-251
- HC-290

Exit: access grants, consultations, governance decisions, federation views, and research jobs flow coherently across interfaces using demo-safe authentication and data.

## Milestone 3 — Backend Integration

Introduce selected runtimes and adapter boundaries without bypassing contracts.

- HC-113, HC-114
- HC-130, HC-131, HC-132
- HC-151, HC-152
- HC-191
- HC-211, HC-212

Exit: basic Nodes and services run behind explicit contracts; SciAgents remains a platform integration and each DMI remains a replaceable, hospital-local Node adapter.

## Milestone 4 — Federation & Governance

Deepen node autonomy, governance enforcement, audit, and organizational security.

- HC-171–HC-175
- HC-230–HC-235
- HC-291, HC-292, HC-293

Exit: node identity, scoped authorization, consent, policy, and audit boundaries are testable without shared databases or raw clinical ledger data.

## Milestone 5 — Research & AI

Move from presentation fixtures toward validated AI and governed compute-to-data capabilities.

- HC-133–HC-136
- HC-252–HC-255

Exit: AI remains advisory and reviewable; authorized research execution produces controlled results without exporting raw hospital data by default.

## Milestone 6 — Production Hardening

Package selected runtimes and complete late integrations after architecture and operational constraints are known.

- HC-192, HC-213, HC-236
- HC-270–HC-274

Exit: deployment artifacts, health checks, installation guidance, real adapters, and operational controls have appropriate validation. Docker is never installed silently.
