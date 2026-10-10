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
      1 => const _PlannedContent(
        icon: Icons.timeline_rounded,
        title: 'Parcours médical fédéré',
        message:
            'La chronologie autorisée sera livrée par HC-012. Ce shell ne charge encore aucun dossier clinique.',
      ),
      2 => const _PlannedContent(
        icon: Icons.shield_outlined,
        title: 'Consentements et accès',
        message:
            'La gestion des accès sera livrée par HC-017 à HC-021. Aucun consentement réel n’est modifié ici.',
      ),
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
      ],
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
