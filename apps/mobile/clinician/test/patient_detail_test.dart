import 'dart:convert';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:hackcure_clinician/app/clinician_app.dart';
import 'package:hackcure_clinician/demo/canonical_clinician.dart';
import 'package:hackcure_clinician/presentation/clinician_theme.dart';
import 'package:hackcure_clinician/presentation/patient_detail_screen.dart';

void main() {
  testWidgets('opens Patient A from the dashboard appointment', (tester) async {
    await _pumpTall(tester, const ClinicianApp());

    await tester.tap(
      find.text('Douleur du genou droit et contrôle cardiologique'),
    );
    await tester.pumpAndSettle();

    expect(find.text('Fiche patient'), findsOneWidget);
    expect(find.text('DÉMO D1 · Données entièrement fictives'), findsOneWidget);
    expect(find.text('Leïla Mansouri'), findsOneWidget);
    expect(find.text('Femme · 58 ans · Tunis'), findsOneWidget);
    expect(find.text('Identifiant fédéré FED-PAT-0001'), findsOneWidget);

    expect(find.text('Consultation de cardiologie'), findsOneWidget);
    expect(
      find.text('Accordé le 10/10/2026 · jusqu’au 24/10/2026'),
      findsOneWidget,
    );
    expect(find.text('Parcours'), findsOneWidget);
    expect(find.text('Médicaments'), findsOneWidget);
    expect(find.text('Laboratoires'), findsOneWidget);

    expect(
      find.text('10:30 · Douleur du genou droit et contrôle cardiologique'),
      findsOneWidget,
    );
    expect(find.text('Rang 2'), findsOneWidget);
    expect(find.text('Priorité moyenne'), findsOneWidget);
    expect(find.text('Nouvelle consultation externe'), findsOneWidget);
    expect(find.byKey(const ValueKey('detail-open-history')), findsOneWidget);
    expect(find.text('PLANNED'), findsNothing);

    await tester.pageBack();
    await tester.pumpAndSettle();
    expect(find.text('Bonjour Dr Gharbi'), findsOneWidget);
  });

  testWidgets('opens Patient B from the priority queue', (tester) async {
    await _pumpTall(tester, const ClinicianApp());
    await tester.tap(
      find.descendant(
        of: find.byType(NavigationBar),
        matching: find.text('File'),
      ),
    );
    await tester.pumpAndSettle();

    await tester.tap(find.text('Ouvrir la fiche').first);
    await tester.pumpAndSettle();

    expect(find.text('Karim Haddad'), findsOneWidget);
    // Born 2 November 1979: not yet 47 on the demo day.
    expect(find.text('Homme · 46 ans · Ariana'), findsOneWidget);
    expect(find.text('Suivi du diabète'), findsOneWidget);
    expect(
      find.text('Accordé le 15/09/2025 · jusqu’au 31/12/2026'),
      findsOneWidget,
    );
    expect(
      find.text('11:30 · Restitution du bilan de suivi du diabète'),
      findsOneWidget,
    );
    expect(find.text('Rang 1'), findsOneWidget);
    expect(
      find.text('HbA1c au-dessus de la plage de référence'),
      findsOneWidget,
    );
    expect(find.text('Suivi en retard'), findsOneWidget);
    expect(
      find.text(
        'Priorité déterministe simulée (MOCKED), pas un triage clinique.',
      ),
      findsOneWidget,
    );
  });

  testWidgets('opens a patient from the authorized patient list', (
    tester,
  ) async {
    await _pumpTall(tester, const ClinicianApp());
    await tester.tap(
      find.descendant(
        of: find.byType(NavigationBar),
        matching: find.text('Patients'),
      ),
    );
    await tester.pumpAndSettle();

    await tester.tap(
      find.descendant(
        of: find.byKey(const ValueKey('authorized-pat-a')),
        matching: find.text('Ouvrir la fiche'),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('Fiche patient'), findsOneWidget);
    expect(find.text('Femme · 58 ans · Tunis'), findsOneWidget);
  });

  testWidgets('shows nothing about a patient without an active grant', (
    tester,
  ) async {
    // pat-c (Nour Jaziri) has granted clin-x no access.
    await _pumpTall(
      tester,
      MaterialApp(
        theme: ClinicianTheme.light(),
        home: const PatientDetailScreen(patientId: 'pat-c'),
      ),
    );

    expect(find.text('Accès non autorisé'), findsOneWidget);
    expect(find.textContaining('Nour'), findsNothing);
    expect(find.textContaining('Jaziri'), findsNothing);
    expect(find.text('Accès autorisé'), findsNothing);
    expect(find.text('Alertes non résolues'), findsNothing);
  });

  test('patient and grant fixtures match the canonical HC-005 data', () {
    final people = _readDemoData('people.json');
    final access = _readDemoData('access.json');

    final patients = (people['patients'] as List).cast<Map<String, dynamic>>();
    for (final patient in demoPatients) {
      final canonical = patients.firstWhere((p) => p['id'] == patient.id);
      expect(canonical['federatedId'], patient.federatedId);
      expect(canonical['firstName'], patient.firstName);
      expect(canonical['lastName'], patient.lastName);
      expect(canonical['sex'], patient.sex);
      expect(canonical['birthDate'], patient.birthDate);
      expect(canonical['city'], patient.city);
    }

    final grants = (access['accessGrants'] as List)
        .cast<Map<String, dynamic>>();
    for (final grant in demoAccessGrants) {
      final canonical = grants.firstWhere((g) => g['id'] == grant.id);
      expect(canonical['granteeId'], demoClinician.id);
      expect(canonical['scope'], grant.scope);
      expect(canonical['purpose'], grant.purpose);
      expect(canonical['grantedAt'], grant.grantedAt);
    }
    expect(
      grants.where(
        (g) => g['patientId'] == 'pat-c' && g['granteeId'] == demoClinician.id,
      ),
      isEmpty,
      reason: 'the no-access test relies on pat-c having no grant to clin-x',
    );
  });
}

Map<String, dynamic> _readDemoData(String name) {
  final file = File('../../../demo-data/$name');
  return jsonDecode(file.readAsStringSync()) as Map<String, dynamic>;
}

/// Renders on a tall surface so whole pages are built.
Future<void> _pumpTall(WidgetTester tester, Widget app) async {
  tester.view.physicalSize = const Size(1080, 4800);
  tester.view.devicePixelRatio = 2.0;
  addTearDown(tester.view.reset);
  await tester.pumpWidget(app);
}
