# RMarkdown-Datenqualitätsbericht (Spezifikation)

## Ziel
Ein ausführlicher, druckoptimierter Bericht auf Basis von **RMarkdown**, der Deskriptivstatistiken, Verteilungsübersichten, Ausreißer- und Fehlwertanalysen für tabellarische Datensätze liefert. Das Layout soll für A4-Druck bzw. PDF-Export paginiert sein.

## Deliverables
1. **RMarkdown-Vorlage** `reports/data-quality-report.Rmd` mit Parametern (mindestens `data_path`, optional `report_title`, `missing_threshold`).
2. **Custom-CSS** `reports/report.css` für paginiertes Druck-Layout (A4-Hochformat, Kopf-/Fußzeile, Abschnittstrennungen per `page-break`-Klassen).
3. **Kurzanleitung** im README-Abschnitt „Bericht erstellen“ zum Rendern mit `rmarkdown::render()` inkl. benötigter Pakete.

## Funktionale Anforderungen
* **Dateninput**: CSV-Datei (UTF-8), eingelesen via `readr::read_csv(show_col_types = FALSE)`; Parametrisierung über `params$data_path`.
* **Berichtsinhalte**:
  - Titelseite mit Reporttitel, Datum, Pfad der Datenquelle.
  - Inhaltsverzeichnis (TOC) bis Tiefe 3.
  - Abschnitt „Datenüberblick“: Zeilen/Spalten-Anzahl, Spaltentypen, Anteil fehlender Werte je Spalte.
  - Abschnitt „Deskriptive Statistiken“:
    * Numerische Variablen: Mittelwert, Median, SD, Min/Max, IQR, Missing-Quote; Tabelle via `dplyr` + `knitr::kable`.
    * Kategorische Variablen: Häufigkeitstabelle (Top-N, default 10) und Missing-Quote.
  - Abschnitt „Verteilungen & Ausreißer“:
    * Für jede numerische Spalte Histogramm + Dichteschätzer (ggplot2) auf Gitternetz, 4 Plots pro Seite mit page-break nach jeder Gruppe.
    * Ausreißer-Kennzahlen pro Spalte nach IQR-Regel (1.5 * IQR); Ausgabe von Unter-/Obergrenze, Anzahl, Anteil.
  - Abschnitt „Fehlende Werte & Datenqualität“:
    * Gesamtsumme fehlender Zellen und Prozent.
    * Heatmap der Missing-Struktur (`naniar::vis_miss`) oder Fallback-Tabelle, falls Paket fehlt.
    * Optional: Duplikatzahl (volle Zeilen) und Anteil.
* **Pagination / Layout**:
  - Verwendung von `pagedown::html_paged` als Output-Format; CSS definiert A4-Ränder, Kopf-/Fußzeile mit Seitenzahlen, `.page-break` Utility.
  - Plots skalieren auf Druckbreite, barrierearme Schrift (z. B. `Inter` oder system-sans) über Google Fonts-Link im YAML-Header.

## Nicht-funktionale Anforderungen
* Keine externen Datenquellen laden (alles lokal). 
* R-Pakete: `tidyverse`, `skimr`, `naniar`, `janitor`, `pagedown`. Plots mit `ggplot2`. Fallback-Code, falls `naniar` nicht installiert (simple Missing-Tabelle).
* Strikte UTF-8-Ausgabe.

## Offene Fragen
* Gibt es bevorzugte Standardpfade für Quelldaten (z. B. `data/input.csv`)?
* Sollen zusätzliche Konfidenzintervalle oder Tests (z. B. Shapiro-Wilk) aufgenommen werden?
* Welche Default-Schwellen für „hohe Missing-Quote“ sind gewünscht (aktuell Parameter `missing_threshold`, z. B. 0.2)?
