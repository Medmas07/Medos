# ADR-0009: Validated interaction source — ONC high-priority list, matched by ingredient name

## Status

Accepted — 2026-10-11, chosen by the HC-163 assignee during HC-163 ([#136](https://github.com/Medmas07/Hackcure_hackathon/issues/136)); subject to pull-request review.

## Context

The medication safety check (HC-160 contract, HC-162 engine, [ADR-0008](ADR-0008-medication-safety-check-host.md)) runs on fictional rules only. HC-163 must integrate a validated interaction source. [OPEN_QUESTIONS.md](../OPEN_QUESTIONS.md) left both the source and the medication terminology undecided.

Forces:

- **Availability and licence**, checked on 2026-10-11:
  - NLM retired the RxNav drug-interaction API in 2024.
  - DrugBank's interaction data is commercial.
  - DDInter 2.0 is reported (by a third-party registry, unconfirmed on DDInter's site) as CC BY-NC-SA 4.0, which does not fit a company product.
  - The ANSM *Thésaurus des interactions médicamenteuses* is official but published only as PDF, and frozen since September 2023.
- **Determinism and no runtime network:** the engine must give the same answer for the same input and run inside the hospital boundary.
- **Honesty:** nothing may be presented as more complete or more validated than it is (AGENTS.md).
- **Demo:** the canonical scenario uses fictional medicines that no real source knows.

## Decision

1. **Source: the ONC high-priority drug–drug interaction list.** Phansalkar et al., JAMIA 2012;19(5):735–743, doi:10.1136/amiajnl-2011-000612 is a peer-reviewed, expert-panel consensus of interactions "contraindicated for concurrent use".
   - It is transcribed from Table 2 ("Final DDI pair and suggested membership") into a versioned snapshot, [`instances/hospital-node/reference/onc-high-priority-ddi-2012.json`](../../instances/hospital-node/reference/onc-high-priority-ddi-2012.json). Each row keeps the members it lists: 13 interactions, 89 ingredients, 362 pairs, all `contraindicated`.
   - The snapshot records every spelling correction and two exclusions. Row 20 (TCAs) lists no members, and row 21 (QT prolongation) defers to the separately licensed CredibleMeds list.
   - Only the drug pairs (facts) and the citation are stored, never the article's text.
2. **Matching by ingredient name**, the English name as printed plus French and other INN synonyms (for example *ciprofloxacine*, *rifampicine*, *péthidine*, *millepertuis*). Case, accents, and apostrophe style are ignored.
   - Anything else (brand names, combinations, doses in the name, unlisted drugs) is `not_in_rule_source`, never assumed safe.
   - No terminology is adopted: the snapshot's code system is a local one.
3. **Per-node switch:** `medication_rule_source` in the node configuration chooses the rules. The value is `demo_fixture` (default, the fictional HC-161 rules, `mocked: true`) or `onc_high_priority_2012` (this snapshot, `mocked: false`). A node uses one source, so provenance is never mixed.
4. **Every answer states the source's scope:** "a minimum set of contraindicated pairs, not exhaustive; no warning does not mean the combination is safe".

## Alternatives considered

- **DDInter 2.0:** about 300,000 graded interactions, but non-commercial share-alike terms (unconfirmed) and a large dataset to vet.
- **ANSM Thésaurus:** the right reference for a French-speaking deployment, with four official levels. It needs a checked extraction from PDF and is no longer updated. It is the natural next source if a licensed, structured version becomes available.
- **RxNorm codes:** sturdier matching, but it adopts a terminology still OPEN, and Tunisian or French hospital records rarely carry RxCUIs.
- **Combining the fictional and the validated rules in one node:** one call would cover both, but a result would mix mocked and validated provenance, which the contract does not model.

## Consequences

### Positive

- A real, cited, peer-reviewed source drives warnings with no model and no network, behind the existing `InteractionRuleSource` port.
- The transcription is auditable: source rows, corrections, exclusions, and a test that freezes the member counts per row.

### Negative

- The list is a **minimum** set from 2012: it misses most interactions and newer drugs. A node using it will report many medications as `not_in_rule_source`.
- Name matching misses brand names and misspellings; such medications are reported, not matched.
- The transcription was done by hand; a reviewer should check it against Table 2.
- The canonical fictional demo cannot use it; it stays on `demo_fixture`.

## Follow-up

- Choose a medication terminology (OPEN) and, with it, a broader licensed source.
- Re-transcribe if the list is revised; bump the snapshot version.
