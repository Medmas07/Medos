import 'package:flutter/material.dart';

import '../demo/canonical_medication_warning.dart';
import 'clinician_theme.dart';

enum MedicationWarningDemoState { ready, checking, pendingReview, reviewed }

class MedicationInteractionWarningView extends StatefulWidget {
  const MedicationInteractionWarningView({super.key});

  @override
  State<MedicationInteractionWarningView> createState() =>
      _MedicationInteractionWarningViewState();
}

class _MedicationInteractionWarningViewState
    extends State<MedicationInteractionWarningView> {
  MedicationWarningDemoState _state = MedicationWarningDemoState.ready;
  int _checkGeneration = 0;

  Future<void> _runCheck() async {
    final generation = ++_checkGeneration;
    setState(() => _state = MedicationWarningDemoState.checking);
    await Future<void>.delayed(const Duration(milliseconds: 650));
    if (!mounted || generation != _checkGeneration) return;
    setState(() => _state = MedicationWarningDemoState.pendingReview);
  }

  void _markReviewed() {
    setState(() => _state = MedicationWarningDemoState.reviewed);
  }

  void _reset() {
    _checkGeneration += 1;
    setState(() => _state = MedicationWarningDemoState.ready);
  }

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(18),
        child: AnimatedSwitcher(
          duration: const Duration(milliseconds: 180),
          child: switch (_state) {
            MedicationWarningDemoState.ready => _Ready(onCheck: _runCheck),
            MedicationWarningDemoState.checking => const _Checking(),
            MedicationWarningDemoState.pendingReview => _Warning(
              reviewed: false,
              onReview: _markReviewed,
              onReset: _reset,
            ),
            MedicationWarningDemoState.reviewed => _Warning(
              reviewed: true,
              onReview: _markReviewed,
              onReset: _reset,
            ),
          },
        ),
      ),
    );
  }
}

class _Ready extends StatelessWidget {
  const _Ready({required this.onCheck});

  final VoidCallback onCheck;

  @override
  Widget build(BuildContext context) {
    return Column(
      key: const ValueKey('medication-check-ready'),
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Row(
          children: [
            const Icon(Icons.medication_outlined, color: ClinicianColors.brand),
            const SizedBox(width: 10),
            Expanded(
              child: Text(
                'Sécurité médicamenteuse',
                style: Theme.of(context).textTheme.titleMedium,
              ),
            ),
            const _MockedPill(),
          ],
        ),
        const SizedBox(height: 14),
        const Text('Médicament proposé'),
        const SizedBox(height: 4),
        Text(
          '${demoMedicationWarning.proposedName} · ${demoMedicationWarning.proposedDosage}',
          style: const TextStyle(fontWeight: FontWeight.w800),
        ),
        const SizedBox(height: 6),
        const Text(
          'Vérification simulée contre le traitement autorisé visible dans le scénario fictif.',
          style: TextStyle(color: ClinicianColors.muted),
        ),
        const SizedBox(height: 14),
        FilledButton.icon(
          key: const ValueKey('run-medication-check'),
          onPressed: onCheck,
          icon: const Icon(Icons.health_and_safety_outlined),
          label: const Text('Vérifier les interactions'),
        ),
      ],
    );
  }
}

class _Checking extends StatelessWidget {
  const _Checking();

  @override
  Widget build(BuildContext context) {
    return const Column(
      key: ValueKey('medication-checking'),
      children: [
        SizedBox(
          width: 36,
          height: 36,
          child: CircularProgressIndicator(strokeWidth: 3),
        ),
        SizedBox(height: 12),
        Text(
          'Vérification déterministe simulée',
          style: TextStyle(fontWeight: FontWeight.w800),
        ),
        SizedBox(height: 6),
        Text('Aucun LLM ne décide si une interaction existe.'),
      ],
    );
  }
}

class _Warning extends StatelessWidget {
  const _Warning({
    required this.reviewed,
    required this.onReview,
    required this.onReset,
  });

  final bool reviewed;
  final VoidCallback onReview;
  final VoidCallback onReset;

