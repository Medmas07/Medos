import 'package:flutter/material.dart';

import '../demo/canonical_clinician.dart';
import 'clinician_labels.dart';
import 'clinician_theme.dart';

/// A patient `clin-x` may see on a date, with the grant that allows it.
typedef AuthorizedPatient = ({
  CanonicalPatientName patient,
  CanonicalAccessGrant grant,
});

/// Splits [grants] on [date] (`YYYY-MM-DD`): patients with an active grant,
/// soonest expiry first, and grants that no longer authorize anything
/// (expired or revoked). Pure, so every state is testable.
({List<AuthorizedPatient> authorized, List<CanonicalAccessGrant> ended})
authorizedPatientsOn(
  List<CanonicalAccessGrant> grants,
  List<CanonicalPatientName> patients,
  String date,
) {
  final byId = {for (final patient in patients) patient.id: patient};
  final authorized = <AuthorizedPatient>[
    for (final grant in grants)
      if (grant.isActiveOn(date))
        (patient: byId[grant.patientId]!, grant: grant),
  ]..sort((a, b) => a.grant.expiresAt.compareTo(b.grant.expiresAt));
  final ended = [
    for (final grant in grants)
      if (!grant.isActiveOn(date)) grant,
  ];
  return (authorized: authorized, ended: ended);
}

/// Whole days from [date] to the grant's expiry date.
int daysLeft(CanonicalAccessGrant grant, String date) => DateTime.parse(
  grant.expiresAt.substring(0, 10),
).difference(DateTime.parse(date)).inDays;

String scopeLabel(String kind) => switch (kind) {
  'encounters' => 'Parcours',
  'medications' => 'Médicaments',
  'labReports' => 'Laboratoires',
  _ => kind,
};

/// Authorized patient list (HC-033, D1): the patients who granted `clin-x`
/// scoped, temporary access, read from fictional HC-005 grants on the demo
/// day. MOCKED: nothing is asked of a Hospital Node or the Federation, and no
/// clinical record is loaded. The patient record and federated history are
/// HC-034 and HC-035.
class AuthorizedPatientsView extends StatelessWidget {
  const AuthorizedPatientsView({
    super.key,
    this.grants = demoAccessGrants,
    this.patients = demoPatients,
    this.date = demoReferenceDate,
  });

  final List<CanonicalAccessGrant> grants;
  final List<CanonicalPatientName> patients;
  final String date;

  @override
  Widget build(BuildContext context) {
    final (:authorized, :ended) = authorizedPatientsOn(grants, patients, date);
    final byId = {for (final patient in patients) patient.id: patient};

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Patients autorisés',
          style: Theme.of(context).textTheme.headlineSmall,
        ),
        const SizedBox(height: 6),
        Text(
          'Journée de démonstration du ${formatDemoDate(date)} · ${authorized.length} patient${authorized.length > 1 ? 's' : ''}',
          style: const TextStyle(
            color: ClinicianColors.demo,
            fontWeight: FontWeight.w600,
          ),
        ),
        const SizedBox(height: 16),
        const _AuthorizationNotice(),
        const SizedBox(height: 20),
        if (authorized.isEmpty)
          const Card(
            key: ValueKey('authorized-empty'),
            child: Padding(
              padding: EdgeInsets.all(18),
              child: Text(
                'Aucun patient ne vous a accordé d’accès actif. Un patient apparaît ici dès qu’il vous en accorde un.',
                textAlign: TextAlign.center,
              ),
            ),
          )
        else
          for (final entry in authorized)
            _AuthorizedPatientCard(entry: entry, date: date),
        const SizedBox(height: 8),
        Text('Accès terminés', style: Theme.of(context).textTheme.titleMedium),
        const SizedBox(height: 8),
        if (ended.isEmpty)
          const Text(
            'Aucun accès expiré ou révoqué.',
            style: TextStyle(color: ClinicianColors.muted),
          )
        else
          for (final grant in ended)
            _EndedGrantTile(
              grant: grant,
              patientName:
                  byId[grant.patientId]?.displayName ?? grant.patientId,
            ),
        const SizedBox(height: 16),
        const _RecordPlanned(),
      ],
    );
  }
}

