Im Tool sollst du mit einer `config.yaml` eine Sammlung von Aufgabentypen konfigurieren und daraus ein oder mehrere Arbeitsblätter als drucktaugliches HTML erzeugen. Grundlage ist das hochgeladene Arbeitsblatt mit 8 nummerierten Aufgabenblöcken, Kopfzeile (Name/Datum) und klaren Rahmen-Layouts.

Im Folgenden eine Spezifikation, mit der du das Tool direkt umsetzen kannst.

---

## 1. Ziel und Umfang

* **Ziel:** Generierung von Grundschul-Mathe-Arbeitsblättern (Klasse 1/2) im Stil des Beispiels als **einzelne HTML-Dateien**, optimiert für A4-Druck (Hochformat).
* **Konfiguration:** erfolgt ausschließlich über `config.yaml`.
* **Batch:** Mehrere Arbeitsblätter mit identischen Einstellungen, aber unterschiedlichen zufälligen Zahlen.
* **Keine Interaktivität:** HTML nur als Drucklayout, keine Eingabelogik im Browser.

---

## 2. Unterstützte Aufgabentypen (Version 1)

Angelehnt an das Beispielblatt:

Jeder Aufgabentyp erhält einen internen `type`-Bezeichner.

1. **Zahldiktat (`number_dictation`)**

   * Darstellung: eine Zeile mit n leeren Kästchen (Rahmen).
   * Konfigurierbar: Anzahl der Kästchen.
   * Optional: „Hilfszahlen“ im Lösungsblatt, im Arbeitsblatt bleiben Kästchen leer.

2. **Zahlen vergleichen (`compare_numbers`)**

   * Jedes Item: Paar ganzer Zahlen (a, b) mit Leerfeld für `<`, `>` oder `=`.
   * Layout: Spalten, jede Zeile mehrere Paare, ähnlich wie auf Seite 1.
   * Konfiguration:

     * `item_count`: Anzahl der Vergleiche.
     * `min_value`, `max_value`: Zahlenbereich.
     * `columns`: Anzahl Spalten (Standard 3).

3. **Vorgänger / Zahl / Nachfolger (`pre_succ_table`)**

   * Tabelle mit 3 Spalten: „Vorgänger | Zahl | Nachfolger“.
   * Pro Zeile sind ein oder mehrere Felder ausgefüllt, die übrigen leer.
   * Konfiguration:

     * `row_count`.
     * `min_value`, `max_value`.
     * `given_field`: `middle`, `left`, `right` oder `mixed`.

4. **Rechnen in einer Liste (`arithmetic_list`)**

   * Einfache Plus/Minus-Aufgaben (z. B. im Zahlenraum bis 20) in zwei oder mehr Spalten untereinander.
   * Konfiguration:

     * `item_count`.
     * `operations`: Liste aus `["+", "-"]` oder explizit `["+"]`, `["-"]`.
     * `min_value`, `max_value`.
     * `allow_negative_results`: Bool (Standard `false`).
     * `columns`: Anzahl Spalten (Standard 2).

5. **Zahlwort – Würfelbild – Zahl (`number_word_table`)**

   * Tabelle mit Spalten „Zahlwort | Würfelbild | Zahl“.
   * Variante des Beispielblatts, Würfelbild kann vorerst nur als vereinfachte ASCII- oder Punktdarstellung umgesetzt werden (z. B. `<span class="dice">•••</span>`).
   * Konfiguration:

     * `row_count`.
     * `min_value`, `max_value` (z. B. 11–99).
     * `given_columns`: Liste aus `["word", "dice", "number"]`, welche Spalte(n) vorausgefüllt werden, die restlichen bleiben leer.

6. **Zahlen ordnen (`ordering`)**

   * Eine vorgegebene Liste von Zahlen, Schüler*innen sollen diese der Größe nach ordnen.
   * Layout wie im Beispiel: Aufgabe „Ordne! Beginne mit der kleinsten Zahl!“ plus Zahlfolge, darunter eine Kette von Kästchen, ggf. mit `<`-Zeichen dazwischen.
   * Konfiguration:

     * `set_size`: wie viele Zahlen im Set.
     * `min_value`, `max_value`.
     * `show_comparison_symbols`: Bool, ob `<` zwischen Kästchen dargestellt wird.

7. **Rechentabellen (`operation_table`)**

   * Tabellen wie in Aufgabe 7: links Plus-Tabelle, rechts Minus-Tabelle; Zeilen/Spalten mit Randzahlen und leeren Feldern.
   * Konfiguration:

     * `tables`: Liste von Tabellen, jede mit:

       * `operation`: `"+"` oder `"-"`.
       * `row_headers`: Liste von Zahlen.
       * `col_headers`: Liste von Zahlen.
       * `given_cells`: Regellogik, z. B. `"none"`, `"diagonal"`, `"random_3"`.

