# Clinician App

## Purpose and status

Mobile product for authorized clinician workflows serving physicians, nurses, and clinics.

HC-032 Priority patient queue is IMPLEMENTED at D1 in `File`: `clin-x`'s fictional queue on the demo day in rank order, each entry with its patient, hard-coded priority (`Priorité élevée` / `moyenne`), fixed-weight demonstration score, visible reasons, the fixture alerts it comes from with their severity, and the expiry of the patient's active access grant. A notice labels the order a deterministic simulated method (MOCKED), hard-coded and without AI, not clinical triage, with the dataset's method description; the per-priority explanation is PLANNED (HC-044). The app displays the fixture's ranking and computes, ranks, or triages nothing. A test checks that every entry matches `demo-data/clinician.json`, has unique rank, concerns a patient with an active grant on the demo day, and cites only that patient's alerts. Checked on the emulator (Pixel 8, API 34).

HC-031 Clinician dashboard is IMPLEMENTED at D1 in `Accueil`: a read-only summary of `clin-x`'s fictional authorized context on the canonical demo day (2026-10-10, `referenceDate` in [`demo-data/manifest.json`](../../../demo-data/manifest.json)), never the device clock. Four tiles count the day's scheduled appointments (2), the patients with an active access grant (2), unresolved alerts (3), and priority-queue entries (2), each opening its destination. Below them: the day's appointments in time order, unresolved alerts ordered by severity then recency, labelled fictional and advisory, and the priority queue in rank order with its reasons, labelled as a deterministic simulated method (MOCKED) and not clinical triage. Each section's `Voir` link opens its destination, whose content is still PLANNED. Figures are computed from presentation fixtures copied from `clinician.json`, `access.json`, and `people.json`; nothing is fetched, stored, ranked, or triaged by the app. Checked on the same emulator (Pixel 8, API 34): all sections render without overflow, and a `Voir` link opens its destination.

IMPLEMENTED at D1 for HC-030: a Flutter Android shell provides five navigable destinations plus explicit content, loading, empty, and error states. It uses the fictional HC-005 clinician `clin-x` (Dr Youssef Gharbi, Cardiologie, Hôpital Universitaire Bab Ennour) in a simulated session and permanently labels demo content. Each destination's status and the tickets that deliver its content:

HC-037 Recording consent UX is MOCKED at D1 in the Consultation destination. For fictional Patient A (`pat-a`, Leïla Mansouri), the clinician must confirm that the recording purpose, human review, and right to refuse or stop were explained before recording consent. Grant, refusal, and withdrawal/reconsideration states are reviewable. The decision is widget-local and session-only; no microphone is activated, no audio or consent is persisted, and no API is called. Real audio capture and the remaining consultation workflow stay PLANNED.

HC-038 Speech-to-text consultation UX is MOCKED at D1 after recording consent. The clinician starts and stops a visibly simulated recording, sees deterministic transcription progress, then reviews the predefined fictional `script-a-2026-10-10` transcript from `demo-data/clinician.json`, with speaker attribution and a permanent MOCKED label. There is no microphone permission, audio capture, speech model, network call, persistence, or clinical extraction. Withdrawing consent hides and cancels the speech-to-text flow.

HC-043 Clinician alert center is MOCKED at D1 with the three canonical fictional alerts from `demo-data/clinician.json`. The center shows patient, date, source reference, and visibly demo-only priority, and lets the clinician mark an alert as examined or restore it. The pending/all filters and reviewed state are widget-local and session-only. Ordering is not clinical triage, no alert is received in real time, and no acknowledgement is persisted or sent to the Notification Service.

HC-042 Medication interaction warning is MOCKED at D1 in the Consultation destination. After recording consent, the clinician can simulate a deterministic check of the fictional planned Dolorane prescription against the authorized fictional medication context. It reveals the canonical major interaction with active Coagulix held by Hospital B, including medication and organization provenance, fictional rule-set name/version, effect, rule recommendation, and pending/reviewed states. The warning explicitly neither blocks nor authorizes prescribing. No LLM creates the warning; no Hospital Node or medication-safety API is called; the medicines and rules are invented and not pharmacologically validated.

