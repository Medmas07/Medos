import 'package:flutter/material.dart';

import '../demo/canonical_patient.dart';
import 'patient_theme.dart';

enum ShellDemoState { content, loading, empty, error }

class PatientShell extends StatefulWidget {
  const PatientShell({super.key});

  @override
  State<PatientShell> createState() => _PatientShellState();
}

class _PatientShellState extends State<PatientShell> {
  int _selectedIndex = 0;
  ShellDemoState _demoState = ShellDemoState.content;

  static const _destinations = <NavigationDestination>[
    NavigationDestination(
      icon: Icon(Icons.home_outlined),
      selectedIcon: Icon(Icons.home_rounded),
      label: 'Accueil',
    ),
    NavigationDestination(
      icon: Icon(Icons.timeline_outlined),
      selectedIcon: Icon(Icons.timeline_rounded),
      label: 'Parcours',
    ),
    NavigationDestination(
      icon: Icon(Icons.verified_user_outlined),
      selectedIcon: Icon(Icons.verified_user_rounded),
      label: 'Accès',
    ),
    NavigationDestination(
      icon: Icon(Icons.person_outline_rounded),
      selectedIcon: Icon(Icons.person_rounded),
      label: 'Profil',
    ),
  ];

  static const _titles = ['Accueil', 'Mon parcours', 'Mes accès', 'Mon profil'];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        titleSpacing: 20,
        title: Row(
          children: [
            Container(
              width: 36,
              height: 36,
              decoration: const BoxDecoration(
                color: PatientColors.brand,
                borderRadius: BorderRadius.all(Radius.circular(12)),
              ),
              child: const Icon(
                Icons.health_and_safety_rounded,
                color: Colors.white,
                size: 22,
              ),
            ),
            const SizedBox(width: 12),
            Expanded(child: Text(_titles[_selectedIndex])),
          ],
        ),
        actions: [
          PopupMenuButton<ShellDemoState>(
            tooltip: 'Choisir un état de démonstration',
            initialValue: _demoState,
            onSelected: (value) => setState(() => _demoState = value),
            itemBuilder: (context) => const [
              PopupMenuItem(
                value: ShellDemoState.content,
                child: Text('État : contenu'),
              ),
              PopupMenuItem(
                value: ShellDemoState.loading,
                child: Text('État : chargement'),
              ),
              PopupMenuItem(
                value: ShellDemoState.empty,
                child: Text('État : vide'),
              ),
              PopupMenuItem(
                value: ShellDemoState.error,
                child: Text('État : erreur'),
              ),
            ],
            icon: const Icon(Icons.science_outlined),
          ),
          const SizedBox(width: 8),
        ],
      ),
      body: SafeArea(
        top: false,
        child: AnimatedSwitcher(
          duration: const Duration(milliseconds: 180),
          child: _buildState(),
        ),
      ),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _selectedIndex,
        destinations: _destinations,
        onDestinationSelected: (index) {
          setState(() {
            _selectedIndex = index;
            _demoState = ShellDemoState.content;
          });
        },
      ),
    );
  }

  Widget _buildState() {
    return switch (_demoState) {
      ShellDemoState.content => _ContentView(index: _selectedIndex),
      ShellDemoState.loading => const _StateView(
        key: ValueKey('loading'),
        icon: _LoadingIndicator(),
        title: 'Chargement de votre vue autorisée',
        message: 'Simulation locale — aucune donnée hospitalière réelle.',
      ),
      ShellDemoState.empty => const _StateView(
        key: ValueKey('empty'),
        icon: Icon(Icons.inbox_outlined, size: 48),
        title: 'Aucune donnée autorisée',
        message:
            'Les informations apparaîtront ici lorsqu’une source autorisée sera disponible.',
      ),
      ShellDemoState.error => _StateView(
        key: const ValueKey('error'),
        icon: const Icon(
          Icons.cloud_off_outlined,
          size: 48,
          color: Color(0xFFB91C1C),
        ),
        title: 'Vue temporairement indisponible',
        message:
            'Erreur de démonstration. Aucun accès direct à un système hospitalier.',
        action: FilledButton.icon(
          onPressed: () => setState(() => _demoState = ShellDemoState.content),
          icon: const Icon(Icons.refresh_rounded),
          label: const Text('Réessayer'),
        ),
      ),
    };
  }
}

