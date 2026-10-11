import 'package:flutter/material.dart';

import '../demo/canonical_consultation.dart';
import 'clinician_labels.dart';
import 'clinician_theme.dart';
import 'extraction_review.dart';

enum ExtractionPhase { idle, extracting, ready, finished }

/// HC-040 review of the fictional extraction draft, item by item.
class ExtractionReviewCard extends StatelessWidget {
  const ExtractionReviewCard({
    super.key,
    required this.phase,
    required this.review,
    required this.onStart,
    required this.onChanged,
    required this.onFinish,
    required this.onReopen,
  });

  final ExtractionPhase phase;
  final ExtractionReview review;
  final VoidCallback onStart;
  final ValueChanged<ExtractionReview> onChanged;
  final VoidCallback onFinish;
  final VoidCallback onReopen;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Row(
              children: [
                const Icon(
                  Icons.auto_awesome_outlined,
                  color: ClinicianColors.brand,
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: Text(
                    'Extraction IA à relire',
                    style: Theme.of(context).textTheme.titleMedium,
                  ),
                ),
                const LabelTag(
                  label: 'MOCKED',
                  color: ClinicianColors.demo,
                  background: ClinicianColors.demoSoft,
                ),
              ],
            ),
            const SizedBox(height: 6),
            const Text(
              'Suggestions tirées de la transcription simulée. Aucune ne devient une donnée clinique confirmée sans votre décision.',
              style: TextStyle(color: ClinicianColors.muted),
            ),
            const SizedBox(height: 4),
            const Text(
              'Brouillon fictif HC-005 ($demoConsultationScriptId) · aucun modèle appelé',
              style: TextStyle(color: ClinicianColors.demo, fontSize: 12),
            ),
            const Divider(height: 24),
            ...switch (phase) {
              ExtractionPhase.idle => [
                FilledButton.icon(
                  key: const ValueKey('run-extraction'),
                  onPressed: onStart,
                  icon: const Icon(Icons.auto_awesome_outlined),
                  label: const Text('Lancer l’extraction simulée'),
                ),
              ],
              ExtractionPhase.extracting => [
                const Column(
                  key: ValueKey('extraction-running'),
                  children: [
                    SizedBox(
                      width: 32,
                      height: 32,
                      child: CircularProgressIndicator(strokeWidth: 3),
                    ),
                    SizedBox(height: 10),
                    Text(
                      'Extraction simulée en cours',
                      style: TextStyle(fontWeight: FontWeight.w800),
                    ),
                  ],
                ),
              ],
              ExtractionPhase.ready || ExtractionPhase.finished => [
                Text(
                  _counts(review),
                  key: const ValueKey('extraction-counts'),
                  style: const TextStyle(fontWeight: FontWeight.w700),
                ),
                for (final category in DemoExtractionCategory.values)
                  if (review.itemsIn(category) case final items
                      when items.isNotEmpty)
                    _CategorySection(
                      category: category,
                      items: items,
                      review: review,
                      locked: phase == ExtractionPhase.finished,
                      onChanged: onChanged,
                    ),
                const SizedBox(height: 12),
                if (phase == ExtractionPhase.ready) ...[
                  FilledButton.icon(
                    key: const ValueKey('finish-extraction-review'),
                    onPressed: review.isComplete ? onFinish : null,
                    icon: const Icon(Icons.fact_check_outlined),
                    label: const Text('Terminer la revue'),
                  ),
                  if (!review.isComplete) ...[
                    const SizedBox(height: 6),
                    const Text(
                      'Décidez de chaque suggestion pour terminer la revue.',
                      textAlign: TextAlign.center,
                      style: TextStyle(color: ClinicianColors.muted),
                    ),
                  ],
                ] else ...[
                  Text(
                    'Revue terminée : ${_retained(review)} élément(s) retenu(s), '
                    '${review.count(ReviewDecision.rejected)} rejeté(s). '
                    'Ils restent un brouillon local ; aucun dossier clinique n’est créé.',
                    key: const ValueKey('extraction-review-done'),
                  ),
                  const SizedBox(height: 8),
                  OutlinedButton(
                    key: const ValueKey('reopen-extraction-review'),
                    onPressed: onReopen,
                    child: const Text('Reprendre la revue'),
                  ),
                ],
              ],
            },
          ],
        ),
      ),
    );
  }
}

int _retained(ExtractionReview review) =>
    review.count(ReviewDecision.accepted) + review.count(ReviewDecision.edited);

String _counts(ExtractionReview review) =>
    '${review.count(ReviewDecision.pending)} en attente · '
    '${review.count(ReviewDecision.accepted)} acceptée(s) · '
    '${review.count(ReviewDecision.edited)} modifiée(s) · '
    '${review.count(ReviewDecision.rejected)} rejetée(s)';

class _CategorySection extends StatelessWidget {
  const _CategorySection({
    required this.category,
    required this.items,
    required this.review,
    required this.locked,
    required this.onChanged,
  });

  final DemoExtractionCategory category;
  final List<DemoExtractionItem> items;
  final ExtractionReview review;
  final bool locked;
  final ValueChanged<ExtractionReview> onChanged;

