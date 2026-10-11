import 'package:flutter/material.dart';

import 'clinician_theme.dart';

enum RecordingConsentState { awaitingDecision, granted, declined }

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
  bool _explanationConfirmed = false;

  void _recordDecision(RecordingConsentState state) {
    setState(() => _state = state);
  }

  void _resetDecision() {
    setState(() {
      _state = RecordingConsentState.awaitingDecision;
      _explanationConfirmed = false;
    });
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
          _DecisionCard(state: _state, onReset: _resetDecision),
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
  const _DecisionCard({required this.state, required this.onReset});

  final RecordingConsentState state;
  final VoidCallback onReset;

  @override
  Widget build(BuildContext context) {
    final granted = state == RecordingConsentState.granted;
    return Card(
      color: granted ? const Color(0xFFECFDF5) : const Color(0xFFFEF2F2),
      child: Padding(
        padding: const EdgeInsets.all(18),
        child: Column(
          children: [
            Icon(
              granted ? Icons.verified_user_outlined : Icons.mic_off_outlined,
              size: 42,
              color: granted ? const Color(0xFF047857) : ClinicianColors.danger,
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
                  ? 'La capture audio reste PLANNED (HC-038) : aucun microphone n’est activé dans cette démo.'
                  : 'Le refus est respecté. Aucun son n’est capturé et la consultation peut continuer sans enregistrement.',
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
            'MOCKED D1 · Décision conservée uniquement dans l’écran. Aucun audio, stockage, contrat API ou consentement juridiquement opposable.',
            style: TextStyle(color: ClinicianColors.demo, height: 1.4),
          ),
        ),
      ],
    );
  }
}