class _ContentView extends StatelessWidget {
  const _ContentView({required this.index});

  final int index;

  @override
  Widget build(BuildContext context) {
    final content = switch (index) {
      0 => const _DashboardContent(),
      1 => const _TimelineContent(),
      2 => const _AccessContent(),
      _ => const _ProfileContent(),
    };

    return ListView(
      key: ValueKey('content-$index'),
      padding: const EdgeInsets.fromLTRB(20, 12, 20, 28),
      children: [const _DemoBanner(), const SizedBox(height: 20), content],
    );
  }
}

class _HomeContent extends StatelessWidget {
  const _HomeContent();

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Bonjour ${demoPatient.firstName}',
          style: Theme.of(context).textTheme.headlineSmall,
        ),
        const SizedBox(height: 6),
        const Text(
          'Votre espace de santé autorisé, simple et transparent.',
          style: TextStyle(color: PatientColors.muted, fontSize: 16),
        ),
        const SizedBox(height: 24),
        const _PreviewCard(
          icon: Icons.timeline_rounded,
          title: 'Parcours médical',
          description: 'Aperçu — fonctionnalité prévue par HC-012.',
        ),
        const SizedBox(height: 12),
        const _PreviewCard(
          icon: Icons.medication_outlined,
          title: 'Mes médicaments',
          description: 'Aperçu — fonctionnalité prévue par HC-014.',
        ),
        const SizedBox(height: 12),
        const _PreviewCard(
          icon: Icons.verified_user_outlined,
          title: 'Accès et consentements',
          description: 'Aperçu — fonctionnalité prévue par HC-017.',
        ),
      ],
    );
  }
}

class _DashboardContent extends StatelessWidget {
  const _DashboardContent();

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Bonjour ${demoPatient.firstName}',
          style: Theme.of(context).textTheme.headlineSmall,
        ),
        const SizedBox(height: 6),
        const SizedBox(height: 20),
        const _AuthorizedViewCard(),
        const SizedBox(height: 16),
        Text(
          'Votre tableau de bord',
          style: Theme.of(context).textTheme.titleLarge,
        ),
        const SizedBox(height: 10),
        const Row(
          children: [
            Expanded(
              child: _DashboardMetric(
                icon: Icons.timeline_rounded,
                value: '3',
                label: 'evenements autorises',
              ),
            ),
            SizedBox(width: 12),
            Expanded(
              child: _DashboardMetric(
                icon: Icons.verified_user_outlined,
                value: '2',
                label: 'sources autorisees',
              ),
            ),
          ],
        ),
        const SizedBox(height: 16),
        Card(
          child: ListTile(
            leading: const Icon(
              Icons.update_rounded,
              color: PatientColors.brand,
            ),
            title: const Text('Derniere mise a jour'),
            subtitle: const Text('Vue autorisee synchronisee aujourd hui'),
            trailing: const _StatusPill(label: 'MOCKED'),
          ),
        ),
        const SizedBox(height: 20),
        Text(
          'Historique des médicaments',
          style: Theme.of(context).textTheme.titleLarge,
        ),
        const SizedBox(height: 10),
        const _MedicationHistorySection(),
        const SizedBox(height: 20),
        Text(
          'Résultats de laboratoire',
          style: Theme.of(context).textTheme.titleLarge,
        ),
        const SizedBox(height: 10),
        const _LaboratoryHistorySection(),
        const SizedBox(height: 20),
        Text(
          'Hôpitaux et médecins',
          style: Theme.of(context).textTheme.titleLarge,
        ),
        const SizedBox(height: 10),
        const _CareHistorySection(),
      ],
    );
  }
}