8. **Zahlenstrahl (`number_line`)**

   * Horizontaler Zahlenstrahl mit gleichmäßigen Markierungen und Kästchen für bestimmte Zahlen (wie in Aufgabe 8).
   * Konfiguration:

     * `start`, `end`, `step` (z. B. 0–100 in Zehnerschritten).
     * `boxes`: Anzahl Kästchen, deren Positionen automatisch gewählt oder ausdrücklich angegeben werden (Liste der Zielzahlen oder Indexe).
     * Darstellung von z. B. vorgegebenen Zahlen in einigen Boxen.

Die Spezifikation ist so angelegt, dass du später weitere `type`s ergänzen kannst.

---

## 3. YAML-Konfiguration

### 3.1. Dateiaufbau

```yaml
# config.yaml
worksheet:
  title: "1. Übungsblatt zum 1. Rechenmeister"
  subtitle: null            # optional
  show_name_field: true
  show_date_field: true
  locale: "de-DE"

output:
  out_dir: "out"
  file_prefix: "rechenmeister_1"
  worksheet_count: 10       # Batch-Größe
  seed: 12345               # optional, für Reproduzierbarkeit

layout:
  page_size: "A4"
  margin_top: "1.5cm"
  margin_right: "1.5cm"
  margin_bottom: "1.5cm"
  margin_left: "1.5cm"
  font_family: "sans-serif"
  font_size_body: "12pt"
  task_spacing: "0.8cm"

tasks:
  - id: 1
    type: "number_dictation"
    title: "Zahldiktat"
    item_count: 10

  - id: 2
    type: "compare_numbers"
    instruction: "Vergleiche! < , > , ="
    item_count: 12
    min_value: 10
    max_value: 100
    columns: 3

  - id: 3
    type: "pre_succ_table"
    row_count: 4
    min_value: 10
    max_value: 99
    given_field: "middle"

  - id: 4
    type: "arithmetic_list"
    instruction: "Rechne! Achte auf das Rechenzeichen!"
    item_count: 12
    operations: ["+", "-"]
    min_value: 0
    max_value: 20
    columns: 2

  # usw. für weitere types
```

Allgemeine Regeln:

* Nicht benötigte Felder sind optional.
* Unerkannte Felder führen idealerweise zu einer Warnung, aber nicht zwingend zu einem Abbruch (logbare Hinweise).

---

## 4. Kommandozeilen-Interface

Python-Skript z. B. `generate_worksheets.py`:

```bash
python generate_worksheets.py --config config.yaml
```

Optionen:

* `--config PATH` (Pflicht).
* `--seed INT` (überschreibt seed aus YAML).
* `--count INT` (überschreibt `worksheet_count`).
* `--out-dir PATH` (überschreibt `output.out_dir`).
* `--answers` (erstellt zusätzlich Lösungsblätter).

---

## 5. Interne Architektur (Python)

### 5.1. Module

* `config.py`

  * Laden und Validieren von `config.yaml` (z. B. mit `pydantic` oder `dataclasses` + manuelle Checks).
* `generators/`

  * `base.py`: abstrakte Basisklasse `TaskGenerator`.
  * Für jeden `type` eine Klasse: `NumberDictationTask`, `CompareNumbersTask`, …
* `html_renderer.py`

  * Funktionen zur Generierung des HTML-Grundgerüsts (Header, CSS, Wrapper).
* `templates/`

  * Jinja2-Templates für Aufgabenblöcke ODER String-Builder in Python (je nach Präferenz).

### 5.2. Datenfluss

1. `config.yaml` einlesen.
2. Globalen Zufallszahlgenerator (z. B. `random.Random(seed + worksheet_index)`) initialisieren.
3. Für jede `worksheet_index` in `0..count-1`:

   * Für jede Aufgabe in `tasks`:

     * passenden `TaskGenerator` instanziieren.
     * `generate_items(rng)` → strukturiertes Datenobjekt (z. B. Liste von Zahlenpaaren, Tabellenmatrix).
   * Gesamte Struktur an `html_renderer.render_worksheet(data)` übergeben.
   * HTML in Datei schreiben, z. B. `rechenmeister_1_001.html`.

Optional: Separat `render_solutions` auf der gleichen Datenbasis.

---

## 6. HTML-Layout & CSS für paginierten Druck

### 6.1. Grundstruktur

