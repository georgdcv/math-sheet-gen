# Zufällige Auswahl für Rechentabellen und Zahlenstrahl

## Hintergrund
Konfigurationsdateien sollen nur noch die Anzahl der nötigen Felder vorgeben. Die konkreten Zahlen für Rechentabellen und Zahlenstrahlen werden erst bei der Generierung zufällig gewählt, bleiben aber nachvollziehbar durch den RNG-Seed.

## Anforderungen
1. **Rechentabellen (`operation_table`)**
   - In `config.yaml` werden nur noch Zeilen- und Spaltenanzahl je Tabelle gepflegt (Default je 2, wenn nichts angegeben ist).
   - Zeilen- und Spaltenköpfe werden bei der Generierung zufällig aus Zehnerzahlen im Bereich 0–100 gewählt.
   - Die Reihenfolge der zufällig gewählten Zehnerzahlen soll selbst zufällig bleiben (keine Sortierung der Auswahl).
   - Für Plus-Tabellen darf kein Ergebnis größer als 100 entstehen; für Minus-Tabellen darf kein Ergebnis negativ werden.
   - Zufällige Auswahl muss deterministisch über den RNG erfolgen.

2. **Zahlenstrahl (`number_line`)**
   - In `config.yaml` wird nur die Anzahl der zu beschriftenden Zahlen angegeben; die konkreten Werte werden zufällig gewählt.
   - Auswahl erfolgt per RNG, bevorzugt Zahlen außerhalb der Major-Ticks (wie bisherige Logik), und sortiert für das Lösungsblatt.
   - Textboxen für die zu beschriftenden Werte sollen nah an den jeweiligen Ticks platziert werden, sodass die Verbindungsstrecken kurz bleiben.

## Offene Fragen
- Keine. Sollten weitere Einschränkungen für die Auswahl der Zahlen gelten (z. B. Mindestabstand), bitte ergänzen.