class _MedicationHistorySection extends StatelessWidget {
  const _MedicationHistorySection();

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        for (final medication in demoMedications)
          Card(
            child: ListTile(
              leading: const CircleAvatar(
                backgroundColor: PatientColors.brandSoft,
                child: Icon(Icons.medication_outlined, color: PatientColors.brand),
              ),
              title: Text(medication.name),
              subtitle: Text(
                '${medication.period}\n${medication.organization}',
              ),
              isThreeLine: true,
              trailing: _StatusPill(label: medication.status.toUpperCase()),
            ),
          ),
      ],
    );
  }
}

class _LaboratoryHistorySection extends StatelessWidget {
  const _LaboratoryHistorySection();

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        for (final report in demoLabReports)
          Card(
            child: ExpansionTile(
              leading: const CircleAvatar(
                backgroundColor: PatientColors.brandSoft,
                child: Icon(Icons.biotech_outlined, color: PatientColors.brand),
              ),
              title: Text(report.title),
              subtitle: Text('${report.date} · ${report.organization}'),
              trailing: const _StatusPill(label: 'AUTORISÉ'),
              childrenPadding: const EdgeInsets.fromLTRB(16, 0, 16, 12),
              children: [
                for (final result in report.results)
                  _LabResultRow(result: result),
                const Align(
                  alignment: Alignment.centerLeft,
                  child: _StatusPill(label: 'DÉMO D1'),
                ),
              ],
            ),
          ),
      ],
    );
  }
}

class _LabResultRow extends StatelessWidget {
  const _LabResultRow({required this.result});

  final CanonicalLabResult result;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8),
      child: Row(
        children: [
          Expanded(child: Text(result.test)),
          Text(
            '${result.value} ${result.unit}',
            style: const TextStyle(fontWeight: FontWeight.w700),
          ),
          const SizedBox(width: 10),
          Text(result.flag, style: const TextStyle(color: PatientColors.muted)),
        ],
      ),
    );
  }
}

class _CareHistorySection extends StatelessWidget {
  const _CareHistorySection();

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        for (final encounter in demoCareHistory)
          Card(
            child: ListTile(
              leading: const CircleAvatar(
                backgroundColor: PatientColors.brandSoft,
                child: Icon(Icons.local_hospital_outlined, color: PatientColors.brand),
              ),
              title: Text(encounter.physician),
              subtitle: Text(
                '${encounter.date} · ${encounter.specialty}\n${encounter.organization}',
              ),
              isThreeLine: true,
              trailing: const _StatusPill(label: 'AUTORISÉ'),
            ),
          ),
      ],
    );
  }
}

class _AccessContent extends StatefulWidget {
  const _AccessContent();

  @override
  State<_AccessContent> createState() => _AccessContentState();
}