```html
<!DOCTYPE html>
<html lang="de">
<head>
  <meta charset="utf-8">
  <title>1. Übungsblatt zum 1. Rechenmeister</title>
  <style>
    @page {
      size: A4 portrait;
      margin: 1.5cm;
    }

    body {
      font-family: sans-serif;
      font-size: 12pt;
    }

    .worksheet {
      page-break-after: always; /* jede Datei hat nur ein Blatt, optional */
    }

    .header {
      display: flex;
      justify-content: space-between;
      border-bottom: 1px solid #000;
      padding-bottom: 0.3cm;
      margin-bottom: 0.5cm;
    }

    .header-field {
      flex: 0 0 48%;
    }

    .task {
      border: 1px solid #000;
      padding: 0.4cm;
      margin-bottom: 0.6cm;
    }

    .task-title {
      font-weight: bold;
      margin-bottom: 0.2cm;
    }

    .number-box {
      display: inline-block;
      width: 1cm;
      height: 1cm;
      border: 1px solid #000;
      margin-right: 0.1cm;
    }

    /* Tabellen, Zahlenstrahl etc. (weitere Klassen) */
  </style>
</head>
<body>
  <div class="worksheet">
    <!-- Kopf -->
    <!-- Aufgabenblöcke -->
  </div>
</body>
</html>
```

### 6.2. Einzelne Aufgabentypen

* **Zahldiktat:** n `<span class="number-box"></span>` in einer Zeile.

* **Vergleiche:** Tabelle mit Paaren, jede Zeile maximal `columns` Items, z. B.:

  ```html
  <table class="compare-table">
    <tr>
      <td>66</td><td><span class="circle"></span></td><td>29</td>
      ...
    </tr>
  </table>
  ```

  `circle` kann z. B. ein leerer Kreis durch CSS (runder Rahmen) oder einfach ein Kästchen sein.

* **Tabellen:** Standard-`<table>` mit CSS `border-collapse: collapse;`. Jede Zelle mit Rahmen.

* **Zahlenstrahl:** einfache Umsetzung als Tabelle mit vielen schmalen Zellen, in denen Zahlen ggf. eingeblendet sind; Kästchen darüber durch zusätzliche Zeile mit `<div class="number-box"></div>` pro markiertem Punkt.

Ziel: reines HTML + CSS, keine externen Ressourcen.

---

## 7. Randomisierung und Regeln

* Pro Arbeitsblatt ein eigener RNG-Seed: `base_seed + worksheet_index`.
* Jeder `TaskGenerator` verwendet nur den ihm übergebenen RNG, damit die Ergebnisse deterministisch reproduzierbar sind.
* Beispiele für Regeln:

  * `compare_numbers`: bei Anteil von Gleichheitszeichen konfigurieren (Parameter `equal_probability`), Standard 0.2.
  * `arithmetic_list`: Aufgabe nur erzeugen, wenn Ergebnis im erlaubten Bereich liegt; ggf. neu ziehen.
  * `ordering`: sicherstellen, dass alle Zahlen verschieden sind.
  * `pre_succ_table`: Zufallswahl, welche Felder leer sind (wenn `given_field = "mixed"`).

---

## 8. Batch-Erstellung

* `worksheet_count` aus YAML bestimmt Anzahl der generierten Dateien.
* Dateinamensschema:

  * Arbeitsblatt: `<file_prefix>_<index:03d>.html` → `rechenmeister_1_001.html`, …
  * Lösungen: `<file_prefix>_<index:03d>_loesung.html`.
* Alle Dateien im Verzeichnis `output.out_dir`.

---

## 9. GitHub-Action (CI)

### 9.1. Struktur des Repositories

* `generate_worksheets.py`
* `config.yaml`
* `requirements.txt`
* `.github/workflows/generate-worksheets.yml`

### 9.2. Beispiel-Workflow (grobe Spezifikation)

* Trigger: `workflow_dispatch` und/oder `push` auf `main`.
* Schritte:

  1. `actions/checkout@v4`
  2. `actions/setup-python@v5` mit Python 3.x.
  3. `pip install -r requirements.txt`.
  4. `python generate_worksheets.py --config config.yaml`.
  5. `actions/upload-artifact@v4`:

     * `name: worksheets`
     * `path: out/**` (oder Wert aus `output.out_dir`).

Damit stehen die erzeugten HTML-Arbeitsblätter in der Actions-Run-Ansicht als herunterladbares Artefakt zur Verfügung.

---

## 10. Erweiterungsmöglichkeiten (nicht zwingend für Version 1)

* PDF-Generierung aus HTML (z. B. mit `weasyprint` in einer separaten Pipeline).
* Mehrsprachigkeit (konfigurierbare Labels „Name“, „Datum“, …).
* Konfigurierbare Schriftarten (z. B. Druckschrift vs. Schulschrift, sofern im Browser verfügbar).
* Konfigurierbare Lösungsblätter (z. B. nur Beispiele oder vollständig ausgefüllt).

---

Wenn du möchtest, kann ich als nächsten Schritt:

* ein minimales `config.yaml` + Gerüst für `generate_worksheets.py` skizzieren oder
* die CSS-Klassen für ein möglichst nahes Layout an deinem Beispiel konkret ausformulieren.
