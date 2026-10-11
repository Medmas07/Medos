# Canonical Demo Scenario

GitHub execution is coordinated by [EPIC - End-to-End Demo](https://github.com/Medmas07/Hackcure_hackathon/issues/23) and implementation issues [HC-240](https://github.com/Medmas07/Hackcure_hackathon/issues/95) through [HC-247](https://github.com/Medmas07/Hackcure_hackathon/issues/102). Stable HC IDs and the complete mapping remain in [the backlog](backlog.md).


This is the principal product demonstration and the basis for P0 ordering. Every person, organization, record, request, and result is fictional and comes from the coherent demo dataset in HC-005. Simulated behavior is visibly represented as demo behavior and is not described as production persistence.

## Cast and story map (HC-240)

Assembled by [HC-240](https://github.com/Medmas07/Hackcure_hackathon/issues/95) at D1. Every product tells the story below with these identities. Ids are those of [`demo-data/`](../../demo-data/README.md), and roles are in its `manifest.json` `scenarioRoles`. A product shows a person by name and an organization by its `organizations.json` name. Never use another or a real establishment's name.

### Cast

| Scenario role | Id | Shown as | Organization | Products |
|---|---|---|---|---|
| Patient A | `pat-a` | Leïla Mansouri | records at all three record holders below | Patient App, Clinician App |
| Patient A's trusted relative | `rel-sami` | Sami Mansouri | — | Patient App (delegation) |
| Dr. X | `clin-x` | Dr Youssef Gharbi, cardiologie | Hôpital Universitaire Bab Ennour (`org-hospital-a`) | Clinician App, Patient App (grant) |
| Hospital A's emergency physician | `clin-rania` | Dr Rania Kefi | Hôpital Universitaire Bab Ennour | Patient A's 2024 emergency visit |
| Hospital B's physician | `clin-ines` | Dr Inès Chaabane | Hôpital Régional Oued Zitoun (`org-hospital-b`) | prescribed Medication A |
| Private doctor | `clin-hatem` | Dr Hatem Bouzid | Cabinet médical Dr Hatem Bouzid (`org-private-practice`) | Patient A's 2025 follow-up |
| Hospital manager (onboarding) | `usr-mehdi` | Mehdi Sassi | Centre Hospitalier Cap Azur (`org-hospital-c`) | Hospital Portal |
| Governance reviewer | `usr-olfa` | Pr Olfa Hamdi | Autorité de Gouvernance et d'Éthique Fédérée (`org-governance`) | Governance Portal |
| Researcher | `usr-aymen` | Dr Aymen Rezgui | Laboratoire de Recherche Cardiométabolique de Carthage (`org-research-lab`) | Research Portal |

| Object | Id | Shown as |
|---|---|---|
| Medication A | `MED-COAGULIX`, record `med-b-leila-coagulix` | Coagulix 5 mg, active since 20 May 2026, prescribed at Hôpital Régional Oued Zitoun |
| Medication B | `MED-DOLORANE` | Dolorane, proposed by Dr. X; conflict `rule-coagulix-dolorane`, expected result `check-a-dolorane` |
| Patient A's grant to Dr. X | `grant-a-drx` | scoped, temporary access until 24 October 2026 |

Patient A's history, newest first: internal medicine consultation, Coagulix, and pre-treatment labs at Hôpital Régional Oued Zitoun (20 May 2026); blood-pressure follow-up and Tensiorel at Cabinet médical Dr Hatem Bouzid (12 June 2025); emergency visit and labs at Hôpital Universitaire Bab Ennour (9 March 2024).

### Story map

What each step uses today. **Fixtures** means local fictional data in the product, labelled as a demo; nothing here is production behavior. A PLANNED screen is owned by the journey tickets HC-241 to HC-245; HC-247 owns fallback mode.

| Steps | Product, entry point | Acting identity | Canonical data | State today |
|---|---|---|---|---|
| 1–2 | Patient App, Accueil and Parcours | `pat-a` | Patient A's records in the three `records/` files | IMPLEMENTED (D1), fixtures |
| 3 | Patient App, Accès, "Accorder un accès" | `pat-a` | `grant-a-drx` | IMPLEMENTED (D1), local state only |
| 4 | Clinician App, Accueil | `clin-x` | `people.json` | IMPLEMENTED (D1), simulated session |
| 5 | Clinician App, Patients | `clin-x` | `grant-a-drx` | IMPLEMENTED (D1), MOCKED authorization from fixtures (HC-033) |
| 6 | Clinician App, Patients | `clin-x` | Patient A's records | Screen PLANNED (HC-035). The Federation Service answers Patient A's federated timeline from the Hospital Nodes over HTTP (HC-141, HC-145; the nodes' data is MOCKED). |
| 7–9 | Clinician App, Consultation | `clin-x`, `pat-a` | `script-a-2026-10-10` | MOCKED (D1): recording consent (HC-037), transcript (HC-038) |
| 10–11 | Clinician App, Consultation | `clin-x` | extraction draft in `script-a-2026-10-10` | Screen PLANNED. The AI extractor's own transcript still differs (see `demo-data` README, known divergence). |
| 12–14 | Clinician App, Consultation | `clin-x` | `MED-DOLORANE` vs `med-b-leila-coagulix`, `check-a-dolorane` | Screen PLANNED. The Hospital Node's deterministic check returns `check-a-dolorane` (HC-162, MOCKED rules). |
| 15–16 | Patient App, Parcours | `pat-a` | the new consultation | PLANNED |
| 17–18 | Hospital Portal (`apps/web/landing/`), registration to `#node-download` | `usr-mehdi` | `app-hospital-c` | IMPLEMENTED (D1), MOCKED review and package |
| 19–23 | Governance Portal, Synchronisations then audit and proof explorer | `usr-olfa` | `sync-001`; examples `dec-sync-002`, `evt-003`, `proof-003` | IMPLEMENTED (D1), decision MOCKED in the browser; simulated proof |
| 24–27 | Research Portal, new project to submission | `usr-aymen` | `proj-001`; `proj-002` under review | IMPLEMENTED (D1), fixtures |
| 28–29 | Governance Portal, research requests | `usr-olfa` | `rar-001` | IMPLEMENTED (D1), decision MOCKED in the browser |
| 30–34 | Research Portal, workspace, executions, results | `usr-aymen` | `job-001`, `res-001` | IMPLEMENTED (D1), simulated execution stages |
| 35–36 | Research Portal, SciAgents | `usr-aymen` | `inv-001` | IMPLEMENTED (D1) fixture; live SciAgents not VALIDATED |

**Kept in sync by tests:** the Patient App (`test/canonical_patient_test.dart`), the Clinician App (`test/clinician_shell_test.dart`), the Governance Portal's demo sign-in personas (`tests/canonicalIdentities.test.ts`), and `demo-data/check_fixtures.py` for the dataset and its scenario roles.

## Patient and clinician journey

1. Open the Patient App.
2. Show Patient A with history from Hospital A, Hospital B, and a private doctor.
3. Patient A grants Dr. X temporary, scoped access.
4. Open the Clinician App as Dr. X.
5. Confirm that Patient A appears in authorized patients.
6. Open Patient A's federated timeline.
7. Start a consultation.
8. Patient A accepts speech recording.
9. Display a simulated speech-to-text transcript.
10. Display AI extraction of symptoms, observations, values, and missing information.
11. Dr. X reviews and validates the extracted information.
12. Dr. X attempts to prescribe Medication B.
13. Detect a deterministic conflict with Medication A previously prescribed at Hospital B.
14. Display the medication warning, provenance, evidence/explanation, and clinician validation action.
15. Return to the Patient App.
16. Show the new consultation in Patient A's timeline.

## Hospital onboarding journey

17. Open the Hospital Portal.
18. Demonstrate registration of a new hospital: documents, technical questionnaire, automated review, human approval, and Node download.

The automated/LLM review and package download may be simulated; governance approval remains a human/governance action.

## Governance journey

19. Open the Governance Portal.
20. Show a synchronization request between Hospital A and Hospital B, including purpose, scope, duration, and consent state.
21. Approve the synchronization request.
22. Show the resulting audit event.
23. Show a simulated blockchain hash/proof without claiming real blockchain persistence or exposing clinical data.

## Research journey

24. Open the Research Portal.
25. Create a research project.
26. Define its population and requested variables.
27. Submit the ethics/data-access request.
28. Show the request arriving in the Governance Portal.
29. Approve the request as the governance authority.
30. Return to the research workspace.
31. Open the Colab-like notebook interface.
32. Run a simulated compute-to-data job.
33. Display the execution stages: Hospital A executing, Hospital B executing, and aggregating results.
34. Show the controlled result.
35. Open the SciAgents panel.
36. Show the scientific investigation result with evidence, hypotheses, contradictions, and citations.

## Demonstrated principles

- Patient history spans organizations without presenting a centralized raw clinical database.
- Access is scoped, temporary, and visible to both sides of the workflow.
- AI output is editable and requires clinician validation where consequences are clinical.
- Medication safety is grounded in deterministic fixtures initially, not an LLM alone.
- Governance authority is distinct from company-managed portals.
- Blockchain content is a simulated minimized proof, never a medical record.
- Research code conceptually moves to authorized hospital execution boundaries; only controlled results return.
- SciAgents is integrated as an external capability, not reimplemented.