class _AccessContentState extends State<_AccessContent> {
  late final Set<String> _revoked = {};
  late final List<CanonicalAccessGrant> _grants = [...demoAccessGrants];
  late final Set<String> _withdrawnDelegations = {};
  late final List<CanonicalDelegation> _delegations = [...demoDelegations];

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text('Mes accès', style: Theme.of(context).textTheme.headlineSmall),
        const SizedBox(height: 6),
        const Text(
          'Contrôlez les autorisations visibles dans votre vue patient.',
          style: TextStyle(color: PatientColors.muted, fontSize: 16),
        ),
        const SizedBox(height: 18),
        const _AccessNotice(),
        const SizedBox(height: 12),
        FilledButton.icon(
          onPressed: _grantAccess,
          icon: const Icon(Icons.person_add_alt_1_rounded),
          label: const Text('Accorder un accès'),
        ),
        const SizedBox(height: 12),
        for (final grant in _grants)
          _AccessGrantCard(
            grant: grant,
            revoked: _revoked.contains(grant.grantee),
            onRevoke: () => _confirmRevoke(grant.grantee),
          ),
        const SizedBox(height: 20),
        Text('Proches de confiance', style: Theme.of(context).textTheme.titleLarge),
        const SizedBox(height: 6),
        const Text(
          'Un proche consulte uniquement la portée que vous choisissez.',
          style: TextStyle(color: PatientColors.muted),
        ),
        const SizedBox(height: 12),
        OutlinedButton.icon(
          onPressed: _delegateAccess,
          icon: const Icon(Icons.family_restroom_rounded),
          label: const Text('Déléguer à un proche'),
        ),
        const SizedBox(height: 12),
        for (final delegation in _delegations)
          _DelegationCard(
            delegation: delegation,
            withdrawn: _withdrawnDelegations.contains(delegation.delegate),
            onWithdraw: () => _confirmWithdraw(delegation.delegate),
          ),
      ],
    );
  }

  Future<void> _delegateAccess() async {
    final delegation = await showDialog<CanonicalDelegation>(
      context: context,
      builder: (context) => const _DelegateAccessDialog(),
    );
    if (delegation == null) return;
    setState(() {
      _withdrawnDelegations.remove(delegation.delegate);
      _delegations
        ..removeWhere((d) => d.delegate == delegation.delegate)
        ..insert(0, delegation);
    });
  }

  Future<void> _confirmWithdraw(String delegate) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Retirer la délégation ?'),
        content: Text(
          '$delegate ne verra plus votre vue autorisée dans cette démonstration.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Annuler'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(context, true),
            child: const Text('Retirer'),
          ),
        ],
      ),
    );
    if (confirmed == true) setState(() => _withdrawnDelegations.add(delegate));
  }

  Future<void> _grantAccess() async {
    final grant = await showDialog<CanonicalAccessGrant>(
      context: context,
      builder: (context) => const _GrantAccessDialog(),
    );
    if (grant != null) setState(() => _grants.insert(0, grant));
  }

  Future<void> _confirmRevoke(String grantee) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Révoquer cet accès ?'),
        content: Text(
          'La vue autorisée de $grantee sera retirée dans cette démonstration.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Annuler'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(context, true),
            child: const Text('Révoquer'),
          ),
        ],
      ),
    );
    if (confirmed == true) setState(() => _revoked.add(grantee));
  }
}

class _GrantAccessDialog extends StatefulWidget {
  const _GrantAccessDialog();

  @override
  State<_GrantAccessDialog> createState() => _GrantAccessDialogState();
}

class _GrantAccessDialogState extends State<_GrantAccessDialog> {
  String _physician = 'Dr Rania Kefi';
  String _scope = 'Parcours, médicaments, laboratoires';
  String _duration = '30 jours';

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text('Accorder un accès'),
      content: SingleChildScrollView(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            DropdownButtonFormField<String>(
              value: _physician,
              decoration: const InputDecoration(labelText: 'Médecin'),
              items: const [
                DropdownMenuItem(value: 'Dr Rania Kefi', child: Text('Dr Rania Kefi')),
                DropdownMenuItem(value: 'Dr Hatem Bouzid', child: Text('Dr Hatem Bouzid')),
              ],
              onChanged: (value) => setState(() => _physician = value!),
            ),
            const SizedBox(height: 12),
            DropdownButtonFormField<String>(
              value: _scope,
              decoration: const InputDecoration(labelText: 'Portée'),
              items: const [
                DropdownMenuItem(
                  value: 'Parcours, médicaments, laboratoires',
                  child: Text('Parcours + médicaments + laboratoires'),
                ),
                DropdownMenuItem(value: 'Parcours', child: Text('Parcours uniquement')),
              ],
              onChanged: (value) => setState(() => _scope = value!),
            ),
            const SizedBox(height: 12),
            DropdownButtonFormField<String>(
              value: _duration,
              decoration: const InputDecoration(labelText: 'Durée'),
              items: const [
                DropdownMenuItem(value: '30 jours', child: Text('30 jours')),
                DropdownMenuItem(value: '90 jours', child: Text('90 jours')),
              ],
              onChanged: (value) => setState(() => _duration = value!),
            ),
          ],
        ),
      ),
      actions: [
        TextButton(onPressed: () => Navigator.pop(context), child: const Text('Annuler')),
        FilledButton(
          onPressed: () => Navigator.pop(
            context,
            CanonicalAccessGrant(
              grantee: _physician,
              purpose: 'Accès accordé depuis l’application patient',
              scope: _scope,
              status: 'Actif',
              expiresAt: 'Expire dans $_duration',
            ),
          ),
          child: const Text('Accorder'),
        ),
      ],
    );
  }
}

