# Spezifikation: Generator für Grundschul-Arbeitsblätter

## Ziel
Erzeugung von einzelnen HTML-Arbeitsblättern (inkl. Lösungsblatt) für Grundschulmathematik. Fokus auf A4-Hochformat, druckoptimiert, ohne Browser-Interaktivität. Die komplette Steuerung erfolgt über `config.yaml`; die Generatorlogik soll deterministisch über RNG-Seeds reproduzierbar sein.

## Ein- und Ausgaben
- **Konfiguration:** Nur über `config.yaml`.
- **Batch:** Mehrere Blätter mit identischen Einstellungen, aber unterschiedlichen Seeds (`base_seed + worksheet_index`).
- **Ausgabe:** Einzelne HTML-Dateien im konfigurierten Ausgabeverzeichnis `output.out_dir` mit Namensschema `<file_prefix>_<index:03d>.html` und `<file_prefix>_<index:03d>_loesung.html`.

### Konfigurationsformat (aktuelle Implementierung)
- Wurzel: `base_seed`, `worksheet_count`, `output`, `worksheet`.
- `output`: `out_dir`, `file_prefix`.
- `worksheet`: `header_left_label`, `header_right_label`, `tasks` (Liste).
- Jedes Task-Element besitzt `type` und optionale Felder:
  - `number_dictation`: `box_count`, `show_helper_numbers` (setzt im Lösungsblatt Hilfsziffern 1..n ein), `title`.
  - `compare_numbers`: `item_count`, `min_value`, `max_value`, `columns`, `equal_probability`, `title`.
  - `pre_succ_table`: `row_count`, `min_value`, `max_value`, `given_field` (`middle` Standard, alternativ `left`, `right`, `mixed`), `title`.
  - `arithmetic_list`: `item_count`, `operations` (`+`/`-`), `min_value`, `max_value`, `allow_negative_results`, `columns`, `title`.
  - `number_word_table`: `first_row_example` (Bool, fügt über `example_number` eine komplett ausgefüllte Beispielzeile hinzu), `row_count` (Anzahl Übungszeilen **exklusive** Beispiel), `min_value`, `max_value`, `given_columns` (Spalten, die im Aufgabenblatt gefüllt sind), `title`.
  - `ordering`: `set_size`, `min_value`, `max_value`, `order` (`increasing`/`decreasing`), `show_comparison_symbols`, `title`.
  - `operation_table`: `result_range` (`min`, `max` Pflicht), `tables` (Liste mit `operation`, `row_count`, `col_count`, `given_cells`), `title`.
    - Zeilen- und Spaltenköpfe werden beim Generieren aus Vielfachen von 10 (0–100) gezogen; Standardanzahl pro Richtung ist 2, wenn nichts angegeben ist.
    - `given_cells`: `none`, `diagonal`, `random_<n>` oder explizite Koordinatenliste.
    - Ergebnisse außerhalb `result_range`, Summen über 100 oder Differenzen unter 0 führen zu einem Fehler.
  - `number_line`: `start`, `end`, `major_tick_interval`, `value_count` (Anzahl zu platzierender Zahlen; Standard 5, Zufallsauswahl außerhalb der Major-Ticks), optional `values`, `title`.

## Layout-Vorgaben
- Jede HTML-Datei enthält genau ein Arbeitsblatt mit optionale `page-break-after: always;`.
- Kopfzeile mit zwei Feldern (z. B. Name/Datum) getrennt durch eine Linie.
- Grundlegende Styles laut Beispiel: 12pt, serifenlose Schrift; nummerierte Kästchen (1cm) für Eingabefelder.
- Für Zahlwort-/Würfel-Aufgaben Google-Font „Zain“ einbinden (preconnect + stylesheet-Link).

## Unterstützte Aufgabentypen (Version 1)
Jeder Typ hat einen `type`-Bezeichner und eigene Parameter. Standardregeln: Aufgaben nur erzeugen, wenn Ergebnisse im erlaubten Bereich liegen; ggf. neu ziehen.

1. **Zahldiktat (`number_dictation`)**
   - Darstellung: Eine Zeile mit n leeren, eingerahmten Kästchen.
   - Parameter: `box_count`. Lösungsblatt kann Hilfszahlen enthalten; Aufgabenblatt bleibt leer.

