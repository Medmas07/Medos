import 'package:flutter/material.dart';

abstract final class ClinicianColors {
  static const brand = Color(0xFF1D4ED8);
  static const brandSoft = Color(0xFFEFF6FF);
  static const demo = Color(0xFF6D28D9);
  static const demoSoft = Color(0xFFF5F3FF);
  static const surface = Color(0xFFF8FAFC);
  static const ink = Color(0xFF0F172A);
  static const muted = Color(0xFF475569);
  static const border = Color(0xFFE2E8F0);
  static const danger = Color(0xFFB91C1C);
}

abstract final class ClinicianTheme {
  static ThemeData light() {
    final colorScheme = ColorScheme.fromSeed(
      seedColor: ClinicianColors.brand,
      brightness: Brightness.light,
      surface: Colors.white,
    );

    return ThemeData(
      useMaterial3: true,
      colorScheme: colorScheme,
      scaffoldBackgroundColor: ClinicianColors.surface,
      appBarTheme: const AppBarTheme(
        backgroundColor: Colors.white,
        foregroundColor: ClinicianColors.ink,
        surfaceTintColor: Colors.transparent,
        elevation: 0,
      ),
      navigationBarTheme: NavigationBarThemeData(
        backgroundColor: Colors.white,
        indicatorColor: ClinicianColors.brandSoft,
        labelTextStyle: WidgetStateProperty.resolveWith((states) {
          return TextStyle(
            fontSize: 12,
            color: states.contains(WidgetState.selected)
                ? ClinicianColors.brand
                : ClinicianColors.muted,
            fontWeight: states.contains(WidgetState.selected)
                ? FontWeight.w700
                : FontWeight.w500,
          );
        }),
      ),
      cardTheme: const CardThemeData(
        color: Colors.white,
        surfaceTintColor: Colors.transparent,
        elevation: 0,
        margin: EdgeInsets.zero,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.all(Radius.circular(20)),
          side: BorderSide(color: ClinicianColors.border),
        ),
      ),
      textTheme: const TextTheme(
        headlineSmall: TextStyle(
          color: ClinicianColors.ink,
          fontWeight: FontWeight.w800,
        ),
        titleLarge: TextStyle(
          color: ClinicianColors.ink,
          fontWeight: FontWeight.w700,
        ),
        titleMedium: TextStyle(
          color: ClinicianColors.ink,
          fontWeight: FontWeight.w700,
        ),
        bodyMedium: TextStyle(color: ClinicianColors.muted, height: 1.45),
      ),
    );
  }
}
