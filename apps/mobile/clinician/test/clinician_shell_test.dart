import 'dart:convert';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:hackcure_clinician/app/clinician_app.dart';
import 'package:hackcure_clinician/demo/canonical_alerts.dart';
import 'package:hackcure_clinician/demo/canonical_consultation.dart';
import 'package:hackcure_clinician/demo/canonical_clinician.dart';
import 'package:hackcure_clinician/demo/canonical_medication_warning.dart';
import 'package:hackcure_clinician/presentation/recording_consent_view.dart';

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
    expect(
      find.text('Priorités déterministes simulées (MOCKED)'),
      findsOneWidget,
    );

    await _tapTab(tester, 'Patients');
    expect(find.text('Patients autorisés'), findsOneWidget);
    expect(find.text('Autorisations fictives (MOCKED)'), findsOneWidget);

    await _tapTab(tester, 'Consultation');
    expect(find.text('Espace de consultation'), findsOneWidget);
    expect(find.text('Aucune consultation en cours'), findsOneWidget);

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

  testWidgets('shows canonical alerts and marks one reviewed locally', (
    tester,
  ) async {
    await tester.pumpWidget(const ClinicianApp());
    await _tapTab(tester, 'Alertes');

    expect(find.text('À examiner (3)'), findsOneWidget);
    expect(
      find.text('HbA1c au-dessus de la plage de référence'),
      findsOneWidget,
    );
    expect(find.text('Priorité haute · démo'), findsOneWidget);
    expect(find.textContaining('ne constitue pas un triage'), findsOneWidget);

    final review = find.byKey(const ValueKey('review-alert-b-hba1c'));
    await tester.drag(find.byType(ListView), const Offset(0, -300));
    await tester.pumpAndSettle();
    await tester.tap(review);
    await tester.pumpAndSettle();

    expect(find.text('À examiner (2)'), findsOneWidget);
    expect(find.text('HbA1c au-dessus de la plage de référence'), findsNothing);

    await tester.drag(find.byType(ListView), const Offset(0, 500));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Toutes'));
    await tester.pumpAndSettle();
    expect(
      find.text('HbA1c au-dessus de la plage de référence'),
      findsOneWidget,
    );
    expect(find.byKey(const ValueKey('restore-alert-b-hba1c')), findsOneWidget);
  });

  testWidgets('requires an explanation before recording consent', (
    tester,
  ) async {
    await tester.pumpWidget(const ClinicianApp());
    await _openConsultation(tester);

    final grant = find.byKey(const ValueKey('recording-consent-grant'));
    expect(tester.widget<FilledButton>(grant).onPressed, isNull);

    await _tapVisible(tester, find.byType(CheckboxListTile));
    expect(tester.widget<FilledButton>(grant).onPressed, isNotNull);

    await tester.ensureVisible(grant);
    await tester.tap(grant);
    await tester.pump();
    expect(
      find.text('Consentement consigné pour cette session'),
      findsOneWidget,
    );
    expect(find.textContaining('sans activer le microphone'), findsOneWidget);

    await _tapVisible(tester, find.text('Retirer le consentement'));
    expect(find.text('Décision requise'), findsOneWidget);
  });

  testWidgets('blocks recording when the fictional patient declines', (
    tester,
  ) async {
    await tester.pumpWidget(const ClinicianApp());
    await _openConsultation(tester);
    await _declineRecording(tester);

    expect(find.text('Enregistrement bloqué'), findsOneWidget);
    expect(find.textContaining('Aucun son n’est capturé'), findsOneWidget);
    expect(find.text('Enregistrement refusé'), findsOneWidget);
  });

  testWidgets(
    'simulates recording progress and displays the fixture transcript',
    (tester) async {
      await tester.pumpWidget(const ClinicianApp());
      await _grantRecordingConsent(tester);

      final start = find.byKey(const ValueKey('start-speech-demo'));
      await tester.ensureVisible(start);
      await tester.tap(start);
      await tester.pump();
      expect(find.text('Enregistrement simulé'), findsOneWidget);
      expect(find.textContaining('aucun son capturé'), findsOneWidget);

      final stop = find.byKey(const ValueKey('stop-speech-demo'));
      await tester.ensureVisible(stop);
      await tester.tap(stop);
      await tester.pump();
      expect(find.text('Transcription simulée en cours'), findsOneWidget);

      await tester.pump(const Duration(milliseconds: 700));
      await tester.pumpAndSettle();
      expect(find.text('Transcription simulée'), findsOneWidget);
      expect(find.text('MOCKED'), findsWidgets);
      expect(find.text(demoTranscriptSegments.first.text), findsOneWidget);
      expect(find.text(demoTranscriptSegments.last.text), findsOneWidget);
    },
  );

  testWidgets('withdrawing consent cancels and hides speech-to-text', (
    tester,
  ) async {
    await tester.pumpWidget(const ClinicianApp());
    await _grantRecordingConsent(tester);

    final start = find.byKey(const ValueKey('start-speech-demo'));
    await tester.ensureVisible(start);
    await tester.tap(start);
    await tester.pump();

    await _tapVisible(tester, find.text('Retirer le consentement'));

    expect(find.text('Décision requise'), findsOneWidget);
    expect(find.byKey(const ValueKey('stop-speech-demo')), findsNothing);
  });

  testWidgets('shows deterministic medication warning and clinician review', (
    tester,
  ) async {
    await tester.pumpWidget(const ClinicianApp());
    await _grantRecordingConsent(tester);

    final runCheck = find.byKey(const ValueKey('run-medication-check'));
    await _scrollTo(tester, runCheck);
    await tester.tap(runCheck);
    await tester.pump();
    expect(find.text('Vérification déterministe simulée'), findsOneWidget);
    expect(find.textContaining('Aucun LLM'), findsOneWidget);

    await tester.pump(const Duration(milliseconds: 650));
    await tester.pumpAndSettle();
    expect(find.text('Interaction majeure à examiner'), findsOneWidget);
    expect(find.text(demoMedicationWarning.effect), findsOneWidget);
    expect(
      find.textContaining(demoMedicationWarning.conflictingOrganizationName),
      findsOneWidget,
    );
    expect(find.textContaining('n’autorise ni ne bloque'), findsOneWidget);

    await _tapVisible(
      tester,
      find.byKey(const ValueKey('review-medication-warning')),
    );
    expect(find.text('Alerte examinée par le clinicien'), findsOneWidget);
  });

  testWidgets('declining recording opens the adaptive intake', (tester) async {
    await tester.pumpWidget(const ClinicianApp());
    await _openConsultation(tester);
    expect(find.text('Anamnèse adaptative'), findsNothing);

    await _declineRecording(tester);

    expect(find.text('Anamnèse adaptative'), findsOneWidget);
    expect(find.text('Étape 1 · Motif principal'), findsOneWidget);
    expect(find.textContaining('non validé cliniquement'), findsOneWidget);
    final next = find.byKey(const ValueKey('intake-continue'));
    expect(tester.widget<FilledButton>(next).onPressed, isNull);
    expect(find.text('Choisissez une réponse pour continuer.'), findsOneWidget);
  });

  testWidgets('branches the intake and summarizes it for review', (
    tester,
  ) async {
    await tester.pumpWidget(const ClinicianApp());
    await _openConsultation(tester);
    await _declineRecording(tester);

    await _answerIntake(tester, ['pain']);
    expect(find.text('Adapté au motif « Douleur »'), findsOneWidget);
    await _answerIntake(tester, ['knee']);
    expect(find.text('Étape 3 · Côté'), findsOneWidget);
    expect(find.text('Localisation paire : « Genou »'), findsOneWidget);
    await _answerIntake(tester, ['right']);
    await _answerIntake(tester, ['1-7d']);
    expect(find.text('Étape 5 · Sévérité'), findsOneWidget);
    await _answerIntake(tester, ['6']);
    expect(find.text('Liste adaptée à « Douleur · Genou »'), findsOneWidget);
    await _answerIntake(tester, ['swelling', 'morning-stiffness']);

    expect(find.byKey(const ValueKey('intake-summary')), findsOneWidget);
    expect(
      find.descendant(
        of: find.byKey(const ValueKey('intake-summary')),
        matching: find.text('BROUILLON'),
      ),
      findsOneWidget,
    );
    expect(find.textContaining('À relire et valider'), findsOneWidget);
    for (final answer in [
      'Douleur',
      'Genou',
      'Droit',
      '1 à 7 jours',
      '6',
      'Gonflement, Raideur matinale',
    ]) {
      expect(find.text(answer), findsOneWidget);
    }
  });

  testWidgets('editing the complaint re-branches and skips steps', (
    tester,
  ) async {
    await tester.pumpWidget(const ClinicianApp());
    await _openConsultation(tester);
    await _declineRecording(tester);
    for (final answer in [
      ['pain'],
      ['knee'],
      ['right'],
      ['1-7d'],
      ['6'],
      ['none'],
    ]) {
      await _answerIntake(tester, answer);
    }

    await _tapVisible(tester, find.byTooltip('Modifier : Motif principal'));
    await _answerIntake(tester, ['fever']);

    expect(find.text('Étape 3 · Sévérité'), findsOneWidget);
    expect(find.text('Température maximale relevée ?'), findsOneWidget);
    expect(find.text('Étapes sautées'), findsOneWidget);
    expect(
      find.text('Localisation : Sans objet pour le motif « Fièvre »'),
      findsOneWidget,
    );

    await _tapVisible(tester, find.byKey(const ValueKey('intake-back')));
    expect(find.text('Étape 2 · Durée'), findsOneWidget);
    final kept = tester.widget<FilterChip>(
      find.byKey(const ValueKey('intake-option-1-7d')),
    );
    expect(kept.selected, isTrue);
  });

  testWidgets('reviewing the recording decision discards the intake', (
    tester,
  ) async {
    await tester.pumpWidget(const ClinicianApp());
    await _openConsultation(tester);
    await _declineRecording(tester);
    await _answerIntake(tester, ['cough']);

    await _tapVisible(tester, find.text('Revoir la décision'));
    expect(find.text('Anamnèse adaptative'), findsNothing);

    await _declineRecording(tester);
    expect(find.text('Étape 1 · Motif principal'), findsOneWidget);
  });

  testWidgets('lists the demo day appointments before a consultation', (
    tester,
  ) async {
    await tester.pumpWidget(const ClinicianApp());
    await _tapTab(tester, 'Consultation');

    expect(find.text('Aucune consultation en cours'), findsOneWidget);
    expect(find.text('Rendez-vous du 10/10/2026'), findsOneWidget);
    expect(find.text('Leïla Mansouri'), findsOneWidget);
    expect(find.text('Karim Haddad'), findsOneWidget);
    expect(
      find.byKey(const ValueKey('start-consultation-appt-a-2026-10-10')),
      findsOneWidget,
    );
    expect(
      find.byKey(const ValueKey('start-consultation-appt-b-2026-10-10')),
      findsNothing,
    );
    expect(
      find.text('Aucun scénario de démonstration pour ce rendez-vous.'),
      findsOneWidget,
    );
    expect(find.text('Consentement à l’enregistrement'), findsNothing);
  });

  testWidgets('starts a consultation with its authorized context and steps', (
    tester,
  ) async {
    await tester.pumpWidget(const ClinicianApp());
    await _openConsultation(tester);

    expect(find.text('EN COURS'), findsOneWidget);
    expect(
      find.text(
        '10/10/2026 · 10:30 · Douleur du genou droit et contrôle cardiologique',
      ),
      findsOneWidget,
    );
    expect(
      find.text('Accès autorisé jusqu’au 24/10/2026 (grant-a-drx)'),
      findsOneWidget,
    );
    expect(find.text('En attente de la décision du patient'), findsOneWidget);
    expect(find.text('PLANNED · HC-040'), findsOneWidget);
    expect(find.text('Consentement à l’enregistrement'), findsOneWidget);

    final close = find.byKey(const ValueKey('close-consultation'));
    await _scrollTo(tester, close);
    expect(find.byKey(const ValueKey('draft-empty')), findsOneWidget);
    expect(tester.widget<FilledButton>(close).onPressed, isNull);
  });

  testWidgets('drafts from the transcript and closes the consultation', (
    tester,
  ) async {
    await tester.pumpWidget(const ClinicianApp());
    await _grantRecordingConsent(tester);
    await _completeTranscript(tester);

    await _scrollTo(tester, find.byKey(const ValueKey('draft-source')));
    expect(find.text('Source : transcription simulée'), findsOneWidget);
    final notes = find.byKey(const ValueKey('consultation-notes'));
    await _scrollTo(tester, notes);
    await tester.enterText(notes, 'Genou droit chaud, mobilité réduite.');
    await _tapVisible(tester, find.byKey(const ValueKey('close-consultation')));

    expect(find.text('CLÔTURÉE'), findsOneWidget);
    expect(find.text('Consultation clôturée (démonstration)'), findsOneWidget);
    expect(find.textContaining('Aucun dossier clinique'), findsOneWidget);
    expect(find.text('Genou droit chaud, mobilité réduite.'), findsOneWidget);

    await _tapVisible(tester, find.byKey(const ValueKey('new-consultation')));
    expect(find.text('Aucune consultation en cours'), findsOneWidget);
  });

  testWidgets('drafts from a completed intake when recording is refused', (
    tester,
  ) async {
    await tester.pumpWidget(const ClinicianApp());
    await _openConsultation(tester);
    await _declineRecording(tester);
    for (final answer in [
      ['fever'],
      ['lt-1d'],
      ['not-measured'],
      ['chills'],
    ]) {
      await _answerIntake(tester, answer);
    }

    await _scrollTo(tester, find.byKey(const ValueKey('draft-source')));
    expect(find.text('Source : anamnèse adaptative'), findsOneWidget);
    expect(find.text('Motif principal : Fièvre'), findsOneWidget);
    expect(find.text('Symptômes associés : Frissons'), findsOneWidget);
    final close = find.byKey(const ValueKey('close-consultation'));
    await _scrollTo(tester, close);
    expect(tester.widget<FilledButton>(close).onPressed, isNotNull);

    await _tapVisible(tester, find.text('Revoir la décision'));
    await _scrollTo(tester, close);
    expect(tester.widget<FilledButton>(close).onPressed, isNull);
  });

  testWidgets('cancelling a consultation asks for confirmation', (
    tester,
  ) async {
    await tester.pumpWidget(const ClinicianApp());
    await _openConsultation(tester);

    await _tapVisible(tester, find.text('Annuler la consultation'));
    expect(find.text('Annuler la consultation ?'), findsOneWidget);
    await tester.tap(find.text('Continuer la consultation'));
    await tester.pumpAndSettle();
    expect(find.text('EN COURS'), findsOneWidget);

    await _tapVisible(tester, find.text('Annuler la consultation'));
    await tester.tap(find.widgetWithText(FilledButton, 'Annuler'));
    await tester.pumpAndSettle();
    expect(find.text('Aucune consultation en cours'), findsOneWidget);
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

    final patient = (people['patients'] as List).firstWhere(
      (p) => p['id'] == demoConsultationPatientId,
    );
    expect(
      '${patient['firstName']} ${patient['lastName']}',
      demoConsultationPatientName,
    );

    final clinicianDemo = _readDemoData('clinician.json');
    final script = (clinicianDemo['consultationScripts'] as List).firstWhere(
      (s) => s['id'] == demoConsultationScriptId,
    );
    expect(script['appointmentId'], demoConsultationAppointmentId);
    expect(script['patientId'], demoConsultationPatientId);
    expect(script['recordingConsent'], 'accepted');
    expect(script['transcript']['mocked'], isTrue);
    final canonicalSegments = script['transcript']['segments'] as List;
    expect(canonicalSegments, hasLength(demoTranscriptSegments.length));
    for (var index = 0; index < demoTranscriptSegments.length; index += 1) {
      expect(canonicalSegments[index]['id'], demoTranscriptSegments[index].id);
      expect(
        (canonicalSegments[index]['text'] as String).replaceAll("'", '’'),
        demoTranscriptSegments[index].text,
      );
      expect(
        canonicalSegments[index]['speaker'],
        demoTranscriptSegments[index].speaker,
      );
    }

    final alerts = clinicianDemo['alerts'] as List;
    expect(alerts, hasLength(demoClinicianAlerts.length));
    for (final preview in demoClinicianAlerts) {
      final canonical = alerts.firstWhere((alert) => alert['id'] == preview.id);
      expect(canonical['patientId'], preview.patientId);
      expect(canonical['type'], preview.type);
      expect(canonical['severity'], preview.severity);
      expect(canonical['title'], preview.title);
      expect(
        (canonical['detail'] as String).replaceAll("'", '’'),
        preview.detail,
      );
      expect(canonical['sourceRecordId'], preview.sourceRecordId);
      expect(canonical['createdAt'], preview.createdAt);
      expect(canonical['status'], 'unresolved');

      final alertPatient = (people['patients'] as List).firstWhere(
        (patient) => patient['id'] == preview.patientId,
      );
      expect(
        '${alertPatient['firstName']} ${alertPatient['lastName']}',
        preview.patientName,
      );
    }

    final medicationRules = _readDemoData('medication-rules.json');
    final medications = medicationRules['medications'] as List;
    final proposed = medications.firstWhere(
      (medication) => medication['code'] == demoMedicationWarning.proposedCode,
    );
    final conflicting = medications.firstWhere(
      (medication) =>
          medication['code'] == demoMedicationWarning.conflictingCode,
    );
    expect(proposed['name'], demoMedicationWarning.proposedName);
    expect(conflicting['name'], demoMedicationWarning.conflictingName);

    final rule = (medicationRules['interactionRules'] as List).firstWhere(
      (entry) => entry['id'] == demoMedicationWarning.ruleId,
    );
    expect(rule['severity'], demoMedicationWarning.severity);
    expect(rule['effect'], demoMedicationWarning.effect);
    expect(rule['recommendation'], demoMedicationWarning.recommendation);
    expect(
      medicationRules['ruleSet']['name'],
      demoMedicationWarning.ruleSetName,
    );
    expect(
      medicationRules['ruleSet']['version'],
      demoMedicationWarning.ruleSetVersion,
    );
    expect(medicationRules['ruleSet']['validated'], isFalse);

    final checkCase = (medicationRules['checkCases'] as List).firstWhere(
      (entry) => entry['id'] == demoMedicationWarning.checkId,
    );
    expect(checkCase['patientId'], demoMedicationWarning.patientId);
    expect(
      checkCase['proposedMedicationCode'],
      demoMedicationWarning.proposedCode,
    );
    expect(
      checkCase['expectedWarnings'][0]['conflictingStatementId'],
      demoMedicationWarning.conflictingStatementId,
    );

    expect(
      script['plannedPrescription']['medicationCode'],
      demoMedicationWarning.proposedCode,
    );
    expect(
      script['plannedPrescription']['dosage'],
      demoMedicationWarning.proposedDosage,
    );

    final hospitalB = _readDemoData('records/hospital-b.json');
    final statement = (hospitalB['medications'] as List).firstWhere(
      (entry) => entry['id'] == demoMedicationWarning.conflictingStatementId,
    );
    expect(statement['medicationCode'], demoMedicationWarning.conflictingCode);
    expect(statement['dosage'], demoMedicationWarning.conflictingDosage);
    expect(statement['status'], 'active');
    expect(
      hospitalB['heldBy'],
      demoMedicationWarning.conflictingOrganizationId,
    );

    final sourceOrganization = (organizations['organizations'] as List)
        .firstWhere(
          (entry) =>
              entry['id'] == demoMedicationWarning.conflictingOrganizationId,
        );
    expect(
      sourceOrganization['name'],
      demoMedicationWarning.conflictingOrganizationName,
    );
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

/// Scrolls [finder] into view in either direction, then taps it.
Future<void> _tapVisible(WidgetTester tester, Finder finder) async {
  await _scrollTo(tester, finder);
  await tester.tap(finder);
  await tester.pumpAndSettle();
}

/// Scrolls [finder] into view in either direction.
Future<void> _scrollTo(WidgetTester tester, Finder finder) async {
  if (finder.evaluate().isNotEmpty) {
    await tester.ensureVisible(finder);
    await tester.pumpAndSettle();
  } else {
    await tester.scrollUntilVisible(
      finder.hitTestable(),
      200,
      scrollable: find.byType(Scrollable).first,
    );
  }
}

/// Opens the Consultation destination and starts Patient A's consultation.
Future<void> _openConsultation(WidgetTester tester) async {
  await _tapTab(tester, 'Consultation');
  await _tapVisible(
    tester,
    find.byKey(ValueKey('start-consultation-$demoConsultationAppointmentId')),
  );
}

Future<void> _declineRecording(WidgetTester tester) async {
  await _tapVisible(
    tester,
    find.byKey(const ValueKey('recording-consent-decline')),
  );
}

/// Selects [optionIds] on the current intake step, then continues.
Future<void> _answerIntake(WidgetTester tester, List<String> optionIds) async {
  for (final id in optionIds) {
    await _tapVisible(tester, find.byKey(ValueKey('intake-option-$id')));
  }
  await _tapVisible(tester, find.byKey(const ValueKey('intake-continue')));
}

Future<void> _grantRecordingConsent(WidgetTester tester) async {
  await _openConsultation(tester);
  await _tapVisible(tester, find.byType(CheckboxListTile));
  await _tapVisible(
    tester,
    find.byKey(const ValueKey('recording-consent-grant')),
  );
}

/// Simulates recording, then waits for the fixture transcript.
Future<void> _completeTranscript(WidgetTester tester) async {
  await _tapVisible(tester, find.byKey(const ValueKey('start-speech-demo')));
  await _scrollTo(tester, find.byKey(const ValueKey('stop-speech-demo')));
  await tester.tap(find.byKey(const ValueKey('stop-speech-demo')));
  await tester.pump(const Duration(milliseconds: 700));
  await tester.pumpAndSettle();
}
