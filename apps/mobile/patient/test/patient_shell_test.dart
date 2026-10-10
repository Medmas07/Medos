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

    expect(find.text('Historique des médicaments'), findsOneWidget);
    expect(find.text('Coagulix'), findsOneWidget);
    expect(find.text('Tensiorel'), findsOneWidget);
    expect(find.text('ACTIF'), findsOneWidget);
    expect(find.text('TERMINÉ'), findsOneWidget);
    expect(find.text('Résultats de laboratoire'), findsOneWidget);
    expect(find.text('Bilan avant traitement'), findsOneWidget);

    await tester.tap(find.text('Bilan avant traitement'));
    await tester.pumpAndSettle();
    expect(find.text('Hémoglobine'), findsOneWidget);
    expect(find.text('12,6 g/dL'), findsOneWidget);
    expect(find.text('DÉMO D1'), findsOneWidget);
    expect(find.text('Hôpitaux et médecins'), findsOneWidget);
    expect(find.text('Dr Inès Chaabane'), findsOneWidget);
    expect(find.text('Dr Youssef Gharbi'), findsOneWidget);
    expect(find.text('Cabinet médical Dr Hatem Bouzid'), findsOneWidget);
  });

  testWidgets('shows consent grants and supports local revocation', (
    tester,
  ) async {
    await tester.pumpWidget(const PatientApp());

    await tester.tap(find.text('Accès'));
    await tester.pumpAndSettle();
    expect(find.text('Mes accès'), findsOneWidget);
    expect(find.text('Dr Youssef Gharbi'), findsOneWidget);
    expect(find.text('Dr Inès Chaabane'), findsOneWidget);
    expect(find.text('Révoquer cet accès'), findsOneWidget);

    await tester.tap(find.text('Révoquer cet accès'));
    await tester.pumpAndSettle();
    expect(find.text('RÉVOQUÉ'), findsOneWidget);
    expect(find.text('Révoquer cet accès'), findsNothing);
  });

  testWidgets('grants a scoped time-limited physician access locally', (
    tester,
  ) async {
    await tester.pumpWidget(const PatientApp());

    await tester.tap(find.text('Accès'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Accorder un accès'));
    await tester.pumpAndSettle();
    expect(find.text('Accorder un accès'), findsOneWidget);
    await tester.tap(find.text('Accorder').last);
    await tester.pumpAndSettle();

    expect(find.text('Dr Rania Kefi'), findsOneWidget);
    expect(find.text('Expire dans 30 jours'), findsOneWidget);
    expect(find.text('DÉMO D1'), findsNWidgets(3));
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

    await tester.tap(find.text('Consultation de suivi'));
    await tester.pumpAndSettle();
    expect(find.text('Organisation'), findsOneWidget);
    expect(find.text('Hôpital Carthage'), findsNWidgets(2));
    expect(find.text('DÉMO D1'), findsOneWidget);
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
