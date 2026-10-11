import 'package:flutter/material.dart';

import '../demo/canonical_clinician.dart';
import 'clinician_labels.dart';
import 'clinician_theme.dart';
import 'patient_detail_screen.dart';

/// Priority patient queue (HC-032, D1): `clin-x`'s fictional queue in rank
/// order with hard-coded deterministic priorities and their visible reasons.
/// The app displays the fixture's ranking; it computes, ranks, and triages
/// nothing, and no AI is involved.
class PriorityQueueView extends StatelessWidget {
  const PriorityQueueView({super.key});

  @override
  Widget build(BuildContext context) {
    final queue = [...demoPriorityQueue]
      ..sort((a, b) => a.rank.compareTo(b.rank));

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'File de priorité',
          style: Theme.of(context).textTheme.headlineSmall,
        ),
        const SizedBox(height: 6),
        Text(
          'Journée de démonstration du ${formatDemoDate(demoReferenceDate)} · ${queue.length} patients',
          style: const TextStyle(
            color: ClinicianColors.demo,
            fontWeight: FontWeight.w600,
          ),
        ),
        const SizedBox(height: 16),
        const _MethodNotice(),
        const SizedBox(height: 20),
        if (queue.isEmpty)
          const Card(
            child: Padding(
              padding: EdgeInsets.all(18),
              child: Text(
                'Aucun patient dans la file.',
                textAlign: TextAlign.center,
              ),
            ),
          )
        else
          for (final entry in queue) _QueueEntryCard(entry: entry),
        const SizedBox(height: 4),
        const _ExplanationPlanned(),
      ],
    );
  }
}

class _MethodNotice extends StatelessWidget {
  const _MethodNotice();

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: ClinicianColors.demoSoft,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: const Color(0xFFDDD6FE)),
      ),
      child: const Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(Icons.rule_rounded, color: ClinicianColors.demo),
              SizedBox(width: 8),
              Expanded(
                child: Text(
                  'Priorités déterministes simulées (MOCKED)',
                  style: TextStyle(
                    color: ClinicianColors.demo,
                    fontWeight: FontWeight.w800,
                  ),
                ),
              ),
            ],
          ),
          SizedBox(height: 8),
          Text(
            'Ordre codé en dur par une méthode de démonstration, sans IA. Ce n’est pas un triage clinique : l’ordre de prise en charge reste votre décision.',
            style: TextStyle(color: ClinicianColors.ink, height: 1.4),
          ),
          SizedBox(height: 6),
          Text(demoPriorityMethodDescription),
        ],
      ),
    );
  }
}

class _QueueEntryCard extends StatelessWidget {
  const _QueueEntryCard({required this.entry});

  final CanonicalQueueEntry entry;

  @override
  Widget build(BuildContext context) {
    final (label, color, background) = severityStyle(entry.priority);
    final grant = demoActiveGrantFor(entry.patientId, demoReferenceDate);

    return Padding(
      key: ValueKey('queue-entry-${entry.id}'),
      padding: const EdgeInsets.only(bottom: 12),
      child: Card(
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  CircleAvatar(
                    radius: 18,
                    backgroundColor: ClinicianColors.brandSoft,
                    foregroundColor: ClinicianColors.brand,
                    child: Text(
                      '${entry.rank}',
                      style: const TextStyle(fontWeight: FontWeight.w800),
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Text(
                      demoPatientName(entry.patientId),
                      style: Theme.of(context).textTheme.titleMedium,
                    ),
                  ),
                  LabelTag(
                    label: 'Priorité ${label.toLowerCase()}',
                    color: color,
                    background: background,
                  ),
                ],
              ),
              const SizedBox(height: 6),
              Padding(
                padding: const EdgeInsets.only(left: 48),
                child: Text(
                  'Score de démonstration : ${entry.score}',
                  style: const TextStyle(
                    color: ClinicianColors.muted,
                    fontSize: 12,
                  ),
                ),
              ),
              const SizedBox(height: 12),
              const _SubHeading('Motifs'),
              for (final reason in entry.reasons)
                _Bullet(icon: Icons.chevron_right_rounded, text: reason),
              const SizedBox(height: 10),
              const _SubHeading('Alertes à l’origine'),
              for (final alertId in entry.alertIds)
                _LinkedAlert(alert: demoAlertById(alertId)),
              const SizedBox(height: 10),
              _Bullet(
                icon: Icons.verified_user_outlined,
                text: grant == null
                    ? 'Aucun accès actif ce jour'
                    : 'Accès autorisé jusqu’au ${formatDemoDate(grant.expiresAt.substring(0, 10))}',
              ),
              Align(
                alignment: Alignment.centerRight,
                child: TextButton.icon(
                  onPressed: () => openPatientDetail(context, entry.patientId),
                  icon: const Icon(Icons.person_search_outlined),
                  label: const Text('Ouvrir la fiche'),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _SubHeading extends StatelessWidget {
  const _SubHeading(this.text);

  final String text;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 4),
      child: Text(
        text,
        style: const TextStyle(
          color: ClinicianColors.ink,
          fontSize: 13,
          fontWeight: FontWeight.w700,
        ),
      ),
    );
  }
}

class _Bullet extends StatelessWidget {
  const _Bullet({required this.icon, required this.text});

  final IconData icon;
  final String text;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 2),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, size: 18, color: ClinicianColors.brand),
          const SizedBox(width: 6),
          Expanded(child: Text(text)),
        ],
      ),
    );
  }
}

class _LinkedAlert extends StatelessWidget {
  const _LinkedAlert({required this.alert});

  final CanonicalAlert alert;

  @override
  Widget build(BuildContext context) {
    final (label, color, background) = severityStyle(alert.severity);
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 3),
      child: Row(
        children: [
          Icon(Icons.warning_amber_rounded, size: 18, color: color),
          const SizedBox(width: 6),
          Expanded(child: Text(alert.title)),
          const SizedBox(width: 8),
          LabelTag(label: label, color: color, background: background),
        ],
      ),
    );
  }
}

class _ExplanationPlanned extends StatelessWidget {
  const _ExplanationPlanned();

  @override
  Widget build(BuildContext context) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Expanded(
          child: Text(
            'L’explication détaillée de chaque priorité sera livrée par HC-044.',
            style: TextStyle(color: ClinicianColors.muted, fontSize: 12),
          ),
        ),
        const SizedBox(width: 8),
        LabelTag(
          label: 'PLANNED',
          color: ClinicianColors.demo,
          background: ClinicianColors.demoSoft,
        ),
      ],
    );
  }
}
