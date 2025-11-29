# Feature-Spezifikation: Kombiniertes Ausgabeformat und Layoutanpassungen

## Kontext
Die Arbeitsblatt-Generierung soll um zusätzliche Ausgabeformate erweitert und bestehende Aufgabentypen optisch angepasst werden. Grundlage ist der aktuelle Generator `generate_worksheets.py` und die Konfiguration über `config.yaml`.

## Anforderungen
- **Würfelbilder:** Die Zeilenhöhe in Tabellenzellen mit Würfelbildern muss erhöht werden, damit genügend Platz für die Darstellung der kombinierenden Strich- und Würfel-SVGs vorhanden ist.
- **Rechentabellen:** Die Ausgangswerte (Zeilen- und Spaltenköpfe) der Rechentabellen sollen mindestens 10 betragen; automatische Generierung und manuelle Vorgaben müssen diese Untergrenze respektieren.
- **Zahlwort-Aufgabe:** In allen Zahlwörtern soll das Segment „und" immer unterstrichen ausgegeben werden, sowohl in Aufgaben- als auch in Lösungsblättern.
- **Vergleichsaufgabe:** In der Aufgabe „Vergleiche! <, >, =" dürfen die Zahlen keine Kästchen-Rahmen mehr besitzen; die Darstellung soll dennoch gleichmäßig ausgerichtet bleiben.
- **Gesamtdokument:** Zusätzlich zu den Einzel-HTMLs für Aufgaben- und Lösungsblätter soll ein kombiniertes HTML-Dokument erzeugt werden, das alle Arbeits- und Lösungsblätter enthält. Zwischen jedem Blatt ist ein Seitenumbruch für den Druck vorzusehen.
- **Würfelbild-Höhe:** Falls in einer Zeile nur Strichlisten ohne Würfelflächen erscheinen, wird ein leeres (weiß auf weiß) Würfelbild als Platzhalter eingefügt, damit die Zeilenhöhe der Würfelspalte konsistent bleibt.
- **Vorgänger/Zahl/Nachfolger:** Alle erzeugten Zahlen liegen im Bereich 10–100; die generierten Vorgänger-/Nachfolgerwerte sollen zweistellig bleiben.
- **Zahlwörter:** Aufgaben zu Zahlwörtern beginnen ab der 21 und schließen glatte Zehner (30, 40, 50, …) aus.

## Offene Fragen
- Sollen im kombinierten Dokument zusätzliche Überschriften oder Trennseiten eingefügt werden, oder genügt die bestehende Seitenstruktur mit Seitenumbrüchen?
