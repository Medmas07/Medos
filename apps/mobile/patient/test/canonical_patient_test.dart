// HC-240: the Patient App's presentation copy tells the HC-005 story.
//
// The fixtures in lib/demo/ are copied by hand (Flutter assets must live in the
// package); these tests read the canonical dataset so a copy cannot drift.
import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:hackcure_patient/demo/canonical_patient.dart';

const _recordFiles = [
  'records/hospital-a.json',
  'records/hospital-b.json',
  'records/private-practice.json',
];

Map<String, dynamic> _readDemoData(String name) {
  final file = File('../../../demo-data/$name');
  return jsonDecode(file.readAsStringSync()) as Map<String, dynamic>;
}

List<Map<String, dynamic>> _list(Map<String, dynamic> data, String key) =>
    (data[key] as List).cast<Map<String, dynamic>>();

void main() {
  final organizations = {
    for (final o in _list(_readDemoData('organizations.json'), 'organizations'))
      o['id'] as String: o['name'] as String,
  };
  final people = _readDemoData('people.json');
  final clinicians = {
    for (final c in _list(people, 'clinicians'))
      c['id'] as String:
          '${c['title'] ?? ''} ${c['firstName']} ${c['lastName']}'.trim(),
  };
  final medicines = {
    for (final m in _list(
      _readDemoData('medication-rules.json'),
      'medications',
    ))
      m['code'] as String: m['name'] as String,
  };
  final patientA = _list(
    people,
    'patients',
  ).firstWhere((p) => p['id'] == 'pat-a');

  // Patient A's records, each with the name of the organization holding it.
  final encounters = <(String, String, String)>[]; // title, holder, clinician
  final medications =
      <(String, String, String, String)>[]; // name, code, holder, status
  final labReports = <(String, String)>[]; // title, holder
  for (final name in _recordFiles) {
    final file = _readDemoData(name);
    final holder = organizations[file['heldBy']]!;
    bool ofPatientA(Map<String, dynamic> r) => r['patientId'] == 'pat-a';
    for (final e in _list(file, 'encounters').where(ofPatientA)) {
      encounters.add((
        e['title'] as String,
        holder,
        clinicians[e['clinicianId']]!,
      ));
    }
    for (final m in _list(file, 'medications').where(ofPatientA)) {
      final code = m['medicationCode'] as String;
      medications.add((medicines[code]!, code, holder, m['status'] as String));
    }
    for (final l in _list(file, 'labReports').where(ofPatientA)) {
      labReports.add((l['title'] as String, holder));
    }
  }
  final holders = encounters.map((e) => e.$2).toSet();

  test('Patient A is the canonical patient', () {
    expect(demoPatient.id, 'pat-a');
    expect(demoPatient.firstName, patientA['firstName']);
    expect(demoPatient.lastName, patientA['lastName']);
  });

  test('every source is an organization holding Patient A records', () {
    expect(demoPatientSources.toSet(), holders);
    final shown = {
      ...demoTimeline.map((e) => e.organization),
      ...demoMedications.map((m) => m.organization),
      ...demoLabReports.map((l) => l.organization),
      ...demoCareHistory.map((c) => c.organization),
    };
    expect(holders.containsAll(shown), isTrue, reason: '$shown');
  });

  test('the timeline and care history are Patient A encounters', () {
    expect(
      {for (final e in demoTimeline) (e.title, e.organization)},
      {for (final e in encounters) (e.$1, e.$2)},
    );
    expect(
      {for (final c in demoCareHistory) (c.organization, c.physician)},
      {for (final e in encounters) (e.$2, e.$3)},
    );
  });

  test('Medication A comes from Hospital B, as the medication check needs', () {
    expect(
      {
        for (final m in demoMedications)
          (m.name, m.code, m.organization, m.status == 'Actif'),
      },
      {for (final m in medications) (m.$1, m.$2, m.$3, m.$4 == 'active')},
    );
    final coagulix = demoMedications.firstWhere(
      (m) => m.code == 'MED-COAGULIX',
    );
    expect(coagulix.organization, organizations['org-hospital-b']);
  });

  test('laboratory reports are Patient A reports', () {
    expect({
      for (final l in demoLabReports) (l.title, l.organization),
    }, labReports.toSet());
  });

  test('grantees and delegates are canonical people', () {
    for (final grant in demoAccessGrants) {
      expect(clinicians.values, contains(grant.grantee));
    }
    final relatives = {
      for (final r in _list(people, 'relatives'))
        '${r['firstName']} ${r['lastName']}',
    };
    for (final delegation in demoDelegations) {
      expect(relatives, contains(delegation.delegate));
    }
  });
}