  @override
  Widget build(BuildContext context) {
    final (title, hint) = switch (category) {
      DemoExtractionCategory.symptom => ('Symptômes', null),
      DemoExtractionCategory.observation => ('Observations', null),
      DemoExtractionCategory.value => ('Mesures', null),
      DemoExtractionCategory.medication => ('Médicaments mentionnés', null),
      DemoExtractionCategory.missingInformation => (
        'Informations manquantes',
        'Accepter : à compléter pendant la consultation.',
      ),
    };
    return Padding(
      padding: const EdgeInsets.only(top: 16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(title, style: Theme.of(context).textTheme.titleSmall),
          if (hint != null)
            Text(
              hint,
              style: const TextStyle(
                color: ClinicianColors.muted,
                fontSize: 12,
              ),
            ),
          for (final item in items)
            _ItemTile(
              item: item,
              review: review,
              locked: locked,
              onChanged: onChanged,
            ),
        ],
      ),
    );
  }
}

class _ItemTile extends StatelessWidget {
  const _ItemTile({
    required this.item,
    required this.review,
    required this.locked,
    required this.onChanged,
  });

  final DemoExtractionItem item;
  final ExtractionReview review;
  final bool locked;
  final ValueChanged<ExtractionReview> onChanged;

  String? get _secondary => switch (item.category) {
    DemoExtractionCategory.value when item.flag == 'high' =>
      'Signalée élevée par le brouillon',
    DemoExtractionCategory.medication =>
      '${item.note} · ${item.medicationCode}',
    _ => item.detail,
  };

  Future<void> _edit(BuildContext context, ItemReview itemReview) async {
    final text = await showDialog<String>(
      context: context,
      builder: (context) =>
          _EditDialog(initialText: itemReview.editedText ?? item.text),
    );
    if (text != null) onChanged(review.edit(item.id, text));
  }

  @override
  Widget build(BuildContext context) {
    final itemReview = review.reviewOf(item.id);
    final decision = itemReview.decision;
    final (label, color, background) = switch (decision) {
      ReviewDecision.pending => (
        'EN ATTENTE',
        const Color(0xFF92400E),
        const Color(0xFFFFFBEB),
      ),
      ReviewDecision.accepted => (
        'ACCEPTÉ',
        const Color(0xFF047857),
        const Color(0xFFECFDF5),
      ),
      ReviewDecision.edited => (
        'MODIFIÉ',
        ClinicianColors.brand,
        ClinicianColors.brandSoft,
      ),
      ReviewDecision.rejected => (
        'REJETÉ',
        ClinicianColors.danger,
        const Color(0xFFFEF2F2),
      ),
    };
    final secondary = _secondary;

    return Container(
      key: ValueKey('extraction-item-${item.id}'),
      margin: const EdgeInsets.only(top: 8),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        border: Border.all(color: ClinicianColors.border),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(
                child: Text(
                  itemReview.editedText ?? item.text,
                  style: TextStyle(
                    fontWeight: FontWeight.w700,
                    decoration: decision == ReviewDecision.rejected
                        ? TextDecoration.lineThrough
                        : null,
                  ),
                ),
              ),
              const SizedBox(width: 8),
              LabelTag(label: label, color: color, background: background),
            ],
          ),
          if (decision == ReviewDecision.edited)
            Padding(
              padding: const EdgeInsets.only(top: 4),
              child: Text(
                'Suggestion initiale : ${item.text}',
                style: const TextStyle(color: ClinicianColors.muted),
              ),
            ),
          if (secondary != null)
            Padding(
              padding: const EdgeInsets.only(top: 4),
              child: Text(
                secondary,
                style: const TextStyle(color: ClinicianColors.muted),
              ),
            ),
          if (!locked)
            Wrap(
              spacing: 4,
              children: decision == ReviewDecision.pending
                  ? [
                      TextButton(
                        key: ValueKey('accept-${item.id}'),
                        onPressed: () => onChanged(review.accept(item.id)),
                        child: const Text('Accepter'),
                      ),
                      TextButton(
                        key: ValueKey('edit-${item.id}'),
                        onPressed: () => _edit(context, itemReview),
                        child: const Text('Modifier'),
                      ),
                      TextButton(
                        key: ValueKey('reject-${item.id}'),
                        onPressed: () => onChanged(review.reject(item.id)),
                        child: const Text('Rejeter'),
                      ),
                    ]
                  : [
                      TextButton(
                        key: ValueKey('undo-${item.id}'),
                        onPressed: () => onChanged(review.undo(item.id)),
                        child: const Text('Annuler la décision'),
                      ),
                    ],
            ),
        ],
      ),
    );
  }
}

class _EditDialog extends StatefulWidget {
  const _EditDialog({required this.initialText});

  final String initialText;

  @override
  State<_EditDialog> createState() => _EditDialogState();
}

class _EditDialogState extends State<_EditDialog> {
  late final _controller = TextEditingController(text: widget.initialText);
  String? _error;

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  void _save() {
    final text = _controller.text.trim();
    if (text.isEmpty) {
      setState(() => _error = 'Le texte ne peut pas être vide.');
      return;
    }
    Navigator.pop(context, text);
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text('Modifier la suggestion'),
      content: TextField(
        key: const ValueKey('extraction-edit-field'),
        controller: _controller,
        autofocus: true,
        minLines: 1,
        maxLines: 4,
        decoration: InputDecoration(errorText: _error),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(context),
          child: const Text('Annuler'),
        ),
        FilledButton(
          key: const ValueKey('extraction-edit-save'),
          onPressed: _save,
          child: const Text('Appliquer'),
        ),
      ],
    );
  }
}
