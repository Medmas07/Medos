import 'package:flutter/material.dart';

import '../presentation/clinician_shell.dart';
import '../presentation/clinician_theme.dart';

class ClinicianApp extends StatelessWidget {
  const ClinicianApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'HackCure Clinicien',
      debugShowCheckedModeBanner: false,
      theme: ClinicianTheme.light(),
      home: const ClinicianShell(),
    );
  }
}