class _AccessNotice extends StatelessWidget {
  const _AccessNotice();

  @override
  Widget build(BuildContext context) {
    return Card(
      color: PatientColors.brandSoft,
      child: const Padding(
        padding: EdgeInsets.all(16),
        child: Row(
          children: [
            Icon(Icons.lock_outline_rounded, color: PatientColors.brand),
            SizedBox(width: 12),
            Expanded(
              child: Text(
                'Vous choisissez quelles sources peuvent partager une vue autorisée.',
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _AccessGrantCard extends StatelessWidget {
  const _AccessGrantCard({
    required this.grant,
    required this.revoked,
    required this.onRevoke,
  });

  final CanonicalAccessGrant grant;
  final bool revoked;
  final VoidCallback onRevoke;

  @override
  Widget build(BuildContext context) {
    final active = grant.status == 'Actif' && !revoked;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(Icons.person_outline_rounded, color: PatientColors.brand),
                const SizedBox(width: 10),
                Expanded(
                  child: Text(
                    grant.grantee,
                    style: Theme.of(context).textTheme.titleMedium,
                  ),
                ),
                _StatusPill(label: revoked ? 'RÉVOQUÉ' : grant.status.toUpperCase()),
              ],
            ),
            const SizedBox(height: 10),
            Text(grant.purpose),
            const SizedBox(height: 4),
            Text(grant.scope, style: const TextStyle(color: PatientColors.muted)),
            const SizedBox(height: 4),
            Text(grant.expiresAt, style: const TextStyle(color: PatientColors.muted)),
            if (active) ...[
              const SizedBox(height: 12),
              OutlinedButton.icon(
                onPressed: onRevoke,
                icon: const Icon(Icons.block_outlined),
                label: const Text('Révoquer cet accès'),
              ),
            ],
            const Align(
              alignment: Alignment.centerRight,
              child: _StatusPill(label: 'DÉMO D1'),
            ),
          ],
        ),
      ),
    );
  }
}

class _DelegateAccessDialog extends StatefulWidget {
  const _DelegateAccessDialog();

  @override
  State<_DelegateAccessDialog> createState() => _DelegateAccessDialogState();
}

class _DelegateAccessDialogState extends State<_DelegateAccessDialog> {
  final _name = TextEditingController();
  String _relationship = 'Fils';
  String _scope = 'Parcours, médicaments';
  String _duration = 'Sans date d’expiration';
  bool _canManageGrants = false;
  String? _nameError;

  @override
  void dispose() {
    _name.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text('Déléguer à un proche'),
      content: SingleChildScrollView(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextField(
              controller: _name,
              decoration: InputDecoration(
                labelText: 'Nom du proche',
                errorText: _nameError,
              ),
            ),
            const SizedBox(height: 12),
            DropdownButtonFormField<String>(
              value: _relationship,
              decoration: const InputDecoration(labelText: 'Lien'),
              items: const [
                DropdownMenuItem(value: 'Fils', child: Text('Fils')),
                DropdownMenuItem(value: 'Fille', child: Text('Fille')),
                DropdownMenuItem(value: 'Conjoint·e', child: Text('Conjoint·e')),
                DropdownMenuItem(value: 'Aidant·e', child: Text('Aidant·e')),
              ],
              onChanged: (value) => setState(() => _relationship = value!),
            ),
            const SizedBox(height: 12),
            DropdownButtonFormField<String>(
              value: _scope,
              decoration: const InputDecoration(labelText: 'Portée'),
              items: const [
                DropdownMenuItem(
                  value: 'Parcours, médicaments',
                  child: Text('Parcours + médicaments'),
                ),
                DropdownMenuItem(value: 'Médicaments', child: Text('Médicaments uniquement')),
              ],
              onChanged: (value) => setState(() => _scope = value!),
            ),
            const SizedBox(height: 12),
            DropdownButtonFormField<String>(
              value: _duration,
              decoration: const InputDecoration(labelText: 'Durée'),
              items: const [
                DropdownMenuItem(
                  value: 'Sans date d’expiration',
                  child: Text('Jusqu’à révocation'),
                ),
                DropdownMenuItem(value: 'Expire dans 30 jours', child: Text('30 jours')),
              ],
              onChanged: (value) => setState(() => _duration = value!),
            ),
            SwitchListTile(
              contentPadding: EdgeInsets.zero,
              value: _canManageGrants,
              title: const Text('Peut gérer mes accès'),
              onChanged: (value) => setState(() => _canManageGrants = value),
            ),
          ],
        ),
      ),
      actions: [
        TextButton(onPressed: () => Navigator.pop(context), child: const Text('Annuler')),
        FilledButton(onPressed: _submit, child: const Text('Déléguer')),
      ],
    );
  }

  void _submit() {
    final name = _name.text.trim();
    if (name.isEmpty) {
      setState(() => _nameError = 'Indiquez le nom du proche.');
      return;
    }
    Navigator.pop(
      context,
      CanonicalDelegation(
        delegate: name,
        relationship: _relationship,
        scope: _scope,
        canManageGrants: _canManageGrants,
        grantedAt: 'Déléguée pendant cette session',
        expiresAt: _duration,
      ),
    );
  }
}

