/// Clinician review of the fictional extraction draft (HC-040).
///
/// The draft is a set of AI suggestions; none becomes retained until the
/// clinician accepts or edits it. Review decisions live in widget state only
/// and are never persisted or sent (MOCKED D1).
library;

import '../demo/canonical_consultation.dart';

enum ReviewDecision { pending, accepted, edited, rejected }

class ItemReview {
  const ItemReview(this.decision, [this.editedText]);

  static const pending = ItemReview(ReviewDecision.pending);

  final ReviewDecision decision;

  /// The clinician's wording, when [decision] is [ReviewDecision.edited].
  final String? editedText;
}

/// An immutable review of [items]: one decision per item id.
class ExtractionReview {
  ExtractionReview(this.items)
    : _reviews = {for (final item in items) item.id: ItemReview.pending};

  const ExtractionReview._(this.items, this._reviews);

  final List<DemoExtractionItem> items;
  final Map<String, ItemReview> _reviews;

  ItemReview reviewOf(String id) => _reviews[id]!;

  /// What the clinician retains for an item, or null if it is not retained.
  String? retainedText(DemoExtractionItem item) {
    final review = reviewOf(item.id);
    return switch (review.decision) {
      ReviewDecision.accepted => item.text,
      ReviewDecision.edited => review.editedText,
      ReviewDecision.pending || ReviewDecision.rejected => null,
    };
  }

  ExtractionReview accept(String id) =>
      _with(id, const ItemReview(ReviewDecision.accepted));

  ExtractionReview reject(String id) =>
      _with(id, const ItemReview(ReviewDecision.rejected));

  /// Records the clinician's wording. Unchanged or blank text is not an edit.
  ExtractionReview edit(String id, String text) {
    final trimmed = text.trim();
    final item = items.firstWhere((item) => item.id == id);
    if (trimmed.isEmpty) return this;
    if (trimmed == item.text) return accept(id);
    return _with(id, ItemReview(ReviewDecision.edited, trimmed));
  }

  ExtractionReview undo(String id) => _with(id, ItemReview.pending);

  int count(ReviewDecision decision) =>
      _reviews.values.where((review) => review.decision == decision).length;

  bool get isComplete => count(ReviewDecision.pending) == 0;

  List<DemoExtractionItem> itemsIn(DemoExtractionCategory category) => [
    for (final item in items)
      if (item.category == category) item,
  ];

  ExtractionReview _with(String id, ItemReview review) {
    if (!_reviews.containsKey(id)) throw ArgumentError.value(id, 'id');
    return ExtractionReview._(items, {..._reviews, id: review});
  }
}