  @override
  Widget build(BuildContext context) {
    return Column(
      key: ValueKey(reviewed ? 'medication-reviewed' : 'medication-warning'),
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Container(
          padding: const EdgeInsets.all(14),
          decoration: BoxDecoration(
            color: reviewed ? const Color(0xFFECFDF5) : const Color(0xFFFEF2F2),
            borderRadius: BorderRadius.circular(14),
          ),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Icon(
                reviewed
                    ? Icons.fact_check_outlined
                    : Icons.warning_amber_rounded,
                color: reviewed
                    ? const Color(0xFF047857)
                    : ClinicianColors.danger,
              ),
              const SizedBox(width: 10),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      reviewed
                          ? 'Alerte examinée par le clinicien'
                          : 'Interaction majeure à examiner',
                      style: const TextStyle(fontWeight: FontWeight.w800),
                    ),
                    const SizedBox(height: 4),
                    Text(demoMedicationWarning.effect),
                  ],
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 14),
        _MedicationRow(
          label: 'Proposition',
          name: demoMedicationWarning.proposedName,
          detail: demoMedicationWarning.proposedDosage,
        ),
        const SizedBox(height: 10),
        _MedicationRow(
          label: 'Traitement actif en conflit',
          name: demoMedicationWarning.conflictingName,
          detail: demoMedicationWarning.conflictingDosage,
        ),
        const SizedBox(height: 6),
        Text(
          'Provenance : ${demoMedicationWarning.conflictingOrganizationName} · ${demoMedicationWarning.conflictingStatementId}',
          style: const TextStyle(color: ClinicianColors.muted, fontSize: 12),
        ),
        const Divider(height: 24),
        Text(
          'Conduite proposée par la règle fictive',
          style: Theme.of(context).textTheme.titleSmall,
        ),
        const SizedBox(height: 5),
        Text(demoMedicationWarning.recommendation),
        const SizedBox(height: 12),
        Container(
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            color: ClinicianColors.demoSoft,
            borderRadius: BorderRadius.circular(12),
          ),
          child: Text(
            'Source MOCKED : règle déterministe ${demoMedicationWarning.ruleSetName} v${demoMedicationWarning.ruleSetVersion} · ${demoMedicationWarning.ruleId}. Source non validée pharmacologiquement.',
            style: const TextStyle(color: ClinicianColors.demo, height: 1.35),
          ),
        ),
        const SizedBox(height: 10),
        const Text(
          'Cette alerte n’autorise ni ne bloque la prescription. La décision et sa justification appartiennent au clinicien.',
          style: TextStyle(fontWeight: FontWeight.w700),
        ),
        const SizedBox(height: 14),
        if (!reviewed)
          FilledButton.icon(
            key: const ValueKey('review-medication-warning'),
            onPressed: onReview,
            icon: const Icon(Icons.check_rounded),
            label: const Text('J’ai examiné l’alerte'),
          )
        else
          OutlinedButton.icon(
            key: const ValueKey('reset-medication-warning'),
            onPressed: onReset,
            icon: const Icon(Icons.replay_rounded),
            label: const Text('Rejouer la démonstration'),
          ),
      ],
    );
  }
}

class _MedicationRow extends StatelessWidget {
  const _MedicationRow({
    required this.label,
    required this.name,
    required this.detail,
  });

  final String label;
  final String name;
  final String detail;

  @override
  Widget build(BuildContext context) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Icon(Icons.medication_rounded, size: 20),
        const SizedBox(width: 9),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                label,
                style: const TextStyle(
                  color: ClinicianColors.muted,
                  fontSize: 12,
                ),
              ),
              Text('$name · $detail'),
            ],
          ),
        ),
      ],
    );
  }
}

class _MockedPill extends StatelessWidget {
  const _MockedPill();

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: ClinicianColors.demoSoft,
        borderRadius: BorderRadius.circular(999),
      ),
      child: const Text(
        'MOCKED',
        style: TextStyle(
          color: ClinicianColors.demo,
          fontSize: 11,
          fontWeight: FontWeight.w800,
        ),
      ),
    );
  }
}
