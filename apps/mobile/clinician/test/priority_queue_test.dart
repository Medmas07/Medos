import 'dart:convert';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:hackcure_clinician/app/clinician_app.dart';
import 'package:hackcure_clinician/demo/canonical_clinician.dart';

void main() {
  testWidgets('lists the queue in rank order with priority and score', (
    tester,
  ) async {
    await _openQueue(tester);

    expect(
      find.text('Journée de démonstration du 10/10/2026 · 2 patients'),
      findsOneWidget,
    );
    final first = tester.getTopLeft(_entry('queue-clin-x-1')).dy;
    final second = tester.getTopLeft(_entry('queue-clin-x-2')).dy;
    expect(first, lessThan(second));

    _expectIn('queue-clin-x-1', 'Karim Haddad');
    _expectIn('queue-clin-x-1', 'Priorité élevée');
    _expectIn('queue-clin-x-1', 'Score de démonstration : 82');
    _expectIn('queue-clin-x-2', 'Leïla Mansouri');
    _expectIn('queue-clin-x-2', 'Priorité moyenne');
    _expectIn('queue-clin-x-2', 'Score de démonstration : 55');
  });

  testWidgets('shows each entry’s reasons and the alerts behind them', (
    tester,
  ) async {
    await _openQueue(tester);

    _expectIn('queue-clin-x-1', 'Résultat biologique anormal non revu');
    // A reason and the title of the alert it comes from.
    _expectIn('queue-clin-x-1', 'Suivi en retard', count: 2);
    _expectIn('queue-clin-x-1', 'HbA1c au-dessus de la plage de référence');
    _expectIn('queue-clin-x-1', 'Élevée');
    _expectIn('queue-clin-x-1', 'Moyenne');
    _expectIn('queue-clin-x-1', 'Accès autorisé jusqu’au 31/12/2026');

    _expectIn('queue-clin-x-2', 'Traitement anticoagulant actif');
    _expectIn('queue-clin-x-2', 'Nouvelle consultation externe', count: 2);
    _expectIn('queue-clin-x-2', 'Faible');
    _expectIn('queue-clin-x-2', 'Accès autorisé jusqu’au 24/10/2026');
  });

  testWidgets('labels the queue a deterministic mock, not triage or AI', (
    tester,
  ) async {
    await _openQueue(tester);

    expect(
      find.text('Priorités déterministes simulées (MOCKED)'),
      findsOneWidget,
    );
    expect(find.textContaining('sans IA'), findsOneWidget);
    expect(find.textContaining('pas un triage clinique'), findsOneWidget);
    expect(find.text(demoPriorityMethodDescription), findsOneWidget);
    expect(
      find.text(
        'L’explication détaillée de chaque priorité sera livrée par HC-044.',
      ),
      findsOneWidget,
    );
    expect(find.text('PLANNED'), findsOneWidget);
  });

  test('queue fixtures match demo-data and stay in authorized context', () {
    final clinician = _readDemoData('clinician.json');
    final queue = (clinician['priorityQueue'] as List)
        .cast<Map<String, dynamic>>()
        .where((e) => e['clinicianId'] == demoClinician.id)
        .toList();
    expect(queue.map((e) => e['id']), demoPriorityQueue.map((e) => e.id));

    for (final (i, entry) in demoPriorityQueue.indexed) {
      expect(queue[i]['score'], entry.score);
      expect(queue[i]['alertIds'], entry.alertIds);
      expect(
        demoActiveGrantFor(entry.patientId, demoReferenceDate),
        isNotNull,
        reason: '${entry.id} must concern a patient with an active grant',
      );
      for (final alertId in entry.alertIds) {
        expect(demoAlertById(alertId).patientId, entry.patientId);
      }
    }
    expect(
      demoPriorityQueue.map((e) => e.rank).toSet().length,
      demoPriorityQueue.length,
      reason: 'ranks must be unique',
    );
  });
}

Map<String, dynamic> _readDemoData(String name) {
  final file = File('../../../demo-data/$name');
  return jsonDecode(file.readAsStringSync()) as Map<String, dynamic>;
}

/// Opens the queue on a tall surface so every entry is built.
Future<void> _openQueue(WidgetTester tester) async {
  tester.view.physicalSize = const Size(1080, 4800);
  tester.view.devicePixelRatio = 2.0;
  addTearDown(tester.view.reset);
  await tester.pumpWidget(const ClinicianApp());
  await tester.tap(
    find.descendant(
      of: find.byType(NavigationBar),
      matching: find.text('File'),
    ),
  );
  await tester.pumpAndSettle();
}

Finder _entry(String id) => find.byKey(ValueKey('queue-entry-$id'));

void _expectIn(String entryId, String text, {int count = 1}) {
  expect(
    find.descendant(of: _entry(entryId), matching: find.text(text)),
    findsNWidgets(count),
  );
}
