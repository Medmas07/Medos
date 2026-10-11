import 'package:flutter/material.dart';

import '../demo/canonical_consultation.dart';
import 'adaptive_intake_view.dart';
import 'clinician_theme.dart';
import 'medication_interaction_warning.dart';

enum RecordingConsentState { awaitingDecision, granted, declined }

enum SpeechToTextDemoState { ready, recording, transcribing, completed }

/// D1 presentation fixture copied from HC-005's fictional Patient A.
/// It is not clinical data and is never persisted or sent anywhere.
const demoConsultationPatientName = 'Leïla Mansouri';
const demoConsultationPatientId = 'pat-a';

class RecordingConsentView extends StatefulWidget {
  const RecordingConsentView({super.key});

  @override
  State<RecordingConsentView> createState() => _RecordingConsentViewState();
}

class _RecordingConsentViewState extends State<RecordingConsentView> {
  RecordingConsentState _state = RecordingConsentState.awaitingDecision;
  SpeechToTextDemoState _speechState = SpeechToTextDemoState.ready;
  bool _explanationConfirmed = false;
  int _transcriptionGeneration = 0;

  void _recordDecision(RecordingConsentState state) {
    setState(() => _state = state);
  }

  void _resetDecision() {
    setState(() {
      _state = RecordingConsentState.awaitingDecision;
      _speechState = SpeechToTextDemoState.ready;
      _explanationConfirmed = false;
      _transcriptionGeneration += 1;
    });
  }

  void _startRecordingSimulation() {
    setState(() => _speechState = SpeechToTextDemoState.recording);
  }

  Future<void> _stopAndTranscribe() async {
    final generation = ++_transcriptionGeneration;
    setState(() => _speechState = SpeechToTextDemoState.transcribing);
    await Future<void>.delayed(const Duration(milliseconds: 700));
    if (!mounted || generation != _transcriptionGeneration) return;
    setState(() => _speechState = SpeechToTextDemoState.completed);
  }

  void _restartTranscriptDemo() {
    setState(() => _speechState = SpeechToTextDemoState.ready);
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Text(
          'Consentement à l’enregistrement',
          style: Theme.of(context).textTheme.headlineSmall,
        ),
        const SizedBox(height: 6),
        const Text(
          'Aucun enregistrement ne peut commencer sans une décision explicite du patient.',
          style: TextStyle(color: ClinicianColors.muted, height: 1.4),
        ),
        const SizedBox(height: 16),
        _PatientCard(state: _state),
        const SizedBox(height: 16),
        if (_state == RecordingConsentState.awaitingDecision)
          _AwaitingDecisionCard(
            explanationConfirmed: _explanationConfirmed,
            onConfirmationChanged: (value) =>
                setState(() => _explanationConfirmed = value ?? false),
            onGrant: _explanationConfirmed
                ? () => _recordDecision(RecordingConsentState.granted)
                : null,
            onDecline: () => _recordDecision(RecordingConsentState.declined),
          )
        else
          _DecisionCard(
            state: _state,
            speechState: _speechState,
            onReset: _resetDecision,
            onStartRecording: _startRecordingSimulation,
            onStopRecording: _stopAndTranscribe,
            onRestartTranscript: _restartTranscriptDemo,
          ),
        const SizedBox(height: 16),
        const _DemoBoundaryCard(),
      ],
    );
  }
}

class _PatientCard extends StatelessWidget {
  const _PatientCard({required this.state});

  final RecordingConsentState state;

