import 'package:flutter/material.dart';

import 'clinician_theme.dart';

/// Formats a fixture's `YYYY-MM-DD` date as `DD/MM/YYYY`.
String formatDemoDate(String isoDate) =>
    '${isoDate.substring(8, 10)}/${isoDate.substring(5, 7)}/${isoDate.substring(0, 4)}';

/// French label of an access grant's record kind.
String scopeLabel(String kind) => switch (kind) {
  'encounters' => 'Parcours',
  'medications' => 'Médicaments',
  'labReports' => 'Laboratoires',
  _ => kind,
};

/// French label and colors for a fixture's `high` / `medium` / `low` value,
/// shared by alert severity and queue priority.
(String, Color, Color) severityStyle(String severity) => switch (severity) {
  'high' => ('Élevée', ClinicianColors.danger, const Color(0xFFFEF2F2)),
  'medium' => ('Moyenne', const Color(0xFFB45309), const Color(0xFFFFFBEB)),
  _ => ('Faible', ClinicianColors.muted, const Color(0xFFF1F5F9)),
};

class LabelTag extends StatelessWidget {
  const LabelTag({
    super.key,
    required this.label,
    required this.color,
    required this.background,
  });

  final String label;
  final Color color;
  final Color background;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: background,
        borderRadius: BorderRadius.circular(999),
      ),
      child: Text(
        label,
        style: TextStyle(
          color: color,
          fontSize: 11,
          fontWeight: FontWeight.w800,
        ),
      ),
    );
  }
}

/// Permanent D1 demo label shown on every screen.
class DemoBanner extends StatelessWidget {
  const DemoBanner({super.key});

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
