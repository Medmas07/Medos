import 'package:flutter/material.dart';

import 'adaptive_intake_flow.dart';
import 'clinician_theme.dart';

/// HC-039 adaptive intake, offered when the patient refuses recording.
///
/// MOCKED D1: answers stay in this widget and disappear with it.
class AdaptiveIntakeView extends StatefulWidget {
  const AdaptiveIntakeView({super.key, this.onSummaryChanged});

  /// Called with the summary once the intake is complete, and with null when
  /// a change makes it incomplete again.
  final ValueChanged<List<IntakeSummaryLine>?>? onSummaryChanged;

  @override
  State<AdaptiveIntakeView> createState() => _AdaptiveIntakeViewState();
}

class _AdaptiveIntakeViewState extends State<AdaptiveIntakeView> {
  AdaptiveIntake _intake = const AdaptiveIntake.empty();

  /// An answered step reopened for editing; null shows the current step.
  IntakeStepId? _editing;
  Set<String> _selection = {};

  IntakeStep? get _shownStep {
    final editing = _editing;
    if (editing == null) return _intake.currentStep;
    return _intake.path.firstWhere((step) => step.id == editing);
  }

  void _show(IntakeStepId? editing) {
    _editing = editing;
    _selection = {...?_intake.answers[_shownStep?.id]};
  }

  void _toggle(IntakeStep step, String optionId) {
    setState(() {
      if (!step.multiSelect || optionId == step.exclusiveOptionId) {
        _selection = {optionId};
      } else if (!_selection.remove(optionId)) {
        _selection
          ..remove(step.exclusiveOptionId)
          ..add(optionId);
      }
    });
  }

  void _confirm(IntakeStep step) {
    setState(() {
      _intake = _intake.answer(step.id, _selection.toList());
      _show(null);
    });
    _reportSummary();
  }

  void _reportSummary() {
    widget.onSummaryChanged?.call(_intake.isComplete ? _intake.summary : null);
  }

  void _back(IntakeStep step) {
    final path = _intake.path;
    final index = path.indexWhere((s) => s.id == step.id);
    setState(() => _show(path[index - 1].id));
  }

  void _restart() {
    setState(() {
      _intake = const AdaptiveIntake.empty();
      _show(null);
    });
    _reportSummary();
  }

  @override
  Widget build(BuildContext context) {
    final step = _shownStep;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(18),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Row(
              children: [
                const Icon(
                  Icons.assignment_outlined,
                  color: ClinicianColors.brand,
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: Text(
                    'Anamnèse adaptative',
                    style: Theme.of(context).textTheme.titleMedium,
                  ),
                ),
                const _Pill(label: 'MOCKED'),
              ],
            ),
            const SizedBox(height: 6),
            const Text(
              'Parcours déterministe : chaque réponse choisit la question suivante.',
              style: TextStyle(color: ClinicianColors.muted),
            ),
            const Divider(height: 24),
            if (step == null)
              _Summary(
                intake: _intake,
                onEdit: (id) => setState(() => _show(id)),
                onRestart: _restart,
              )
            else
              _Question(
                step: step,
                number: _intake.path.indexWhere((s) => s.id == step.id) + 1,
                selection: _selection,
                onToggle: (optionId) => _toggle(step, optionId),
                onBack: step.id == _intake.path.first.id
                    ? null
                    : () => _back(step),
                onConfirm: _selection.isEmpty ? null : () => _confirm(step),
              ),
            if (_intake.skipped.isNotEmpty) ...[
              const SizedBox(height: 12),
              _SkippedSteps(skipped: _intake.skipped),
            ],
            const SizedBox(height: 12),
            const Text(
              'Questionnaire fictif, non validé cliniquement : il n’établit ni diagnostic, ni priorité, ni conduite à tenir.',
              style: TextStyle(color: ClinicianColors.demo, fontSize: 12),
            ),
          ],
        ),
      ),
    );
  }
}

class _Question extends StatelessWidget {
  const _Question({
    required this.step,
    required this.number,
    required this.selection,
    required this.onToggle,
    required this.onBack,
    required this.onConfirm,
  });

  final IntakeStep step;
  final int number;
  final Set<String> selection;
  final ValueChanged<String> onToggle;
  final VoidCallback? onBack;
  final VoidCallback? onConfirm;

