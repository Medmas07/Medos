# Patient App

## Purpose and status

HC-021 Digital restriction / erasure request is IMPLEMENTED at D1 in `Profil`: the patient submits a restriction, erasure (where legally permitted), anonymization, or optional-permission withdrawal request for one or all of Patient A's sources and follows its status. After a simulated delay it moves from `SOUMISE` to `EN ANALYSE`. Hospital/governance review and the decision stay pending, and the screen states that data needed for care or legal obligations may be retained. Requests exist only in session state and are labelled demo; nothing is sent to a Hospital Node or Governance Node, and no data is restricted or deleted.

HC-020 Delegate access to a trusted relative is IMPLEMENTED at D1 in `Accès`: a "Proches de confiance" section shows the canonical fictional delegation `deleg-a-sami` (Sami Mansouri, read-only, parcours and médicaments, no expiry), a form to delegate to a named relative with a relationship, scope, duration, and opt-in grant management, and a confirmed withdrawal. Delegations exist only in session state and are labelled demo; nothing is issued to, recorded by, or enforced on a Hospital Node, and the relative has no app view.

HC-019 Revoke physician access is IMPLEMENTED at D1 with a confirmation step and session-local status change for a fictional grant. It is a demo interaction only; it does not revoke production authorization or update Hospital Node persistence.

HC-018 Grant physician access is IMPLEMENTED at D1 with a local form for selecting a fictional physician, scope, and duration. The resulting grant exists only in session state and is visibly marked as demo behavior; it does not issue or persist production authorization.

HC-017 Consent and access management is IMPLEMENTED at D1 with local fictional grants, visible scope and expiry, and a session-only revoke interaction. It is a demo UI and does not issue, persist, or enforce production consent.

HC-016 Hospital and physician history is IMPLEMENTED at D1 with a local authorized-view list of fictional care encounters, source organizations, physicians, and specialties. It is presentation-only and does not expose hospital persistence.

HC-015 Laboratory results history is IMPLEMENTED at D1 with a local authorized-view list of fictional laboratory results, source organization, reference ranges, and explicit demo status. It is presentation-only and does not interpret results or access hospital persistence.

HC-014 Medication history is IMPLEMENTED at D1 with a local authorized-view list of fictional medications and source organizations. It is presentation-only and does not provide medication safety advice or connect to hospital persistence.

HC-012 Federated patient medical timeline is IMPLEMENTED at D1 with a local, deterministic timeline assembled from three fictional organizations. It is an authorized-view presentation demo; it does not contact Hospital Nodes or load clinical persistence.

HC-011 Patient dashboard is IMPLEMENTED at D1: the home view summarizes a fictional authorized view with source and event counts, a visible MOCKED label, and no hospital data access. It is a demo boundary, not production integration.

IMPLEMENTED at D1 for HC-010: a Flutter Android shell provides four navigable destinations (`Accueil`, `Parcours`, `Accès`, `Profil`) plus explicit content, loading, empty, and error states. It uses the fictional HC-005 Patient A identity and permanently labels demo content. Feature content beyond the shell remains PLANNED.

Flutter + Dart and the Android-first development path are CONFIRMED by [ADR-0004](../../../docs/decisions/ADR-0004-mobile-technology.md). The shell was generated with Flutter 3.44.6 / Dart 3.12.2; exact resolved packages are recorded in `pubspec.lock`.

## Responsibilities and owned concepts

- Longitudinal views across organizations, event details, medications, labs, and notifications.
- User interactions for physician access, revocation, family delegation, consent, and restriction/erasure requests.

## Communication boundaries

The Patient App consumes authorized views through explicit Federation/Hospital Node-facing API contracts. It does not directly access or own hospital databases.

At D1 there is no HTTP client, persistence, authentication, or backend integration. `lib/demo/canonical_patient.dart` is a presentation-only copy of the canonical fictional `pat-a` identity from [`demo-data/people.json`](../../../demo-data/people.json); it is not a clinical domain model. Planned screens explicitly state that they do not load or modify clinical data.

## Non-responsibilities

It is not the clinical source of record, a Governance decision maker, or a guarantee of unconditional medical-record deletion.

## Expected contracts

PLANNED patient-view, timeline, medication, consent/access-grant, request-status, and notification contracts.

Push is ready on the server side (HC-204, [ADR-0012](../../../docs/decisions/ADR-0012-mobile-push-provider.md)). The app has not implemented it yet. To receive pushes, it needs a UnifiedPush connector that registers the device's endpoint and RFC 8291 keys through [`push-subscriptions.v1.yaml`](../../../contracts/api/notifications/push-subscriptions.v1.yaml), decrypts each message, and opens the notification it names in the app. Messages never carry clinical text.

## Structure

- `lib/app/`: Flutter composition root.
- `lib/presentation/`: Material theme, application shell, navigation, and reviewable states.
- `lib/demo/`: minimal fictional presentation fixture; no real patient data.
- `test/`: widget tests for navigation, demo labelling, canonical identity, and UI states.
- `android/`: application-local Android infrastructure generated by Flutter.

## Commands

Run from `apps/mobile/patient/`:

| Purpose | Command |
|---|---|
| Resolve locked packages | `flutter pub get` |
| Analyze | `flutter analyze` |
| Test | `flutter test` |
| Run on the configured emulator | `flutter run -d emulator-5554` |
| Build a debug APK | `flutter build apk --debug` |

The emulator identifier is environment-specific; use `flutter devices` if it differs. A successful debug build or demo run is not production, privacy, security, or clinical validation.