class _DelegationCard extends StatelessWidget {
  const _DelegationCard({
    required this.delegation,
    required this.withdrawn,
    required this.onWithdraw,
  });

  final CanonicalDelegation delegation;
  final bool withdrawn;
  final VoidCallback onWithdraw;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(Icons.family_restroom_rounded, color: PatientColors.brand),
                const SizedBox(width: 10),
                Expanded(
                  child: Text(
                    '${delegation.delegate} · ${delegation.relationship}',
                    style: Theme.of(context).textTheme.titleMedium,
                  ),
                ),
                _StatusPill(label: withdrawn ? 'RETIRÉ' : 'DÉLÉGUÉ'),
              ],
            ),
            const SizedBox(height: 10),
            Text(delegation.scope),
            const SizedBox(height: 4),
            Text(
              delegation.canManageGrants
                  ? 'Peut gérer vos accès'
                  : 'Lecture seule — ne peut pas gérer vos accès',
              style: const TextStyle(color: PatientColors.muted),
            ),
            const SizedBox(height: 4),
            Text(
              '${delegation.grantedAt} · ${delegation.expiresAt}',
              style: const TextStyle(color: PatientColors.muted),
            ),
            if (!withdrawn) ...[
              const SizedBox(height: 12),
              OutlinedButton.icon(
                onPressed: onWithdraw,
                icon: const Icon(Icons.person_remove_outlined),
                label: const Text('Retirer la délégation'),
              ),
            ],
            const Align(
              alignment: Alignment.centerRight,
              child: _StatusPill(label: 'DÉMO D1'),
            ),
          ],
        ),
      ),
    );
  }
}

class _AuthorizedViewCard extends StatelessWidget {
  const _AuthorizedViewCard();

  @override
  Widget build(BuildContext context) {
    return Card(
      color: PatientColors.brand,
      child: Padding(
        padding: const EdgeInsets.all(18),
        child: Row(
          children: [
            const CircleAvatar(
              backgroundColor: Colors.white24,
              child: Icon(Icons.lock_open_rounded, color: Colors.white),
            ),
            const SizedBox(width: 14),
            const Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Vue autorisee active',
                    style: TextStyle(
                      color: Colors.white,
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                ],
              ),
            ),
            const Icon(Icons.check_circle_rounded, color: Colors.white),
          ],
        ),
      ),
    );
  }
}