  @override
  Widget build(BuildContext context) {
    final (label, color, background) = switch (state) {
      RecordingConsentState.awaitingDecision => (
        'Décision requise',
        const Color(0xFF92400E),
        const Color(0xFFFFFBEB),
      ),
      RecordingConsentState.granted => (
        'Consentement obtenu',
        const Color(0xFF047857),
        const Color(0xFFECFDF5),
      ),
      RecordingConsentState.declined => (
        'Enregistrement refusé',
        ClinicianColors.danger,
        const Color(0xFFFEF2F2),
      ),
    };

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(18),
        child: Row(
          children: [
            const CircleAvatar(
              backgroundColor: ClinicianColors.brandSoft,
              foregroundColor: ClinicianColors.brand,
              child: Text('LM'),
            ),
            const SizedBox(width: 12),
            const Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    demoConsultationPatientName,
                    style: TextStyle(fontWeight: FontWeight.w800),
                  ),
                  Text(
                    'Patient fictif HC-005 · pat-a',
                    style: TextStyle(color: ClinicianColors.muted),
                  ),
                ],
              ),
            ),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
              decoration: BoxDecoration(
                color: background,
                borderRadius: BorderRadius.circular(999),
              ),
              child: Text(
                label,
                style: TextStyle(
                  color: color,
                  fontSize: 12,
                  fontWeight: FontWeight.w800,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _AwaitingDecisionCard extends StatelessWidget {
  const _AwaitingDecisionCard({
    required this.explanationConfirmed,
    required this.onConfirmationChanged,
    required this.onGrant,
    required this.onDecline,
  });

  final bool explanationConfirmed;
  final ValueChanged<bool?> onConfirmationChanged;
  final VoidCallback? onGrant;
  final VoidCallback onDecline;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(18),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'À expliquer au patient',
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const SizedBox(height: 12),
            const _ExplanationLine(
              icon: Icons.mic_none_rounded,
              text:
                  'La consultation sera enregistrée pour préparer une transcription.',
            ),
            const _ExplanationLine(
              icon: Icons.person_outline_rounded,
              text:
                  'Le clinicien devra relire et valider tout contenu produit.',
            ),
            const _ExplanationLine(
              icon: Icons.stop_circle_outlined,
              text:
                  'Le patient peut refuser ou demander l’arrêt à tout moment.',
            ),
            const Divider(height: 24),
            CheckboxListTile(
              contentPadding: EdgeInsets.zero,
              controlAffinity: ListTileControlAffinity.leading,
              value: explanationConfirmed,
              onChanged: onConfirmationChanged,
              title: const Text(
                'J’ai expliqué la finalité et recueilli la décision du patient.',
              ),
            ),
            const SizedBox(height: 8),
            Row(
              children: [
                Expanded(
                  child: OutlinedButton.icon(
                    key: const ValueKey('recording-consent-decline'),
                    onPressed: onDecline,
                    icon: const Icon(Icons.mic_off_outlined),
                    label: const Text('Le patient refuse'),
                  ),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: FilledButton.icon(
                    key: const ValueKey('recording-consent-grant'),
                    onPressed: onGrant,
                    icon: const Icon(Icons.check_circle_outline_rounded),
                    label: const Text('Consentement obtenu'),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class _ExplanationLine extends StatelessWidget {
  const _ExplanationLine({required this.icon, required this.text});

  final IconData icon;
  final String text;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, size: 20, color: ClinicianColors.brand),
          const SizedBox(width: 10),
          Expanded(child: Text(text)),
        ],
      ),
    );
  }
}

class _DecisionCard extends StatelessWidget {
  const _DecisionCard({
    required this.state,
    required this.speechState,
    required this.onReset,
    required this.onStartRecording,
    required this.onStopRecording,
    required this.onRestartTranscript,
  });

  final RecordingConsentState state;
  final SpeechToTextDemoState speechState;
  final VoidCallback onReset;
  final VoidCallback onStartRecording;
  final VoidCallback onStopRecording;
  final VoidCallback onRestartTranscript;

  @override
  Widget build(BuildContext context) {
    final granted = state == RecordingConsentState.granted;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Card(
          color: granted ? const Color(0xFFECFDF5) : const Color(0xFFFEF2F2),
          child: Padding(
            padding: const EdgeInsets.all(18),
            child: Column(
              children: [
                Icon(
                  granted
                      ? Icons.verified_user_outlined
                      : Icons.mic_off_outlined,
                  size: 42,
                  color: granted
                      ? const Color(0xFF047857)
                      : ClinicianColors.danger,
                ),
                const SizedBox(height: 10),
                Text(
                  granted
                      ? 'Consentement consigné pour cette session'
                      : 'Enregistrement bloqué',
                  textAlign: TextAlign.center,
                  style: Theme.of(context).textTheme.titleMedium,
                ),
                const SizedBox(height: 6),
                Text(
                  granted
                      ? 'La démonstration peut continuer sans activer le microphone de l’appareil.'
                      : 'Le refus est respecté. Aucun son n’est capturé et la consultation continue avec l’anamnèse adaptative.',
                  textAlign: TextAlign.center,
                ),
                const SizedBox(height: 14),
                OutlinedButton(
                  onPressed: onReset,
                  child: Text(
                    granted ? 'Retirer le consentement' : 'Revoir la décision',
                  ),
                ),
              ],
            ),
          ),
        ),
        const SizedBox(height: 12),
        if (granted) ...[
          _SpeechToTextCard(
            state: speechState,
            onStart: onStartRecording,
            onStop: onStopRecording,
            onRestart: onRestartTranscript,
          ),
          const SizedBox(height: 12),
          const MedicationInteractionWarningView(),
        ] else
          const AdaptiveIntakeView(),
      ],
    );
  }
}

class _SpeechToTextCard extends StatelessWidget {
  const _SpeechToTextCard({
    required this.state,
    required this.onStart,
    required this.onStop,
    required this.onRestart,
  });

  final SpeechToTextDemoState state;
  final VoidCallback onStart;
  final VoidCallback onStop;
  final VoidCallback onRestart;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(18),
        child: AnimatedSwitcher(
          duration: const Duration(milliseconds: 180),
          child: switch (state) {
            SpeechToTextDemoState.ready => _ReadyToRecord(onStart: onStart),
            SpeechToTextDemoState.recording => _Recording(onStop: onStop),
            SpeechToTextDemoState.transcribing => const _Transcribing(),
            SpeechToTextDemoState.completed => _Transcript(
              onRestart: onRestart,
            ),
          },
        ),
      ),
    );
  }
}

class _ReadyToRecord extends StatelessWidget {
  const _ReadyToRecord({required this.onStart});

  final VoidCallback onStart;

