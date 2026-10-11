import 'package:flutter/material.dart';

import '../demo/canonical_clinician.dart';
import 'clinician_destination.dart';
import 'clinician_labels.dart';
import 'clinician_theme.dart';
import 'patient_detail_screen.dart';

/// Clinician dashboard (HC-031, D1): a read-only summary of the fictional
/// authorized context of `clin-x` on the canonical demo day. Every figure is
/// computed from presentation fixtures; nothing is fetched or stored.
class ClinicianDashboard extends StatelessWidget {
  const ClinicianDashboard({super.key, required this.onNavigate});

  final ValueChanged<ClinicianDestination> onNavigate;

  @override
  Widget build(BuildContext context) {
    final appointments =
        demoAppointments
            .where(
              (a) => a.date == demoReferenceDate && a.status == 'scheduled',
            )
            .toList()
          ..sort((a, b) => a.scheduledAt.compareTo(b.scheduledAt));
    final authorizedPatients = demoAccessGrants
        .where((g) => g.isActiveOn(demoReferenceDate))
        .map((g) => g.patientId)
        .toSet();
    final alerts = demoAlerts.where((a) => a.status == 'unresolved').toList()
      ..sort((a, b) {
        final bySeverity = _severityRank(
          a.severity,
        ).compareTo(_severityRank(b.severity));
        return bySeverity != 0
            ? bySeverity
            : b.createdAt.compareTo(a.createdAt);
      });
    final queue = [...demoPriorityQueue]
      ..sort((a, b) => a.rank.compareTo(b.rank));

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Bonjour ${demoClinician.title} ${demoClinician.lastName}',
          style: Theme.of(context).textTheme.headlineSmall,
        ),
        const SizedBox(height: 6),
        Text(
          '${demoClinician.specialty} · ${demoClinician.organizationName}',
          style: const TextStyle(color: ClinicianColors.muted, fontSize: 16),
        ),
        const SizedBox(height: 4),
        Text(
          'Journée de démonstration du ${formatDemoDate(demoReferenceDate)}',
          style: const TextStyle(
            color: ClinicianColors.demo,
            fontWeight: FontWeight.w600,
          ),
        ),
        const SizedBox(height: 16),
        const _BoundaryNote(),
        const SizedBox(height: 20),
        GridView.count(
          crossAxisCount: 2,
          shrinkWrap: true,
          physics: const NeverScrollableScrollPhysics(),
          mainAxisSpacing: 12,
          crossAxisSpacing: 12,
          childAspectRatio: 1.6,
          children: [
            _Metric(
              key: const ValueKey('metric-appointments'),
              icon: Icons.event_rounded,
              value: appointments.length,
              label: 'rendez-vous aujourd’hui',
              onTap: () => onNavigate(ClinicianDestination.consultation),
            ),
            _Metric(
              key: const ValueKey('metric-patients'),
              icon: Icons.people_rounded,
              value: authorizedPatients.length,
              label: 'patients autorisés',
              onTap: () => onNavigate(ClinicianDestination.patients),
            ),
            _Metric(
              key: const ValueKey('metric-alerts'),
              icon: Icons.notifications_rounded,
              value: alerts.length,
              label: 'alertes non résolues',
              onTap: () => onNavigate(ClinicianDestination.alerts),
            ),
            _Metric(
              key: const ValueKey('metric-queue'),
              icon: Icons.format_list_numbered_rounded,
              value: queue.length,
              label: 'patients dans la file',
              onTap: () => onNavigate(ClinicianDestination.queue),
            ),
          ],
        ),
        const SizedBox(height: 24),
        _SectionHeader(
          title: 'Rendez-vous du jour',
          onSeeAll: () => onNavigate(ClinicianDestination.consultation),
        ),
        if (appointments.isEmpty)
          const _EmptySection(message: 'Aucun rendez-vous programmé ce jour.')
        else
          for (final appointment in appointments)
            _AppointmentTile(appointment: appointment),
        const SizedBox(height: 24),
        _SectionHeader(
          title: 'Alertes à revoir',
          onSeeAll: () => onNavigate(ClinicianDestination.alerts),
        ),
        if (alerts.isEmpty)
          const _EmptySection(message: 'Aucune alerte non résolue.')
        else
          for (final alert in alerts) _AlertTile(alert: alert),
        const SizedBox(height: 8),
        const _Footnote(
          'Alertes fictives et consultatives : elles ne remplacent pas le jugement clinique.',
        ),
        const SizedBox(height: 24),
        _SectionHeader(
          title: 'File de priorité',
          onSeeAll: () => onNavigate(ClinicianDestination.queue),
        ),
        if (queue.isEmpty)
          const _EmptySection(message: 'Aucun patient dans la file.')
        else
          for (final entry in queue) _QueueTile(entry: entry),
        const SizedBox(height: 8),
        const _Footnote(
          'Priorités déterministes simulées (MOCKED), pas un triage clinique. $demoPriorityMethodDescription',
        ),
      ],
    );
  }
}

int _severityRank(String severity) => switch (severity) {
  'high' => 0,
  'medium' => 1,
  'low' => 2,
  _ => 3,
};

