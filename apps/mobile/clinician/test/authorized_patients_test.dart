import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:hackcure_clinician/app/clinician_app.dart';
import 'package:hackcure_clinician/demo/canonical_clinician.dart';
import 'package:hackcure_clinician/presentation/authorized_patients_view.dart';

const _expired = CanonicalAccessGrant(
  id: 'grant-test-expired',
  patientId: 'pat-a',
  scope: ['encounters'],
  purpose: 'Test',
  status: 'active',
  grantedAt: '2026-09-01T09:00:00+01:00',
  expiresAt: '2026-10-09T09:00:00+01:00',
);

const _revoked = CanonicalAccessGrant(
  id: 'grant-test-revoked',
  patientId: 'pat-b',
  scope: ['medications'],
  purpose: 'Test',
  status: 'revoked',
  grantedAt: '2026-09-01T09:00:00+01:00',
  expiresAt: '2026-12-01T09:00:00+01:00',
);

Future<void> _pumpView(WidgetTester tester, Widget view) async {
  tester.view.physicalSize = const Size(1080, 4800);
  tester.view.devicePixelRatio = 2.0;
  addTearDown(tester.view.reset);
  await tester.pumpWidget(
    MaterialApp(
      home: Scaffold(body: ListView(children: [view])),
    ),
  );
}

void main() {
  group('authorizedPatientsOn', () {
    test(
      'lists clin-x patients with an active grant, soonest expiry first',
      () {
        final (:authorized, :ended) = authorizedPatientsOn(
          demoAccessGrants,
          demoPatients,
          demoReferenceDate,
        );

        expect(authorized.map((e) => e.patient.id), ['pat-a', 'pat-b']);
        expect(authorized.map((e) => e.grant.id), [
          'grant-a-drx',
          'grant-b-drx',
        ]);
        expect(ended, isEmpty);
      },
    );

    test('an expired or revoked grant authorizes nothing', () {
      final (:authorized, :ended) = authorizedPatientsOn(
        [_expired, _revoked],
        demoPatients,
        demoReferenceDate,
      );

      expect(authorized, isEmpty);
      expect(ended.map((g) => g.id), [
        'grant-test-expired',
        'grant-test-revoked',
      ]);
    });

    test('a grant ends on its expiry day', () {
      expect(
        authorizedPatientsOn(
          demoAccessGrants,
          demoPatients,
          '2026-10-24',
        ).authorized.map((e) => e.patient.id),
        ['pat-b'],
      );
    });

    test('days left and ages are computed against the demo day', () {
      expect(daysLeft(demoAccessGrants[0], demoReferenceDate), 14);
      expect(daysLeft(demoAccessGrants[1], demoReferenceDate), 82);
      expect(demoPatients[0].ageOn(demoReferenceDate), 58);
      expect(demoPatients[1].ageOn(demoReferenceDate), 46);
    });
  });

  testWidgets('shows each authorized patient with purpose, scope, and term', (
    tester,
  ) async {
    await _pumpView(tester, const AuthorizedPatientsView());

    expect(
      find.text('Journée de démonstration du 10/10/2026 · 2 patients'),
      findsOneWidget,
    );
    expect(find.text('Autorisations fictives (MOCKED)'), findsOneWidget);

    final leila = find.byKey(const ValueKey('authorized-pat-a'));
    for (final text in [
      'Leïla Mansouri',
      '58 ans',
      'Accès actif',
      'Consultation de cardiologie',
      'Parcours',
      'Médicaments',
      'Laboratoires',
      'Accordé le 10/10/2026 · jusqu’au 24/10/2026 (14 jours restants)',
      'Autorisation grant-a-drx',
    ]) {
      expect(
        find.descendant(of: leila, matching: find.text(text)),
        findsOneWidget,
        reason: text,
      );
    }
    final karim = find.byKey(const ValueKey('authorized-pat-b'));
    expect(
      find.descendant(of: karim, matching: find.text('Suivi du diabète')),
      findsOneWidget,
    );
    expect(
      tester.getTopLeft(leila).dy < tester.getTopLeft(karim).dy,
      isTrue,
      reason: 'soonest expiry first',
    );

    expect(find.text('Aucun accès expiré ou révoqué.'), findsOneWidget);
    expect(find.text('Fiche patient et historique fédéré'), findsOneWidget);
  });

  testWidgets('shows an explicit empty state and ended grants', (tester) async {
    await _pumpView(
      tester,
      const AuthorizedPatientsView(grants: [_expired, _revoked]),
    );

    expect(
      find.text('Journée de démonstration du 10/10/2026 · 0 patient'),
      findsOneWidget,
    );
    expect(find.byKey(const ValueKey('authorized-empty')), findsOneWidget);
    expect(find.byKey(const ValueKey('authorized-pat-a')), findsNothing);
    expect(
      find.text('Expiré le 09/10/2026 · aucun accès au dossier'),
      findsOneWidget,
    );
    expect(
      find.text('Révoqué par le patient · aucun accès au dossier'),
      findsOneWidget,
    );
  });

  testWidgets('is the Patients destination of the shell', (tester) async {
    await tester.pumpWidget(const ClinicianApp());
    await tester.tap(find.text('Patients'));
    await tester.pumpAndSettle();

    expect(find.byType(AuthorizedPatientsView), findsOneWidget);
    expect(find.text('Leïla Mansouri'), findsOneWidget);
  });
}
