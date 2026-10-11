import 'dart:convert';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:hackcure_clinician/app/clinician_app.dart';
import 'package:hackcure_clinician/demo/canonical_clinician.dart';
import 'package:hackcure_clinician/demo/canonical_federated_history.dart';
import 'package:hackcure_clinician/presentation/federated_history_view.dart';

final _grantA = demoAccessGrants.firstWhere((g) => g.id == 'grant-a-drx');
final _grantB = demoAccessGrants.firstWhere((g) => g.id == 'grant-b-drx');

Map<String, dynamic> _readDemoData(String name) {
  final file = File('../../../demo-data/$name');
  return jsonDecode(file.readAsStringSync()) as Map<String, dynamic>;
}

List<Map<String, dynamic>> _list(Map<String, dynamic> data, String key) =>
    (data[key] as List).cast<Map<String, dynamic>>();

void _useTallSurface(WidgetTester tester) {
  tester.view.physicalSize = const Size(1080, 6000);
  tester.view.devicePixelRatio = 2.0;
  addTearDown(tester.view.reset);
}

Future<void> _chooseScenario(WidgetTester tester, String label) async {
  await tester.tap(find.byTooltip('Choisir un scénario de démonstration'));
  await tester.pumpAndSettle();
  await tester.tap(find.text(label).last);
  await tester.pumpAndSettle();
}