  @override
  Widget build(BuildContext context) {
    return Column(
      key: ValueKey('intake-step-${step.id.name}'),
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Étape $number · ${step.title}',
          style: const TextStyle(
            color: ClinicianColors.brand,
            fontSize: 12,
            fontWeight: FontWeight.w800,
          ),
        ),
        const SizedBox(height: 4),
        Text(step.question, style: Theme.of(context).textTheme.titleMedium),
        if (step.basis case final basis?) ...[
          const SizedBox(height: 6),
          Row(
            children: [
              const Icon(
                Icons.alt_route_rounded,
                size: 16,
                color: ClinicianColors.muted,
              ),
              const SizedBox(width: 6),
              Expanded(
                child: Text(
                  basis,
                  style: const TextStyle(color: ClinicianColors.muted),
                ),
              ),
            ],
          ),
        ],
        const SizedBox(height: 12),
        Wrap(
          spacing: 8,
          runSpacing: 8,
          children: [
            for (final option in step.options)
              FilterChip(
                key: ValueKey('intake-option-${option.id}'),
                label: Text(option.label),
                selected: selection.contains(option.id),
                showCheckmark: step.multiSelect,
                onSelected: (_) => onToggle(option.id),
              ),
          ],
        ),
        const SizedBox(height: 12),
        if (onConfirm == null)
          Text(
            step.multiSelect
                ? 'Choisissez au moins une réponse pour continuer.'
                : 'Choisissez une réponse pour continuer.',
            style: const TextStyle(color: ClinicianColors.muted),
          ),
        const SizedBox(height: 8),
        Row(
          children: [
            if (onBack != null)
              TextButton.icon(
                key: const ValueKey('intake-back'),
                onPressed: onBack,
                icon: const Icon(Icons.arrow_back_rounded),
                label: const Text('Précédent'),
              ),
            const Spacer(),
            FilledButton(
              key: const ValueKey('intake-continue'),
              onPressed: onConfirm,
              child: const Text('Continuer'),
            ),
          ],
        ),
      ],
    );
  }
}

class _Summary extends StatelessWidget {
  const _Summary({
    required this.intake,
    required this.onEdit,
    required this.onRestart,
  });

  final AdaptiveIntake intake;
  final ValueChanged<IntakeStepId> onEdit;
  final VoidCallback onRestart;

  @override
  Widget build(BuildContext context) {
    return Column(
      key: const ValueKey('intake-summary'),
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Row(
          children: [
            Expanded(
              child: Text(
                'Résumé à relire',
                style: Theme.of(context).textTheme.titleMedium,
              ),
            ),
            const _Pill(label: 'BROUILLON'),
          ],
        ),
        const SizedBox(height: 6),
        const Text(
          'À relire et valider par le clinicien. Rien n’est enregistré ni transmis ; il alimente le brouillon de consultation.',
          style: TextStyle(color: ClinicianColors.muted),
        ),
        const SizedBox(height: 8),
        for (final line in intake.summary)
          ListTile(
            contentPadding: EdgeInsets.zero,
            dense: true,
            title: Text(
              line.step.title,
              style: const TextStyle(color: ClinicianColors.muted),
            ),
            subtitle: Text(
              line.answer,
              style: const TextStyle(
                color: ClinicianColors.ink,
                fontSize: 15,
                fontWeight: FontWeight.w700,
              ),
            ),
            trailing: IconButton(
              tooltip: 'Modifier : ${line.step.title}',
              onPressed: () => onEdit(line.step.id),
              icon: const Icon(Icons.edit_outlined),
            ),
          ),
        const SizedBox(height: 8),
        OutlinedButton.icon(
          onPressed: onRestart,
          icon: const Icon(Icons.replay_rounded),
          label: const Text('Recommencer l’anamnèse'),
        ),
      ],
    );
  }
}

class _SkippedSteps extends StatelessWidget {
  const _SkippedSteps({required this.skipped});

  final List<SkippedIntakeStep> skipped;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text(
          'Étapes sautées',
          style: TextStyle(fontSize: 12, fontWeight: FontWeight.w800),
        ),
        for (final step in skipped)
          Padding(
            padding: const EdgeInsets.only(top: 4),
            child: Text(
              '${step.title} : ${step.reason}',
              style: const TextStyle(color: ClinicianColors.muted),
            ),
          ),
      ],
    );
  }
}

class _Pill extends StatelessWidget {
  const _Pill({required this.label});

  final String label;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: ClinicianColors.demoSoft,
        borderRadius: BorderRadius.circular(999),
      ),
      child: Text(
        label,
        style: const TextStyle(
          color: ClinicianColors.demo,
          fontSize: 11,
          fontWeight: FontWeight.w800,
        ),
      ),
    );
  }
}
