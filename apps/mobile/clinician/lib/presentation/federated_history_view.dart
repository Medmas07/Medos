import 'package:flutter/material.dart';

import '../demo/canonical_clinician.dart';
import '../demo/canonical_federated_history.dart';
import 'clinician_labels.dart';
import 'clinician_theme.dart';

/// Demo scenarios of the simulated Federation answer (HC-035, D1).
enum FederationScenario {
  /// Every node answers: the Federation Service's default HTTP mode.
  complete,

  /// The private practice's node cannot be reached (its DMI is disconnected
  /// in HC-005), as in the contract's `partialTimeline` example.
  partial,

  /// The Federation Service itself answers `503 federation_unavailable`.
  unavailable,
}

class NodeResult {
  const NodeResult({
    required this.organizationRef,
    required this.nodeRef,
    required this.status,
    required this.entryCount,
    this.problemCode,
  });

  final String organizationRef;
  final String nodeRef;

  /// `ok` or `unavailable` here; the contract also has `denied`, `timeout`,
  /// and `not_asked`.
  final String status;
  final int entryCount;
  final String? problemCode;
}

class FederatedHistory {
  const FederatedHistory({
    required this.completeness,
    required this.nodeResults,
    required this.entries,
  });

  /// `complete` only when every node answered `ok`.
  final String completeness;
  final List<NodeResult> nodeResults;

  /// Newest first; only entries inside the grant's scope, from nodes that
  /// answered `ok`.
  final List<FederatedEntry> entries;
}

/// Thrown for [FederationScenario.unavailable]: no node was asked.
class FederationUnavailable implements Exception {
  const FederationUnavailable();
}

/// Builds the simulated Federation answer for [grant]'s patient, as the
/// contract would: each node reports how it answered, entries keep their
/// source, and a node that does not answer makes the result `partial`.
FederatedHistory federatedHistoryFor(
  CanonicalAccessGrant grant,
  FederationScenario scenario, {
  List<FederatedEntry> entries = demoFederatedEntries,
}) {
  if (scenario == FederationScenario.unavailable) {
    throw const FederationUnavailable();
  }
  bool answers(String organizationRef) =>
      scenario == FederationScenario.complete ||
      organizationRef != 'org-private-practice';
  final inScope = [
    for (final entry in entries)
      if (entry.patientId == grant.patientId &&
          grant.scope.contains(entry.scopeKind))
        entry,
  ];
  final nodeResults = [
    for (final node in demoFederationNodes)
      answers(node.organizationRef)
          ? NodeResult(
              organizationRef: node.organizationRef,
              nodeRef: node.nodeRef,
              status: 'ok',
              entryCount: inScope
                  .where((e) => e.organizationRef == node.organizationRef)
                  .length,
            )
          : NodeResult(
              organizationRef: node.organizationRef,
              nodeRef: node.nodeRef,
              status: 'unavailable',
              entryCount: 0,
              problemCode: 'node_unavailable',
            ),
  ];
  return FederatedHistory(
    completeness: nodeResults.every((n) => n.status == 'ok')
        ? 'complete'
        : 'partial',
    nodeResults: nodeResults,
    entries: [
      for (final entry in inScope)
        if (answers(entry.organizationRef)) entry,
    ]..sort((a, b) => b.occurredAt.compareTo(a.occurredAt)),
  );
}

/// Opens [patient]'s federated history under [grant].
void openFederatedHistory(
  BuildContext context,
  CanonicalPatient patient,
  CanonicalAccessGrant grant,
) {
  Navigator.of(context).push(
    MaterialPageRoute<void>(
      builder: (_) => FederatedHistoryView(patient: patient, grant: grant),
    ),
  );
}

/// Clinician federated patient history (HC-035, D1): one authorized
/// patient's history across Hospital Nodes, each entry with its source.
/// MOCKED: a simulated answer in the federated-patient-query contract's
/// shape, built from fictional fixtures; nothing is requested.
class FederatedHistoryView extends StatefulWidget {
  const FederatedHistoryView({
    super.key,
    required this.patient,
    required this.grant,
    this.entries = demoFederatedEntries,
    this.loadingDelay = const Duration(milliseconds: 600),
  });

  final CanonicalPatient patient;
  final CanonicalAccessGrant grant;
  final List<FederatedEntry> entries;

  /// Simulated wait for the Federation's answer.
  final Duration loadingDelay;

  @override
  State<FederatedHistoryView> createState() => _FederatedHistoryViewState();
}

