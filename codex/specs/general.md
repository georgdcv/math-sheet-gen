## 1. Ziel und Umfang

* **Ziel:** Generierung von Grundschul-Mathe-Arbeitsblättern als **einzelne HTML-Dateien**, optimiert für A4-Druck (Hochformat) inkl. Lösungsblätter.
* **Konfiguration:** erfolgt ausschließlich über `config.yaml`.
* **Batch:** Mehrere Arbeitsblätter mit identischen Einstellungen, aber unterschiedlichen zufälligen Zahlen.
* **Keine Interaktivität:** HTML nur als Drucklayout, keine Eingabelogik im Browser.

---

## 2. Unterstützte Aufgabentypen (Version 1)

Jeder Aufgabentyp erhält einen internen `type`-Bezeichner.

1. **Zahldiktat (`number_dictation`)**

   * Instruktion: "Zahlendiktat"
   * Darstellung: eine Zeile mit n leeren Kästchen (Rahmen).
   * Konfigurierbar: Anzahl der Kästchen.
   * Optional: „Hilfszahlen“ im Lösungsblatt, im Arbeitsblatt bleiben Kästchen leer.

2. **Zahlen vergleichen (`compare_numbers`)**

   * Instruktion: "Vergleiche! <, >, ="
   * Jedes Item: Paar ganzer Zahlen (a, b) mit Leerfeld (Kreis) für `<`, `>` oder `=`.
   * Layout: Spalten, jede Zeile mehrere Paare.
   * Konfiguration:

     * `item_count`: Anzahl der Vergleiche.
     * `min_value`, `max_value`: Zahlenbereich.
     * `columns`: Anzahl Spalten (Standard 3).
    
   * Lösungsblatt: Eintragen der korrekten Vergleichszeichen stt der Leerfelder (Kreise)

3. **Vorgänger / Zahl / Nachfolger (`pre_succ_table`)**

   * Instruktion: keine
   * Tabelle mit 3 Spalten: „Vorgänger | Zahl | Nachfolger“.
   * Pro Zeile sind ein oder mehrere Felder ausgefüllt, die übrigen leer.
   * Konfiguration:

     * `row_count`.
     * `min_value`, `max_value`.
     * `given_field`: `middle`, `left`, `right` oder `mixed`.
    
   * Lösungsblatt: Alle Zahlen eingetragen

4. **Rechnen in einer Liste (`arithmetic_list`)**

   * Instruktion: "Rechne! Achte auf das Rechenzeichen!"
   * Einfache Plus/Minus-Aufgaben (z. B. im Zahlenraum bis 20) in zwei oder mehr Spalten untereinander.
   * Konfiguration:

     * `item_count`.
     * `operations`: Liste aus `["+", "-"]` oder explizit `["+"]`, `["-"]`.
     * `min_value`, `max_value`.
     * `allow_negative_results`: Bool (Standard `false`).
     * `columns`: Anzahl Spalten (Standard 2).

