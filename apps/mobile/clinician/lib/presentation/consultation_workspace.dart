import 'package:flutter/material.dart';

import '../demo/canonical_clinician.dart';
import '../demo/canonical_consultation.dart';
import 'clinician_labels.dart';
import 'clinician_theme.dart';
import 'extraction_review.dart';
import 'extraction_review_card.dart';
import 'recording_consent_view.dart';

enum _WorkspacePhase { notStarted, inProgress, closed }

/// HC-036 consultation workspace: starts a consultation from the demo day's
/// appointments, frames the recording, transcription or intake steps, and
/// assembles a local draft. After a simulated transcript, the clinician reviews
/// the fictional AI extraction draft item by item (HC-040).
///
/// MOCKED D1: the consultation, its draft, and its notes live in this widget
/// only. Closing creates no clinical record and sends nothing.
class ConsultationWorkspace extends StatefulWidget {
  const ConsultationWorkspace({super.key});

  @override
  State<ConsultationWorkspace> createState() => _ConsultationWorkspaceState();
}

class _ConsultationWorkspaceState extends State<ConsultationWorkspace> {
  _WorkspacePhase _phase = _WorkspacePhase.notStarted;
  ConsultationCapture _capture = const ConsultationCapture(
    consent: RecordingConsentState.awaitingDecision,
    transcriptReady: false,
  );
  final _notes = TextEditingController();
  ExtractionPhase _extractionPhase = ExtractionPhase.idle;
  ExtractionReview _review = ExtractionReview(demoExtractionItems);
  int _extractionGeneration = 0;

  CanonicalAppointment get _appointment => demoAppointments.firstWhere(
    (appointment) => appointment.id == demoConsultationAppointmentId,
  );

  @override
  void dispose() {
    _notes.dispose();
    super.dispose();
  }

  bool get _extractionAvailable =>
      _capture.consent == RecordingConsentState.granted &&
      _capture.transcriptReady;

  void _onCaptureChanged(ConsultationCapture capture) {
    setState(() {
      _capture = capture;
      if (!_extractionAvailable) _resetExtraction();
    });
  }

  void _resetExtraction() {
    _extractionPhase = ExtractionPhase.idle;
    _review = ExtractionReview(demoExtractionItems);
    _extractionGeneration += 1;
  }

  Future<void> _runExtraction() async {
    final generation = ++_extractionGeneration;
    setState(() => _extractionPhase = ExtractionPhase.extracting);
    await Future<void>.delayed(const Duration(milliseconds: 800));
    if (!mounted || generation != _extractionGeneration) return;
    setState(() => _extractionPhase = ExtractionPhase.ready);
  }

  void _start() {
    setState(() => _phase = _WorkspacePhase.inProgress);
  }

  void _close() {
    setState(() => _phase = _WorkspacePhase.closed);
  }

  void _reset() {
    setState(() {
      _phase = _WorkspacePhase.notStarted;
      _capture = const ConsultationCapture(
        consent: RecordingConsentState.awaitingDecision,
        transcriptReady: false,
      );
      _notes.clear();
      _resetExtraction();
    });
  }

  Future<void> _confirmCancel() async {
    final cancel = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Annuler la consultation ?'),
        content: const Text(
          'Le brouillon et les notes de cette démonstration seront effacés.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Continuer la consultation'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(context, true),
            child: const Text('Annuler'),
          ),
        ],
      ),
    );
    if (cancel ?? false) _reset();
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Text(
          'Espace de consultation',
          style: Theme.of(context).textTheme.headlineSmall,
        ),
        const SizedBox(height: 6),
        const Text(
          'Consultation fondée uniquement sur le contexte patient autorisé.',
          style: TextStyle(color: ClinicianColors.muted, height: 1.4),
        ),
        const SizedBox(height: 16),
        ...switch (_phase) {
          _WorkspacePhase.notStarted => [_AppointmentPicker(onStart: _start)],
          _WorkspacePhase.inProgress => [
            _ConsultationHeader(appointment: _appointment, closed: false),
            const SizedBox(height: 12),
            _WorkflowSteps(
              capture: _capture,
              extractionPhase: _extractionPhase,
              review: _review,
            ),
            const SizedBox(height: 20),
            RecordingConsentView(onCaptureChanged: _onCaptureChanged),
            const SizedBox(height: 20),
            _DraftCard(capture: _capture, notes: _notes),
            const SizedBox(height: 12),
            if (_extractionAvailable) ...[
              ExtractionReviewCard(
                phase: _extractionPhase,
                review: _review,
                onStart: _runExtraction,
                onChanged: (review) => setState(() => _review = review),
                onFinish: () =>
                    setState(() => _extractionPhase = ExtractionPhase.finished),
                onReopen: () =>
                    setState(() => _extractionPhase = ExtractionPhase.ready),
              ),
              const SizedBox(height: 12),
            ],
            FilledButton.icon(
              key: const ValueKey('close-consultation'),
              onPressed: _hasSource(_capture) ? _close : null,
              icon: const Icon(Icons.task_alt_rounded),
              label: const Text('Clôturer la consultation'),
            ),
            if (!_hasSource(_capture)) ...[
              const SizedBox(height: 6),
              const Text(
                'Terminez la transcription ou l’anamnèse pour constituer le brouillon.',
                textAlign: TextAlign.center,
                style: TextStyle(color: ClinicianColors.muted),
              ),
            ],
            TextButton(
              onPressed: _confirmCancel,
              child: const Text('Annuler la consultation'),
            ),
          ],
          _WorkspacePhase.closed => [
            _ConsultationHeader(appointment: _appointment, closed: true),
            const SizedBox(height: 12),
            _ClosedSummary(
              capture: _capture,
              extractionPhase: _extractionPhase,
              review: _review,
              notes: _notes.text.trim(),
              onReset: _reset,
            ),
          ],
        },
      ],
    );
  }
}

