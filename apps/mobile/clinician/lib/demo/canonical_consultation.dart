/// Presentation-only copy of the HC-005 fictional consultation script.
///
/// This fixture is not captured audio, a clinical record, or an AI result. It
/// is checked against `demo-data/clinician.json` by the widget test suite.
class DemoTranscriptSegment {
  const DemoTranscriptSegment({
    required this.id,
    required this.speaker,
    required this.text,
  });

  final String id;
  final String speaker;
  final String text;
}

const demoConsultationScriptId = 'script-a-2026-10-10';
const demoConsultationAppointmentId = 'appt-a-2026-10-10';

const demoTranscriptSegments = <DemoTranscriptSegment>[
  DemoTranscriptSegment(
    id: 'seg-1',
    speaker: 'clinician',
    text: 'Bonjour Madame Mansouri, qu’est-ce qui vous amène aujourd’hui ?',
  ),
  DemoTranscriptSegment(
    id: 'seg-2',
    speaker: 'patient',
    text:
        'J’ai mal au genou droit depuis une semaine, surtout le matin, et il est un peu gonflé.',
  ),
  DemoTranscriptSegment(
    id: 'seg-3',
    speaker: 'clinician',
    text: 'Vous avez pris quelque chose pour la douleur ?',
  ),
  DemoTranscriptSegment(
    id: 'seg-4',
    speaker: 'patient',
    text: 'Non, rien. Je prends seulement mon traitement pour la tension.',
  ),
  DemoTranscriptSegment(
    id: 'seg-5',
    speaker: 'clinician',
    text:
        'Votre tension est à 148 sur 92 aujourd’hui. Le genou est chaud, la mobilité est un peu réduite.',
  ),
];

enum DemoExtractionCategory {
  symptom,
  observation,
  value,
  medication,
  missingInformation,
}

/// One item of the HC-005 fictional extraction draft
/// (`consultationScripts[].extractionDraft` in `demo-data/clinician.json`).
///
/// It is a fixed demo result, not the output of a model, and it stays a
/// suggestion until the clinician accepts it.
class DemoExtractionItem {
  const DemoExtractionItem({
    required this.id,
    required this.category,
    required this.label,
    this.detail,
    this.value,
    this.unit,
    this.flag,
    this.medicationCode,
    this.note,
  });

  final String id;
  final DemoExtractionCategory category;
  final String label;
  final String? detail;
  final String? value;
  final String? unit;
  final String? flag;
  final String? medicationCode;
  final String? note;

  /// The reviewable statement, as the clinician would edit it.
  String get text => switch (category) {
    DemoExtractionCategory.value => '$label : $value $unit',
    _ => label,
  };
}

/// `extractionDraft.status` in the fixture.
const demoExtractionStatus = 'pending_clinician_review';

const demoExtractionItems = <DemoExtractionItem>[
  DemoExtractionItem(
    id: 'ext-s1',
    category: DemoExtractionCategory.symptom,
    label: 'Douleur du genou droit',
    detail: 'Depuis une semaine, prédominance matinale',
  ),
  DemoExtractionItem(
    id: 'ext-s2',
    category: DemoExtractionCategory.symptom,
    label: 'Gonflement du genou droit',
  ),
  DemoExtractionItem(
    id: 'ext-o1',
    category: DemoExtractionCategory.observation,
    label: 'Genou droit chaud, mobilité réduite',
  ),
  DemoExtractionItem(
    id: 'ext-v1',
    category: DemoExtractionCategory.value,
    label: 'Pression artérielle',
    value: '148/92',
    unit: 'mmHg',
    flag: 'high',
  ),
  DemoExtractionItem(
    id: 'ext-m1',
    category: DemoExtractionCategory.medication,
    label: 'Traitement pour la tension',
    medicationCode: 'MED-TENSIOREL',
    note: 'Rapproché de l’historique fédéré',
  ),
  // The fixture's missing information is a list of strings without ids.
  DemoExtractionItem(
    id: 'ext-missing-1',
    category: DemoExtractionCategory.missingInformation,
    label: 'Intensité de la douleur (échelle 0-10)',
  ),
  DemoExtractionItem(
    id: 'ext-missing-2',
    category: DemoExtractionCategory.missingInformation,
    label: 'Traumatisme récent',
  ),
  DemoExtractionItem(
    id: 'ext-missing-3',
    category: DemoExtractionCategory.missingInformation,
    label:
        'Traitement anticoagulant non mentionné par la patiente alors qu’il figure dans l’historique fédéré',
  ),
];
