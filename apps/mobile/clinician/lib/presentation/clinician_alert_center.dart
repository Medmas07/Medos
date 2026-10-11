import 'package:flutter/material.dart';

import '../demo/canonical_alerts.dart';
import 'clinician_theme.dart';

enum AlertCenterFilter { toReview, all }

class ClinicianAlertCenter extends StatefulWidget {
  const ClinicianAlertCenter({super.key});

  @override
  State<ClinicianAlertCenter> createState() => _ClinicianAlertCenterState();
}

class _ClinicianAlertCenterState extends State<ClinicianAlertCenter> {
  AlertCenterFilter _filter = AlertCenterFilter.toReview;
  final Set<String> _reviewedIds = {};

  @override
  Widget build(BuildContext context) {
    final visibleAlerts = _filter == AlertCenterFilter.all
        ? demoClinicianAlerts
        : demoClinicianAlerts
              .where((alert) => !_reviewedIds.contains(alert.id))
              .toList();

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Text(
          'Centre d’alertes',
          style: Theme.of(context).textTheme.headlineSmall,
        ),
        const SizedBox(height: 6),
        const Text(
          'Éléments fictifs à examiner par le clinicien. Leur ordre ne constitue pas un triage.',
          style: TextStyle(color: ClinicianColors.muted, height: 1.4),
        ),
        const SizedBox(height: 14),
        const _AlertBoundaryNote(),
        const SizedBox(height: 16),
        SegmentedButton<AlertCenterFilter>(
          segments: [
            ButtonSegment(
              value: AlertCenterFilter.toReview,
              icon: const Icon(Icons.mark_email_unread_outlined),
              label: Text(
                'À examiner (${demoClinicianAlerts.length - _reviewedIds.length})',
              ),
            ),
            const ButtonSegment(
              value: AlertCenterFilter.all,
              icon: Icon(Icons.notifications_outlined),
              label: Text('Toutes'),
            ),
          ],
          selected: {_filter},
          onSelectionChanged: (selection) {
            setState(() => _filter = selection.single);
          },
        ),
        const SizedBox(height: 16),
        if (visibleAlerts.isEmpty)
          _ReviewedEmptyState(
            onShowAll: () => setState(() => _filter = AlertCenterFilter.all),
          )
        else
          for (final alert in visibleAlerts) ...[
            _AlertCard(
              alert: alert,
              reviewed: _reviewedIds.contains(alert.id),
              onToggleReviewed: () {
                setState(() {
                  if (!_reviewedIds.add(alert.id)) {
                    _reviewedIds.remove(alert.id);
                  }
                });
              },
            ),
            const SizedBox(height: 12),
          ],
      ],
    );
  }
}

class _AlertBoundaryNote extends StatelessWidget {
  const _AlertBoundaryNote();

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: ClinicianColors.demoSoft,
        borderRadius: BorderRadius.circular(14),
      ),
      child: const Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(Icons.science_outlined, color: ClinicianColors.demo),
          SizedBox(width: 10),
          Expanded(
            child: Text(
              'MOCKED D1 · Alertes canoniques locales. Aucun flux temps réel, accusé persistant ou décision clinique automatisée.',
              style: TextStyle(color: ClinicianColors.demo, height: 1.4),
            ),
          ),
        ],
      ),
    );
  }
}

class _AlertCard extends StatelessWidget {
  const _AlertCard({
    required this.alert,
    required this.reviewed,
    required this.onToggleReviewed,
  });

  final DemoClinicianAlert alert;
  final bool reviewed;
  final VoidCallback onToggleReviewed;

  @override
  Widget build(BuildContext context) {
    final (label, color, background, icon) = switch (alert.severity) {
      'high' => (
        'Priorité haute · démo',
        ClinicianColors.danger,
        const Color(0xFFFEF2F2),
        Icons.error_outline_rounded,
      ),
      'medium' => (
        'Priorité moyenne · démo',
        const Color(0xFFB45309),
        const Color(0xFFFFFBEB),
        Icons.schedule_outlined,
      ),
      _ => (
        'Information · démo',
        ClinicianColors.brand,
        ClinicianColors.brandSoft,
        Icons.info_outline_rounded,
      ),
    };

    return Card(
      key: ValueKey('alert-${alert.id}'),
      child: Padding(
        padding: const EdgeInsets.all(18),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Container(
                  width: 42,
                  height: 42,
                  decoration: BoxDecoration(
                    color: background,
                    borderRadius: BorderRadius.circular(13),
                  ),
                  child: Icon(icon, color: color),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        alert.title,
                        style: Theme.of(context).textTheme.titleMedium,
                      ),
                      const SizedBox(height: 4),
                      Text(
                        '${alert.patientName} · ${_displayDate(alert.createdAt)}',
                        style: const TextStyle(color: ClinicianColors.muted),
                      ),
                    ],
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 5),
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
            const SizedBox(height: 12),
            Text(alert.detail),
            const SizedBox(height: 8),
            Text(
              'Source fictive : ${alert.sourceRecordId}',
              style: const TextStyle(
                color: ClinicianColors.muted,
                fontSize: 12,
              ),
            ),
            const SizedBox(height: 12),
            Align(
              alignment: Alignment.centerRight,
              child: reviewed
                  ? TextButton.icon(
                      key: ValueKey('restore-${alert.id}'),
                      onPressed: onToggleReviewed,
                      icon: const Icon(Icons.undo_rounded),
                      label: const Text('Remettre à examiner'),
                    )
                  : FilledButton.tonalIcon(
                      key: ValueKey('review-${alert.id}'),
                      onPressed: onToggleReviewed,
                      icon: const Icon(Icons.check_rounded),
                      label: const Text('Marquer comme examinée'),
                    ),
            ),
          ],
        ),
      ),
    );
  }

  String _displayDate(String value) {
    final date = DateTime.parse(value);
    return '${date.day.toString().padLeft(2, '0')}/${date.month.toString().padLeft(2, '0')}/${date.year}';
  }
}

class _ReviewedEmptyState extends StatelessWidget {
  const _ReviewedEmptyState({required this.onShowAll});

  final VoidCallback onShowAll;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          children: [
            const Icon(
              Icons.task_alt_rounded,
              size: 46,
              color: Color(0xFF047857),
            ),
            const SizedBox(height: 12),
            Text(
              'Toutes les alertes ont été examinées',
              textAlign: TextAlign.center,
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const SizedBox(height: 6),
            const Text(
              'État local de démonstration, réinitialisé à la fermeture de l’application.',
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 12),
            OutlinedButton(
              onPressed: onShowAll,
              child: const Text('Afficher toutes les alertes'),
            ),
          ],
        ),
      ),
    );
  }
}