2. **Zahlen vergleichen (`compare_numbers`)**
   - Instruktion: "Vergleiche! <, >, =".
   - Elemente: Paare (a, b) mit Leerfeld (Kreis) für Vergleichszeichen.
   - Parameter: `item_count`, `min_value`, `max_value`, `columns` (Default 3), `equal_probability` (Default 0.2).
   - Lösungsblatt trägt korrektes Zeichen ein.

3. **Vorgänger/Zahl/Nachfolger (`pre_succ_table`)**
   - Tabelle mit Spalten „Vorgänger | Zahl | Nachfolger“.
   - Parameter: `row_count`, `min_value`, `max_value`, `given_field` (`middle`, `left`, `right`, `mixed`).
   - Bei `mixed` pro Zeile zufällig wählbarer leerer Bereich. Lösungsblatt füllt alle Felder.

4. **Rechnen in einer Liste (`arithmetic_list`)**
   - Instruktion: "Rechne! Achte auf das Rechenzeichen!".
   - Einfache Plus/Minus-Aufgaben in Spalten untereinander.
   - Parameter: `item_count`, `operations` (Subset von `+`, `-`), `min_value`, `max_value`, `allow_negative_results` (Default false), `columns` (Default 2).

5. **Zahlwort – Würfelbild – Zahl (`number_word_table`)**
   - Tabelle „Zahlwort | Würfelbild | Zahl“ für zweistellige Zahlen (11–99 empfohlen).
   - Parameter: `first_row_example` (Default true) mit `example_number` (Default 49), `row_count`, `min_value`, `max_value`, `given_columns` (Subset von `word`, `dice`, `number`).
   - Zehner als Strichgruppen, Einer als Würfelbild (5er-Clustering möglich). Lösungsblatt füllt fehlende Felder.
   - Zusammengesetzte Zahlwörter nutzen die Standard-Unterstreichung des „und“ (kein Sonderformat nötig).

6. **Zahlen ordnen (`ordering`)**
   - Instruktion: "Ordne! Beginne mit der kleinsten/größten Zahl!" (unterstrichene Vorgabe richtet sich nach `order`).
   - Parameter: `set_size`, `min_value`, `max_value`, `order` (`increasing` Standard, alternativ `decreasing`), `show_comparison_symbols` (Bool für `<` oder `>` zwischen Kästchen).
   - Alle Zahlen eines Sets müssen verschieden sein.

7. **Rechentabellen (`operation_table`)**
   - Instruktion: "Achte auf das Rechenzeichen!".
   - Parameter: `tables` (Liste mit `operation`, `row_count`, `col_count`, `given_cells` z. B. `none`, `diagonal`, `random_3`), `result_range` { `min`, `max` } als Pflicht, optional globale Default-Anzahl `row_count`/`col_count`.
   - Zeilen- und Spaltenköpfe werden zufällig aus Zehnerzahlen 0–100 gezogen. Plus-Ergebnisse dürfen 100 nicht überschreiten, Minus-Ergebnisse nicht negativ sein; Verstöße führen zu einem Fehler.
   - Aufgaben außerhalb des Ergebnisbereichs verwerfen und neu ziehen.
   - Lösungsblatt füllt **alle** Felder der Tabelle vollständig aus, unabhängig davon, ob sie im Aufgabenblatt leer waren.

8. **Zahlenstrahl (`number_line`)**
   - Geschlossener Wertebereich (z. B. 0–100) mit Tickmarks für jede ganze Zahl.
   - Hauptticks (z. B. Vielfache von 10) länger/markiert; Nebenticks kürzer.
   - Parameter: `value_count` (Standard 5, wählt Zufallszahlen außerhalb der Hauptticks), optional explizite `values`.
   - Kästchen und Verbindungslinien für Platzierung der Zahlen.
   - Default-Werte: `start = 0`, `end = 100`, `major_tick_interval = 10` (Hauptticks auf Vielfachen von 10).

## Randomisierung
- Pro Arbeitsblatt eigener RNG basierend auf Seed-Versatz (`base_seed + worksheet_index`).
- Jeder Task-Generator nutzt nur seinen übergebenen RNG, damit Ergebnisse deterministisch sind.

## CI / GitHub Actions
- Workflow (grobe Spezifikation):
  1. `actions/checkout@v4`
  2. `actions/setup-python@v5` (Python 3.x)
  3. `pip install -r requirements.txt`
  4. `python generate_worksheets.py --config config.yaml`
  5. `actions/upload-artifact@v4` mit `name: worksheets`, `path: out/**` oder Wert aus `output.out_dir`.

## Offene Fragen
- keine
