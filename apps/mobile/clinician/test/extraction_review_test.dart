import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:hackcure_clinician/demo/canonical_consultation.dart';
import 'package:hackcure_clinician/presentation/extraction_review.dart';

void main() {
  DemoExtractionItem item(String id) =>
      demoExtractionItems.firstWhere((item) => item.id == id);

  test('starts with every suggestion pending and nothing retained', () {
    final review = ExtractionReview(demoExtractionItems);

    expect(review.count(ReviewDecision.pending), demoExtractionItems.length);
    expect(review.isComplete, isFalse);
    for (final item in demoExtractionItems) {
      expect(review.retainedText(item), isNull);
    }
  });

  test('accept, edit, and reject decide what is retained', () {
    final review = ExtractionReview(demoExtractionItems)
        .accept('ext-s1')
        .edit('ext-v1', 'Pression artérielle : 150/90 mmHg')
        .reject('ext-o1');

    expect(review.retainedText(item('ext-s1')), 'Douleur du genou droit');
    expect(
      review.retainedText(item('ext-v1')),
      'Pression artérielle : 150/90 mmHg',
    );
    expect(review.reviewOf('ext-v1').decision, ReviewDecision.edited);
    expect(review.retainedText(item('ext-o1')), isNull);
    expect(review.count(ReviewDecision.accepted), 1);
    expect(review.count(ReviewDecision.edited), 1);
    expect(review.count(ReviewDecision.rejected), 1);
  });

  test('a blank edit is ignored and an unchanged edit is an acceptance', () {
    final review = ExtractionReview(demoExtractionItems);

    expect(
      review.edit('ext-s1', '   ').reviewOf('ext-s1').decision,
      ReviewDecision.pending,
    );
    expect(
      review.edit('ext-s1', ' Douleur du genou droit ').reviewOf('ext-s1'),
      isA<ItemReview>().having(
        (r) => r.decision,
        'decision',
        ReviewDecision.accepted,
      ),
    );
  });

  test('undo returns a decision to pending', () {
    final review = ExtractionReview(
      demoExtractionItems,
    ).reject('ext-m1').undo('ext-m1');

    expect(review.reviewOf('ext-m1').decision, ReviewDecision.pending);
  });

  test('is complete once every suggestion has a decision', () {
    var review = ExtractionReview(demoExtractionItems);
    for (final item in demoExtractionItems.skip(1)) {
      review = review.accept(item.id);
    }
    expect(review.isComplete, isFalse);

    review = review.reject(demoExtractionItems.first.id);
    expect(review.isComplete, isTrue);
  });

  test('groups suggestions by category and rejects unknown ids', () {
    final review = ExtractionReview(demoExtractionItems);

    expect(
      [
        for (final item in review.itemsIn(DemoExtractionCategory.symptom))
          item.id,
      ],
      ['ext-s1', 'ext-s2'],
    );
    expect(
      review.itemsIn(DemoExtractionCategory.missingInformation),
      hasLength(3),
    );
    expect(() => review.accept('unknown'), throwsArgumentError);
  });

  test('the extraction fixture matches the canonical HC-005 draft', () {
    final data =
        jsonDecode(File('../../../demo-data/clinician.json').readAsStringSync())
            as Map<String, dynamic>;
    final script = (data['consultationScripts'] as List).firstWhere(
      (s) => s['id'] == demoConsultationScriptId,
    );
    final draft = script['extractionDraft'] as Map<String, dynamic>;
    String text(Object? value) => (value as String).replaceAll("'", '’');

    expect(draft['mocked'], isTrue);
    expect(draft['status'], demoExtractionStatus);

    List<DemoExtractionItem> inCategory(DemoExtractionCategory category) => [
      for (final item in demoExtractionItems)
        if (item.category == category) item,
    ];

    final symptoms = draft['symptoms'] as List;
    final symptomItems = inCategory(DemoExtractionCategory.symptom);
    expect(symptomItems, hasLength(symptoms.length));
    for (var i = 0; i < symptoms.length; i += 1) {
      expect(symptomItems[i].id, symptoms[i]['id']);
      expect(symptomItems[i].label, text(symptoms[i]['label']));
      expect(
        symptomItems[i].detail,
        symptoms[i]['detail'] == null ? null : text(symptoms[i]['detail']),
      );
    }

    final observations = draft['observations'] as List;
    final observationItems = inCategory(DemoExtractionCategory.observation);
    expect(observationItems, hasLength(observations.length));
    for (var i = 0; i < observations.length; i += 1) {
      expect(observationItems[i].id, observations[i]['id']);
      expect(observationItems[i].label, text(observations[i]['label']));
    }

    final values = draft['values'] as List;
    final valueItems = inCategory(DemoExtractionCategory.value);
    expect(valueItems, hasLength(values.length));
    for (var i = 0; i < values.length; i += 1) {
      expect(valueItems[i].id, values[i]['id']);
      expect(valueItems[i].label, text(values[i]['label']));
      expect(valueItems[i].value, values[i]['value']);
      expect(valueItems[i].unit, values[i]['unit']);
      expect(valueItems[i].flag, values[i]['flag']);
    }

    final medications = draft['medicationsMentioned'] as List;
    final medicationItems = inCategory(DemoExtractionCategory.medication);
    expect(medicationItems, hasLength(medications.length));
    for (var i = 0; i < medications.length; i += 1) {
      expect(medicationItems[i].id, medications[i]['id']);
      expect(medicationItems[i].label, text(medications[i]['label']));
      expect(
        medicationItems[i].medicationCode,
        medications[i]['medicationCode'],
      );
      expect(medicationItems[i].note, text(medications[i]['note']));
    }

    final missing = draft['missingInformation'] as List;
    expect(
      [
        for (final item in inCategory(
          DemoExtractionCategory.missingInformation,
        ))
          item.label,
      ],
      [for (final entry in missing) text(entry)],
    );
  });
}
