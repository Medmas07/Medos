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
