# Clinician App

## Purpose and status

Mobile product for authorized clinician workflows serving physicians, nurses, and clinics.

HC-031 Clinician dashboard is IMPLEMENTED at D1 in `Accueil`: a read-only summary of `clin-x`'s fictional authorized context on the canonical demo day (2026-10-10, `referenceDate` in [`demo-data/manifest.json`](../../../demo-data/manifest.json)), never the device clock. Four tiles count the day's scheduled appointments (2), the patients with an active access grant (2), unresolved alerts (3), and priority-queue entries (2), each opening its destination. Below them: the day's appointments in time order, unresolved alerts ordered by severity then recency, labelled fictional and advisory, and the priority queue in rank order with its reasons, labelled as a deterministic simulated method (MOCKED) and not clinical triage. Each section's `Voir` link opens its destination, whose content is still PLANNED. Figures are computed from presentation fixtures copied from `clinician.json`, `access.json`, and `people.json`; nothing is fetched, stored, ranked, or triaged by the app. Checked on the same emulator (Pixel 8, API 34): all sections render without overflow, and a `Voir` link opens its destination.

IMPLEMENTED at D1 for HC-030: a Flutter Android shell provides five navigable destinations plus explicit content, loading, empty, and error states. It uses the fictional HC-005 clinician `clin-x` (Dr Youssef Gharbi, Cardiologie, Hôpital Universitaire Bab Ennour) in a simulated session and permanently labels demo content. Each destination's status and the tickets that deliver its content:

HC-037 Recording consent UX is MOCKED at D1 in the Consultation destination. For fictional Patient A (`pat-a`, Leïla Mansouri), the clinician must confirm that the recording purpose, human review, and right to refuse or stop were explained before recording consent. Grant, refusal, and withdrawal/reconsideration states are reviewable. The decision is widget-local and session-only; no microphone is activated, no audio or consent is persisted, and no API is called. Real audio capture and the remaining consultation workflow stay PLANNED.

HC-038 Speech-to-text consultation UX is MOCKED at D1 after recording consent. The clinician starts and stops a visibly simulated recording, sees deterministic transcription progress, then reviews the predefined fictional `script-a-2026-10-10` transcript from `demo-data/clinician.json`, with speaker attribution and a permanent MOCKED label. There is no microphone permission, audio capture, speech model, network call, persistence, or clinical extraction. Withdrawing consent hides and cancels the speech-to-text flow.

HC-043 Clinician alert center is MOCKED at D1 with the three canonical fictional alerts from `demo-data/clinician.json`. The center shows patient, date, source reference, and visibly demo-only priority, and lets the clinician mark an alert as examined or restore it. The pending/all filters and reviewed state are widget-local and session-only. Ordering is not clinical triage, no alert is received in real time, and no acknowledgement is persisted or sent to the Notification Service.

| Destination | Planned content |
|---|---|
| `Accueil` | Clinician dashboard, IMPLEMENTED at D1 (HC-031, see above). |
| `File` | Priority patient queue (HC-032) and its explanation (HC-044). |
| `Patients` | Authorized patient list, patient detail, and federated history (HC-033 to HC-035). |
| `Consultation` | Recording consent and speech-to-text UX are MOCKED (HC-037, HC-038); consultation workspace, real audio capture/transcription, adaptive intake, AI extraction and lab review, and medication warning remain PLANNED (HC-036, HC-039 to HC-042). |
| `Alertes` | Clinician alert center is MOCKED with canonical fixtures and session-local review state (HC-043). |

The profile sheet (app bar avatar) shows the fictional identity and states that the session is simulated: there is no authentication or authorization. The flask menu switches the current destination between content, loading, empty, and error states; navigating returns to content.

Flutter + Dart and the Android-first development path are CONFIRMED by [ADR-0004](../../../docs/decisions/ADR-0004-mobile-technology.md). The shell was generated with Flutter 3.44.6 / Dart 3.12.2; exact resolved packages are recorded in `pubspec.lock`. `flutter analyze` and `flutter test` pass, and `flutter build apk --debug` succeeded. The APK was installed and launched on an Android emulator (Pixel 8, API 34): the dashboard, a destination switch, and the profile sheet rendered with no Flutter error in the log. This is a runtime smoke test, not clinical, security, or production validation.

## Responsibilities and owned concepts

- Authorized patient lists, longitudinal views, consultation workspace, alerts, and priority presentation.
- Consent-aware speech-to-text, adaptive intake, extraction review, lab review, and medication-warning presentation.

## Communication boundaries

The Clinician App consumes authorized context through explicit APIs and never accesses hospital databases directly. Clinical AI output is advisory and subject to clinician review.

At D1 there is no HTTP client, persistence, authentication, or backend integration. Files under `lib/demo/` are presentation-only copies of the canonical fictional clinician identity, consultation, and alerts from [`demo-data/`](../../../demo-data/); tests fail if those copies drift. They are not identity, authorization, notification, or clinical domain models. Planned destinations state that they load no clinical data.

## Non-responsibilities

It does not have autonomous diagnostic or prescription authority, make Governance decisions, or treat LLM output as validated clinical truth. Any future priority display does not replace clinical judgment.

## Expected contracts

PLANNED authorization, patient-view, consultation, extraction-review, medication-safety, alert, queue, and notification contracts. Existing candidates include the Federation [patient query](../../../contracts/federation/federated-patient-query.v1.yaml) (served through HC-114 / HC-141), the [medication safety check](../../../contracts/api/medication-safety/medication-safety-check.v1.yaml), and the Notification Service's clinician alerts; the app consumes none of them.

## Structure

- `lib/app/`: Flutter composition root.
- `lib/presentation/`: Material theme, application shell, navigation, and reviewable states.
- `lib/demo/`: fictional presentation fixtures (identity, demo day, appointments, alerts, priority queue, access grants, patient names); no real patient or clinician data.
- `test/`: widget tests for navigation, demo labelling, canonical identity, UI states, the dashboard's figures, order, labels, and links, and fixture consistency with `demo-data/`.
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
