/// Deterministic adaptive intake for the D1 Clinician App (HC-039).
///
/// The question set is invented demo content, not a validated clinical
/// questionnaire. Branching only chooses which question comes next and which
/// answers it offers; it never scores, prioritizes, diagnoses, or recommends.
/// Answers live in widget state only and are never persisted or sent.
library;

enum IntakeStepId { complaint, location, side, duration, severity, associated }

class IntakeOption {
  const IntakeOption(this.id, this.label);

  final String id;
  final String label;
}

class IntakeStep {
  const IntakeStep({
    required this.id,
    required this.title,
    required this.question,
    required this.options,
    this.basis,
    this.multiSelect = false,
    this.exclusiveOptionId,
  });

  final IntakeStepId id;
  final String title;
  final String question;
  final List<IntakeOption> options;

  /// Which earlier answers chose this question or its options, for review.
  final String? basis;
  final bool multiSelect;

  /// In a multi-select step, an option that cannot be combined with others.
  final String? exclusiveOptionId;

  String labelOf(String optionId) =>
      options.firstWhere((option) => option.id == optionId).label;
}

class SkippedIntakeStep {
  const SkippedIntakeStep(this.title, this.reason);

  final String title;
  final String reason;
}

class IntakeSummaryLine {
  const IntakeSummaryLine(this.step, this.answer);

  final IntakeStep step;
  final String answer;
}

/// An immutable intake: the answers given so far, already pruned of any
/// answer that earlier answers made inapplicable.
class AdaptiveIntake {
  const AdaptiveIntake._(this.answers);

  const AdaptiveIntake.empty() : answers = const {};

  final Map<IntakeStepId, List<String>> answers;

  /// Records [values] for [id], then drops later answers that no longer fit.
  AdaptiveIntake answer(IntakeStepId id, List<String> values) {
    final raw = Map<IntakeStepId, List<String>>.of(answers)..[id] = values;
    return AdaptiveIntake._(_normalize(raw));
  }

  /// The questions on the current branch, in order, up to the first one that
  /// depends on an unanswered question.
  List<IntakeStep> get path => [
    for (final resolution in _resolutions())
      if (resolution case _Ask(:final step)) step,
  ];

  /// Questions the current answers make irrelevant, with the reason.
  List<SkippedIntakeStep> get skipped => [
    for (final resolution in _resolutions())
      if (resolution case _Skip(:final title, :final reason))
        SkippedIntakeStep(title, reason),
  ];

  /// The first unanswered question, or null once the intake is complete.
  IntakeStep? get currentStep {
    for (final step in path) {
      if (!answers.containsKey(step.id)) return step;
    }
    return null;
  }

  bool get isComplete => currentStep == null;

  List<IntakeSummaryLine> get summary => [
    for (final step in path)
      if (answers[step.id] case final values?)
        IntakeSummaryLine(step, values.map(step.labelOf).join(', ')),
  ];

  Iterable<_Resolution> _resolutions() sync* {
    for (final id in IntakeStepId.values) {
      final resolution = _resolve(id, answers);
      if (resolution is _Blocked) return;
      yield resolution;
    }
  }

  static Map<IntakeStepId, List<String>> _normalize(
    Map<IntakeStepId, List<String>> raw,
  ) {
    final kept = <IntakeStepId, List<String>>{};
    for (final id in IntakeStepId.values) {
      if (_resolve(id, kept) case _Ask(:final step)) {
        final valid = {for (final option in step.options) option.id};
        final values = [
          for (final value in raw[id] ?? const <String>[])
            if (valid.contains(value)) value,
        ];
        final exclusiveMixed =
            values.length > 1 && values.contains(step.exclusiveOptionId);
        if (values.isEmpty || exclusiveMixed) continue;
        if (!step.multiSelect && values.length > 1) continue;
        kept[id] = values;
      }
    }
    return kept;
  }
}

sealed class _Resolution {}

final class _Ask extends _Resolution {
  _Ask(this.step);

  final IntakeStep step;
}

final class _Skip extends _Resolution {
  _Skip(this.title, this.reason);

  final String title;
  final String reason;
}

/// The question depends on an earlier question that has no answer yet.
final class _Blocked extends _Resolution {}

String? _single(Map<IntakeStepId, List<String>> answers, IntakeStepId id) {
  final values = answers[id];
  return values == null || values.length != 1 ? null : values.single;
}

