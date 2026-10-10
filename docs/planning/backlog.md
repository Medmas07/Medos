# Implementation Backlog

HC identifiers are stable product-planning IDs; GitHub issue numbers are repository execution IDs. Issue bodies contain scope, mock policy, acceptance criteria, dependencies, and upgrade paths.

Implementation strategy: **visual first, functional second, deep infrastructure third**. Mocks must be explicit and use fictional data.

## Product Foundation

| Planning ID and issue | Priority | Depth | Effort | MVP | Milestone |
|---|---|---|---|---|---|
| [HC-001 — Select web frontend technology](https://github.com/Medmas07/Hackcure_hackathon/issues/24) | P0 | D0 | XS | yes | Milestone 0 — Architecture Decisions |
| [HC-002 — Select mobile technology](https://github.com/Medmas07/Hackcure_hackathon/issues/25) | P0 | D0 | XS | yes | Milestone 0 — Architecture Decisions |
| [HC-003 — Select backend/runtime strategy](https://github.com/Medmas07/Hackcure_hackathon/issues/26) | P0 | D0 | S | yes | Milestone 0 — Architecture Decisions |
| [HC-004 — Build shared visual design system](https://github.com/Medmas07/Hackcure_hackathon/issues/27) | P0 | D1 | M | yes | Milestone 1 — Visual Ecosystem |
| [HC-005 — Create canonical demo fixtures](https://github.com/Medmas07/Hackcure_hackathon/issues/28) | P0 | D1 | M | yes | Milestone 1 — Visual Ecosystem |

## Patient Experience

| Planning ID and issue | Priority | Depth | Effort | MVP | Milestone |
|---|---|---|---|---|---|
| [HC-010 — Patient App shell and navigation](https://github.com/Medmas07/Hackcure_hackathon/issues/29) | P0 | D1 | S | yes | Milestone 1 — Visual Ecosystem |
| [HC-011 — Patient dashboard](https://github.com/Medmas07/Hackcure_hackathon/issues/30) | P0 | D1 | S | yes | Milestone 1 — Visual Ecosystem |
| [HC-012 — Federated patient medical timeline](https://github.com/Medmas07/Hackcure_hackathon/issues/31) | P0 | D1 | M | yes | Milestone 1 — Visual Ecosystem |
| [HC-013 — Patient medical event detail](https://github.com/Medmas07/Hackcure_hackathon/issues/32) | P0 | D1 | S | yes | Milestone 1 — Visual Ecosystem |
| [HC-014 — Medication history](https://github.com/Medmas07/Hackcure_hackathon/issues/33) | P0 | D1 | S | yes | Milestone 1 — Visual Ecosystem |
| [HC-015 — Laboratory results history](https://github.com/Medmas07/Hackcure_hackathon/issues/34) | P1 | D1 | S | yes | Milestone 1 — Visual Ecosystem |
| [HC-016 — Hospital and physician history](https://github.com/Medmas07/Hackcure_hackathon/issues/35) | P1 | D1 | S | yes | Milestone 1 — Visual Ecosystem |
| [HC-017 — Consent and access management](https://github.com/Medmas07/Hackcure_hackathon/issues/36) | P0 | D1 | M | yes | Milestone 1 — Visual Ecosystem |
| [HC-018 — Grant physician access](https://github.com/Medmas07/Hackcure_hackathon/issues/37) | P0 | D1 | M | yes | Milestone 1 — Visual Ecosystem |
| [HC-019 — Revoke physician access](https://github.com/Medmas07/Hackcure_hackathon/issues/38) | P1 | D1 | S | yes | Milestone 1 — Visual Ecosystem |
| [HC-020 — Delegate access to trusted relative](https://github.com/Medmas07/Hackcure_hackathon/issues/39) | P1 | D1 | M | yes | Milestone 1 — Visual Ecosystem |
| [HC-021 — Digital restriction / erasure request](https://github.com/Medmas07/Hackcure_hackathon/issues/40) | P1 | D1 | M | yes | Milestone 1 — Visual Ecosystem |
| [HC-022 — Patient notification center](https://github.com/Medmas07/Hackcure_hackathon/issues/41) | P1 | D1 | S | yes | Milestone 1 — Visual Ecosystem |

## Clinician Experience

| Planning ID and issue | Priority | Depth | Effort | MVP | Milestone |
|---|---|---|---|---|---|
| [HC-030 — Clinician App shell and navigation](https://github.com/Medmas07/Hackcure_hackathon/issues/42) | P0 | D1 | S | yes | Milestone 1 — Visual Ecosystem |
| [HC-031 — Clinician dashboard](https://github.com/Medmas07/Hackcure_hackathon/issues/43) | P0 | D1 | S | yes | Milestone 1 — Visual Ecosystem |
| [HC-032 — Priority patient queue](https://github.com/Medmas07/Hackcure_hackathon/issues/44) | P0 | D1 | M | yes | Milestone 1 — Visual Ecosystem |
| [HC-033 — Authorized patient list](https://github.com/Medmas07/Hackcure_hackathon/issues/45) | P0 | D1 | S | yes | Milestone 1 — Visual Ecosystem |
| [HC-034 — Clinician patient detail](https://github.com/Medmas07/Hackcure_hackathon/issues/46) | P0 | D1 | S | yes | Milestone 1 — Visual Ecosystem |
| [HC-035 — Clinician federated patient history](https://github.com/Medmas07/Hackcure_hackathon/issues/47) | P0 | D1 | M | yes | Milestone 1 — Visual Ecosystem |
| [HC-036 — Consultation workspace](https://github.com/Medmas07/Hackcure_hackathon/issues/48) | P0 | D1 | M | yes | Milestone 1 — Visual Ecosystem |
| [HC-037 — Recording consent UX](https://github.com/Medmas07/Hackcure_hackathon/issues/49) | P0 | D1 | S | yes | Milestone 1 — Visual Ecosystem |
| [HC-038 — Speech-to-text consultation UX](https://github.com/Medmas07/Hackcure_hackathon/issues/50) | P0 | D1 | M | yes | Milestone 1 — Visual Ecosystem |
| [HC-039 — Adaptive intake workflow](https://github.com/Medmas07/Hackcure_hackathon/issues/51) | P0 | D1 | M | yes | Milestone 1 — Visual Ecosystem |
| [HC-040 — AI clinical extraction review](https://github.com/Medmas07/Hackcure_hackathon/issues/52) | P0 | D1 | M | yes | Milestone 1 — Visual Ecosystem |
| [HC-041 — Lab result extraction review](https://github.com/Medmas07/Hackcure_hackathon/issues/53) | P1 | D1 | M | yes | Milestone 1 — Visual Ecosystem |
| [HC-042 — Medication interaction warning](https://github.com/Medmas07/Hackcure_hackathon/issues/54) | P0 | D1 | M | yes | Milestone 1 — Visual Ecosystem |
| [HC-043 — Clinician alert center](https://github.com/Medmas07/Hackcure_hackathon/issues/55) | P1 | D1 | S | yes | Milestone 1 — Visual Ecosystem |
| [HC-044 — Queue priority explanation](https://github.com/Medmas07/Hackcure_hackathon/issues/56) | P1 | D1 | S | yes | Milestone 1 — Visual Ecosystem |

## Hospital Onboarding

| Planning ID and issue | Priority | Depth | Effort | MVP | Milestone |
|---|---|---|---|---|---|
| [HC-050 — Hospital Portal shell](https://github.com/Medmas07/Hackcure_hackathon/issues/57) | P0 | D1 | S | yes | Milestone 1 — Visual Ecosystem |
| [HC-051 — Hospital registration flow](https://github.com/Medmas07/Hackcure_hackathon/issues/58) | P0 | D1 | M | yes | Milestone 1 — Visual Ecosystem |
| [HC-052 — Hospital organization profile](https://github.com/Medmas07/Hackcure_hackathon/issues/59) | P0 | D1 | S | yes | Milestone 1 — Visual Ecosystem |
| [HC-053 — Hospital document upload](https://github.com/Medmas07/Hackcure_hackathon/issues/60) | P0 | D1 | M | yes | Milestone 1 — Visual Ecosystem |
| [HC-054 — Hospital agreements workflow](https://github.com/Medmas07/Hackcure_hackathon/issues/61) | P0 | D1 | S | yes | Milestone 1 — Visual Ecosystem |
| [HC-055 — Technical onboarding questionnaire](https://github.com/Medmas07/Hackcure_hackathon/issues/62) | P0 | D1 | M | yes | Milestone 1 — Visual Ecosystem |
| [HC-056 — DMI/HIS information questionnaire](https://github.com/Medmas07/Hackcure_hackathon/issues/63) | P0 | D1 | M | yes | Milestone 1 — Visual Ecosystem |
| [HC-057 — Automated onboarding review](https://github.com/Medmas07/Hackcure_hackathon/issues/64) | P0 | D1 | M | yes | Milestone 1 — Visual Ecosystem |
| [HC-058 — Human hospital validation state](https://github.com/Medmas07/Hackcure_hackathon/issues/65) | P0 | D1 | S | yes | Milestone 1 — Visual Ecosystem |
| [HC-059 — Hospital approval page](https://github.com/Medmas07/Hackcure_hackathon/issues/66) | P0 | D1 | XS | yes | Milestone 1 — Visual Ecosystem |
| [HC-060 — Hospital Node configuration summary](https://github.com/Medmas07/Hackcure_hackathon/issues/67) | P0 | D1 | M | yes | Milestone 1 — Visual Ecosystem |
| [HC-061 — Hospital Node download page](https://github.com/Medmas07/Hackcure_hackathon/issues/68) | P0 | D1 | M | yes | Milestone 1 — Visual Ecosystem |
| [HC-062 — Hospital Node installation guide](https://github.com/Medmas07/Hackcure_hackathon/issues/69) | P1 | D1 | S | yes | Milestone 1 — Visual Ecosystem |
| [HC-063 — Hospital Node status dashboard](https://github.com/Medmas07/Hackcure_hackathon/issues/70) | P1 | D1 | M | yes | Milestone 1 — Visual Ecosystem |

## Governance & Ethics

| Planning ID and issue | Priority | Depth | Effort | MVP | Milestone |
|---|---|---|---|---|---|
| [HC-070 — Governance Portal shell](https://github.com/Medmas07/Hackcure_hackathon/issues/71) | P0 | D1 | S | yes | Milestone 1 — Visual Ecosystem |
| [HC-071 — Governance dashboard](https://github.com/Medmas07/Hackcure_hackathon/issues/72) | P0 | D1 | M | yes | Milestone 1 — Visual Ecosystem |
| [HC-072 — Pending hospital approval list](https://github.com/Medmas07/Hackcure_hackathon/issues/73) | P0 | D1 | S | yes | Milestone 1 — Visual Ecosystem |
| [HC-073 — Hospital approval review](https://github.com/Medmas07/Hackcure_hackathon/issues/74) | P0 | D1 | M | yes | Milestone 1 — Visual Ecosystem |
| [HC-074 — Synchronization request list](https://github.com/Medmas07/Hackcure_hackathon/issues/75) | P0 | D1 | S | yes | Milestone 1 — Visual Ecosystem |
| [HC-075 — Synchronization request detail](https://github.com/Medmas07/Hackcure_hackathon/issues/76) | P0 | D1 | M | yes | Milestone 1 — Visual Ecosystem |
| [HC-076 — Approve/reject synchronization request](https://github.com/Medmas07/Hackcure_hackathon/issues/77) | P0 | D1 | M | yes | Milestone 1 — Visual Ecosystem |
| [HC-077 — Research access request list](https://github.com/Medmas07/Hackcure_hackathon/issues/78) | P0 | D1 | S | yes | Milestone 1 — Visual Ecosystem |
| [HC-078 — Research access request review](https://github.com/Medmas07/Hackcure_hackathon/issues/79) | P0 | D1 | M | yes | Milestone 1 — Visual Ecosystem |
| [HC-079 — Governance audit timeline](https://github.com/Medmas07/Hackcure_hackathon/issues/80) | P1 | D1 | M | yes | Milestone 1 — Visual Ecosystem |
| [HC-080 — Blockchain proof explorer](https://github.com/Medmas07/Hackcure_hackathon/issues/81) | P1 | D1 | M | yes | Milestone 1 — Visual Ecosystem |

## Research Platform

| Planning ID and issue | Priority | Depth | Effort | MVP | Milestone |
|---|---|---|---|---|---|
| [HC-090 — Research Portal shell](https://github.com/Medmas07/Hackcure_hackathon/issues/82) | P0 | D1 | S | yes | Milestone 1 — Visual Ecosystem |
| [HC-091 — Researcher dashboard](https://github.com/Medmas07/Hackcure_hackathon/issues/83) | P0 | D1 | S | yes | Milestone 1 — Visual Ecosystem |
| [HC-092 — Create research project](https://github.com/Medmas07/Hackcure_hackathon/issues/84) | P0 | D1 | M | yes | Milestone 1 — Visual Ecosystem |
| [HC-093 — Upload research protocol/documents](https://github.com/Medmas07/Hackcure_hackathon/issues/85) | P1 | D1 | M | yes | Milestone 1 — Visual Ecosystem |
| [HC-094 — Define research population](https://github.com/Medmas07/Hackcure_hackathon/issues/86) | P0 | D1 | M | yes | Milestone 1 — Visual Ecosystem |
| [HC-095 — Define requested variables/data](https://github.com/Medmas07/Hackcure_hackathon/issues/87) | P0 | D1 | M | yes | Milestone 1 — Visual Ecosystem |
| [HC-096 — Select participating hospitals](https://github.com/Medmas07/Hackcure_hackathon/issues/88) | P0 | D1 | S | yes | Milestone 1 — Visual Ecosystem |
| [HC-097 — Submit research data-access request](https://github.com/Medmas07/Hackcure_hackathon/issues/89) | P0 | D1 | M | yes | Milestone 1 — Visual Ecosystem |
| [HC-098 — Research request status](https://github.com/Medmas07/Hackcure_hackathon/issues/90) | P0 | D1 | S | yes | Milestone 1 — Visual Ecosystem |
| [HC-099 — Colab-like research workspace](https://github.com/Medmas07/Hackcure_hackathon/issues/91) | P0 | D1 | L | yes | Milestone 1 — Visual Ecosystem |
| [HC-100 — Compute-to-Data execution visualization](https://github.com/Medmas07/Hackcure_hackathon/issues/92) | P0 | D1 | M | yes | Milestone 1 — Visual Ecosystem |
| [HC-101 — Research experiment result panel](https://github.com/Medmas07/Hackcure_hackathon/issues/93) | P0 | D1 | M | yes | Milestone 1 — Visual Ecosystem |
| [HC-102 — SciAgents research panel](https://github.com/Medmas07/Hackcure_hackathon/issues/94) | P0 | D1 | M | yes | Milestone 1 — Visual Ecosystem |

## Hospital Node

| Planning ID and issue | Priority | Depth | Effort | MVP | Milestone |
|---|---|---|---|---|---|
| [HC-110 — Hospital Node runtime skeleton](https://github.com/Medmas07/Hackcure_hackathon/issues/103) | P1 | D2 | M | yes | Milestone 3 — Backend Integration |
| [HC-111 — Hospital Node health endpoint](https://github.com/Medmas07/Hackcure_hackathon/issues/104) | P1 | D2 | S | yes | Milestone 3 — Backend Integration |
| [HC-112 — Hospital Node configuration loading](https://github.com/Medmas07/Hackcure_hackathon/issues/105) | P1 | D2 | M | yes | Milestone 3 — Backend Integration |
| [HC-113 — Mock clinical repository](https://github.com/Medmas07/Hackcure_hackathon/issues/106) | P1 | D2 | M | yes | Milestone 3 — Backend Integration |
| [HC-114 — Patient history API](https://github.com/Medmas07/Hackcure_hackathon/issues/107) | P1 | D2 | M | yes | Milestone 3 — Backend Integration |
| [HC-115 — Consent/access API](https://github.com/Medmas07/Hackcure_hackathon/issues/108) | P1 | D2 | M | yes | Milestone 3 — Backend Integration |
| [HC-116 — Hospital audit-event API](https://github.com/Medmas07/Hackcure_hackathon/issues/109) | P2 | D2 | M | no | Milestone 3 — Backend Integration |

## Hospital Node Legacy/DMI Integration

| Planning ID and issue | Priority | Depth | Effort | MVP | Milestone |
|---|---|---|---|---|---|
| [HC-120 — Define Hospital Node DMI adapter port](https://github.com/Medmas07/Hackcure_hackathon/issues/149) | P1 | D1 | S | no | Milestone 3 — Backend Integration |
| [HC-121 — Create mock local DMI adapter](https://github.com/Medmas07/Hackcure_hackathon/issues/150) | P2 | D2 | M | no | Milestone 3 — Backend Integration |
| [HC-122 — Define DMI-to-canonical mapping strategy](https://github.com/Medmas07/Hackcure_hackathon/issues/151) | P2 | D2 | M | no | Milestone 3 — Backend Integration |
| [HC-123 — Implement sample hospital-specific DMI adapter](https://github.com/Medmas07/Hackcure_hackathon/issues/152) | P3 | D3 | L | no | Milestone 3 — Backend Integration |

## Governance Node

| Planning ID and issue | Priority | Depth | Effort | MVP | Milestone |
|---|---|---|---|---|---|
| [HC-130 — Governance Node runtime skeleton](https://github.com/Medmas07/Hackcure_hackathon/issues/110) | P1 | D2 | M | yes | Milestone 4 — Federation & Governance |
| [HC-131 — Hospital approval API](https://github.com/Medmas07/Hackcure_hackathon/issues/111) | P1 | D2 | M | yes | Milestone 4 — Federation & Governance |
| [HC-132 — Synchronization request API](https://github.com/Medmas07/Hackcure_hackathon/issues/112) | P1 | D2 | M | yes | Milestone 4 — Federation & Governance |
| [HC-133 — Research request API](https://github.com/Medmas07/Hackcure_hackathon/issues/113) | P1 | D2 | M | yes | Milestone 4 — Federation & Governance |
| [HC-134 — Governance audit API](https://github.com/Medmas07/Hackcure_hackathon/issues/114) | P2 | D2 | M | no | Milestone 4 — Federation & Governance |
| [HC-135 — Governance policy engine](https://github.com/Medmas07/Hackcure_hackathon/issues/115) | P2 | D3 | L | no | Milestone 4 — Federation & Governance |
| [HC-136 — Consent policy evaluation](https://github.com/Medmas07/Hackcure_hackathon/issues/116) | P2 | D3 | L | no | Milestone 4 — Federation & Governance |

## Federation

| Planning ID and issue | Priority | Depth | Effort | MVP | Milestone |
|---|---|---|---|---|---|
| [HC-140 — Define federation contract](https://github.com/Medmas07/Hackcure_hackathon/issues/117) | P1 | D1 | M | yes | Milestone 4 — Federation & Governance |
| [HC-141 — Mock federated patient aggregation](https://github.com/Medmas07/Hackcure_hackathon/issues/118) | P1 | D2 | M | yes | Milestone 4 — Federation & Governance |
| [HC-142 — Node registry](https://github.com/Medmas07/Hackcure_hackathon/issues/119) | P2 | D2 | M | no | Milestone 4 — Federation & Governance |
| [HC-143 — Node capability discovery](https://github.com/Medmas07/Hackcure_hackathon/issues/120) | P2 | D2 | M | no | Milestone 4 — Federation & Governance |
| [HC-144 — Temporary sync authorization](https://github.com/Medmas07/Hackcure_hackathon/issues/121) | P2 | D3 | L | no | Milestone 4 — Federation & Governance |
| [HC-145 — Real Node-to-Node communication](https://github.com/Medmas07/Hackcure_hackathon/issues/122) | P2 | D3 | L | no | Milestone 4 — Federation & Governance |
| [HC-146 — Cross-node patient query](https://github.com/Medmas07/Hackcure_hackathon/issues/123) | P2 | D3 | L | no | Milestone 4 — Federation & Governance |
| [HC-147 — Federation failure handling](https://github.com/Medmas07/Hackcure_hackathon/issues/124) | P3 | D3 | M | no | Milestone 4 — Federation & Governance |

## AI Services

| Planning ID and issue | Priority | Depth | Effort | MVP | Milestone |
|---|---|---|---|---|---|
| [HC-150 — AI service runtime skeleton](https://github.com/Medmas07/Hackcure_hackathon/issues/125) | P1 | D2 | M | yes | Milestone 5 — Research & AI |
| [HC-151 — Define AI provider port](https://github.com/Medmas07/Hackcure_hackathon/issues/126) | P1 | D1 | M | yes | Milestone 5 — Research & AI |
| [HC-152 — Clinical extraction contract](https://github.com/Medmas07/Hackcure_hackathon/issues/127) | P1 | D1 | M | yes | Milestone 5 — Research & AI |
| [HC-153 — Real clinical extraction integration](https://github.com/Medmas07/Hackcure_hackathon/issues/128) | P2 | D3 | M | no | Milestone 5 — Research & AI |
| [HC-154 — LLM-assisted hospital document review](https://github.com/Medmas07/Hackcure_hackathon/issues/129) | P2 | D3 | M | no | Milestone 5 — Research & AI |
| [HC-155 — Lab extraction service](https://github.com/Medmas07/Hackcure_hackathon/issues/130) | P2 | D3 | M | no | Milestone 5 — Research & AI |
| [HC-156 — Medication warning explanation](https://github.com/Medmas07/Hackcure_hackathon/issues/131) | P2 | D3 | M | no | Milestone 5 — Research & AI |
| [HC-157 — Priority queue explanation](https://github.com/Medmas07/Hackcure_hackathon/issues/132) | P2 | D3 | M | no | Milestone 5 — Research & AI |

## Medication Safety

| Planning ID and issue | Priority | Depth | Effort | MVP | Milestone |
|---|---|---|---|---|---|
| [HC-160 — Define medication safety contract](https://github.com/Medmas07/Hackcure_hackathon/issues/133) | P1 | D1 | S | yes | Milestone 5 — Research & AI |
| [HC-161 — Demo medication interaction fixtures](https://github.com/Medmas07/Hackcure_hackathon/issues/134) | P0 | D1 | S | yes | Milestone 5 — Research & AI |
| [HC-162 — Implement deterministic medication interaction engine](https://github.com/Medmas07/Hackcure_hackathon/issues/135) | P2 | D2 | M | no | Milestone 5 — Research & AI |
| [HC-163 — Integrate validated medication interaction source](https://github.com/Medmas07/Hackcure_hackathon/issues/136) | P3 | D3 | L | no | Milestone 5 — Research & AI |
| [HC-164 — Add AI explanation layer](https://github.com/Medmas07/Hackcure_hackathon/issues/137) | P2 | D3 | M | no | Milestone 5 — Research & AI |

## SciAgents Integration

| Planning ID and issue | Priority | Depth | Effort | MVP | Milestone |
|---|---|---|---|---|---|
| [HC-170 — Define SciAgents communication contract](https://github.com/Medmas07/Hackcure_hackathon/issues/138) | P1 | D1 | S | yes | Milestone 5 — Research & AI |
| [HC-171 — Implement SciAgents client adapter](https://github.com/Medmas07/Hackcure_hackathon/issues/139) | P1 | D2 | M | yes | Milestone 5 — Research & AI |
| [HC-172 — Connect Research Portal to SciAgents](https://github.com/Medmas07/Hackcure_hackathon/issues/140) | P1 | D2 | M | yes | Milestone 5 — Research & AI |
| [HC-173 — Display SciAgents execution progress](https://github.com/Medmas07/Hackcure_hackathon/issues/141) | P2 | D2 | M | no | Milestone 5 — Research & AI |

## Compute-to-Data

| Planning ID and issue | Priority | Depth | Effort | MVP | Milestone |
|---|---|---|---|---|---|
| [HC-180 — Define research job contract](https://github.com/Medmas07/Hackcure_hackathon/issues/142) | P1 | D1 | M | yes | Milestone 5 — Research & AI |
| [HC-181 — Mock distributed research execution](https://github.com/Medmas07/Hackcure_hackathon/issues/143) | P1 | D2 | M | yes | Milestone 5 — Research & AI |
| [HC-182 — Research job orchestrator](https://github.com/Medmas07/Hackcure_hackathon/issues/144) | P2 | D3 | L | no | Milestone 5 — Research & AI |
| [HC-183 — Hospital-side research execution agent](https://github.com/Medmas07/Hackcure_hackathon/issues/145) | P2 | D3 | L | no | Milestone 5 — Research & AI |
| [HC-184 — Controlled result aggregation](https://github.com/Medmas07/Hackcure_hackathon/issues/146) | P2 | D3 | L | no | Milestone 5 — Research & AI |
| [HC-185 — Research output validation](https://github.com/Medmas07/Hackcure_hackathon/issues/147) | P3 | D4 | L | no | Milestone 6 — Production Hardening |
| [HC-186 — Isolated research sandbox](https://github.com/Medmas07/Hackcure_hackathon/issues/148) | P3 | D4 | XL | no | Milestone 6 — Production Hardening |

## Blockchain / Immutable Audit

| Planning ID and issue | Priority | Depth | Effort | MVP | Milestone |
|---|---|---|---|---|---|
| [HC-190 — Define AuditLedgerPort](https://github.com/Medmas07/Hackcure_hackathon/issues/153) | P2 | D1 | S | no | Milestone 4 — Federation & Governance |
| [HC-191 — Implement simulated immutable ledger](https://github.com/Medmas07/Hackcure_hackathon/issues/154) | P2 | D2 | M | no | Milestone 4 — Federation & Governance |
| [HC-192 — Governance ledger event hashing](https://github.com/Medmas07/Hackcure_hackathon/issues/155) | P2 | D2 | M | no | Milestone 4 — Federation & Governance |
| [HC-193 — Evaluate permissioned ledger technologies](https://github.com/Medmas07/Hackcure_hackathon/issues/156) | P3 | D0 | M | no | Milestone 4 — Federation & Governance |
| [HC-194 — Implement real blockchain/ledger adapter](https://github.com/Medmas07/Hackcure_hackathon/issues/157) | P3 | D4 | XL | no | Milestone 6 — Production Hardening |

## Notifications

| Planning ID and issue | Priority | Depth | Effort | MVP | Milestone |
|---|---|---|---|---|---|
| [HC-200 — Notification UI fixtures](https://github.com/Medmas07/Hackcure_hackathon/issues/158) | P1 | D1 | S | yes | Milestone 3 — Backend Integration |
| [HC-201 — Define notification event contract](https://github.com/Medmas07/Hackcure_hackathon/issues/159) | P2 | D1 | S | no | Milestone 3 — Backend Integration |
| [HC-202 — Notification service](https://github.com/Medmas07/Hackcure_hackathon/issues/160) | P2 | D2 | M | no | Milestone 3 — Backend Integration |
| [HC-203 — Real-time clinician alerts](https://github.com/Medmas07/Hackcure_hackathon/issues/161) | P2 | D3 | M | no | Milestone 3 — Backend Integration |
| [HC-204 — Mobile push notifications](https://github.com/Medmas07/Hackcure_hackathon/issues/162) | P3 | D3 | L | no | Milestone 3 — Backend Integration |

## Security & Audit

| Planning ID and issue | Priority | Depth | Effort | MVP | Milestone |
|---|---|---|---|---|---|
| [HC-210 — Demo authentication flow](https://github.com/Medmas07/Hackcure_hackathon/issues/163) | P1 | D1 | M | yes | Milestone 4 — Federation & Governance |
| [HC-211 — Real authentication foundation](https://github.com/Medmas07/Hackcure_hackathon/issues/164) | P2 | D2 | M | no | Milestone 4 — Federation & Governance |
| [HC-212 — Role-based access control](https://github.com/Medmas07/Hackcure_hackathon/issues/165) | P2 | D2 | M | no | Milestone 4 — Federation & Governance |
| [HC-213 — Hospital organization identity](https://github.com/Medmas07/Hackcure_hackathon/issues/166) | P2 | D3 | L | no | Milestone 4 — Federation & Governance |
| [HC-214 — Signed federation authorization](https://github.com/Medmas07/Hackcure_hackathon/issues/167) | P3 | D4 | L | no | Milestone 6 — Production Hardening |
| [HC-215 — Security audit and threat model](https://github.com/Medmas07/Hackcure_hackathon/issues/168) | P3 | D4 | L | no | Milestone 6 — Production Hardening |

## Deployment

| Planning ID and issue | Priority | Depth | Effort | MVP | Milestone |
|---|---|---|---|---|---|
| [HC-220 — Containerize Hospital Node](https://github.com/Medmas07/Hackcure_hackathon/issues/169) | P2 | D3 | L | no | Milestone 6 — Production Hardening |
| [HC-221 — Hospital Node installation package](https://github.com/Medmas07/Hackcure_hackathon/issues/170) | P2 | D3 | L | no | Milestone 6 — Production Hardening |
| [HC-222 — Container runtime detection](https://github.com/Medmas07/Hackcure_hackathon/issues/171) | P3 | D3 | M | no | Milestone 6 — Production Hardening |
| [HC-223 — Hospital Node deployment health checks](https://github.com/Medmas07/Hackcure_hackathon/issues/172) | P2 | D3 | M | no | Milestone 6 — Production Hardening |
| [HC-224 — Containerize Governance Node](https://github.com/Medmas07/Hackcure_hackathon/issues/173) | P2 | D3 | L | no | Milestone 6 — Production Hardening |
| [HC-225 — Preview environment](https://github.com/Medmas07/Hackcure_hackathon/issues/174) | P2 | D2 | M | no | Milestone 6 — Production Hardening |
| [HC-226 — Frontend deployment](https://github.com/Medmas07/Hackcure_hackathon/issues/175) | P2 | D3 | M | no | Milestone 6 — Production Hardening |
| [HC-227 — Backend deployment](https://github.com/Medmas07/Hackcure_hackathon/issues/176) | P2 | D3 | M | no | Milestone 6 — Production Hardening |

## End-to-End Demo

| Planning ID and issue | Priority | Depth | Effort | MVP | Milestone |
|---|---|---|---|---|---|
| [HC-240 — Assemble canonical demo identities and story](https://github.com/Medmas07/Hackcure_hackathon/issues/95) | P0 | D1 | S | yes | Milestone 2 — Interactive Demo |
| [HC-241 — Connect Patient App demo journey](https://github.com/Medmas07/Hackcure_hackathon/issues/96) | P0 | D1 | M | yes | Milestone 2 — Interactive Demo |
| [HC-242 — Connect Clinician demo journey](https://github.com/Medmas07/Hackcure_hackathon/issues/97) | P0 | D1 | M | yes | Milestone 2 — Interactive Demo |
| [HC-243 — Connect Hospital onboarding demo journey](https://github.com/Medmas07/Hackcure_hackathon/issues/98) | P0 | D1 | M | yes | Milestone 2 — Interactive Demo |
| [HC-244 — Connect Governance demo journey](https://github.com/Medmas07/Hackcure_hackathon/issues/99) | P0 | D1 | M | yes | Milestone 2 — Interactive Demo |
| [HC-245 — Connect Research demo journey](https://github.com/Medmas07/Hackcure_hackathon/issues/100) | P0 | D1 | M | yes | Milestone 2 — Interactive Demo |
| [HC-246 — Full ecosystem rehearsal](https://github.com/Medmas07/Hackcure_hackathon/issues/101) | P0 | D1 | M | yes | Milestone 2 — Interactive Demo |
| [HC-247 — Demo fallback mode](https://github.com/Medmas07/Hackcure_hackathon/issues/102) | P0 | D1 | M | yes | Milestone 2 — Interactive Demo |

## Summary

- Implementation issues: 153
- P0: 66; P1: 38; P2: 38; P3: 11
- D0: 4; D1: 88; D2: 29; D3: 27; D4: 5
- MVP Yes: 103; MVP No: 50
