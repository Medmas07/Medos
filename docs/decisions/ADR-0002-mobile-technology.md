# ADR-0002: Mobile technology for Patient App and Clinician App

## Status

Accepted — 2026-10-10, through HC-002 ([#25](https://github.com/Medmas07/Hackcure_hackathon/issues/25)).

## Context

The repository plans two mobile products: the [Patient App](../../apps/mobile/patient/README.md) and the [Clinician App](../../apps/mobile/clinician/README.md). Both are documentation-only boundaries. HC-010 and HC-030 require a mobile technology choice and an Android development path before either application is initialized.

The decision must fit these constraints:

- deliver two reviewable mobile experiences during a two-day hackathon;
- target Android first without closing an eventual iOS path;
- use the team's available Flutter development skills;
- keep each product independently owned and deployable;
- preserve Clean / Hexagonal boundaries around future domain and application logic;
- access clinical information only through explicit authorized contracts, never through hospital persistence;
- add no framework, dependency, generated native project, or product behavior in this D0 decision ticket.

## Decision

Patient App and Clinician App will use **Flutter with Dart**.

| Concern | Choice |
|---|---|
| Mobile UI/runtime | Flutter stable channel |
| Language | Dart with sound null safety and analyzer rules |
| Project model | One independent Flutter project per product |
| Product locations | `apps/mobile/patient/` and `apps/mobile/clinician/` |
| Initial target | Android |
| Package manager | Dart pub through the Flutter CLI |
| Initial build path | Local Android toolchain; no hosted build service required |

The two products may share an ecosystem and conventions, but they do not import from each other. Reusable code is extracted into a justified Dart package under `packages/` only after a concrete repeated need exists; this ADR does not create a generic shared layer.

Widgets, navigation, plugins, storage, networking, notifications, and device APIs belong at delivery or adapter boundaries. Future domain rules and application use cases must remain plain Dart and must not depend on Flutter widgets, plugins, operating-system APIs, persistence, or transport details. The applications consume explicit API contracts and never connect directly to a Hospital Node database or DMI/HIS.

### Android development path

HC-010 and HC-030 will each initialize its own Flutter project in the existing product directory while preserving its README. The implementation ticket must record the Flutter SDK version used and commit the generated dependency lockfile.

The path is:

1. Install the Flutter SDK stable channel and add its `bin` directory to `PATH`.
2. Install Android Studio, the Android SDK and command-line tools; accept the required SDK licenses.
3. Validate the toolchain with `flutter doctor` and confirm an emulator or authorized physical device with `flutter devices`.
4. Initialize each product with Android support in its existing directory; no root-level Flutter or Android project is created.
5. Fetch locked dependencies with `flutter pub get`, run on the selected device with `flutter run`, then validate with `flutter analyze` and `flutter test`.
6. Before review of an implemented shell, build the Android artifact with `flutter build apk` and perform a runtime smoke test on an emulator or authorized physical device.

Generated `android/` files are application-local infrastructure. Platform channels and platform-specific plugins are adapters and must not leak into domain or application logic. iOS remains possible through Flutter, but local iOS compilation requires macOS and Xcode and is outside the Android-first D0 outcome.

The presence of a successful Flutter build does not validate security, privacy, clinical behavior, or production readiness. Signing, distribution, and store delivery require separate decisions and evidence.

### D0 demonstration

The reviewable D0 outcome is this ADR and the aligned component/architecture documentation. There is no UI or API behavior, so loading, empty, error, and status states are not applicable yet. No patient fixture—real or fictional—is introduced by this issue.

## Alternatives considered

- **React Native with Expo and TypeScript:** offers fast setup, a strong ecosystem, and skill reuse with the web portals. Rejected because the team has stronger, immediately available Flutter skills, which lowers delivery risk for the two-day hackathon.
- **React Native without a framework:** provides direct native-project control, but requires more assembly of common mobile concerns and does not benefit from the team's stated Flutter experience.
- **Kotlin Multiplatform with Compose Multiplatform:** stable Android and iOS targets and flexible code sharing make it credible for a native-focused product. Rejected for this initial delivery because the Gradle, platform-source-set, and iOS/Xcode toolchain adds more setup than the Android-first demo requires.
- **Separate native Kotlin and Swift applications:** maximizes platform-specific control. Rejected because it duplicates implementation and specialist knowledge across two products and two platforms before any requirement justifies that cost.

## Consequences

### Positive

- The choice uses development skills already available to the team.
- A single Flutter/Dart toolchain supports both mobile products and preserves a future iOS path.
- Android development, static analysis, tests, and builds use one CLI.
- Patient and Clinician products keep separate ownership and release boundaries.
- Local Android builds do not depend on a paid or hosted build service.

### Negative

- Flutter introduces Dart and a separate SDK from the TypeScript web stack.
- Each application initially has its own generated platform projects and dependency tree.
- Native plugins and Flutter/Android version compatibility must be checked and pinned per application.
- Some capabilities may require application-local Kotlin code or platform channels.
- iOS builds cannot be validated locally from Windows and require later macOS/Xcode access.

## Follow-up

- HC-010: initialize and demonstrate the Patient App Flutter shell on Android using this decision.
- HC-030: initialize and demonstrate the Clinician App Flutter shell on Android using this decision.
- Routing, state management, HTTP client, persistence, authentication, secure storage, notification providers, API contracts, signing, distribution, and store release remain undecided until a ticket requires them.
- The first feature using a native plugin must document its adapter boundary and test strategy.
- Production security, privacy, clinical validation, and deployment require separate implementation and evidence.

## Sources

- [Flutter: Install Flutter](https://docs.flutter.dev/install)
- [Flutter: Set up Android development](https://docs.flutter.dev/platform-integration/android/setup)
- [Flutter command-line reference](https://docs.flutter.dev/reference/flutter-cli)
- [Kotlin Multiplatform: supported-platform stability](https://kotlinlang.org/docs/multiplatform/supported-platforms.html)
- [Compose Multiplatform: create an application](https://kotlinlang.org/docs/multiplatform/compose-multiplatform-getting-started.html)