String _label(List<IntakeOption> options, String id) =>
    options.firstWhere((option) => option.id == id).label;

_Resolution _resolve(IntakeStepId id, Map<IntakeStepId, List<String>> a) {
  if (id == IntakeStepId.complaint) return _Ask(_complaintStep);

  final complaint = _single(a, IntakeStepId.complaint);
  if (complaint == null) return _Blocked();
  final complaintLabel = _label(_complaints, complaint);
  final byComplaint = 'Adapté au motif « $complaintLabel »';
  final noObjectForComplaint = 'Sans objet pour le motif « $complaintLabel »';

  switch (id) {
    case IntakeStepId.complaint:
      throw StateError('unreachable');
    case IntakeStepId.location:
      final options = _locations[complaint];
      return options == null
          ? _Skip('Localisation', noObjectForComplaint)
          : _Ask(
              IntakeStep(
                id: id,
                title: 'Localisation',
                question: 'Où se situe le symptôme ?',
                options: options,
                basis: byComplaint,
              ),
            );
    case IntakeStepId.side:
      final options = _locations[complaint];
      if (options == null) return _Skip('Côté', noObjectForComplaint);
      final location = _single(a, IntakeStepId.location);
      if (location == null) return _Blocked();
      final locationLabel = _label(options, location);
      return _pairedLocations.contains(location)
          ? _Ask(
              IntakeStep(
                id: id,
                title: 'Côté',
                question: 'De quel côté ?',
                options: _sides,
                basis: 'Localisation paire : « $locationLabel »',
              ),
            )
          : _Skip('Côté', 'Sans objet pour la localisation « $locationLabel »');
    case IntakeStepId.duration:
      return _Ask(_durationStep);
    case IntakeStepId.severity:
      final (question, options) = _severities[complaint]!;
      return _Ask(
        IntakeStep(
          id: id,
          title: 'Sévérité',
          question: question,
          options: options,
          basis: byComplaint,
        ),
      );
    case IntakeStepId.associated:
      var symptoms = _associatedByComplaint[complaint];
      var basis = 'Liste adaptée au motif « $complaintLabel »';
      if (symptoms == null) {
        final location = _single(a, IntakeStepId.location);
        if (location == null) return _Blocked();
        symptoms = _associatedByLocation['$complaint/$location']!;
        basis =
            'Liste adaptée à « $complaintLabel · '
            '${_label(_locations[complaint]!, location)} »';
      }
      return _Ask(
        IntakeStep(
          id: id,
          title: 'Symptômes associés',
          question: 'Le patient présente-t-il aussi… ?',
          options: [...symptoms, _noneOfThese],
          basis: basis,
          multiSelect: true,
          exclusiveOptionId: _noneOfThese.id,
        ),
      );
  }
}

const _complaints = [
  IntakeOption('pain', 'Douleur'),
  IntakeOption('fever', 'Fièvre'),
  IntakeOption('cough', 'Toux ou gêne respiratoire'),
  IntakeOption('rash', 'Éruption cutanée'),
];

const _complaintStep = IntakeStep(
  id: IntakeStepId.complaint,
  title: 'Motif principal',
  question: 'Quel est le motif principal de consultation ?',
  options: _complaints,
);

/// Complaints with no entry here have no location question.
const _locations = <String, List<IntakeOption>>{
  'pain': [
    IntakeOption('head', 'Tête'),
    IntakeOption('chest', 'Thorax'),
    IntakeOption('abdomen', 'Abdomen'),
    IntakeOption('back', 'Dos'),
    IntakeOption('shoulder', 'Épaule'),
    IntakeOption('knee', 'Genou'),
  ],
  'rash': [
    IntakeOption('face', 'Visage'),
    IntakeOption('trunk', 'Tronc'),
    IntakeOption('limbs', 'Membres'),
    IntakeOption('widespread', 'Généralisée'),
  ],
};

const _pairedLocations = {'shoulder', 'knee'};

const _sides = [
  IntakeOption('right', 'Droit'),
  IntakeOption('left', 'Gauche'),
  IntakeOption('both', 'Des deux côtés'),
];

