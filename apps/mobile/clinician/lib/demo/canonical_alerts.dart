/// Presentation-only copy of the HC-005 fictional clinician alerts.
///
/// These are not live notifications or clinical guidance. Tests verify this
/// copy against `demo-data/clinician.json`.
class DemoClinicianAlert {
  const DemoClinicianAlert({
    required this.id,
    required this.patientId,
    required this.patientName,
    required this.type,
    required this.severity,
    required this.title,
    required this.detail,
    required this.sourceRecordId,
    required this.createdAt,
  });

  final String id;
  final String patientId;
  final String patientName;
  final String type;
  final String severity;
  final String title;
  final String detail;
  final String sourceRecordId;
  final String createdAt;
}

const demoClinicianAlerts = <DemoClinicianAlert>[
  DemoClinicianAlert(
    id: 'alert-b-hba1c',
    patientId: 'pat-b',
    patientName: 'Karim Haddad',
    type: 'abnormal_lab',
    severity: 'high',
    title: 'HbA1c au-dessus de la plage de référence',
    detail: 'HbA1c 8,9 % (référence 4,0-6,0 %), prélevé le 30/09/2026.',
    sourceRecordId: 'lab-a-2026-karim',
    createdAt: '2026-09-30T16:00:00+01:00',
  ),
  DemoClinicianAlert(
    id: 'alert-b-followup',
    patientId: 'pat-b',
    patientName: 'Karim Haddad',
    type: 'missed_follow_up',
    severity: 'medium',
    title: 'Suivi en retard',
    detail: 'Contrôle prévu à 12 mois non réalisé dans les délais.',
    sourceRecordId: 'enc-a-2025-karim',
    createdAt: '2026-09-16T08:00:00+01:00',
  ),
  DemoClinicianAlert(
    id: 'alert-a-external',
    patientId: 'pat-a',
    patientName: 'Leïla Mansouri',
    type: 'new_external_consultation',
    severity: 'low',
    title: 'Nouvelle consultation externe',
    detail:
        'Consultation de médecine interne à l’Hôpital Régional Oued Zitoun, avec instauration d’un traitement.',
    sourceRecordId: 'enc-b-2026-leila',
    createdAt: '2026-10-10T09:01:00+01:00',
  ),
];
