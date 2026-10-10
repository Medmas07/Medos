import 'package:flutter/material.dart';

import '../presentation/patient_shell.dart';
import '../presentation/patient_theme.dart';

class PatientApp extends StatelessWidget {
  const PatientApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'HackCure Patient',
      debugShowCheckedModeBanner: false,
      theme: PatientTheme.light(),
      home: const PatientShell(),
    );
  }
}
