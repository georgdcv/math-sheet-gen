# Feature-Spezifikation: Aufgaben- und Layout-Verbesserungen

## Kontext
Umsetzung weiterer Funktionswünsche für die Arbeitsblatt-Generierung. Basis ist der bestehende Generator `generate_worksheets.py` gemäß `codex/specs/worksheet-generator.md`.

## Anforderungen
- **Würfelbilder:** Statt linearer Punkte müssen echte Würfelaugen (1–5) dargestellt werden, idealerweise als SVG. Für Einer >5 werden kombinierte Würfel (5 + Rest) gezeigt. Zehner bleiben als Strichgruppen.
- **Zahlen vergleichen:** Die Wahrscheinlichkeit für Gleichheitszeichen (`=`) soll gering sein. Dafür einen konfigurierbaren Parameter mit niedrigerem Default vorsehen.
- **Rechnen in einer Liste (+/−):**
  - Konfigurierbare Wahrscheinlichkeit für Aufgaben mit Zehnerübergang (Standard 100 %).
  - Konfigurierbares Maximum für den zweiten Operand (z. B. ≤10).
  - Regeln gelten für Addition und Subtraktion, unter Einhaltung des Ergebnisbereichs.
- **Rechentabellen:**
  - Rechenart durch Symbol in der linken oberen Tabellenzelle kennzeichnen (kein separater Label-Text).
  - Standardmäßig zwei 2×2-Tabellen nebeneinander erzeugen, wenn keine Vorgaben gemacht werden.
  - Schrittweite/Skalierung der Zeilen- und Spaltenwerte (1er oder 10er) konfigurierbar und wirksam.
- **Zahlenstrahl:** Neuaufbau mit korrekter Darstellung (auch im Druck), bevorzugt als SVG mit Ticks, Labels, Kästchen und Verbindungslinien.
- **Zahlen ordnen:** Lösung als einzeilige Tabelle, in der jede Ziffer und jedes Vergleichszeichen eine eigene Spalte erhält.

## Offene Fragen
- Sollen Vergleichszeichen in der Sortieraufgabe auch im Aufgabenblatt sichtbar sein, wenn `show_comparison_symbols` deaktiviert ist? Aktuell werden leere Felder eingeplant, Zeichen erscheinen nur, wenn konfiguriert.