class _DashboardMetric extends StatelessWidget {
  const _DashboardMetric({
    required this.icon,
    required this.value,
    required this.label,
  });

  final IconData icon;
  final String value;
  final String label;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Icon(icon, color: PatientColors.brand),
            const SizedBox(height: 12),
            Text(value, style: Theme.of(context).textTheme.headlineMedium),
            const SizedBox(height: 2),
            Text(label, style: const TextStyle(color: PatientColors.muted)),
          ],
        ),
      ),
    );
  }
}

class _ProfileContent extends StatelessWidget {
  const _ProfileContent();

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Row(
          children: [
            const CircleAvatar(
              radius: 30,
              backgroundColor: PatientColors.brandSoft,
              foregroundColor: PatientColors.brand,
              child: Text(
                'LM',
                style: TextStyle(fontSize: 20, fontWeight: FontWeight.w800),
              ),
            ),
            const SizedBox(width: 16),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    demoPatient.displayName,
                    style: Theme.of(context).textTheme.titleLarge,
                  ),
                  const SizedBox(height: 4),
                  Text('${demoPatient.city} · ${demoPatient.id}'),
                  const SizedBox(height: 8),
                  const Text(
                    'Identité fictive HC-005',
                    style: TextStyle(
                      color: PatientColors.demo,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _TimelineContent extends StatelessWidget {
  const _TimelineContent();

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Parcours médical fédéré',
          style: Theme.of(context).textTheme.headlineSmall,
        ),
        const SizedBox(height: 6),
        const Text(
          'Une vue longitudinale composée de sources autorisées.',
          style: TextStyle(color: PatientColors.muted, fontSize: 16),
        ),
        const SizedBox(height: 18),
        for (var index = 0; index < demoTimeline.length; index++)
          _TimelineEventCard(
            event: demoTimeline[index],
            isLast: index == demoTimeline.length - 1,
          ),
      ],
    );
  }
}

class _TimelineEventCard extends StatelessWidget {
  const _TimelineEventCard({required this.event, required this.isLast});

