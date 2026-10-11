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
