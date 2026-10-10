# Canonical Demo Scenario

This is the principal product demonstration and the basis for P0 ordering. Every person, organization, record, request, and result is fictional and comes from the coherent demo dataset in HC-005. Simulated behavior is visibly represented as demo behavior and is not described as production persistence.

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