  final CanonicalTimelineEvent event;
  final bool isLast;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: EdgeInsets.only(bottom: isLast ? 0 : 12),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Column(
            children: [
              const Icon(Icons.circle, size: 12, color: PatientColors.brand),
              if (!isLast)
                Container(
                  width: 2,
                  height: 72,
                  color: PatientColors.brandSoft,
                ),
            ],
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Card(
              clipBehavior: Clip.antiAlias,
              child: InkWell(
                onTap: () => _showEventDetail(context),
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(event.date, style: const TextStyle(color: PatientColors.muted)),
                      const SizedBox(height: 4),
                      Text(event.title, style: Theme.of(context).textTheme.titleMedium),
                      const SizedBox(height: 4),
                      Text(event.organization, style: const TextStyle(fontWeight: FontWeight.w700)),
                      const SizedBox(height: 8),
                      Text(event.summary),
                      const SizedBox(height: 10),
                      Row(
                        children: [
                          _StatusPill(label: event.kind),
                          const SizedBox(width: 8),
                          const _StatusPill(label: 'AUTORISÉ'),
                        ],
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  void _showEventDetail(BuildContext context) {
    showModalBottomSheet<void>(
      context: context,
      showDragHandle: true,
      builder: (context) => SafeArea(
        child: ListView(
          shrinkWrap: true,
          padding: const EdgeInsets.fromLTRB(24, 8, 24, 24),
          children: [
            Text(event.title, style: Theme.of(context).textTheme.headlineSmall),
            const SizedBox(height: 8),
            Text(event.date, style: const TextStyle(color: PatientColors.muted)),
            const SizedBox(height: 20),
            _DetailRow(label: 'Organisation', value: event.organization),
            _DetailRow(label: 'Type', value: event.kind),
            _DetailRow(label: 'Resume', value: event.summary),
            const SizedBox(height: 12),
            const Row(
              children: [
                _StatusPill(label: 'AUTORISÉ'),
                SizedBox(width: 8),
                _StatusPill(label: 'DÉMO D1'),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class _DetailRow extends StatelessWidget {
  const _DetailRow({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 14),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(label, style: const TextStyle(color: PatientColors.muted)),
          const SizedBox(height: 3),
          Text(value, style: Theme.of(context).textTheme.titleMedium),
        ],
      ),
    );
  }
}

class _PlannedContent extends StatelessWidget {
  const _PlannedContent({
    required this.icon,
    required this.title,
    required this.message,
  });

  final IconData icon;
  final String title;
  final String message;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          children: [
            Icon(icon, size: 48, color: PatientColors.brand),
            const SizedBox(height: 16),
            Text(
              title,
              textAlign: TextAlign.center,
              style: Theme.of(context).textTheme.titleLarge,
            ),
            const SizedBox(height: 8),
            Text(message, textAlign: TextAlign.center),
            const SizedBox(height: 16),
            const _StatusPill(label: 'PLANNED'),
          ],
        ),
      ),
    );
  }
}

class _PreviewCard extends StatelessWidget {
  const _PreviewCard({
    required this.icon,
    required this.title,
    required this.description,
  });

  final IconData icon;
  final String title;
  final String description;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(18),
        child: Row(
          children: [
            Container(
              width: 48,
              height: 48,
              decoration: const BoxDecoration(
                color: PatientColors.brandSoft,
                borderRadius: BorderRadius.all(Radius.circular(15)),
              ),
              child: Icon(icon, color: PatientColors.brand),
            ),
            const SizedBox(width: 14),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(title, style: Theme.of(context).textTheme.titleMedium),
                  const SizedBox(height: 3),
                  Text(description),
                ],
              ),
            ),
            const Icon(Icons.chevron_right_rounded, color: PatientColors.muted),
          ],
        ),
      ),
    );
  }
}

class _DemoBanner extends StatelessWidget {
  const _DemoBanner();

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
      decoration: BoxDecoration(
        color: PatientColors.demoSoft,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: const Color(0xFFDDD6FE)),
      ),
      child: const Row(
        children: [
          Icon(Icons.science_outlined, color: PatientColors.demo),
          SizedBox(width: 10),
          Expanded(
            child: Text(
              'DÉMO D1 · Données entièrement fictives',
              style: TextStyle(
                color: PatientColors.demo,
                fontWeight: FontWeight.w800,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _StateView extends StatelessWidget {
  const _StateView({
    super.key,
    required this.icon,
    required this.title,
    required this.message,
    this.action,
  });

  final Widget icon;
  final String title;
  final String message;
  final Widget? action;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: SingleChildScrollView(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            icon,
            const SizedBox(height: 18),
            Text(
              title,
              textAlign: TextAlign.center,
              style: Theme.of(context).textTheme.titleLarge,
            ),
            const SizedBox(height: 8),
            Text(message, textAlign: TextAlign.center),
            if (action != null) ...[const SizedBox(height: 20), action!],
          ],
        ),
      ),
    );
  }
}

class _LoadingIndicator extends StatelessWidget {
  const _LoadingIndicator();

  @override
  Widget build(BuildContext context) {
    return const SizedBox(
      width: 42,
      height: 42,
      child: CircularProgressIndicator(strokeWidth: 3),
    );
  }
}

class _StatusPill extends StatelessWidget {
  const _StatusPill({required this.label});

  final String label;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
      decoration: BoxDecoration(
        color: PatientColors.demoSoft,
        borderRadius: BorderRadius.circular(999),
      ),
      child: Text(
        label,
        style: const TextStyle(
          color: PatientColors.demo,
          fontSize: 12,
          fontWeight: FontWeight.w800,
        ),
      ),
    );
  }
}