class _AuthorizationNotice extends StatelessWidget {
  const _AuthorizationNotice();

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
              Icon(Icons.verified_user_outlined, color: ClinicianColors.demo),
              SizedBox(width: 8),
              Expanded(
                child: Text(
                  'Autorisations fictives (MOCKED)',
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
            'Chaque patient listé vous a accordé un accès limité dans le temps et le périmètre. La liste vient des autorisations fictives de démonstration : aucun Hospital Node ni la Federation n’est interrogé, et aucun dossier clinique n’est chargé.',
            style: TextStyle(color: ClinicianColors.ink, height: 1.4),
          ),
        ],
      ),
    );
  }
}

class _AuthorizedPatientCard extends StatelessWidget {
  const _AuthorizedPatientCard({required this.entry, required this.date});

  final AuthorizedPatient entry;
  final String date;

  @override
  Widget build(BuildContext context) {
    final (:patient, :grant) = entry;
    final left = daysLeft(grant, date);

    return Padding(
      key: ValueKey('authorized-${patient.id}'),
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
                      '${patient.firstName[0]}${patient.lastName[0]}',
                      style: const TextStyle(fontWeight: FontWeight.w800),
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          patient.displayName,
                          style: Theme.of(context).textTheme.titleMedium,
                        ),
                        Text(
                          '${patient.ageOn(date)} ans',
                          style: const TextStyle(color: ClinicianColors.muted),
                        ),
                      ],
                    ),
                  ),
                  const LabelTag(
                    label: 'Accès actif',
                    color: Color(0xFF047857),
                    background: Color(0xFFECFDF5),
                  ),
                ],
              ),
              const SizedBox(height: 12),
              Text(
                grant.purpose,
                style: const TextStyle(fontWeight: FontWeight.w700),
              ),
              const SizedBox(height: 8),
              Wrap(
                spacing: 6,
                runSpacing: 6,
                children: [
                  for (final kind in grant.scope)
                    LabelTag(
                      label: scopeLabel(kind),
                      color: ClinicianColors.brand,
                      background: ClinicianColors.brandSoft,
                    ),
                ],
              ),
              const SizedBox(height: 10),
              Text(
                'Accordé le ${formatDemoDate(grant.grantedAt)} · jusqu’au ${formatDemoDate(grant.expiresAt)} ($left jour${left > 1 ? 's' : ''} restant${left > 1 ? 's' : ''})',
                style: const TextStyle(color: ClinicianColors.muted),
              ),
              Text(
                'Autorisation ${grant.id}',
                style: const TextStyle(
                  color: ClinicianColors.muted,
                  fontSize: 12,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _EndedGrantTile extends StatelessWidget {
  const _EndedGrantTile({required this.grant, required this.patientName});

  final CanonicalAccessGrant grant;
  final String patientName;

  @override
  Widget build(BuildContext context) {
    final reason = grant.status == 'revoked'
        ? 'Révoqué par le patient'
        : 'Expiré le ${formatDemoDate(grant.expiresAt)}';
    return ListTile(
      key: ValueKey('ended-${grant.id}'),
      contentPadding: EdgeInsets.zero,
      leading: const Icon(Icons.lock_clock_outlined),
      title: Text(patientName),
      subtitle: Text('$reason · aucun accès au dossier'),
    );
  }
}

class _RecordPlanned extends StatelessWidget {
  const _RecordPlanned();

  @override
  Widget build(BuildContext context) {
    return const Card(
      child: ListTile(
        leading: Icon(Icons.folder_shared_outlined),
        title: Text('Fiche patient et historique fédéré'),
        subtitle: Text(
          'PLANNED (HC-034, HC-035) : ouvrir un patient n’est pas encore disponible.',
        ),
      ),
    );
  }
}