void main() {
  group('federatedHistoryFor', () {
    test('every node answers: Patient A history from three sources', () {
      final history = federatedHistoryFor(_grantA, FederationScenario.complete);

      expect(history.completeness, 'complete');
      expect(
        {
          for (final n in history.nodeResults)
            n.nodeRef: (n.status, n.entryCount),
        },
        {
          'node-hospital-a': ('ok', 2),
          'node-hospital-b': ('ok', 3),
          'node-private-practice': ('ok', 2),
        },
      );
      expect(history.entries.map((e) => e.entryRef), [
        'lab-b-2026-leila',
        'enc-b-2026-leila',
        'med-b-leila-coagulix',
        'enc-pp-2025-leila',
        'med-pp-leila-tensiorel',
        'lab-a-2024-leila',
        'enc-a-2024-leila-er',
      ]);
    });

    test('an unreachable node makes the result partial and adds nothing', () {
      final history = federatedHistoryFor(_grantA, FederationScenario.partial);

      expect(history.completeness, 'partial');
      final practice = history.nodeResults.firstWhere(
        (n) => n.nodeRef == 'node-private-practice',
      );
      expect(practice.status, 'unavailable');
      expect(practice.entryCount, 0);
      expect(practice.problemCode, 'node_unavailable');
      expect(history.entries, hasLength(5));
      expect(
        history.entries.where(
          (e) => e.organizationRef == 'org-private-practice',
        ),
        isEmpty,
      );
    });

    test('an unavailable Federation answers nothing', () {
      expect(
        () => federatedHistoryFor(_grantA, FederationScenario.unavailable),
        throwsA(isA<FederationUnavailable>()),
      );
    });

    test('only entries inside the grant scope are disclosed', () {
      const medicationsOnly = CanonicalAccessGrant(
        id: 'grant-test',
        patientId: 'pat-a',
        scope: ['medications'],
        purpose: 'Test',
        status: 'active',
        grantedAt: '2026-10-10T09:00:00+01:00',
        expiresAt: '2026-10-24T09:00:00+01:00',
      );
      final history = federatedHistoryFor(
        medicationsOnly,
        FederationScenario.complete,
      );

      expect(history.entries.map((e) => e.recordType).toSet(), {'medication'});
      expect(history.entries.map((e) => e.title), ['Coagulix', 'Tensiorel']);
    });

    test('Patient B: every node answers, only Hospital A holds records', () {
      final history = federatedHistoryFor(_grantB, FederationScenario.complete);

      expect(history.completeness, 'complete');
      expect(history.nodeResults.map((n) => n.entryCount), [4, 0, 0]);
      expect(history.entries.every((e) => e.patientId == 'pat-b'), isTrue);
    });
  });

  test('the federated history fixture matches the canonical HC-005 data', () {
    final organizations = {
      for (final o in _list(
        _readDemoData('organizations.json'),
        'organizations',
      ))
        o['id'] as String: o,
    };
    final people = _readDemoData('people.json');
    final clinicians = {
      for (final c in _list(people, 'clinicians'))
        c['id'] as String:
            '${c['title'] ?? ''} ${c['firstName']} ${c['lastName']}'.trim(),
    };
    final medicines = {
      for (final m in _list(
        _readDemoData('medication-rules.json'),
        'medications',
      ))
        m['code'] as String: m['name'] as String,
    };

    for (final MapEntry(:key, :value) in demoOrganizationNames.entries) {
      expect(organizations[key]!['name'], value);
    }
    for (final node in demoFederationNodes) {
      expect(organizations[node.organizationRef]!['node']['id'], node.nodeRef);
    }
    for (final MapEntry(:key, :value) in demoClinicianNames.entries) {
      expect(clinicians[key], value);
    }

    // Every record of clin-x's patients, and nothing else, with its source.
    final expected = <String, (String, String, String, String, String?)>{};
    for (final name in [
      'records/hospital-a.json',
      'records/hospital-b.json',
      'records/private-practice.json',
    ]) {
      final file = _readDemoData(name);
      final holder = file['heldBy'] as String;
      bool ofPatients(Map<String, dynamic> r) =>
          demoPatients.any((p) => p.id == r['patientId']);
      for (final e in _list(file, 'encounters').where(ofPatients)) {
        expect(e['startedAt'], isNotNull);
        expected[e['id']] = (
          e['patientId'],
          'encounter',
          holder,
          e['title'],
          e['clinicianId'],
        );
      }
      for (final m in _list(file, 'medications').where(ofPatients)) {
        expected[m['id']] = (
          m['patientId'],
          'medication',
          holder,
          medicines[m['medicationCode']]!,
          m['prescribedById'],
        );
      }
      for (final l in _list(file, 'labReports').where(ofPatients)) {
        expected[l['id']] = (
          l['patientId'],
          'lab_report',
          holder,
          l['title'],
          null,
        );
      }
    }

    expect({
      for (final e in demoFederatedEntries)
        e.entryRef: (
          e.patientId,
          e.recordType,
          e.organizationRef,
          e.title,
          e.clinicianRef,
        ),
    }, expected);
    for (final e in demoFederatedEntries) {
      final node = demoFederationNodes.firstWhere(
        (n) => n.organizationRef == e.organizationRef,
      );
      expect(e.nodeRef, node.nodeRef);
    }
  });

  testWidgets('opens Patient A history from the authorized patient list', (
    tester,
  ) async {
    _useTallSurface(tester);
    await tester.pumpWidget(const ClinicianApp());
    await tester.tap(find.text('Patients'));
    await tester.pumpAndSettle();

    await tester.tap(find.byKey(const ValueKey('open-history-pat-a')));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300));
    expect(find.byKey(const ValueKey('history-loading')), findsOneWidget);
    await tester.pumpAndSettle();

    expect(find.text('Historique fédéré'), findsOneWidget);
    expect(find.text('Réponse fédérée simulée (MOCKED)'), findsOneWidget);
    expect(find.byKey(const ValueKey('completeness-complete')), findsOneWidget);
    expect(
      find.byKey(const ValueKey('source-node-hospital-b')),
      findsOneWidget,
    );
    expect(find.text('A répondu · 3 entrées'), findsOneWidget);

    final coagulix = find.byKey(const ValueKey('entry-med-b-leila-coagulix'));
    expect(
      find.descendant(
        of: coagulix,
        matching: find.text(
          'Source : Hôpital Régional Oued Zitoun · Dr Inès Chaabane',
        ),
      ),
      findsOneWidget,
    );
    expect(
      find.byKey(const ValueKey('entry-enc-a-2024-leila-er')),
      findsOneWidget,
    );
  });

  testWidgets('opens the history from the patient detail too', (tester) async {
    _useTallSurface(tester);
    await tester.pumpWidget(const ClinicianApp());
    await tester.tap(find.text('Patients'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Ouvrir la fiche').first);
    await tester.pumpAndSettle();

    await tester.tap(find.byKey(const ValueKey('detail-open-history')));
    await tester.pumpAndSettle();

    expect(find.text('Réponse fédérée simulée (MOCKED)'), findsOneWidget);
    expect(find.byKey(const ValueKey('completeness-complete')), findsOneWidget);
  });

  testWidgets('shows partial and unavailable answers explicitly', (
    tester,
  ) async {
    _useTallSurface(tester);
    final patient = demoPatients.firstWhere((p) => p.id == 'pat-a');
    await tester.pumpWidget(
      MaterialApp(
        home: FederatedHistoryView(
          patient: patient,
          grant: _grantA,
          loadingDelay: Duration.zero,
        ),
      ),
    );
    await tester.pumpAndSettle();

    await _chooseScenario(tester, 'Scénario : une source injoignable');
    expect(find.byKey(const ValueKey('completeness-partial')), findsOneWidget);
    expect(
      find.text('Injoignable (node_unavailable) · aucune entrée reçue'),
      findsOneWidget,
    );
    expect(find.byKey(const ValueKey('entry-enc-pp-2025-leila')), findsNothing);
    expect(
      find.byKey(const ValueKey('entry-med-b-leila-coagulix')),
      findsOneWidget,
    );

    await _chooseScenario(tester, 'Scénario : Federation indisponible');
    expect(find.byKey(const ValueKey('history-error')), findsOneWidget);
    expect(
      find.byKey(const ValueKey('entry-med-b-leila-coagulix')),
      findsNothing,
    );

    await tester.tap(find.text('Réessayer'));
    await tester.pumpAndSettle();
    expect(find.byKey(const ValueKey('completeness-complete')), findsOneWidget);
  });

  testWidgets('an empty answer is not presented as an empty history', (
    tester,
  ) async {
    _useTallSurface(tester);
    final patient = demoPatients.firstWhere((p) => p.id == 'pat-a');
    await tester.pumpWidget(
      MaterialApp(
        home: FederatedHistoryView(
          patient: patient,
          grant: _grantA,
          entries: const [],
          loadingDelay: Duration.zero,
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.byKey(const ValueKey('history-empty')), findsOneWidget);
    expect(find.byKey(const ValueKey('completeness-complete')), findsOneWidget);
  });
}
