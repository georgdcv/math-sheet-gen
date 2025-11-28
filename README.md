# math-sheet-gen

Automatisierte Erstellung von druckbaren Mathearbeitsblättern gemäß der Spezifikation in `codex/specs/worksheet-generator.md`.

## Nutzung
1. Passe die Einstellungen in `config.yaml` an (Aufgabentypen, Wertebereiche, Ausgabeverzeichnis usw.).
2. Führe den Generator aus:
   ```bash
   python generate_worksheets.py --config config.yaml
   ```
3. Die Arbeitsblätter (inklusive Lösungsblätter) werden im konfigurierten `output.out_dir` abgelegt.

Die Konfiguration kann wahlweise mit PyYAML gelesen werden (CI-Standard) oder mit dem eingebauten Minimal-YAML-Parser, falls keine externen Pakete installiert werden können.
