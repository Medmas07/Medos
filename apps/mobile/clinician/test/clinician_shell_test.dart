import 'dart:convert';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:hackcure_clinician/app/clinician_app.dart';
import 'package:hackcure_clinician/demo/canonical_clinician.dart';

void main() {
  testWidgets('shows the D1 demo boundary and canonical fictional clinician', (
    tester,
  ) async {
    await tester.pumpWidget(const ClinicianApp());

    expect(find.text('DÉMO D1 · Données entièrement fictives'), findsOneWidget);
    expect(find.text('Bonjour Dr Gharbi'), findsOneWidget);
    expect(
      find.text('Cardiologie · Hôpital Universitaire Bab Ennour'),
      findsOneWidget,
    );
    expect(
      find.textContaining('ne se connecte à aucune base hospitalière'),
      findsOneWidget,
    );

    await tester.tap(find.byTooltip('Profil du clinicien'));
    await tester.pumpAndSettle();

    expect(find.text('Dr Youssef Gharbi'), findsOneWidget);
    expect(find.text('Médecin · Cardiologie'), findsOneWidget);
    expect(find.text('Identité fictive HC-005'), findsOneWidget);
    expect(
      find.text(
        'Session simulée : aucune authentification ni autorisation réelle.',
      ),
      findsOneWidget,
    );
  });

  testWidgets('navigates between the five shell destinations', (tester) async {
    await tester.pumpWidget(const ClinicianApp());

    await _tapTab(tester, 'File');
    expect(find.text('File de priorité'), findsOneWidget);
    expect(find.text('PLANNED'), findsOneWidget);

    await _tapTab(tester, 'Patients');
    expect(find.text('Patients autorisés'), findsOneWidget);
    expect(find.text('PLANNED'), findsOneWidget);

    await _tapTab(tester, 'Consultation');
    expect(find.text('Espace de consultation'), findsOneWidget);
    expect(find.textContaining('brouillon à valider'), findsOneWidget);

    await _tapTab(tester, 'Alertes');
    expect(find.text('Centre d’alertes'), findsOneWidget);

    await _tapTab(tester, 'Accueil');
    expect(find.text('Bonjour Dr Gharbi'), findsOneWidget);
    expect(find.text('PLANNED'), findsNothing);
  });

  testWidgets('exposes loading, empty, error, and retry states', (
    tester,
  ) async {
    await tester.pumpWidget(const ClinicianApp());

    await _selectDemoState(tester, 'État : chargement');
    expect(find.byType(CircularProgressIndicator), findsOneWidget);
    expect(
      find.text('Chargement du contexte patient autorisé'),
      findsOneWidget,
    );

    await _selectDemoState(tester, 'État : vide');
    expect(find.text('Aucun contexte patient autorisé'), findsOneWidget);

    await _selectDemoState(tester, 'État : erreur');
    expect(find.text('Contexte temporairement indisponible'), findsOneWidget);
    await tester.tap(find.text('Réessayer'));
    await tester.pumpAndSettle();
    expect(find.text('Bonjour Dr Gharbi'), findsOneWidget);
  });

  testWidgets('navigating resets the demo state to content', (tester) async {
    await tester.pumpWidget(const ClinicianApp());

    await _selectDemoState(tester, 'État : erreur');
    await _tapTab(tester, 'Alertes');

    expect(find.text('Contexte temporairement indisponible'), findsNothing);
    expect(find.text('Centre d’alertes'), findsOneWidget);
  });

  test('the presentation fixture matches the canonical HC-005 data', () {
    final people = _readDemoData('people.json');
    final organizations = _readDemoData('organizations.json');
    expect(people['fictional'], isTrue);

    final clinician = (people['clinicians'] as List).firstWhere(
      (c) => c['id'] == demoClinician.id,
    );
    expect(clinician['title'], demoClinician.title);
    expect(clinician['firstName'], demoClinician.firstName);
    expect(clinician['lastName'], demoClinician.lastName);
    expect(clinician['role'], 'physician');
    expect(clinician['specialty'], demoClinician.specialty);
    expect(clinician['organizationId'], demoClinician.organizationId);

    final organization = (organizations['organizations'] as List).firstWhere(
      (o) => o['id'] == demoClinician.organizationId,
    );
    expect(organization['name'], demoClinician.organizationName);
  });
}

Map<String, dynamic> _readDemoData(String name) {
  final file = File('../../../demo-data/$name');
  return jsonDecode(file.readAsStringSync()) as Map<String, dynamic>;
}

Future<void> _tapTab(WidgetTester tester, String label) async {
  await tester.tap(
    find.descendant(of: find.byType(NavigationBar), matching: find.text(label)),
  );
  await tester.pumpAndSettle();
}

Future<void> _selectDemoState(WidgetTester tester, String label) async {
  await tester.tap(find.byTooltip('Choisir un état de démonstration'));
  await tester.pump();
  await tester.pump(const Duration(milliseconds: 250));
  await tester.tap(find.text(label));
  await tester.pump();
  await tester.pump(const Duration(milliseconds: 250));
}
