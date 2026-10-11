import 'package:flutter/material.dart';

import '../demo/canonical_clinician.dart';
import 'clinician_dashboard.dart';
import 'clinician_destination.dart';
import 'clinician_theme.dart';
import 'priority_queue_view.dart';
import 'recording_consent_view.dart';

enum ShellDemoState { content, loading, empty, error }

class ClinicianShell extends StatefulWidget {
  const ClinicianShell({super.key});

  @override
  State<ClinicianShell> createState() => _ClinicianShellState();
}

class _ClinicianShellState extends State<ClinicianShell> {
  ClinicianDestination _selected = ClinicianDestination.home;
  ShellDemoState _demoState = ShellDemoState.content;

  static const _destinations = <NavigationDestination>[
    NavigationDestination(
      icon: Icon(Icons.dashboard_outlined),
      selectedIcon: Icon(Icons.dashboard_rounded),
      label: 'Accueil',
    ),
    NavigationDestination(
      icon: Icon(Icons.format_list_numbered_outlined),
      selectedIcon: Icon(Icons.format_list_numbered_rounded),
      label: 'File',
    ),
    NavigationDestination(
      icon: Icon(Icons.people_outline_rounded),
      selectedIcon: Icon(Icons.people_rounded),
      label: 'Patients',
    ),
    NavigationDestination(
      icon: Icon(Icons.medical_services_outlined),
      selectedIcon: Icon(Icons.medical_services_rounded),
      label: 'Consultation',
    ),
    NavigationDestination(
      icon: Icon(Icons.notifications_none_rounded),
      selectedIcon: Icon(Icons.notifications_rounded),
      label: 'Alertes',
    ),
  ];

  static const _titles = {
    ClinicianDestination.home: 'Tableau de bord',
    ClinicianDestination.queue: 'File patients',
    ClinicianDestination.patients: 'Mes patients',
    ClinicianDestination.consultation: 'Consultation',
    ClinicianDestination.alerts: 'Mes alertes',
  };

  void _select(ClinicianDestination destination) {
    setState(() {
      _selected = destination;
      _demoState = ShellDemoState.content;
    });
  }

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
                color: ClinicianColors.brand,
                borderRadius: BorderRadius.all(Radius.circular(12)),
              ),
              child: const Icon(
                Icons.medical_services_rounded,
                color: Colors.white,
                size: 20,
              ),
            ),
            const SizedBox(width: 12),
            Expanded(child: Text(_titles[_selected]!)),
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
          IconButton(
            tooltip: 'Profil du clinicien',
            onPressed: () => _showProfile(context),
            icon: CircleAvatar(
              radius: 16,
              backgroundColor: ClinicianColors.brandSoft,
              foregroundColor: ClinicianColors.brand,
              child: Text(
                demoClinician.initials,
                style: const TextStyle(
                  fontSize: 12,
                  fontWeight: FontWeight.w800,
                ),
              ),
            ),
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
        selectedIndex: _selected.index,
        destinations: _destinations,
        onDestinationSelected: (index) =>
            _select(ClinicianDestination.values[index]),
      ),
    );
  }

  void _showProfile(BuildContext context) {
    showModalBottomSheet<void>(
      context: context,
      showDragHandle: true,
      backgroundColor: Colors.white,
      builder: (context) => const _ProfileSheet(),
    );
  }

  Widget _buildState() {
    return switch (_demoState) {
      ShellDemoState.content => _ContentView(
        destination: _selected,
        onNavigate: _select,
      ),
      ShellDemoState.loading => const _StateView(
        key: ValueKey('loading'),
        icon: _LoadingIndicator(),
        title: 'Chargement du contexte patient autorisé',
        message: 'Simulation locale — aucune donnée hospitalière réelle.',
      ),
      ShellDemoState.empty => const _StateView(
        key: ValueKey('empty'),
        icon: Icon(Icons.inbox_outlined, size: 48),
        title: 'Aucun contexte patient autorisé',
        message:
            'Les informations apparaîtront ici lorsqu’un patient vous aura accordé un accès.',
      ),
      ShellDemoState.error => _StateView(
        key: const ValueKey('error'),
        icon: const Icon(
          Icons.cloud_off_outlined,
          size: 48,
          color: ClinicianColors.danger,
        ),
        title: 'Contexte temporairement indisponible',
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
  const _ContentView({required this.destination, required this.onNavigate});

  final ClinicianDestination destination;
  final ValueChanged<ClinicianDestination> onNavigate;

  @override
  Widget build(BuildContext context) {
    final content = switch (destination) {
      ClinicianDestination.home => ClinicianDashboard(onNavigate: onNavigate),
      ClinicianDestination.queue => const PriorityQueueView(),
      ClinicianDestination.patients => const _PlannedContent(
        icon: Icons.people_rounded,
        title: 'Patients autorisés',
        message:
            'La liste des patients autorisés, leur fiche et leur historique fédéré seront livrés par HC-033 à HC-035. Ce shell ne charge aucun dossier clinique.',
      ),
      ClinicianDestination.consultation => const RecordingConsentView(),
      ClinicianDestination.alerts => const _PlannedContent(
        icon: Icons.notifications_rounded,
        title: 'Centre d’alertes',
        message:
            'Le centre d’alertes sera livré par HC-043. Aucune alerte réelle n’est reçue ici.',
      ),
    };

    return ListView(
      key: ValueKey('content-${destination.name}'),
      padding: const EdgeInsets.fromLTRB(20, 12, 20, 28),
      children: [const _DemoBanner(), const SizedBox(height: 20), content],
    );
  }
}

class _ProfileSheet extends StatelessWidget {
  const _ProfileSheet();

  @override
  Widget build(BuildContext context) {
    return SafeArea(
      child: Padding(
        padding: const EdgeInsets.fromLTRB(24, 0, 24, 24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                CircleAvatar(
                  radius: 30,
                  backgroundColor: ClinicianColors.brandSoft,
                  foregroundColor: ClinicianColors.brand,
                  child: Text(
                    demoClinician.initials,
                    style: const TextStyle(
                      fontSize: 20,
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                ),
                const SizedBox(width: 16),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        demoClinician.displayName,
                        style: Theme.of(context).textTheme.titleLarge,
                      ),
                      const SizedBox(height: 4),
                      Text(
                        '${demoClinician.roleLabel} · ${demoClinician.specialty}',
                      ),
                      Text(
                        '${demoClinician.organizationName} · ${demoClinician.id}',
                      ),
                    ],
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),
            const Text(
              'Identité fictive HC-005',
              style: TextStyle(
                color: ClinicianColors.demo,
                fontWeight: FontWeight.w700,
              ),
            ),
            const SizedBox(height: 4),
            const Text(
              'Session simulée : aucune authentification ni autorisation réelle.',
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
            Icon(icon, size: 48, color: ClinicianColors.brand),
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

class _DemoBanner extends StatelessWidget {
  const _DemoBanner();

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
      decoration: BoxDecoration(
        color: ClinicianColors.demoSoft,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: const Color(0xFFDDD6FE)),
      ),
      child: const Row(
        children: [
          Icon(Icons.science_outlined, color: ClinicianColors.demo),
          SizedBox(width: 10),
          Expanded(
            child: Text(
              'DÉMO D1 · Données entièrement fictives',
              style: TextStyle(
                color: ClinicianColors.demo,
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
        color: ClinicianColors.demoSoft,
        borderRadius: BorderRadius.circular(999),
      ),
      child: Text(
        label,
        style: const TextStyle(
          color: ClinicianColors.demo,
          fontSize: 12,
          fontWeight: FontWeight.w800,
        ),
      ),
    );
  }
}