bool _hasSource(ConsultationCapture capture) => switch (capture.consent) {
  RecordingConsentState.granted => capture.transcriptReady,
  RecordingConsentState.declined => capture.intakeSummary != null,
  RecordingConsentState.awaitingDecision => false,
};

class _AppointmentPicker extends StatelessWidget {
  const _AppointmentPicker({required this.onStart});

  final VoidCallback onStart;

  @override
  Widget build(BuildContext context) {
    final appointments = [
      for (final appointment in demoAppointments)
        if (appointment.date == demoReferenceDate) appointment,
    ]..sort((a, b) => a.scheduledAt.compareTo(b.scheduledAt));

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        const Card(
          child: ListTile(
            leading: Icon(Icons.event_note_outlined),
            title: Text('Aucune consultation en cours'),
            subtitle: Text(
              'Choisissez un rendez-vous du jour pour ouvrir l’espace de consultation.',
            ),
          ),
        ),
        const SizedBox(height: 12),
        Text(
          'Rendez-vous du ${formatDemoDate(demoReferenceDate)}',
          style: Theme.of(context).textTheme.titleMedium,
        ),
        const SizedBox(height: 8),
        for (final appointment in appointments)
          _AppointmentCard(appointment: appointment, onStart: onStart),
      ],
    );
  }
}

class _AppointmentCard extends StatelessWidget {
  const _AppointmentCard({required this.appointment, required this.onStart});

  final CanonicalAppointment appointment;
  final VoidCallback onStart;

  @override
  Widget build(BuildContext context) {
    final grant = demoActiveGrantFor(appointment.patientId, demoReferenceDate);
    final hasScenario = appointment.id == demoConsultationAppointmentId;
    final blockedReason = grant == null
        ? 'Aucun accès autorisé actif pour ce patient.'
        : hasScenario
        ? null
        : 'Aucun scénario de démonstration pour ce rendez-vous.';

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Text(
                  appointment.time,
                  style: const TextStyle(
                    color: ClinicianColors.brand,
                    fontWeight: FontWeight.w800,
                  ),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: Text(
                    demoPatientName(appointment.patientId),
                    style: Theme.of(context).textTheme.titleMedium,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 4),
            Text(appointment.reason),
            const SizedBox(height: 10),
            if (blockedReason == null)
              FilledButton.icon(
                key: ValueKey('start-consultation-${appointment.id}'),
                onPressed: onStart,
                icon: const Icon(Icons.play_arrow_rounded),
                label: const Text('Démarrer la consultation'),
              )
            else
              Text(
                blockedReason,
                style: const TextStyle(color: ClinicianColors.muted),
              ),
          ],
        ),
      ),
    );
  }
}

class _ConsultationHeader extends StatelessWidget {
  const _ConsultationHeader({required this.appointment, required this.closed});

  final CanonicalAppointment appointment;
  final bool closed;

