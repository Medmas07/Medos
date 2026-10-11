import 'package:flutter/material.dart';

import '../demo/canonical_clinician.dart';
import 'clinician_labels.dart';
import 'clinician_theme.dart';

/// Opens the fictional patient's detail page.
void openPatientDetail(BuildContext context, String patientId) {
  Navigator.of(context).push(
    MaterialPageRoute<void>(
      builder: (_) => PatientDetailScreen(patientId: patientId),
    ),
  );
}

/// Clinician patient detail (HC-034, D1): what `clin-x` may see about one
/// fictional patient on the demo day, from presentation fixtures. Without an
/// active access grant nothing about the patient is shown, not even a name.
class PatientDetailScreen extends StatelessWidget {
  const PatientDetailScreen({super.key, required this.patientId});

  final String patientId;

  @override
  Widget build(BuildContext context) {
    final grant = demoActiveGrantFor(patientId, demoReferenceDate);

    return Scaffold(
      appBar: AppBar(title: const Text('Fiche patient')),
      body: SafeArea(
        top: false,
        child: ListView(
          padding: const EdgeInsets.fromLTRB(20, 12, 20, 28),
          children: [
            const DemoBanner(),
            const SizedBox(height: 20),
            if (grant == null)
              const _NoAccess()
            else
              _AuthorizedDetail(
                patient: demoPatientById(patientId),
                grant: grant,
              ),
          ],
        ),
      ),
    );
  }
}

class _NoAccess extends StatelessWidget {
  const _NoAccess();

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          children: [
            const Icon(
              Icons.lock_outline_rounded,
              size: 48,
              color: ClinicianColors.danger,
            ),
            const SizedBox(height: 16),
            Text(
              'Accès non autorisé',
              textAlign: TextAlign.center,
              style: Theme.of(context).textTheme.titleLarge,
            ),
            const SizedBox(height: 8),
            const Text(
              'Aucun accès actif n’a été accordé par ce patient ce jour. Aucune information le concernant n’est affichée.',
              textAlign: TextAlign.center,
            ),
          ],
        ),
      ),
    );
  }
}

class _AuthorizedDetail extends StatelessWidget {
  const _AuthorizedDetail({required this.patient, required this.grant});

  final CanonicalPatient patient;
  final CanonicalAccessGrant grant;

  @override
  Widget build(BuildContext context) {
    final appointments =
        demoAppointments
            .where(
              (a) => a.patientId == patient.id && a.date == demoReferenceDate,
            )
            .toList()
          ..sort((a, b) => a.scheduledAt.compareTo(b.scheduledAt));
    final queueEntries = demoPriorityQueue
        .where((e) => e.patientId == patient.id)
        .toList();
    final alerts = demoAlerts
        .where((a) => a.patientId == patient.id && a.status == 'unresolved')
        .toList();

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        _IdentityCard(patient: patient),
        const SizedBox(height: 16),
        _Section(
          title: 'Accès autorisé',
          children: [
            Text(grant.purpose, style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 4),
            Text(
              'Accordé le ${_date(grant.grantedAt)} · jusqu’au ${_date(grant.expiresAt)}',
            ),
            const SizedBox(height: 10),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                for (final item in grant.scope)
                  LabelTag(
                    label: scopeLabel(item),
                    color: ClinicianColors.brand,
                    background: ClinicianColors.brandSoft,
                  ),
              ],
            ),
            const SizedBox(height: 10),
            const Text(
              'Vue autorisée par le patient, limitée à ce périmètre et à cette durée. Aucune copie du dossier hospitalier ; le patient peut retirer cet accès.',
              style: TextStyle(fontSize: 12, color: ClinicianColors.muted),
            ),
          ],
        ),
        _Section(
          title: 'Aujourd’hui',
          children: [
            if (appointments.isEmpty)
              const Text('Aucun rendez-vous ce jour.')
            else
              for (final appointment in appointments)
                Text('${appointment.time} · ${appointment.reason}'),
          ],
        ),
        _Section(
          title: 'File de priorité',
          children: [
            if (queueEntries.isEmpty)
              const Text('Ce patient n’est pas dans la file.')
            else
              for (final entry in queueEntries) _QueuePosition(entry: entry),
          ],
        ),
        _Section(
          title: 'Alertes non résolues',
          children: [
            if (alerts.isEmpty)
              const Text('Aucune alerte non résolue.')
            else
              for (final alert in alerts) _AlertRow(alert: alert),
            const SizedBox(height: 6),
            const Text(
              'Alertes fictives et consultatives.',
              style: TextStyle(fontSize: 12, color: ClinicianColors.muted),
            ),
          ],
        ),
        const _HistoryPlanned(),
      ],
    );
  }
}

String _date(String isoDateTime) =>
    formatDemoDate(isoDateTime.substring(0, 10));

class _IdentityCard extends StatelessWidget {
  const _IdentityCard({required this.patient});

  final CanonicalPatient patient;

  @override
  Widget build(BuildContext context) {
    final sex = patient.sex == 'female' ? 'Femme' : 'Homme';
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Row(
          children: [
            CircleAvatar(
              radius: 28,
              backgroundColor: ClinicianColors.brandSoft,
              foregroundColor: ClinicianColors.brand,
              child: Text(
                patient.initials,
                style: const TextStyle(
                  fontSize: 18,
                  fontWeight: FontWeight.w800,
                ),
              ),
            ),
            const SizedBox(width: 16),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    patient.displayName,
                    style: Theme.of(context).textTheme.titleLarge,
                  ),
                  const SizedBox(height: 4),
                  Text(
                    '$sex · ${patient.ageOn(demoReferenceDate)} ans · ${patient.city}',
                  ),
                  Text('Identifiant fédéré ${patient.federatedId}'),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _Section extends StatelessWidget {
  const _Section({required this.title, required this.children});

  final String title;
  final List<Widget> children;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 16),
      child: Card(
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(title, style: Theme.of(context).textTheme.titleMedium),
              const SizedBox(height: 10),
              ...children,
            ],
          ),
        ),
      ),
    );
  }
}

class _QueuePosition extends StatelessWidget {
  const _QueuePosition({required this.entry});

  final CanonicalQueueEntry entry;

  @override
  Widget build(BuildContext context) {
    final (label, color, background) = severityStyle(entry.priority);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Expanded(child: Text('Rang ${entry.rank}')),
            LabelTag(
              label: 'Priorité ${label.toLowerCase()}',
              color: color,
              background: background,
            ),
          ],
        ),
        const SizedBox(height: 4),
        Text(entry.reasons.join(' · ')),
        const SizedBox(height: 6),
        const Text(
          'Priorité déterministe simulée (MOCKED), pas un triage clinique.',
          style: TextStyle(fontSize: 12, color: ClinicianColors.muted),
        ),
      ],
    );
  }
}

class _AlertRow extends StatelessWidget {
  const _AlertRow({required this.alert});

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

class _HistoryPlanned extends StatelessWidget {
  const _HistoryPlanned();

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Icon(Icons.history_rounded, color: ClinicianColors.brand),
            const SizedBox(width: 10),
            const Expanded(
              child: Text(
                'Historique fédéré (consultations, médicaments, biologie des établissements autorisés) : livré par HC-035.',
              ),
            ),
            const SizedBox(width: 8),
            LabelTag(
              label: 'PLANNED',
              color: ClinicianColors.demo,
              background: ClinicianColors.demoSoft,
            ),
          ],
        ),
      ),
    );
  }
}