class _FederatedHistoryViewState extends State<FederatedHistoryView> {
  FederationScenario _scenario = FederationScenario.complete;
  bool _loading = true;
  int _request = 0;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    final request = ++_request;
    setState(() => _loading = true);
    await Future<void>.delayed(widget.loadingDelay);
    if (!mounted || request != _request) return;
    setState(() => _loading = false);
  }

  void _select(FederationScenario scenario) {
    _scenario = scenario;
    _load();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Historique fédéré'),
        actions: [
          PopupMenuButton<FederationScenario>(
            tooltip: 'Choisir un scénario de démonstration',
            initialValue: _scenario,
            onSelected: _select,
            itemBuilder: (context) => const [
              PopupMenuItem(
                value: FederationScenario.complete,
                child: Text('Scénario : toutes les sources'),
              ),
              PopupMenuItem(
                value: FederationScenario.partial,
                child: Text('Scénario : une source injoignable'),
              ),
              PopupMenuItem(
                value: FederationScenario.unavailable,
                child: Text('Scénario : Federation indisponible'),
              ),
            ],
            icon: const Icon(Icons.science_outlined),
          ),
        ],
      ),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(20, 12, 20, 28),
        children: [
          _PatientHeader(patient: widget.patient, grant: widget.grant),
          const SizedBox(height: 16),
          const _SimulationNotice(),
          const SizedBox(height: 20),
          ..._result(context),
        ],
      ),
    );
  }

  List<Widget> _result(BuildContext context) {
    if (_loading) {
      return const [
        Padding(
          key: ValueKey('history-loading'),
          padding: EdgeInsets.symmetric(vertical: 32),
          child: Column(
            children: [
              CircularProgressIndicator(),
              SizedBox(height: 12),
              Text('Interrogation simulée des Hospital Nodes…'),
            ],
          ),
        ),
      ];
    }
    final FederatedHistory history;
    try {
      history = federatedHistoryFor(
        widget.grant,
        _scenario,
        entries: widget.entries,
      );
    } on FederationUnavailable {
      return [
        Card(
          key: const ValueKey('history-error'),
          child: Padding(
            padding: const EdgeInsets.all(18),
            child: Column(
              children: [
                const Icon(
                  Icons.cloud_off_outlined,
                  size: 40,
                  color: ClinicianColors.danger,
                ),
                const SizedBox(height: 8),
                Text(
                  'Federation indisponible',
                  style: Theme.of(context).textTheme.titleMedium,
                ),
                const SizedBox(height: 6),
                const Text(
                  'Erreur de démonstration (503) : aucun Hospital Node n’a été interrogé. Aucun historique n’est affiché plutôt qu’un historique incomplet non signalé.',
                  textAlign: TextAlign.center,
                ),
                const SizedBox(height: 12),
                FilledButton.icon(
                  onPressed: () => _select(FederationScenario.complete),
                  icon: const Icon(Icons.refresh_rounded),
                  label: const Text('Réessayer'),
                ),
              ],
            ),
          ),
        ),
      ];
    }
    return [
      _CompletenessBanner(history: history),
      const SizedBox(height: 12),
      _SourcesCard(history: history),
      const SizedBox(height: 20),
      Text('Chronologie', style: Theme.of(context).textTheme.titleMedium),
      const SizedBox(height: 8),
      if (history.entries.isEmpty)
        const Card(
          key: ValueKey('history-empty'),
          child: Padding(
            padding: EdgeInsets.all(18),
            child: Text(
              'Aucune entrée dans le périmètre autorisé. Ce n’est pas une absence d’historique : seules les entrées couvertes par l’autorisation sont communiquées.',
              textAlign: TextAlign.center,
            ),
          ),
        )
      else
        for (final entry in history.entries) _EntryCard(entry: entry),
    ];
  }
}

class _PatientHeader extends StatelessWidget {
  const _PatientHeader({required this.patient, required this.grant});

  final CanonicalPatient patient;
  final CanonicalAccessGrant grant;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          patient.displayName,
          style: Theme.of(context).textTheme.headlineSmall,
        ),
        const SizedBox(height: 4),
        Text(
          '${grant.purpose} · autorisation ${grant.id} jusqu’au ${formatDemoDate(grant.expiresAt)}',
          style: const TextStyle(color: ClinicianColors.muted),
        ),
        const SizedBox(height: 8),
        Wrap(
          spacing: 6,
          runSpacing: 6,
          children: [
            for (final kind in grant.scope)
              LabelTag(
                label: scopeLabel(kind),
                color: ClinicianColors.brand,
                background: ClinicianColors.brandSoft,
              ),
          ],
        ),
      ],
    );
  }
}