  @override
  Widget build(BuildContext context) {
    final grant = demoActiveGrantFor(appointment.patientId, demoReferenceDate)!;
    return Card(
      color: ClinicianColors.brandSoft,
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(
                  child: Text(
                    demoPatientName(appointment.patientId),
                    style: Theme.of(context).textTheme.titleMedium,
                  ),
                ),
                closed
                    ? const LabelTag(
                        label: 'CLÔTURÉE',
                        color: ClinicianColors.muted,
                        background: Color(0xFFF1F5F9),
                      )
                    : const LabelTag(
                        label: 'EN COURS',
                        color: Color(0xFF047857),
                        background: Color(0xFFECFDF5),
                      ),
              ],
            ),
            const SizedBox(height: 4),
            Text(
              '${formatDemoDate(appointment.date)} · ${appointment.time} · '
              '${appointment.reason}',
            ),
            const SizedBox(height: 8),
            Row(
              children: [
                const Icon(
                  Icons.verified_user_outlined,
                  size: 18,
                  color: ClinicianColors.brand,
                ),
                const SizedBox(width: 6),
                Expanded(
                  child: Text(
                    'Accès autorisé jusqu’au '
                    '${formatDemoDate(grant.expiresAt.substring(0, 10))} '
                    '(${grant.id})',
                    style: const TextStyle(color: ClinicianColors.muted),
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

enum _StepStatus { pending, active, done, planned }

class _WorkflowSteps extends StatelessWidget {
  const _WorkflowSteps({
    required this.capture,
    required this.extractionPhase,
    required this.review,
  });

  final ConsultationCapture capture;
  final ExtractionPhase extractionPhase;
  final ExtractionReview review;

  @override
  Widget build(BuildContext context) {
    final declined = capture.consent == RecordingConsentState.declined;
    final decided = capture.consent != RecordingConsentState.awaitingDecision;
    final captured = _hasSource(capture);
    final steps = <(String, String, _StepStatus)>[
      (
        'Consentement à l’enregistrement',
        switch (capture.consent) {
          RecordingConsentState.awaitingDecision =>
            'En attente de la décision du patient',
          RecordingConsentState.granted => 'Accepté',
          RecordingConsentState.declined => 'Refusé',
        },
        decided ? _StepStatus.done : _StepStatus.active,
      ),
      (
        declined ? 'Anamnèse adaptative' : 'Transcription simulée',
        captured ? 'Terminée' : (decided ? 'En cours' : 'Après la décision'),
        captured
            ? _StepStatus.done
            : (decided ? _StepStatus.active : _StepStatus.pending),
      ),
      (
        'Brouillon de consultation',
        captured ? 'Prêt à clôturer' : 'En attente du recueil',
        captured ? _StepStatus.active : _StepStatus.pending,
      ),
      (
        'Extraction IA à relire',
        declined
            ? 'Pas d’extraction de démonstration pour l’anamnèse'
            : !captured
            ? 'Après la transcription'
            : switch (extractionPhase) {
                ExtractionPhase.idle => 'À lancer',
                ExtractionPhase.extracting => 'Extraction simulée en cours',
                ExtractionPhase.ready =>
                  '${review.count(ReviewDecision.pending)} suggestion(s) en attente',
                ExtractionPhase.finished => 'Revue terminée',
              },
        switch (extractionPhase) {
          ExtractionPhase.finished => _StepStatus.done,
          _ when captured && !declined => _StepStatus.active,
          _ => _StepStatus.pending,
        },
      ),
      (
        'Validation et dossier clinique',
        'PLANNED · aucun dossier créé',
        _StepStatus.planned,
      ),
    ];

    return Card(
      child: Padding(
        padding: const EdgeInsets.fromLTRB(16, 14, 16, 6),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Déroulé de la consultation',
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const SizedBox(height: 8),
            for (final (index, (title, detail, status)) in steps.indexed)
              _StepRow(
                number: index + 1,
                title: title,
                detail: detail,
                status: status,
              ),
          ],
        ),
      ),
    );
  }
}

class _StepRow extends StatelessWidget {
  const _StepRow({
    required this.number,
    required this.title,
    required this.detail,
    required this.status,
  });

  final int number;
  final String title;
  final String detail;
  final _StepStatus status;

  @override
  Widget build(BuildContext context) {
    final (icon, color) = switch (status) {
      _StepStatus.done => (Icons.check_circle_rounded, const Color(0xFF047857)),
      _StepStatus.active => (Icons.radio_button_checked, ClinicianColors.brand),
      _StepStatus.pending => (
        Icons.radio_button_unchecked,
        ClinicianColors.muted,
      ),
      _StepStatus.planned => (Icons.schedule_rounded, ClinicianColors.demo),
    };
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Row(
        children: [
          Icon(icon, size: 20, color: color),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  '$number. $title',
                  style: const TextStyle(fontWeight: FontWeight.w700),
                ),
                Text(detail, style: TextStyle(color: color, fontSize: 13)),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _DraftCard extends StatelessWidget {
  const _DraftCard({required this.capture, required this.notes});

  final ConsultationCapture capture;
  final TextEditingController notes;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Row(
              children: [
                Expanded(
                  child: Text(
                    'Brouillon de consultation',
                    style: Theme.of(context).textTheme.titleMedium,
                  ),
                ),
                const LabelTag(
                  label: 'BROUILLON',
                  color: ClinicianColors.demo,
                  background: ClinicianColors.demoSoft,
                ),
              ],
            ),
            const SizedBox(height: 6),
            const Text(
              'Non validé. Les éléments ci-dessous restent à relire par le clinicien.',
              style: TextStyle(color: ClinicianColors.muted),
            ),
            const Divider(height: 24),
            _DraftSource(capture: capture),
            const SizedBox(height: 12),
            TextField(
              key: const ValueKey('consultation-notes'),
              controller: notes,
              minLines: 3,
              maxLines: 6,
              decoration: const InputDecoration(
                labelText: 'Notes du clinicien',
                hintText: 'Observations, examen, conduite envisagée…',
                border: OutlineInputBorder(),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _DraftSource extends StatelessWidget {
  const _DraftSource({required this.capture});

  final ConsultationCapture capture;

  @override
  Widget build(BuildContext context) {
    if (!_hasSource(capture)) {
      return const Text(
        'Aucun recueil pour l’instant : le brouillon se remplit après la transcription ou l’anamnèse.',
        key: ValueKey('draft-empty'),
        style: TextStyle(color: ClinicianColors.muted),
      );
    }
    final summary = capture.intakeSummary;
    if (capture.consent == RecordingConsentState.declined && summary != null) {
      return _SourceBlock(
        title: 'Source : anamnèse adaptative',
        lines: [
          for (final line in summary) '${line.step.title} : ${line.answer}',
        ],
      );
    }
    return _SourceBlock(
      title: 'Source : transcription simulée',
      lines: [
        '${demoTranscriptSegments.length} segments du script fictif '
            '$demoConsultationScriptId',
        for (final segment in demoTranscriptSegments)
          if (segment.speaker == 'patient')
            '$demoConsultationPatientName : « ${segment.text} »',
      ],
    );
  }
}

class _SourceBlock extends StatelessWidget {
  const _SourceBlock({required this.title, required this.lines});

  final String title;
  final List<String> lines;

  @override
  Widget build(BuildContext context) {
    return Column(
      key: const ValueKey('draft-source'),
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(title, style: const TextStyle(fontWeight: FontWeight.w800)),
        for (final line in lines)
          Padding(padding: const EdgeInsets.only(top: 4), child: Text(line)),
      ],
    );
  }
}

class _ClosedSummary extends StatelessWidget {
  const _ClosedSummary({
    required this.capture,
    required this.extractionPhase,
    required this.review,
    required this.notes,
    required this.onReset,
  });

  final ConsultationCapture capture;
  final ExtractionPhase extractionPhase;
  final ExtractionReview review;
  final String notes;
  final VoidCallback onReset;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(
              'Consultation clôturée (démonstration)',
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const SizedBox(height: 6),
            const Text(
              'Le brouillon reste dans cet écran. Aucun dossier clinique n’est créé et rien n’est transmis ; la validation finale et le dossier clinique restent PLANNED.',
              style: TextStyle(color: ClinicianColors.muted),
            ),
            const Divider(height: 24),
            _DraftSource(capture: capture),
            const SizedBox(height: 12),
            const Text(
              'Notes du clinicien',
              style: TextStyle(fontWeight: FontWeight.w800),
            ),
            const SizedBox(height: 4),
            Text(notes.isEmpty ? 'Aucune note saisie.' : notes),
            if (capture.consent == RecordingConsentState.granted) ...[
              const SizedBox(height: 12),
              const Text(
                'Extraction IA retenue',
                style: TextStyle(fontWeight: FontWeight.w800),
              ),
              const SizedBox(height: 4),
              if (extractionPhase == ExtractionPhase.finished) ...[
                for (final item in review.items)
                  if (review.retainedText(item) case final text?)
                    Padding(
                      padding: const EdgeInsets.only(top: 2),
                      child: Text('• $text'),
                    ),
              ] else
                const Text(
                  'Revue non terminée : aucune suggestion n’est retenue.',
                  key: ValueKey('closed-extraction-not-reviewed'),
                ),
            ],
            const SizedBox(height: 16),
            OutlinedButton.icon(
              key: const ValueKey('new-consultation'),
              onPressed: onReset,
              icon: const Icon(Icons.event_note_outlined),
              label: const Text('Retour aux rendez-vous'),
            ),
          ],
        ),
      ),
    );
  }
}
