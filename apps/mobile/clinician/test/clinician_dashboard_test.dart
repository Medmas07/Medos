import 'dart:convert';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:hackcure_clinician/app/clinician_app.dart';
import 'package:hackcure_clinician/demo/canonical_clinician.dart';

void main() {
  testWidgets('summarizes the authorized context of the demo day', (
    tester,
  ) async {
    await _pumpTallApp(tester);

    expect(find.text('Journée de démonstration du 10/10/2026'), findsOneWidget);
    _expectMetric('metric-appointments', '2', 'rendez-vous aujourd’hui');
    _expectMetric('metric-patients', '2', 'patients autorisés');
    _expectMetric('metric-alerts', '3', 'alertes non résolues');
    _expectMetric('metric-queue', '2', 'patients dans la file');
  });

  testWidgets('lists the day’s appointments in time order', (tester) async {
    await _pumpTallApp(tester);

    final first = tester.getTopLeft(find.text('10:30')).dy;
    final second = tester.getTopLeft(find.text('11:30')).dy;
    expect(first, lessThan(second));
    expect(
      find.text('Douleur du genou droit et contrôle cardiologique'),
      findsOneWidget,
    );
    expect(
      find.text('Restitution du bilan de suivi du diabète'),
      findsOneWidget,
    );
    expect(find.text('Programmé'), findsNWidgets(2));
  });

  testWidgets('orders alerts by severity and labels them advisory', (
    tester,
  ) async {
    await _pumpTallApp(tester);

    final high = tester
        .getTopLeft(find.text('HbA1c au-dessus de la plage de référence'))
        .dy;
    final medium = tester.getTopLeft(find.text('Suivi en retard')).dy;
    final low = tester
        .getTopLeft(find.text('Nouvelle consultation externe'))
        .dy;
    expect(high, lessThan(medium));
    expect(medium, lessThan(low));
    expect(find.text('Élevée'), findsOneWidget);
    expect(find.text('Moyenne'), findsOneWidget);
    expect(find.text('Faible'), findsOneWidget);
    expect(find.text('Karim Haddad · 30/09/2026'), findsOneWidget);
    expect(
      find.textContaining('ne remplacent pas le jugement clinique'),
      findsOneWidget,
    );
  });

  testWidgets('shows the queue as a deterministic mock, not triage', (
    tester,
  ) async {
    await _pumpTallApp(tester);

    expect(find.text('Priorité élevée'), findsOneWidget);
    expect(find.text('Priorité moyenne'), findsOneWidget);
    expect(
      find.text('Résultat biologique anormal non revu · Suivi en retard'),
      findsOneWidget,
    );
    expect(
      find.textContaining('Priorités déterministes simulées (MOCKED)'),
      findsOneWidget,
    );
    expect(find.textContaining('pas un triage clinique'), findsOneWidget);
  });

  testWidgets('metrics and section links open their destination', (
    tester,
  ) async {
    await _pumpTallApp(tester);

    await tester.tap(find.byKey(const ValueKey('metric-alerts')));
    await tester.pumpAndSettle();
    expect(find.text('Mes alertes'), findsOneWidget);
    expect(_selectedTab(tester), 4);

    await tester.tap(
      find.descendant(
        of: find.byType(NavigationBar),
        matching: find.text('Accueil'),
      ),
    );
    await tester.pumpAndSettle();
    await tester.tap(find.bySemanticsLabel('Voir : File de priorité'));
    await tester.pumpAndSettle();
    expect(find.text('File patients'), findsOneWidget);
    expect(_selectedTab(tester), 1);
  });

  test('the dashboard fixtures match the canonical HC-005 data', () {
    final manifest = _readDemoData('manifest.json');
    final clinician = _readDemoData('clinician.json');
    final access = _readDemoData('access.json');
    final people = _readDemoData('people.json');
    expect(clinician['fictional'], isTrue);
    expect(manifest['referenceDate'], demoReferenceDate);
    expect(
      clinician['priorityMethod']['description'],
      demoPriorityMethodDescription,
    );

    List<Map<String, dynamic>> ofClinician(List<dynamic> items, String key) =>
        items
            .cast<Map<String, dynamic>>()
            .where((item) => item[key] == demoClinician.id)
            .toList();

    final appointments = ofClinician(clinician['appointments'], 'clinicianId');
    expect(appointments.map((a) => a['id']), demoAppointments.map((a) => a.id));
    for (final (i, a) in demoAppointments.indexed) {
      expect(appointments[i]['patientId'], a.patientId);
      expect(appointments[i]['scheduledAt'], a.scheduledAt);
      expect(appointments[i]['reason'], a.reason);
      expect(appointments[i]['status'], a.status);
    }

    final alerts = ofClinician(clinician['alerts'], 'clinicianId');
    expect(alerts.map((a) => a['id']), demoAlerts.map((a) => a.id));
    for (final (i, a) in demoAlerts.indexed) {
      expect(alerts[i]['patientId'], a.patientId);
      expect(alerts[i]['severity'], a.severity);
      expect(alerts[i]['title'], a.title);
      expect(alerts[i]['createdAt'], a.createdAt);
      expect(alerts[i]['status'], a.status);
    }

    final queue = ofClinician(clinician['priorityQueue'], 'clinicianId');
    expect(queue.map((e) => e['id']), demoPriorityQueue.map((e) => e.id));
    for (final (i, e) in demoPriorityQueue.indexed) {
      expect(queue[i]['patientId'], e.patientId);
      expect(queue[i]['rank'], e.rank);
      expect(queue[i]['priority'], e.priority);
      expect(queue[i]['reasons'], e.reasons);
    }

    final grants = ofClinician(access['accessGrants'], 'granteeId');
    expect(grants.map((g) => g['id']), demoAccessGrants.map((g) => g.id));
    for (final (i, g) in demoAccessGrants.indexed) {
      expect(grants[i]['patientId'], g.patientId);
      expect(grants[i]['status'], g.status);
      expect(grants[i]['expiresAt'], g.expiresAt);
    }

    final patients = (people['patients'] as List).cast<Map<String, dynamic>>();
    for (final patient in demoPatients) {
      final canonical = patients.firstWhere((p) => p['id'] == patient.id);
      expect(canonical['firstName'], patient.firstName);
      expect(canonical['lastName'], patient.lastName);
    }
  });
}

Map<String, dynamic> _readDemoData(String name) {
  final file = File('../../../demo-data/$name');
  return jsonDecode(file.readAsStringSync()) as Map<String, dynamic>;
}

/// Renders the app on a tall surface so the whole dashboard is built.
Future<void> _pumpTallApp(WidgetTester tester) async {
  tester.view.physicalSize = const Size(1080, 4800);
  tester.view.devicePixelRatio = 2.0;
  addTearDown(tester.view.reset);
  await tester.pumpWidget(const ClinicianApp());
}

void _expectMetric(String key, String value, String label) {
  final metric = find.byKey(ValueKey(key));
  expect(
    find.descendant(of: metric, matching: find.text(value)),
    findsOneWidget,
  );
  expect(
    find.descendant(of: metric, matching: find.text(label)),
    findsOneWidget,
  );
}

int _selectedTab(WidgetTester tester) =>
    tester.widget<NavigationBar>(find.byType(NavigationBar)).selectedIndex;