class _BoundaryNote extends StatelessWidget {
  const _BoundaryNote();

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: ClinicianColors.brandSoft,
        borderRadius: BorderRadius.circular(14),
      ),
      child: const Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(Icons.shield_outlined, color: ClinicianColors.brand),
          SizedBox(width: 10),
          Expanded(
            child: Text(
              'Contexte patient autorisé uniquement : cette application ne se connecte à aucune base hospitalière. L’IA reste une aide soumise à votre validation.',
              style: TextStyle(color: ClinicianColors.ink, height: 1.4),
            ),
          ),
        ],
      ),
    );
  }
}

class _Metric extends StatelessWidget {
  const _Metric({
    super.key,
    required this.icon,
    required this.value,
    required this.label,
    required this.onTap,
  });

  final IconData icon;
  final int value;
  final String label;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Card(
      clipBehavior: Clip.antiAlias,
      child: InkWell(
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.all(14),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Row(
                children: [
                  Icon(icon, color: ClinicianColors.brand, size: 22),
                  const Spacer(),
                  Text(
                    '$value',
                    style: const TextStyle(
                      color: ClinicianColors.ink,
                      fontSize: 26,
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                ],
              ),
              Text(label, maxLines: 2, overflow: TextOverflow.ellipsis),
            ],
          ),
        ),
      ),
    );
  }
}

class _SectionHeader extends StatelessWidget {
  const _SectionHeader({required this.title, required this.onSeeAll});

  final String title;
  final VoidCallback onSeeAll;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Row(
        children: [
          Expanded(
            child: Text(title, style: Theme.of(context).textTheme.titleLarge),
          ),
          TextButton(
            onPressed: onSeeAll,
            child: Text('Voir', semanticsLabel: 'Voir : $title'),
          ),
        ],
      ),
    );
  }
}

class _AppointmentTile extends StatelessWidget {
  const _AppointmentTile({required this.appointment});

  final CanonicalAppointment appointment;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Card(
        child: ListTile(
          onTap: () => openPatientDetail(context, appointment.patientId),
          contentPadding: const EdgeInsets.symmetric(
            horizontal: 16,
            vertical: 6,
          ),
          leading: Text(
            appointment.time,
            style: const TextStyle(
              color: ClinicianColors.brand,
              fontSize: 16,
              fontWeight: FontWeight.w800,
            ),
          ),
          title: Text(
            demoPatientName(appointment.patientId),
            style: Theme.of(context).textTheme.titleMedium,
          ),
          subtitle: Text(appointment.reason),
          trailing: const LabelTag(
            label: 'Programmé',
            color: ClinicianColors.brand,
            background: ClinicianColors.brandSoft,
          ),
        ),
      ),
    );
  }
}

class _AlertTile extends StatelessWidget {
  const _AlertTile({required this.alert});

  final CanonicalAlert alert;

  @override
  Widget build(BuildContext context) {
    final (label, color, background) = severityStyle(alert.severity);
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Card(
        child: ListTile(
          onTap: () => openPatientDetail(context, alert.patientId),
          contentPadding: const EdgeInsets.symmetric(
            horizontal: 16,
            vertical: 6,
          ),
          leading: Icon(Icons.warning_amber_rounded, color: color),
          title: Text(
            alert.title,
            style: Theme.of(context).textTheme.titleMedium,
          ),
          subtitle: Text(
            '${demoPatientName(alert.patientId)} · ${formatDemoDate(alert.createdAt.substring(0, 10))}',
          ),
          trailing: LabelTag(
            label: label,
            color: color,
            background: background,
          ),
        ),
      ),
    );
  }
}

class _QueueTile extends StatelessWidget {
  const _QueueTile({required this.entry});

  final CanonicalQueueEntry entry;

  @override
  Widget build(BuildContext context) {
    final (label, color, background) = severityStyle(entry.priority);
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Card(
        child: ListTile(
          onTap: () => openPatientDetail(context, entry.patientId),
          contentPadding: const EdgeInsets.symmetric(
            horizontal: 16,
            vertical: 6,
          ),
          leading: CircleAvatar(
            radius: 16,
            backgroundColor: ClinicianColors.brandSoft,
            foregroundColor: ClinicianColors.brand,
            child: Text(
              '${entry.rank}',
              style: const TextStyle(fontWeight: FontWeight.w800),
            ),
          ),
          title: Text(
            demoPatientName(entry.patientId),
            style: Theme.of(context).textTheme.titleMedium,
          ),
          subtitle: Text(entry.reasons.join(' · ')),
          trailing: LabelTag(
            label: 'Priorité ${label.toLowerCase()}',
            color: color,
            background: background,
          ),
        ),
      ),
    );
  }
}

class _EmptySection extends StatelessWidget {
  const _EmptySection({required this.message});

  final String message;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(18),
        child: Text(message, textAlign: TextAlign.center),
      ),
    );
  }
}

class _Footnote extends StatelessWidget {
  const _Footnote(this.text);

  final String text;

  @override
  Widget build(BuildContext context) {
    return Text(
      text,
      style: const TextStyle(
        color: ClinicianColors.muted,
        fontSize: 12,
        height: 1.4,
      ),
    );
  }
}