  @override
  Widget build(BuildContext context) {
    return Column(
      key: const ValueKey('speech-ready'),
      children: [
        const Icon(
          Icons.graphic_eq_rounded,
          size: 42,
          color: ClinicianColors.brand,
        ),
        const SizedBox(height: 10),
        Text(
          'Transcription de consultation',
          style: Theme.of(context).textTheme.titleMedium,
        ),
        const SizedBox(height: 6),
        const Text(
          'Lancer le scénario préenregistré fictif. Aucun accès au microphone ne sera demandé.',
          textAlign: TextAlign.center,
        ),
        const SizedBox(height: 14),
        FilledButton.icon(
          key: const ValueKey('start-speech-demo'),
          onPressed: onStart,
          icon: const Icon(Icons.play_arrow_rounded),
          label: const Text('Démarrer la simulation'),
        ),
      ],
    );
  }
}

class _Recording extends StatelessWidget {
  const _Recording({required this.onStop});

  final VoidCallback onStop;

  @override
  Widget build(BuildContext context) {
    return Column(
      key: const ValueKey('speech-recording'),
      children: [
        const Icon(
          Icons.fiber_manual_record,
          size: 42,
          color: ClinicianColors.danger,
        ),
        const SizedBox(height: 10),
        Text(
          'Enregistrement simulé',
          style: Theme.of(context).textTheme.titleMedium,
        ),
        const SizedBox(height: 6),
        const Text('Scénario fictif en cours · aucun son capturé'),
        const SizedBox(height: 14),
        FilledButton.icon(
          key: const ValueKey('stop-speech-demo'),
          onPressed: onStop,
          icon: const Icon(Icons.stop_rounded),
          label: const Text('Arrêter et transcrire'),
        ),
      ],
    );
  }
}

class _Transcribing extends StatelessWidget {
  const _Transcribing();

  @override
  Widget build(BuildContext context) {
    return const Column(
      key: ValueKey('speech-transcribing'),
      children: [
        SizedBox(
          width: 36,
          height: 36,
          child: CircularProgressIndicator(strokeWidth: 3),
        ),
        SizedBox(height: 12),
        Text(
          'Transcription simulée en cours',
          style: TextStyle(fontWeight: FontWeight.w800),
        ),
        SizedBox(height: 6),
        Text('Chargement déterministe du script fictif HC-005.'),
      ],
    );
  }
}

class _Transcript extends StatelessWidget {
  const _Transcript({required this.onRestart});

  final VoidCallback onRestart;

  @override
  Widget build(BuildContext context) {
    return Column(
      key: const ValueKey('speech-completed'),
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Row(
          children: [
            const Icon(
              Icons.description_outlined,
              color: ClinicianColors.brand,
            ),
            const SizedBox(width: 10),
            Expanded(
              child: Text(
                'Transcription simulée',
                style: Theme.of(context).textTheme.titleMedium,
              ),
            ),
            const _MockedPill(),
          ],
        ),
        const SizedBox(height: 6),
        const Text(
          'À relire par le clinicien · aucune donnée n’est enregistrée.',
          style: TextStyle(color: ClinicianColors.muted),
        ),
        const Divider(height: 24),
        for (final segment in demoTranscriptSegments)
          _TranscriptSegment(segment: segment),
        const SizedBox(height: 8),
        OutlinedButton.icon(
          onPressed: onRestart,
          icon: const Icon(Icons.replay_rounded),
          label: const Text('Rejouer la démonstration'),
        ),
      ],
    );
  }
}

class _TranscriptSegment extends StatelessWidget {
  const _TranscriptSegment({required this.segment});

  final DemoTranscriptSegment segment;

  @override
  Widget build(BuildContext context) {
    final clinician = segment.speaker == 'clinician';
    return Padding(
      padding: const EdgeInsets.only(bottom: 14),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            clinician ? 'Dr Youssef Gharbi' : demoConsultationPatientName,
            style: TextStyle(
              color: clinician ? ClinicianColors.brand : ClinicianColors.demo,
              fontSize: 12,
              fontWeight: FontWeight.w800,
            ),
          ),
          const SizedBox(height: 3),
          Text(segment.text),
        ],
      ),
    );
  }
}

class _MockedPill extends StatelessWidget {
  const _MockedPill();

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: ClinicianColors.demoSoft,
        borderRadius: BorderRadius.circular(999),
      ),
      child: const Text(
        'MOCKED',
        style: TextStyle(
          color: ClinicianColors.demo,
          fontSize: 11,
          fontWeight: FontWeight.w800,
        ),
      ),
    );
  }
}

class _DemoBoundaryCard extends StatelessWidget {
  const _DemoBoundaryCard();

  @override
  Widget build(BuildContext context) {
    return const Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Icon(Icons.info_outline_rounded, size: 20, color: ClinicianColors.demo),
        SizedBox(width: 8),
        Expanded(
          child: Text(
            'MOCKED D1 · Consentement, transcription et anamnèse restent uniquement dans l’écran. Aucun microphone, audio, stockage, contrat API ou consentement juridiquement opposable.',
            style: TextStyle(color: ClinicianColors.demo, height: 1.4),
          ),
        ),
      ],
    );
  }
}
