import 'package:flutter_test/flutter_test.dart';
import 'package:hackcure_clinician/presentation/adaptive_intake_flow.dart';

void main() {
  AdaptiveIntake answer(List<(IntakeStepId, List<String>)> answers) {
    var intake = const AdaptiveIntake.empty();
    for (final (id, values) in answers) {
      intake = intake.answer(id, values);
    }
    return intake;
  }

  List<IntakeStepId> ids(AdaptiveIntake intake) => [
    for (final step in intake.path) step.id,
  ];

  List<String> optionIds(IntakeStep step) => [
    for (final option in step.options) option.id,
  ];

  test('starts with the chief complaint only', () {
    const intake = AdaptiveIntake.empty();

    expect(ids(intake), [IntakeStepId.complaint]);
    expect(intake.currentStep!.id, IntakeStepId.complaint);
    expect(intake.isComplete, isFalse);
    expect(intake.skipped, isEmpty);
  });

  test('asks the side for a paired joint and lists joint symptoms', () {
    final intake = answer([
      (IntakeStepId.complaint, ['pain']),
      (IntakeStepId.location, ['knee']),
    ]);

    expect(intake.currentStep!.id, IntakeStepId.side);
    expect(intake.currentStep!.basis, 'Localisation paire : « Genou »');

    final done = answer([
      (IntakeStepId.complaint, ['pain']),
      (IntakeStepId.location, ['knee']),
      (IntakeStepId.side, ['right']),
      (IntakeStepId.duration, ['1-7d']),
      (IntakeStepId.severity, ['6']),
      (IntakeStepId.associated, ['swelling', 'morning-stiffness']),
    ]);
    expect(ids(done), [
      IntakeStepId.complaint,
      IntakeStepId.location,
      IntakeStepId.side,
      IntakeStepId.duration,
      IntakeStepId.severity,
      IntakeStepId.associated,
    ]);
    final associated = done.path.last;
    expect(associated.multiSelect, isTrue);
    expect(associated.basis, 'Liste adaptée à « Douleur · Genou »');
    expect(optionIds(associated), contains('morning-stiffness'));
    expect(done.isComplete, isTrue);
    expect(
      [for (final line in done.summary) line.answer],
      [
        'Douleur',
        'Genou',
        'Droit',
        '1 à 7 jours',
        '6',
        'Gonflement, Raideur matinale',
      ],
    );
  });

  test('skips the side for an unpaired location', () {
    final intake = answer([
      (IntakeStepId.complaint, ['pain']),
      (IntakeStepId.location, ['chest']),
    ]);

    expect(intake.currentStep!.id, IntakeStepId.duration);
    expect(intake.skipped.single.title, 'Côté');
    expect(
      intake.skipped.single.reason,
      'Sans objet pour la localisation « Thorax »',
    );
  });

  test('skips location and side for fever and adapts severity', () {
    final intake = answer([
      (IntakeStepId.complaint, ['fever']),
      (IntakeStepId.duration, ['lt-1d']),
    ]);

    expect(ids(intake), [
      IntakeStepId.complaint,
      IntakeStepId.duration,
      IntakeStepId.severity,
      IntakeStepId.associated,
    ]);
    expect([for (final s in intake.skipped) s.title], ['Localisation', 'Côté']);
    expect(intake.currentStep!.question, 'Température maximale relevée ?');
    expect(optionIds(intake.currentStep!), contains('not-measured'));
  });

  test('chooses associated symptoms by complaint and location', () {
    IntakeStep associatedFor(String complaint, String? location) {
      final intake = answer([
        (IntakeStepId.complaint, [complaint]),
        if (location != null) (IntakeStepId.location, [location]),
        if (location == 'knee' || location == 'shoulder')
          (IntakeStepId.side, ['left']),
        (IntakeStepId.duration, ['1-4w']),
        (IntakeStepId.severity, [intakeFirstSeverity(complaint)]),
      ]);
      return intake.currentStep!;
    }

    expect(optionIds(associatedFor('pain', 'chest')), contains('palpitations'));
    expect(optionIds(associatedFor('pain', 'back')), contains('tingling'));
    expect(optionIds(associatedFor('cough', null)), contains('wheeze'));
    final rash = associatedFor('rash', 'face');
    expect(optionIds(rash), contains('itch'));
    expect(rash.basis, 'Liste adaptée au motif « Éruption cutanée »');
    expect(optionIds(rash).last, 'none');
  });

  test('changing the complaint drops answers that no longer apply', () {
    final pain = answer([
      (IntakeStepId.complaint, ['pain']),
      (IntakeStepId.location, ['knee']),
      (IntakeStepId.side, ['right']),
      (IntakeStepId.duration, ['1-7d']),
      (IntakeStepId.severity, ['6']),
      (IntakeStepId.associated, ['fever']),
    ]);

    final fever = pain.answer(IntakeStepId.complaint, ['fever']);

    expect(fever.answers.keys, [IntakeStepId.complaint, IntakeStepId.duration]);
    expect(fever.currentStep!.id, IntakeStepId.severity);
  });

  test('changing the location keeps answers that still fit', () {
    final knee = answer([
      (IntakeStepId.complaint, ['pain']),
      (IntakeStepId.location, ['knee']),
      (IntakeStepId.side, ['right']),
      (IntakeStepId.duration, ['1-7d']),
      (IntakeStepId.severity, ['6']),
      (IntakeStepId.associated, ['swelling']),
    ]);

    final shoulder = knee.answer(IntakeStepId.location, ['shoulder']);
    expect(shoulder.isComplete, isTrue);
    expect(shoulder.answers[IntakeStepId.side], ['right']);

    final head = knee.answer(IntakeStepId.location, ['head']);
    expect(head.answers.containsKey(IntakeStepId.side), isFalse);
    expect(head.answers.containsKey(IntakeStepId.associated), isFalse);
    expect(head.answers[IntakeStepId.severity], ['6']);
    expect(head.currentStep!.id, IntakeStepId.associated);
  });

  test('rejects invalid, mixed exclusive, and multiple single answers', () {
    final base = answer([
      (IntakeStepId.complaint, ['cough']),
      (IntakeStepId.duration, ['gt-1m']),
      (IntakeStepId.severity, ['rest']),
    ]);

    expect(
      base.answer(IntakeStepId.associated, ['none', 'fever']).isComplete,
      isFalse,
    );
    expect(
      base.answer(IntakeStepId.associated, ['unknown']).isComplete,
      isFalse,
    );
    expect(
      base.answer(IntakeStepId.duration, ['lt-1d', 'gt-1m']).currentStep!.id,
      IntakeStepId.duration,
    );
    expect(base.answer(IntakeStepId.associated, ['none']).isComplete, isTrue);
  });
}

String intakeFirstSeverity(String complaint) => switch (complaint) {
  'pain' => '3',
  'fever' => 'lt-38.5',
  'cough' => 'rest',
  _ => 'mild',
};
