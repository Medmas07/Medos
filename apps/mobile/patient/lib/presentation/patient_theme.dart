import 'package:flutter/material.dart';

abstract final class PatientColors {
  static const brand = Color(0xFF0F766E);
  static const brandSoft = Color(0xFFF0FDFA);
  static const demo = Color(0xFF6D28D9);
  static const demoSoft = Color(0xFFF5F3FF);
  static const surface = Color(0xFFF8FAFC);
  static const ink = Color(0xFF0F172A);
  static const muted = Color(0xFF475569);
  static const border = Color(0xFFE2E8F0);
}

abstract final class PatientTheme {
  static ThemeData light() {
    final colorScheme = ColorScheme.fromSeed(
      seedColor: PatientColors.brand,
      brightness: Brightness.light,
      surface: Colors.white,
    );

    return ThemeData(
      useMaterial3: true,
      colorScheme: colorScheme,
      scaffoldBackgroundColor: PatientColors.surface,
      appBarTheme: const AppBarTheme(
        backgroundColor: Colors.white,
        foregroundColor: PatientColors.ink,
        surfaceTintColor: Colors.transparent,
        elevation: 0,
      ),
      navigationBarTheme: NavigationBarThemeData(
        backgroundColor: Colors.white,
        indicatorColor: PatientColors.brandSoft,
        labelTextStyle: WidgetStateProperty.resolveWith((states) {
          return TextStyle(
            color: states.contains(WidgetState.selected)
                ? PatientColors.brand
                : PatientColors.muted,
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
          side: BorderSide(color: PatientColors.border),
        ),
      ),
      textTheme: const TextTheme(
        headlineSmall: TextStyle(
          color: PatientColors.ink,
          fontWeight: FontWeight.w800,
        ),
        titleLarge: TextStyle(
          color: PatientColors.ink,
          fontWeight: FontWeight.w700,
        ),
        titleMedium: TextStyle(
          color: PatientColors.ink,
          fontWeight: FontWeight.w700,
        ),
        bodyMedium: TextStyle(color: PatientColors.muted, height: 1.45),
      ),
    );
  }
}
