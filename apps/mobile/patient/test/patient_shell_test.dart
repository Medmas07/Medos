import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:hackcure_patient/app/patient_app.dart';

void main() {
  testWidgets('shows the D1 demo boundary and canonical fictional patient', (
    tester,
  ) async {
    await tester.pumpWidget(const PatientApp());

    expect(find.text('DÉMO D1 · Données entièrement fictives'), findsOneWidget);
    expect(find.text('Bonjour Leïla'), findsOneWidget);

    await tester.tap(find.text('Profil'));
    await tester.pumpAndSettle();

    expect(find.text('Leïla Mansouri'), findsOneWidget);
    expect(find.text('Identité fictive HC-005'), findsOneWidget);
  });

  testWidgets('shows the patient dashboard authorized-view summary', (
    tester,
  ) async {
    await tester.pumpWidget(const PatientApp());

    expect(find.text('Vue autorisee active'), findsOneWidget);
    expect(find.text('3'), findsOneWidget);
    expect(find.text('evenements autorises'), findsOneWidget);
    expect(find.text('2'), findsOneWidget);
    expect(find.text('sources autorisees'), findsOneWidget);
    expect(find.text('MOCKED'), findsOneWidget);
  });

  testWidgets('renders the federated authorized timeline fixtures', (
    tester,
  ) async {
    await tester.pumpWidget(const PatientApp());

    await tester.tap(find.text('Parcours'));
    await tester.pumpAndSettle();

    expect(find.text('Consultation de suivi'), findsOneWidget);
    expect(find.text('Hôpital Carthage'), findsOneWidget);
    expect(find.text('Laboratoire El Amal'), findsOneWidget);
    expect(find.text('AUTORISÉ'), findsNWidgets(3));
  });

  testWidgets('navigates between shell destinations', (tester) async {
    await tester.pumpWidget(const PatientApp());

    await tester.tap(find.text('Parcours'));
    await tester.pumpAndSettle();
    expect(find.text('Parcours médical fédéré'), findsOneWidget);

    await tester.tap(find.text('Accès'));
    await tester.pumpAndSettle();
    expect(find.text('Consentements et accès'), findsOneWidget);

    await tester.tap(find.text('Profil'));
    await tester.pumpAndSettle();
    expect(find.text('Leïla Mansouri'), findsOneWidget);

    await tester.tap(find.text('Accueil'));
    await tester.pumpAndSettle();
    expect(find.text('Bonjour Leïla'), findsOneWidget);
  });

  testWidgets('exposes loading, empty, error, and retry states', (
    tester,
  ) async {
    await tester.pumpWidget(const PatientApp());

    await _selectDemoState(tester, 'État : chargement');
    expect(find.byType(CircularProgressIndicator), findsOneWidget);
    expect(find.text('Chargement de votre vue autorisée'), findsOneWidget);

    await _selectDemoState(tester, 'État : vide');
    expect(find.text('Aucune donnée autorisée'), findsOneWidget);

    await _selectDemoState(tester, 'État : erreur');
    expect(find.text('Vue temporairement indisponible'), findsOneWidget);
    await tester.tap(find.text('Réessayer'));
    await tester.pumpAndSettle();
    expect(find.text('Bonjour Leïla'), findsOneWidget);
  });
}

Future<void> _selectDemoState(WidgetTester tester, String label) async {
  await tester.tap(find.byTooltip('Choisir un état de démonstration'));
  await tester.pump();
  await tester.pump(const Duration(milliseconds: 250));
  await tester.tap(find.text(label));
  await tester.pump();
  await tester.pump(const Duration(milliseconds: 250));
}
