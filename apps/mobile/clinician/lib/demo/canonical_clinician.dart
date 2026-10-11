/// Presentation-only fixture copied from HC-005's canonical fictional dataset
/// (`clin-x` in `demo-data/people.json`, `org-hospital-a` in
/// `demo-data/organizations.json`).
///
/// This is not an identity, authorization, or clinical domain model and must
/// be replaced by an authenticated session and authorized clinical-context
/// contracts when they exist.
class CanonicalClinicianPreview {
  const CanonicalClinicianPreview({
    required this.id,
    required this.title,
    required this.firstName,
    required this.lastName,
    required this.roleLabel,
    required this.specialty,
    required this.organizationId,
    required this.organizationName,
  });

  final String id;
  final String title;
  final String firstName;
  final String lastName;
  final String roleLabel;
  final String specialty;
  final String organizationId;
  final String organizationName;

  String get displayName => '$title $firstName $lastName';

  String get initials => '${firstName[0]}${lastName[0]}';
}

const demoClinician = CanonicalClinicianPreview(
  id: 'clin-x',
  title: 'Dr',
  firstName: 'Youssef',
  lastName: 'Gharbi',
  roleLabel: 'Médecin',
  specialty: 'Cardiologie',
  organizationId: 'org-hospital-a',
  organizationName: 'Hôpital Universitaire Bab Ennour',
);

/// The canonical demo day (`referenceDate` in `demo-data/manifest.json`).
/// The dashboard is computed against it, never against the device clock.
const demoReferenceDate = '2026-10-10';

class CanonicalPatient {
  const CanonicalPatient({
    required this.id,
    required this.federatedId,
    required this.firstName,
    required this.lastName,
    required this.sex,
    required this.birthDate,
    required this.city,
  });

  final String id;
  final String federatedId;
  final String firstName;
  final String lastName;
  final String sex;
  final String birthDate;
  final String city;

  String get displayName => '$firstName $lastName';

  String get initials => '${firstName[0]}${lastName[0]}';

  /// Age in whole years on [date] (`YYYY-MM-DD`).
  int ageOn(String date) {
    final years =
        int.parse(date.substring(0, 4)) - int.parse(birthDate.substring(0, 4));
    final hadBirthday =
        date.substring(5).compareTo(birthDate.substring(5)) >= 0;
    return hadBirthday ? years : years - 1;
  }
}

/// The fictional patients appearing in `clin-x`'s demo data
/// (`demo-data/people.json`). Local hospital identifiers are left out.
const demoPatients = <CanonicalPatient>[
  CanonicalPatient(
    id: 'pat-a',
    federatedId: 'FED-PAT-0001',
    firstName: 'Leïla',
    lastName: 'Mansouri',
    sex: 'female',
    birthDate: '1968-04-17',
    city: 'Tunis',
  ),
  CanonicalPatient(
    id: 'pat-b',
    federatedId: 'FED-PAT-0002',
    firstName: 'Karim',
    lastName: 'Haddad',
    sex: 'male',
    birthDate: '1979-11-02',
    city: 'Ariana',
  ),
];

CanonicalPatient demoPatientById(String patientId) =>
    demoPatients.firstWhere((patient) => patient.id == patientId);

String demoPatientName(String patientId) =>
    demoPatientById(patientId).displayName;

/// `clin-x`'s access grants (`demo-data/access.json`).
class CanonicalAccessGrant {
  const CanonicalAccessGrant({
    required this.id,
    required this.patientId,
    required this.scope,
    required this.purpose,
    required this.status,
    required this.grantedAt,
    required this.expiresAt,
  });

  final String id;
  final String patientId;

  /// Record kinds the patient authorized: `encounters`, `medications`,
  /// `labReports`.
  final List<String> scope;
  final String purpose;
  final String status;
  final String grantedAt;
  final String expiresAt;

  bool isActiveOn(String date) =>
      status == 'active' && expiresAt.substring(0, 10).compareTo(date) > 0;
}

const demoAccessGrants = <CanonicalAccessGrant>[
  CanonicalAccessGrant(
    id: 'grant-a-drx',
    patientId: 'pat-a',
    scope: ['encounters', 'medications', 'labReports'],
    purpose: 'Consultation de cardiologie',
    status: 'active',
    grantedAt: '2026-10-10T09:00:00+01:00',
    expiresAt: '2026-10-24T09:00:00+01:00',
  ),
  CanonicalAccessGrant(
    id: 'grant-b-drx',
    patientId: 'pat-b',
    scope: ['encounters', 'medications', 'labReports'],
    purpose: 'Suivi du diabète',
    status: 'active',
    grantedAt: '2025-09-15T09:45:00+01:00',
    expiresAt: '2026-12-31T23:59:00+01:00',
  ),
];

