import 'package:flutter/material.dart';

import 'clinician_theme.dart';

/// Formats a fixture's `YYYY-MM-DD` date as `DD/MM/YYYY`.
String formatDemoDate(String isoDate) =>
    '${isoDate.substring(8, 10)}/${isoDate.substring(5, 7)}/${isoDate.substring(0, 4)}';

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
