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

  testWidgets('shows medication, laboratory, and care history', (tester) async {
    await tester.pumpWidget(const PatientApp());

    expect(find.text('Historique des médicaments'), findsOneWidget);
    expect(find.text('Coagulix'), findsOneWidget);
    expect(find.text('Tensiorel'), findsOneWidget);
    expect(find.text('ACTIF'), findsOneWidget);
    expect(find.text('TERMINÉ'), findsOneWidget);
    expect(find.text('Résultats de laboratoire'), findsOneWidget);
    expect(find.text('Bilan avant traitement'), findsOneWidget);

    await _tapVisible(tester, find.text('Bilan avant traitement'));
    expect(find.text('Hémoglobine'), findsOneWidget);
    expect(find.text('12,6 g/dL'), findsOneWidget);
    expect(find.text('DÉMO D1'), findsOneWidget);
    expect(find.text('Hôpitaux et médecins'), findsOneWidget);
    expect(find.text('Dr Inès Chaabane'), findsOneWidget);
    expect(find.text('Dr Youssef Gharbi'), findsOneWidget);
    // The organization shares its subtitle with the date and specialty.
    expect(
      find.textContaining('Cabinet médical Dr Hatem Bouzid'),
      findsOneWidget,
    );
  });

  testWidgets('shows consent grants and supports local revocation', (
    tester,
  ) async {
    await tester.pumpWidget(const PatientApp());

    await tester.tap(find.text('Accès'));
    await tester.pumpAndSettle();
    expect(find.text('Mes accès'), findsNWidgets(2));
    expect(find.text('Dr Youssef Gharbi'), findsOneWidget);
    expect(find.text('Dr Inès Chaabane'), findsOneWidget);
    expect(find.text('Révoquer cet accès'), findsOneWidget);

    await _tapVisible(tester, find.text('Révoquer cet accès'));
    expect(find.text('Révoquer cet accès ?'), findsOneWidget);
    await tester.tap(find.text('Révoquer').last);
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
    await _tapVisible(tester, find.text('Accorder un accès'));
    expect(
      find.descendant(
        of: find.byType(AlertDialog),
        matching: find.text('Accorder un accès'),
      ),
      findsOneWidget,
    );
    await tester.tap(find.text('Accorder').last);
    await tester.pumpAndSettle();

    expect(find.text('Dr Rania Kefi'), findsOneWidget);
    expect(find.text('Expire dans 30 jours'), findsOneWidget);
    expect(find.text('DÉMO D1'), findsNWidgets(4));
  });

  testWidgets('shows the canonical delegation to a trusted relative', (
    tester,
  ) async {
    await tester.pumpWidget(const PatientApp());

    await tester.tap(find.text('Accès'));
    await tester.pumpAndSettle();
    await tester.scrollUntilVisible(
      find.text('Retirer la délégation').hitTestable(),
      200,
    );

    expect(find.text('Proches de confiance'), findsOneWidget);
    expect(find.text('Sami Mansouri · Fils'), findsOneWidget);
    expect(find.text('Parcours, médicaments'), findsNWidgets(2));
    expect(
      find.text('Lecture seule — ne peut pas gérer vos accès'),
      findsOneWidget,
    );
    expect(find.text('DÉLÉGUÉ'), findsOneWidget);
  });

  testWidgets('delegates scoped access to a relative locally', (tester) async {
    await tester.pumpWidget(const PatientApp());

    await tester.tap(find.text('Accès'));
    await tester.pumpAndSettle();
    await _tapVisible(tester, find.text('Déléguer à un proche'));

    await tester.tap(find.text('Déléguer').last);
    await tester.pumpAndSettle();
    expect(find.text('Indiquez le nom du proche.'), findsOneWidget);

    await tester.enterText(find.byType(TextField), 'Amel Mansouri');
    await tester.tap(find.text('Déléguer').last);
    await tester.pumpAndSettle();

    expect(find.text('Amel Mansouri · Fils'), findsOneWidget);
    expect(
      find.text('Déléguée pendant cette session · Sans date d’expiration'),
      findsOneWidget,
    );
  });

  testWidgets('withdraws a relative delegation after confirmation', (
    tester,
  ) async {
    await tester.pumpWidget(const PatientApp());

    await tester.tap(find.text('Accès'));
    await tester.pumpAndSettle();
    await _tapVisible(tester, find.text('Retirer la délégation'));
    expect(find.text('Retirer la délégation ?'), findsOneWidget);
    await tester.tap(find.text('Retirer').last);
    await tester.pumpAndSettle();

    expect(find.text('RETIRÉ'), findsOneWidget);
    expect(find.text('Retirer la délégation'), findsNothing);
  });

  testWidgets('tracks a restriction request without promising deletion', (
    tester,
  ) async {
    await tester.pumpWidget(const PatientApp());

    await tester.tap(find.text('Profil'));
    await tester.pumpAndSettle();
    await tester.scrollUntilVisible(
      find.text('Aucune demande en cours').hitTestable(),
      200,
    );
    expect(find.text('Mes demandes sur mes données'), findsOneWidget);

    await _tapVisible(tester, find.text('Faire une demande'));
    expect(find.textContaining('jamais garanti'), findsOneWidget);
    await tester.tap(find.text('Envoyer la demande'));
    await tester.pumpAndSettle();

    expect(find.text('Aucune demande en cours'), findsNothing);
    expect(find.text('Restreindre l’utilisation future'), findsOneWidget);
    expect(find.text('Toutes mes sources'), findsOneWidget);
    expect(find.text('SOUMISE'), findsOneWidget);

    await tester.pump(const Duration(seconds: 2));
    await tester.pump();
    expect(find.text('EN ANALYSE'), findsOneWidget);
    expect(
      find.textContaining('obligations légales ou de soins'),
      findsOneWidget,
    );
    expect(find.text('Revue hôpital / gouvernance'), findsOneWidget);
  });

  testWidgets('shows the notification center and marks notifications read', (
    tester,
  ) async {
    await tester.pumpWidget(const PatientApp());

    expect(find.text('1'), findsOneWidget);
    await tester.tap(find.byTooltip('Notifications'));
    await tester.pumpAndSettle();

    expect(find.text('Accès accordé'), findsOneWidget);
    expect(find.text('Nouveau bilan disponible'), findsOneWidget);
    expect(find.text('NON LUE'), findsOneWidget);
    expect(find.text('LUE'), findsOneWidget);

    await tester.tap(find.text('Non lues (1)'));
    await tester.pumpAndSettle();
    expect(find.text('Nouveau bilan disponible'), findsNothing);

    await tester.tap(find.text('Accès accordé'));
    await tester.pumpAndSettle();
    expect(find.text('Aucune notification non lue'), findsOneWidget);

    await tester.pageBack();
    await tester.pumpAndSettle();
    expect(find.text('1'), findsNothing);
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

    await _tapVisible(tester, find.text('Consultation de suivi'));
    expect(find.text('Organisation'), findsOneWidget);
    expect(find.text('Hôpital Carthage'), findsNWidgets(2));
    await tester.scrollUntilVisible(
      find.text('DÉMO D1').hitTestable(),
      100,
      scrollable: find.descendant(
        of: find.byType(BottomSheet),
        matching: find.byType(Scrollable),
      ),
    );
    expect(find.text('DÉMO D1'), findsOneWidget);
  });

  testWidgets('navigates between shell destinations', (tester) async {
    await tester.pumpWidget(const PatientApp());

    await tester.tap(find.text('Parcours'));
    await tester.pumpAndSettle();
    expect(find.text('Parcours médical fédéré'), findsOneWidget);

    await tester.tap(find.text('Accès'));
    await tester.pumpAndSettle();
    expect(find.text('Proches de confiance'), findsOneWidget);

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

/// Scrolls [finder] until it can receive a tap, then taps it.
///
/// `scrollUntilVisible` alone stops at widgets laid out below the test
/// viewport, so taps on them miss.
Future<void> _tapVisible(WidgetTester tester, Finder finder) async {
  await tester.scrollUntilVisible(finder.hitTestable(), 200);
  await tester.tap(finder);
  await tester.pumpAndSettle();
}
