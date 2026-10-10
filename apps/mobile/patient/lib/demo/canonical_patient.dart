/// Presentation-only fixture copied from HC-005's canonical fictional dataset.
///
/// This is not a clinical domain model and must be replaced by an authorized
/// view contract when that contract exists.
class CanonicalPatientPreview {
  const CanonicalPatientPreview({
    required this.id,
    required this.firstName,
    required this.lastName,
    required this.city,
  });

  final String id;
  final String firstName;
  final String lastName;
  final String city;

  String get displayName => '$firstName $lastName';
}

const demoPatient = CanonicalPatientPreview(
  id: 'pat-a',
  firstName: 'Leïla',
  lastName: 'Mansouri',
  city: 'Tunis',
);

class CanonicalTimelineEvent {
  const CanonicalTimelineEvent({
    required this.date,
    required this.title,
    required this.organization,
    required this.summary,
    required this.kind,
  });

  final String date;
  final String title;
  final String organization;
  final String summary;
  final String kind;
}

const demoTimeline = <CanonicalTimelineEvent>[
  CanonicalTimelineEvent(
    date: '12 juin 2025',
    title: 'Consultation de suivi',
    organization: 'Hôpital Carthage',
    summary: 'Suivi annuel et recommandations de prévention.',
    kind: 'Consultation',
  ),
  CanonicalTimelineEvent(
    date: '03 mai 2025',
    title: 'Résultat de laboratoire',
    organization: 'Laboratoire El Amal',
    summary: 'Bilan de routine disponible dans votre vue autorisée.',
    kind: 'Laboratoire',
  ),
  CanonicalTimelineEvent(
    date: '18 février 2025',
    title: 'Visite de médecine générale',
    organization: 'Clinique Les Jasmins',
    summary: 'Note de visite partagée avec votre autorisation.',
    kind: 'Consultation',
  ),
];

class CanonicalMedication {
  const CanonicalMedication({
    required this.name,
    required this.code,
    required this.organization,
    required this.period,
    required this.status,
  });

  final String name;
  final String code;
  final String organization;
  final String period;
  final String status;
}

const demoMedications = <CanonicalMedication>[
  CanonicalMedication(
    name: 'Coagulix',
    code: 'MED-COAGULIX',
    organization: 'Hôpital Carthage',
    period: 'Actif depuis mai 2025',
    status: 'Actif',
  ),
  CanonicalMedication(
    name: 'Tensiorel',
    code: 'MED-TENSIOREL',
    organization: 'Clinique Les Jasmins',
    period: 'Terminé en janvier 2025',
    status: 'Terminé',
  ),
];

class CanonicalLabResult {
  const CanonicalLabResult({
    required this.test,
    required this.value,
    required this.unit,
    required this.referenceRange,
    required this.flag,
  });

  final String test;
  final String value;
  final String unit;
  final String referenceRange;
  final String flag;
}

class CanonicalLabReport {
  const CanonicalLabReport({
    required this.date,
    required this.title,
    required this.organization,
    required this.results,
  });

  final String date;
  final String title;
  final String organization;
  final List<CanonicalLabResult> results;
}

const demoLabReports = <CanonicalLabReport>[
  CanonicalLabReport(
    date: '20 mai 2026',
    title: 'Bilan avant traitement',
    organization: 'Hôpital Carthage',
    results: [
      CanonicalLabResult(
        test: 'Hémoglobine',
        value: '12,6',
        unit: 'g/dL',
        referenceRange: '12,0–16,0',
        flag: 'Normal',
      ),
      CanonicalLabResult(
        test: 'Plaquettes',
        value: '245',
        unit: 'G/L',
        referenceRange: '150–400',
        flag: 'Normal',
      ),
      CanonicalLabResult(
        test: 'Créatinine',
        value: '11,4',
        unit: 'mg/L',
        referenceRange: '6,0–12,0',
        flag: 'Normal',
      ),
    ],
  ),
];

class CanonicalCareEncounter {
  const CanonicalCareEncounter({
    required this.date,
    required this.organization,
    required this.physician,
    required this.specialty,
    required this.summary,
  });

  final String date;
  final String organization;
  final String physician;
  final String specialty;
  final String summary;
}

const demoCareHistory = <CanonicalCareEncounter>[
  CanonicalCareEncounter(
    date: '20 mai 2026',
    organization: 'Hôpital Régional Oued Zitoun',
    physician: 'Dr Inès Chaabane',
    specialty: 'Médecine interne',
    summary: 'Consultation de médecine interne et bilan avant traitement.',
  ),
  CanonicalCareEncounter(
    date: '14 mars 2026',
    organization: 'Hôpital Universitaire Bab Ennour',
    physician: 'Dr Youssef Gharbi',
    specialty: 'Cardiologie',
    summary: 'Suivi cardiologique et recommandations de prévention.',
  ),
  CanonicalCareEncounter(
    date: '08 janvier 2026',
    organization: 'Cabinet médical Dr Hatem Bouzid',
    physician: 'Dr Hatem Bouzid',
    specialty: 'Médecine générale',
    summary: 'Consultation de suivi avec le médecin traitant.',
  ),
];

class CanonicalAccessGrant {
  const CanonicalAccessGrant({
    required this.grantee,
    required this.purpose,
    required this.scope,
    required this.status,
    required this.expiresAt,
  });

  final String grantee;
  final String purpose;
  final String scope;
  final String status;
  final String expiresAt;
}

const demoAccessGrants = <CanonicalAccessGrant>[
  CanonicalAccessGrant(
    grantee: 'Dr Youssef Gharbi',
    purpose: 'Consultation de cardiologie',
    scope: 'Parcours, médicaments, laboratoires',
    status: 'Actif',
    expiresAt: 'Expire le 24 octobre 2026',
  ),
  CanonicalAccessGrant(
    grantee: 'Dr Inès Chaabane',
    purpose: 'Consultation de médecine interne',
    scope: 'Parcours, médicaments',
    status: 'Expiré',
    expiresAt: 'Expiré le 20 août 2026',
  ),
];
