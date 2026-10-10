# ADR-0005: Location and format of the canonical demo data

## Status

Accepted — 2026-10-10, chosen by the HC-005 assignee during HC-005 ([#28](https://github.com/Medmas07/Hackcure_hackathon/issues/28)); subject to pull-request review.

## Context

HC-005 must provide one coherent, fictional dataset reused by every product: three web portals in TypeScript ([ADR-0001](ADR-0001-web-frontend-technology.md)), two Flutter apps ([ADR-0004](ADR-0004-mobile-technology.md)), and Python backends whose mock APIs (HC-115 to HC-117) will later serve it ([ADR-0003](ADR-0003-backend-runtime-strategy.md)). No existing boundary fits:

- `contracts/` describes communication between components, and no contract exists yet;
- `tests/` holds cross-system tests, while this data is runtime demo content;
- `docs/` holds knowledge, not data products load;
- placing the data inside one product would make the others depend on it.

The data must also not suggest a central clinical database, and it must stay obviously fictional.

## Decision

- **Location:** a named top-level boundary, `demo-data/`, holding only fictional demo data and its integrity checker.
- **Format:** plain JSON, readable from TypeScript, Dart, and Python without a dependency. Keys and status codes are English; display text is French (`fr-TN`), matching a Tunisian setting with invented establishments and people.
- **Ownership-shaped files:** clinical records are split by holding organization (`records/<organization>.json`), each written only by that organization's clinicians. Governance, access, research, clinician-view, and notification data have their own files. A `manifest.json` maps the scenario roles of the [canonical demo](../planning/demo-scenario.md) to ids.
- **Fictional medicines:** medicines and the interaction rule are invented and marked `validated: false`, so no fixture can be mistaken for clinical guidance.
- **Integrity checker:** `demo-data/check_fixtures.py` (standard library only) enforces unique ids, resolvable references, record ownership, ISO dates, minimized and hash-consistent simulated ledger proofs, explicit fictional markers, and the scenario invariants.
- **Not contracts:** the JSON shapes are fixture shapes, not API contracts. Contracts under `contracts/` remain the communication source of truth once defined.

### Evidence

On 2026-10-10 with Python 3.10.5, the checker passed on the dataset and failed with precise messages on six deliberately broken copies. A temporary Vite 8 / TypeScript 6 project placed at `apps/web/<portal>/` depth (removed afterwards) imported `demo-data/people.json` by relative path; `tsc -b`, `vite build`, and `vite dev` all worked with inferred types and no configuration. Flutter and Python consumption were not tested.

## Alternatives considered

- **`contracts/fixtures/`:** keeps the top level unchanged, but mixes fixture data with communication definitions before any contract exists.
- **`tests/fixtures/`:** natural for test data, but products would load runtime demo content from a test folder.
- **One file per entity type (all encounters together):** simpler to read, but presents clinical records as one central collection, contradicting the federated model.
- **Real medicine names with a known interaction:** more convincing, but it would be a real medical statement without a validated source.
- **Generated per-language code (TypeScript, Dart, Python):** typed access, but adds a generator and three outputs to keep in sync for a two-day hackathon.

## Consequences

### Positive

- One dataset and one set of ids across all five products and later mock APIs.
- File layout demonstrates that records stay with their holding organization.
- Coherence is machine-checked, so edits cannot silently break the demo.

### Negative

- Products duplicate the fixture types in their own language until contracts exist.
- Flutter cannot read assets outside its package; the mobile shells must copy or bundle the files.
- Runtime demo state (new consultation, approvals) is not shared between products until the Milestone 2 mock APIs exist.

## Follow-up

- HC-010, HC-030: choose how the Flutter apps bundle the files they need.
- HC-050, HC-070, HC-090: replace design-system placeholder content with these fixtures.
- HC-110, HC-115 to HC-117: define contracts and serve this data through them.
- When product CI is configured, run `python demo-data/check_fixtures.py`.
