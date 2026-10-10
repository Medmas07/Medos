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