HC-039 Adaptive intake workflow is MOCKED at D1 in the Consultation destination. When fictional Patient A refuses recording, an adaptive form replaces speech-to-text, following the product vision's order: chief complaint, body location, duration, severity, and associated symptoms. Branching is deterministic and lives in `lib/presentation/adaptive_intake_flow.dart`, which has no Flutter dependency: the complaint decides whether location is asked (pain and rash only), a paired joint (shoulder, knee) adds a side question, the severity question and its answers depend on the complaint (0 to 10 pain scale, maximum temperature, effort tolerance, impact), and the associated-symptom list depends on the complaint and, for pain, the location. Each question says which earlier answer chose it, skipped steps are listed with their reason, and an earlier answer can be changed: answers that no longer fit are dropped, the others kept. The result is a review summary labelled as a draft for clinician validation. The questions are invented demo content, not a validated clinical questionnaire; the form does not score, prioritize, diagnose, or recommend. Answers are widget-local and disappear when the recording decision is reviewed; nothing is persisted or sent, and no consultation draft is created (HC-036). The product vision's last step, relevant history, is not in HC-039's objective and stays PLANNED; it depends on the authorized federated history (HC-035). The medication interaction warning (HC-042) is still shown only after recording consent, not after the intake.

| Destination | Planned content |
|---|---|
| `Accueil` | Clinician dashboard, IMPLEMENTED at D1 (HC-031, see above). |
| `File` | Priority patient queue, IMPLEMENTED at D1 (HC-032, see above); its explanation is PLANNED (HC-044). |
| `Patients` | Authorized patient list, patient detail, and federated history (HC-033 to HC-035). |
| `Consultation` | Recording consent, speech-to-text, adaptive intake, and medication interaction warning UX are MOCKED (HC-037 to HC-039, HC-042); consultation workspace, real audio capture/transcription, and AI extraction/lab review remain PLANNED (HC-036, HC-040, HC-041). |
| `Alertes` | Clinician alert center is MOCKED with canonical fixtures and session-local review state (HC-043). |

The profile sheet (app bar avatar) shows the fictional identity and states that the session is simulated: there is no authentication or authorization. The flask menu switches the current destination between content, loading, empty, and error states; navigating returns to content.

Flutter + Dart and the Android-first development path are CONFIRMED by [ADR-0004](../../../docs/decisions/ADR-0004-mobile-technology.md). The shell was generated with Flutter 3.44.6 / Dart 3.12.2; exact resolved packages are recorded in `pubspec.lock`. `flutter analyze` and `flutter test` pass, and `flutter build apk --debug` succeeded. The APK was installed and launched on an Android emulator (Pixel 8, API 34): the dashboard, a destination switch, and the profile sheet rendered with no Flutter error in the log. This is a runtime smoke test, not clinical, security, or production validation.

## Responsibilities and owned concepts

- Authorized patient lists, longitudinal views, consultation workspace, alerts, and priority presentation.
- Consent-aware speech-to-text, adaptive intake, extraction review, lab review, and medication-warning presentation.

## Communication boundaries

The Clinician App consumes authorized context through explicit APIs and never accesses hospital databases directly. Clinical AI output is advisory and subject to clinician review.

At D1 there is no HTTP client, persistence, authentication, or backend integration. Files under `lib/demo/` are presentation-only copies of the canonical fictional clinician identity, consultation, alerts, and medication warning from [`demo-data/`](../../../demo-data/); tests fail if those copies drift. They are not identity, authorization, notification, medication-safety, or clinical domain models. Planned destinations state that they load no clinical data.

## Non-responsibilities

It does not have autonomous diagnostic or prescription authority, make Governance decisions, or treat LLM output as validated clinical truth. Any future priority display does not replace clinical judgment.

## Expected contracts

PLANNED authorization, patient-view, consultation, extraction-review, medication-safety, alert, queue, and notification contracts. Existing candidates include the Federation [patient query](../../../contracts/federation/federated-patient-query.v1.yaml) (served through HC-114 / HC-141), the [medication safety check](../../../contracts/api/medication-safety/medication-safety-check.v1.yaml), and the Notification Service's clinician alerts; the app consumes none of them.

## Structure

- `lib/app/`: Flutter composition root.
- `lib/presentation/`: Material theme, application shell, navigation, reviewable states, the dashboard, the priority queue, and shared label helpers; `adaptive_intake_flow.dart` holds the intake's branching rules without Flutter.
- `lib/demo/`: fictional presentation fixtures (identity, demo day, appointments, alerts, priority queue, access grants, patient names); no real patient or clinician data.
- `test/`: widget tests for navigation, demo labelling, canonical identity, UI states, the dashboard's figures, order, labels, and links, the priority queue's order, reasons, linked alerts, and labels, and fixture consistency with `demo-data/`; unit tests for the adaptive intake's branching and answer pruning.
- `android/`: application-local Android infrastructure generated by Flutter.

## Commands

Run from `apps/mobile/clinician/`:

| Purpose | Command |
|---|---|
| Resolve locked packages | `flutter pub get` |
| Analyze | `flutter analyze` |
| Test | `flutter test` |
| Run on the configured emulator | `flutter run -d emulator-5554` |
| Build a debug APK | `flutter build apk --debug` |

The emulator identifier is environment-specific; use `flutter devices` if it differs. A successful debug build or demo run is not production, privacy, security, or clinical validation.
