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

## Bericht erstellen (RMarkdown)
Für einen druckoptimierten Datenqualitätsbericht steht `reports/data-quality-report.Rmd` bereit. Voraussetzungen: R mit den Paketen `rmarkdown`, `pagedown`, `tidyverse`, `janitor`, `skimr`, `gridExtra` und optional `naniar`.

Beispielaufruf in R:

```r
rmarkdown::render(
  "reports/data-quality-report.Rmd",
  params = list(
    data_path = "data/input.csv", # Pfad zur CSV-Datenquelle
    report_title = "Datenqualitätsbericht"
  )
)
```

Das Ergebnis ist ein paginiertes HTML-Dokument (A4) mit Deskriptivstatistiken, Verteilungsplots, Ausreißer- und Fehlwert-Analysen. Das Layout wird über `reports/report.css` gesteuert.