5. **Zahlwort – Würfelbild – Zahl (`number_word_table`)**

   * Tabelle mit Spalten „Zahlwort | Würfelbild | Zahl“.
   * Zahlwort für zweistellige Zahlen (Beispiel "neunundvierzig", "und" wird unterstrichen).
   * Würfelbild kann vorerst nur als vereinfachte ASCII- oder Punktdarstellung umgesetzt werden (z. B. `<span class="dice">•••</span>`). Ganze Zehner werden als Vertikale Striche dargestellt. Die Einer als Würfelbilder dargestellt, wobei 5 ggf. gruppiert werden.
   * Konfiguration:
     * `first_row_example: Standardmäßig true; erste Spalte ist mit einem Beispiel voll ausgefüllt
     * `example_number`: 49
     * `row_count`.
     * `min_value`, `max_value` (z. B. 11–99).
     * `given_columns`: Liste aus `["word", "dice", "number"]`, welche Spalte(n) vorausgefüllt werden, die restlichen bleiben leer.
   * Schrift: Wenn möglich Grundschulschrift verwenden; bevorzugt die Google-Font "Zain" via
     ```html
     <link rel='preconnect' href='https://fonts.googleapis.com'>
     <link rel='preconnect' href='https://fonts.gstatic.com' crossorigin>
     <link href='https://fonts.googleapis.com/css2?family=Zain:ital,wght@0,200;0,300;0,400;0,700;0,800;0,900;1,300;1,400&display=swap' rel='stylesheet'>
     ```

6. **Zahlen ordnen (`ordering`)**

   * Instruktion: "Ordne! Beginne mit der kleinsten/größten Zahl!" (es wird nur kleinsten oder größten angezeigt und unterstrichen)
   * Eine vorgegebene Liste von Zahlen, Schüler*innen sollen diese der Größe nach ordnen.
   * Layout wie im Beispiel: Aufgabe „Ordne! Beginne mit der kleinsten Zahl!“ plus Zahlfolge, darunter eine Kette von Kästchen, ggf. mit `<`- oder `>`-Zeichen dazwischen.
   * Konfiguration:

     * `set_size`: wie viele Zahlen im Set.
     * `min_value`, `max_value`.
     * `order`: increasing (standard) vs. decreasing
     * `show_comparison_symbols`: Bool, ob `<` zwischen Kästchen dargestellt wird.

7. **Rechentabellen (`operation_table`)**

   * Instruktion: "Achte auf das Rechenzeichen!"
   * Tabellen wie in Aufgabe 7: links Plus-Tabelle, rechts Minus-Tabelle; Zeilen/Spalten mit Randzahlen und leeren Feldern.
   * Konfiguration:

     * `tables`: Liste von Tabellen, jede mit:

       * `operation`: `"+"` oder `"-"`.
       * `row_count`: Anzahl der Zeilen (Standard 2, wenn nicht gesetzt).
       * `col_count`: Anzahl der Spalten (Standard 2, wenn nicht gesetzt).
       * `given_cells`: Regellogik, z. B. `"none"`, `"diagonal"`, `"random_3"`.

     * Zeilen- und Spaltenköpfe werden zufällig als Vielfache von 10 aus dem Bereich 0–100 gewählt.

     * Plus-Ergebnisse dürfen 100 nicht überschreiten; Minus-Ergebnisse dürfen nicht negativ werden.

     * `result_range`: Pflichtfeld zum Begrenzen der Ergebnisse, z. B. `{ min: 0, max: 100 }`; Aufgaben, die außerhalb liegen, werden verworfen/neu gezogen.

8. **Zahlenstrahl (`number_line`)**

Zahlenstrahl: Kästchen und Verbindungslinien

Der Zahlenstrahl bildet einen geschlossenen Wertebereich (z. B. 0–100) mit Tickmarken für jede ganze Zahl.

Hauptticks (z. B. Vielfache von 10) sind länger/gekennzeichnet.

Aktuelle Konfiguration:

* `start`, `end`, `major_tick_interval` steuern den Bereich und die Hauptticks.
* `value_count` legt fest, wie viele zufällige Zahlen (außerhalb der Hauptticks) beschriftet werden; `values` kann optional explizite Werte liefern.

Nebenticks (z. B. alle übrigen ganzen Zahlen) sind kürzer.

RM2

Oberhalb des Zahlenstrahls werden mehrere Eingabekästchen (number-box) dargestellt.

Die Kästchen sind horizontal gleichmäßig verteilt und nicht zwingend direkt über dem Ziel-Tick angeordnet.

Einige Kästchen können bereits mit einer Zahl beschriftet sein (z. B. „7“, „23“); andere bleiben leer.

RM2

Jedes Kästchen ist einem konkreten Tick auf dem Zahlenstrahl zugeordnet (z. B. Wert 7, 23, …).

Vom unteren Rand des Kästchens führt eine schräge Verbindungslinie (connector) zu genau diesem Tick.

Die Linie endet mittig auf der Tickmarke der zugehörigen Zahl.

Da die Kästchen gleichmäßig verteilt sind, kann die Verbindungslinie nach links oder rechts geneigt sein; sie ist also nicht zwingend vertikal.

Auf dem Arbeitsblatt:

Kästchen sind leer (bis auf evtl. vorgegebene Beispiele),

Schüler*innen sollen die Zahlen im Kästchen eintragen, die am Ende der jeweiligen Verbindungslinie auf dem Zahlenstrahl markiert sind.

Auf dem Lösungsblatt:

Jedes Kästchen enthält die korrekte Zahl des verbundenen Ticks (z. B. 7, 23, …).

Die Zuordnung „Kästchen ↔ Tick“ bleibt visuell identisch, nur der Inhalt des Kästchens unterscheidet sich.

Technische Anforderung:
Das Layout muss es ermöglichen, Kästchen unabhängig von der exakten Tick-Position horizontal zu platzieren und die Verbindung über eine diagonal verlaufende Linie zum Tick herzustellen (z. B. über absolut positionierte, dünne Linien-Elemente mit Rotation).

**Konfiguration (Vorschlag)**

* `range_min`, `range_max`: Geschlossener Wertebereich des Zahlenstrahls (z. B. 0–100).
* `major_tick_every`: Abstand zwischen Hauptticks (z. B. 10).
* `label_every`: Alle wieviel Ticks eine Zahlbeschriftung erscheint (Standard = `major_tick_every`).
* `box_count`: Anzahl der Kästchen oberhalb des Zahlenstrahls.
* `prefilled_count`: Wie viele der Kästchen bereits eine Zahl enthalten (z. B. 1 Beispiel).
* `tick_assignment`: Liste oder Regel, die festlegt, welche Tick-Werte den Kästchen zugeordnet werden (z. B. "random_unique" im Bereich, ohne Wiederholungen).
* `spacing`: Horizontaler Verteilungsmodus der Kästchen (z. B. `"even"` oder explizite Prozentwerte), unabhängig von den Tick-Positionen.

* Wertebereich und Ticks sind ausschließlich ganzzahlig; Bruchteile (z. B. 0,5) werden nicht benötigt.
* Wenn `tick_assignment` mehr eindeutige Werte braucht als der Bereich hergibt (z. B. `random_unique` bei kleinem Range und großem `box_count`), muss die Generierung mit einer hilfreichen Fehlermeldung abbrechen.

Beispiel-Konfiguration:

```yaml
  - id: 8
    type: "number_line"
    instruction: "Trage die passenden Zahlen ein!"
    range_min: 0
    range_max: 100
    major_tick_every: 10
    label_every: 10
    box_count: 6
    prefilled_count: 1
    tick_assignment: "random_unique"
    spacing: "even"
```

---

## 3. YAML-Konfiguration

### 3.1. Dateiaufbau

Beispielhaft! Muss nochmal abgeglichen werden mit der Spezifikation oben.

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
* Unerkannte oder ungültige Felder gelten als Fehler und führen zum Abbruch der Build-Pipeline ("strict mode" als Standardverhalten).

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

* Erweiterung mit einem GUI zur Konfiguration der Arbeitsblätter und Auswahl von Aufgabentypen
* PDF-Generierung aus HTML (z. B. mit `weasyprint` in einer separaten Pipeline).
* Mehrsprachigkeit (konfigurierbare Labels „Name“, „Datum“, …).
* Konfigurierbare Schriftarten (z. B. Druckschrift vs. Schulschrift, sofern im Browser verfügbar).

---