/// `clin-x`'s appointments (`demo-data/clinician.json`).
class CanonicalAppointment {
  const CanonicalAppointment({
    required this.id,
    required this.patientId,
    required this.scheduledAt,
    required this.reason,
    required this.status,
  });

  final String id;
  final String patientId;
  final String scheduledAt;
  final String reason;
  final String status;

  String get date => scheduledAt.substring(0, 10);

  /// Wall-clock time in the fixture's own offset.
  String get time => scheduledAt.substring(11, 16);
}

const demoAppointments = <CanonicalAppointment>[
  CanonicalAppointment(
    id: 'appt-a-2026-10-10',
    patientId: 'pat-a',
    scheduledAt: '2026-10-10T10:30:00+01:00',
    reason: 'Douleur du genou droit et contrôle cardiologique',
    status: 'scheduled',
  ),
  CanonicalAppointment(
    id: 'appt-b-2026-10-10',
    patientId: 'pat-b',
    scheduledAt: '2026-10-10T11:30:00+01:00',
    reason: 'Restitution du bilan de suivi du diabète',
    status: 'scheduled',
  ),
];

/// `clin-x`'s alerts (`demo-data/clinician.json`). They are fictional and
/// advisory; the alert center (HC-043) will show their details.
class CanonicalAlert {
  const CanonicalAlert({
    required this.id,
    required this.patientId,
    required this.severity,
    required this.title,
    required this.createdAt,
    required this.status,
  });

  final String id;
  final String patientId;
  final String severity;
  final String title;
  final String createdAt;
  final String status;
}

const demoAlerts = <CanonicalAlert>[
  CanonicalAlert(
    id: 'alert-b-hba1c',
    patientId: 'pat-b',
    severity: 'high',
    title: 'HbA1c au-dessus de la plage de référence',
    createdAt: '2026-09-30T16:00:00+01:00',
    status: 'unresolved',
  ),
  CanonicalAlert(
    id: 'alert-b-followup',
    patientId: 'pat-b',
    severity: 'medium',
    title: 'Suivi en retard',
    createdAt: '2026-09-16T08:00:00+01:00',
    status: 'unresolved',
  ),
  CanonicalAlert(
    id: 'alert-a-external',
    patientId: 'pat-a',
    severity: 'low',
    title: 'Nouvelle consultation externe',
    createdAt: '2026-10-10T09:01:00+01:00',
    status: 'unresolved',
  ),
];

/// `clin-x`'s priority queue (`demo-data/clinician.json`), ranked by a
/// deterministic mock method. It is not clinical triage.
class CanonicalQueueEntry {
  const CanonicalQueueEntry({
    required this.id,
    required this.patientId,
    required this.rank,
    required this.priority,
    required this.score,
    required this.reasons,
    required this.alertIds,
  });

  final String id;
  final String patientId;
  final int rank;
  final String priority;

  /// Fixed-weight demonstration score; not a clinical measure.
  final int score;
  final List<String> reasons;
  final List<String> alertIds;
}

const demoPriorityQueue = <CanonicalQueueEntry>[
  CanonicalQueueEntry(
    id: 'queue-clin-x-1',
    patientId: 'pat-b',
    rank: 1,
    priority: 'high',
    score: 82,
    alertIds: ['alert-b-hba1c', 'alert-b-followup'],
    reasons: ['Résultat biologique anormal non revu', 'Suivi en retard'],
  ),
  CanonicalQueueEntry(
    id: 'queue-clin-x-2',
    patientId: 'pat-a',
    rank: 2,
    priority: 'medium',
    score: 55,
    alertIds: ['alert-a-external'],
    reasons: [
      'Nouvelle consultation externe',
      'Traitement anticoagulant actif',
    ],
  ),
];

/// `priorityMethod.description` in `demo-data/clinician.json`.
const demoPriorityMethodDescription =
    "Score = somme de poids fixes par type d'alerte non résolue. Méthode de démonstration, non validée cliniquement, qui ne remplace pas le jugement clinique.";

CanonicalAlert demoAlertById(String alertId) =>
    demoAlerts.firstWhere((alert) => alert.id == alertId);

/// The patient's access grant active on [date], if any.
CanonicalAccessGrant? demoActiveGrantFor(String patientId, String date) {
  for (final grant in demoAccessGrants) {
    if (grant.patientId == patientId && grant.isActiveOn(date)) return grant;
  }
  return null;
}