const _durationStep = IntakeStep(
  id: IntakeStepId.duration,
  title: 'Durée',
  question: 'Depuis combien de temps ?',
  options: [
    IntakeOption('lt-1d', 'Moins de 24 heures'),
    IntakeOption('1-7d', '1 à 7 jours'),
    IntakeOption('1-4w', '1 à 4 semaines'),
    IntakeOption('gt-1m', 'Plus d’un mois'),
  ],
);

const _severities = <String, (String, List<IntakeOption>)>{
  'pain': (
    'Intensité de la douleur selon le patient (0 à 10) ?',
    [
      IntakeOption('0', '0'),
      IntakeOption('1', '1'),
      IntakeOption('2', '2'),
      IntakeOption('3', '3'),
      IntakeOption('4', '4'),
      IntakeOption('5', '5'),
      IntakeOption('6', '6'),
      IntakeOption('7', '7'),
      IntakeOption('8', '8'),
      IntakeOption('9', '9'),
      IntakeOption('10', '10'),
    ],
  ),
  'fever': (
    'Température maximale relevée ?',
    [
      IntakeOption('lt-38.5', 'Moins de 38,5 °C'),
      IntakeOption('38.5-39.4', '38,5 à 39,4 °C'),
      IntakeOption('ge-39.5', '39,5 °C ou plus'),
      IntakeOption('not-measured', 'Non mesurée'),
    ],
  ),
  'cough': (
    'Retentissement sur l’effort ?',
    [
      IntakeOption('heavy-effort', 'Gêne à l’effort important'),
      IntakeOption('light-effort', 'Gêne à l’effort léger'),
      IntakeOption('rest', 'Gêne au repos'),
    ],
  ),
  'rash': (
    'Retentissement sur le quotidien ?',
    [
      IntakeOption('mild', 'Gêne légère'),
      IntakeOption('moderate', 'Gêne modérée'),
      IntakeOption('marked', 'Gêne importante (sommeil, activités)'),
    ],
  ),
};

const _fever = IntakeOption('fever', 'Fièvre');
const _nausea = IntakeOption('nausea', 'Nausées ou vomissements');
const _urinary = IntakeOption('urinary', 'Brûlures urinaires');
const _breathless = IntakeOption('breathless', 'Essoufflement');

const _jointSymptoms = [
  IntakeOption('swelling', 'Gonflement'),
  IntakeOption('warmth', 'Chaleur ou rougeur'),
  IntakeOption('morning-stiffness', 'Raideur matinale'),
  IntakeOption('trauma', 'Traumatisme récent'),
  _fever,
];

/// Pain symptoms depend on where the pain is.
const _associatedByLocation = <String, List<IntakeOption>>{
  'pain/head': [
    _nausea,
    IntakeOption('vision', 'Troubles visuels'),
    IntakeOption('neck-stiffness', 'Raideur de la nuque'),
    _fever,
  ],
  'pain/chest': [
    _breathless,
    IntakeOption('palpitations', 'Palpitations'),
    IntakeOption('sweating', 'Sueurs'),
    IntakeOption('radiation', 'Irradiation vers le bras ou la mâchoire'),
  ],
  'pain/abdomen': [
    _nausea,
    IntakeOption('transit', 'Troubles du transit'),
    _urinary,
    _fever,
  ],
  'pain/back': [
    IntakeOption('leg-radiation', 'Irradiation dans la jambe'),
    IntakeOption('tingling', 'Fourmillements'),
    _urinary,
    _fever,
  ],
  'pain/shoulder': _jointSymptoms,
  'pain/knee': _jointSymptoms,
};

const _associatedByComplaint = <String, List<IntakeOption>>{
  'fever': [
    IntakeOption('chills', 'Frissons'),
    IntakeOption('cough', 'Toux'),
    IntakeOption('headache', 'Maux de tête'),
    IntakeOption('aches', 'Courbatures'),
    _urinary,
  ],
  'cough': [
    IntakeOption('sputum', 'Expectorations'),
    _breathless,
    IntakeOption('wheeze', 'Sifflements'),
    _fever,
  ],
  'rash': [
    IntakeOption('itch', 'Démangeaisons'),
    IntakeOption('local-pain', 'Douleur locale'),
    IntakeOption('face-swelling', 'Gonflement du visage ou des lèvres'),
    _fever,
  ],
};

const _noneOfThese = IntakeOption('none', 'Aucun de ces symptômes');
