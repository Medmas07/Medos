/// Presentation-only copy of the authorized history the Federation would
/// return for `clin-x`'s patients, shaped like `FederatedQueryResult` in
/// `contracts/federation/federated-patient-query.v1.yaml` (HC-035, D1).
///
/// The entries are Patient A's and Patient B's records in the three HC-005
/// `demo-data/records/` files. This is not a clinical model and no request is
/// made: the app has no HTTP client. Checked against `demo-data/` by tests.
library;

/// One timeline entry with the organization and node holding it.
class FederatedEntry {
  const FederatedEntry({
    required this.entryRef,
    required this.patientId,
    required this.recordType,
    required this.occurredAt,
    required this.organizationRef,
    required this.nodeRef,
    required this.title,
    required this.detail,
    this.clinicianRef,
  });

  final String entryRef;
  final String patientId;

  /// `encounter`, `medication`, or `lab_report`, as in the contract.
  final String recordType;
  final String occurredAt;
  final String organizationRef;
  final String nodeRef;
  final String title;
  final String detail;
  final String? clinicianRef;

  /// The grant scope kind (`access.json`) that covers this entry.
  String get scopeKind => switch (recordType) {
    'encounter' => 'encounters',
    'medication' => 'medications',
    _ => 'labReports',
  };
}

/// The approved Hospital Nodes the Federation asks (registry seed, HC-142).
const demoFederationNodes = <({String organizationRef, String nodeRef})>[
  (organizationRef: 'org-hospital-a', nodeRef: 'node-hospital-a'),
  (organizationRef: 'org-hospital-b', nodeRef: 'node-hospital-b'),
  (organizationRef: 'org-private-practice', nodeRef: 'node-private-practice'),
];

/// `name` in `demo-data/organizations.json`.
const demoOrganizationNames = <String, String>{
  'org-hospital-a': 'Hôpital Universitaire Bab Ennour',
  'org-hospital-b': 'Hôpital Régional Oued Zitoun',
  'org-private-practice': 'Cabinet médical Dr Hatem Bouzid',
};

/// Authors of the entries (`demo-data/people.json`).
const demoClinicianNames = <String, String>{
  'clin-x': 'Dr Youssef Gharbi',
  'clin-rania': 'Dr Rania Kefi',
  'clin-mariem': 'Mariem Ayari',
  'clin-ines': 'Dr Inès Chaabane',
  'clin-hatem': 'Dr Hatem Bouzid',
};