class _SimulationNotice extends StatelessWidget {
  const _SimulationNotice();

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: ClinicianColors.demoSoft,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: const Color(0xFFDDD6FE)),
      ),
      child: const Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(Icons.hub_outlined, color: ClinicianColors.demo),
              SizedBox(width: 8),
              Expanded(
                child: Text(
                  'Réponse fédérée simulée (MOCKED)',
                  style: TextStyle(
                    color: ClinicianColors.demo,
                    fontWeight: FontWeight.w800,
                  ),
                ),
              ),
            ],
          ),
          SizedBox(height: 8),
          Text(
            'Présentée au format du contrat federated-patient-query v1, à partir de dossiers fictifs. Aucune requête n’est envoyée à la Federation ni aux Hospital Nodes, et rien n’est conservé sur l’appareil.',
            style: TextStyle(color: ClinicianColors.ink, height: 1.4),
          ),
        ],
      ),
    );
  }
}

class _CompletenessBanner extends StatelessWidget {
  const _CompletenessBanner({required this.history});

  final FederatedHistory history;

  @override
  Widget build(BuildContext context) {
    final missing = history.nodeResults.where((n) => n.status != 'ok').length;
    final complete = history.completeness == 'complete';
    return Container(
      key: ValueKey('completeness-${history.completeness}'),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: complete ? const Color(0xFFECFDF5) : const Color(0xFFFFFBEB),
        borderRadius: BorderRadius.circular(14),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(
            complete ? Icons.check_circle_outline : Icons.warning_amber_rounded,
            color: complete ? const Color(0xFF047857) : const Color(0xFFB45309),
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Text(
              complete
                  ? 'Historique complet : toutes les sources interrogées ont répondu.'
                  : 'Historique partiel : $missing source${missing > 1 ? 's' : ''} n’a pas pu être jointe. Des entrées peuvent manquer ; leur absence ne prouve rien.',
              style: const TextStyle(fontWeight: FontWeight.w600),
            ),
          ),
        ],
      ),
    );
  }
}

class _SourcesCard extends StatelessWidget {
  const _SourcesCard({required this.history});

  final FederatedHistory history;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.fromLTRB(16, 12, 16, 8),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Sources', style: Theme.of(context).textTheme.titleSmall),
            for (final node in history.nodeResults)
              ListTile(
                key: ValueKey('source-${node.nodeRef}'),
                contentPadding: EdgeInsets.zero,
                dense: true,
                leading: Icon(
                  node.status == 'ok'
                      ? Icons.check_circle_outline
                      : Icons.portable_wifi_off_rounded,
                  color: node.status == 'ok'
                      ? const Color(0xFF047857)
                      : const Color(0xFFB45309),
                ),
                title: Text(demoOrganizationNames[node.organizationRef]!),
                subtitle: Text(
                  node.status == 'ok'
                      ? 'A répondu · ${node.entryCount} entrée${node.entryCount > 1 ? 's' : ''}'
                      : 'Injoignable (${node.problemCode}) · aucune entrée reçue',
                ),
              ),
          ],
        ),
      ),
    );
  }
}

class _EntryCard extends StatelessWidget {
  const _EntryCard({required this.entry});

  final FederatedEntry entry;

  @override
  Widget build(BuildContext context) {
    final (icon, kind) = switch (entry.recordType) {
      'encounter' => (Icons.event_note_outlined, 'Consultation'),
      'medication' => (Icons.medication_outlined, 'Médicament'),
      _ => (Icons.biotech_outlined, 'Laboratoire'),
    };
    final author = demoClinicianNames[entry.clinicianRef];
    return Padding(
      key: ValueKey('entry-${entry.entryRef}'),
      padding: const EdgeInsets.only(bottom: 10),
      child: Card(
        child: Padding(
          padding: const EdgeInsets.all(14),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Icon(icon, color: ClinicianColors.brand),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      '$kind · ${formatDemoDate(entry.occurredAt)}',
                      style: const TextStyle(
                        color: ClinicianColors.muted,
                        fontSize: 12,
                      ),
                    ),
                    Text(
                      entry.title,
                      style: Theme.of(context).textTheme.titleSmall,
                    ),
                    const SizedBox(height: 4),
                    Text(entry.detail),
                    const SizedBox(height: 6),
                    Text(
                      'Source : ${demoOrganizationNames[entry.organizationRef]}${author == null ? '' : ' · $author'}',
                      style: const TextStyle(
                        color: ClinicianColors.muted,
                        fontSize: 12,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
