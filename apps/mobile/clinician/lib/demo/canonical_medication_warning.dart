/// Presentation-only copy of the HC-005 fictional medication check scenario.
///
/// The medicines and rule are invented. They must never guide care. Tests
/// verify this copy against the canonical demo files.
class DemoMedicationWarning {
  const DemoMedicationWarning({
    required this.checkId,
    required this.patientId,
    required this.proposedCode,
    required this.proposedName,
    required this.proposedDosage,
    required this.conflictingStatementId,
    required this.conflictingCode,
    required this.conflictingName,
    required this.conflictingDosage,
    required this.conflictingOrganizationId,
    required this.conflictingOrganizationName,
    required this.ruleId,
    required this.severity,
    required this.effect,
    required this.recommendation,
    required this.ruleSetName,
    required this.ruleSetVersion,
  });

  final String checkId;
  final String patientId;
  final String proposedCode;
  final String proposedName;
  final String proposedDosage;
  final String conflictingStatementId;
  final String conflictingCode;
  final String conflictingName;
  final String conflictingDosage;
  final String conflictingOrganizationId;
  final String conflictingOrganizationName;
  final String ruleId;
  final String severity;
  final String effect;
  final String recommendation;
  final String ruleSetName;
  final String ruleSetVersion;
}

const demoMedicationWarning = DemoMedicationWarning(
  checkId: 'check-a-dolorane',
  patientId: 'pat-a',
  proposedCode: 'MED-DOLORANE',
  proposedName: 'Dolorane',
  proposedDosage: '400 mg, 3 fois par jour pendant 5 jours',
  conflictingStatementId: 'med-b-leila-coagulix',
  conflictingCode: 'MED-COAGULIX',
  conflictingName: 'Coagulix',
  conflictingDosage: '5 mg, 2 fois par jour',
  conflictingOrganizationId: 'org-hospital-b',
  conflictingOrganizationName: 'Hôpital Régional Oued Zitoun',
  ruleId: 'rule-coagulix-dolorane',
  severity: 'major',
  effect: 'Risque hémorragique accru.',
  recommendation:
      'Envisager une alternative à Dolorane et vérifier le traitement en cours avec le prescripteur. Décision à valider par le clinicien.',
  ruleSetName: 'demo-interaction-rules',
  ruleSetVersion: '1.0.0',
);