const demoFederatedEntries = <FederatedEntry>[
  // Patient A, Hôpital Régional Oued Zitoun.
  FederatedEntry(
    entryRef: 'enc-b-2026-leila',
    patientId: 'pat-a',
    recordType: 'encounter',
    occurredAt: '2026-05-20T14:00:00+01:00',
    organizationRef: 'org-hospital-b',
    nodeRef: 'node-hospital-b',
    title: 'Consultation de médecine interne',
    detail: 'Palpitations récidivantes.',
    clinicianRef: 'clin-ines',
  ),
  FederatedEntry(
    entryRef: 'med-b-leila-coagulix',
    patientId: 'pat-a',
    recordType: 'medication',
    occurredAt: '2026-05-20T00:00:00+01:00',
    organizationRef: 'org-hospital-b',
    nodeRef: 'node-hospital-b',
    title: 'Coagulix',
    detail: '5 mg, 2 fois par jour · en cours',
    clinicianRef: 'clin-ines',
  ),
  FederatedEntry(
    entryRef: 'lab-b-2026-leila',
    patientId: 'pat-a',
    recordType: 'lab_report',
    occurredAt: '2026-05-20T14:40:00+01:00',
    organizationRef: 'org-hospital-b',
    nodeRef: 'node-hospital-b',
    title: 'Bilan avant traitement',
    detail: 'Hémoglobine 12,6 g/dL · Plaquettes 245 G/L · Créatinine 11,4 mg/L',
  ),
  // Patient A, Cabinet médical Dr Hatem Bouzid.
  FederatedEntry(
    entryRef: 'enc-pp-2025-leila',
    patientId: 'pat-a',
    recordType: 'encounter',
    occurredAt: '2025-06-12T17:15:00+01:00',
    organizationRef: 'org-private-practice',
    nodeRef: 'node-private-practice',
    title: 'Suivi tensionnel',
    detail: 'Céphalées matinales et chiffres tensionnels élevés à domicile.',
    clinicianRef: 'clin-hatem',
  ),
  FederatedEntry(
    entryRef: 'med-pp-leila-tensiorel',
    patientId: 'pat-a',
    recordType: 'medication',
    occurredAt: '2025-06-12T00:00:00+01:00',
    organizationRef: 'org-private-practice',
    nodeRef: 'node-private-practice',
    title: 'Tensiorel',
    detail: '10 mg, 1 fois par jour · en cours',
    clinicianRef: 'clin-hatem',
  ),
  // Patient A, Hôpital Universitaire Bab Ennour.
  FederatedEntry(
    entryRef: 'enc-a-2024-leila-er',
    patientId: 'pat-a',
    recordType: 'encounter',
    occurredAt: '2024-03-09T22:40:00+01:00',
    organizationRef: 'org-hospital-a',
    nodeRef: 'node-hospital-a',
    title: 'Consultation aux urgences',
    detail: 'Palpitations et essoufflement depuis la veille.',
    clinicianRef: 'clin-rania',
  ),
  FederatedEntry(
    entryRef: 'lab-a-2024-leila',
    patientId: 'pat-a',
    recordType: 'lab_report',
    occurredAt: '2024-03-09T23:05:00+01:00',
    organizationRef: 'org-hospital-a',
    nodeRef: 'node-hospital-a',
    title: 'Bilan aux urgences',
    detail:
        'Hémoglobine 13,1 g/dL · Potassium 4,2 mmol/L · Créatinine 8,9 mg/L',
  ),
  // Patient B, Hôpital Universitaire Bab Ennour.
  FederatedEntry(
    entryRef: 'lab-a-2026-karim',
    patientId: 'pat-b',
    recordType: 'lab_report',
    occurredAt: '2026-09-30T09:40:00+01:00',
    organizationRef: 'org-hospital-a',
    nodeRef: 'node-hospital-a',
    title: 'Bilan de suivi du diabète',
    detail:
        'HbA1c 8,9 % (élevée) · Glycémie à jeun 1,62 g/L (élevée) · Créatinine 9,8 mg/L',
  ),
  FederatedEntry(
    entryRef: 'enc-a-2026-karim',
    patientId: 'pat-b',
    recordType: 'encounter',
    occurredAt: '2026-09-30T09:30:00+01:00',
    organizationRef: 'org-hospital-a',
    nodeRef: 'node-hospital-a',
    title: 'Prélèvement de contrôle',
    detail: 'Bilan de suivi du diabète.',
    clinicianRef: 'clin-mariem',
  ),
  FederatedEntry(
    entryRef: 'med-a-karim-glucorel',
    patientId: 'pat-b',
    recordType: 'medication',
    occurredAt: '2025-09-15T00:00:00+01:00',
    organizationRef: 'org-hospital-a',
    nodeRef: 'node-hospital-a',
    title: 'Glucorel',
    detail: '850 mg, 2 fois par jour · en cours',
    clinicianRef: 'clin-x',
  ),
  FederatedEntry(
    entryRef: 'enc-a-2025-karim',
    patientId: 'pat-b',
    recordType: 'encounter',
    occurredAt: '2025-09-15T10:00:00+01:00',
    organizationRef: 'org-hospital-a',
    nodeRef: 'node-hospital-a',
    title: 'Bilan cardiométabolique',
    detail: 'Fatigue et soif importante.',
    clinicianRef: 'clin-x',
  ),
];
