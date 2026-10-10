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
