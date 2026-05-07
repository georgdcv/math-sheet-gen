# Zahlendiktat und Würfelbild-Höhenanpassung

## Ziel
* Auf dem **Lösungsblatt** des Zahlendiktats sollen automatisch zufällig generierte Zahlen (20–100) erscheinen, die für das Diktat verwendet werden können.
* Die Zeilen der Aufgabe **Zahlwort – Würfelbild – Zahl** sollen überall die gleiche Höhe haben. Leere Würfelbild-Zellen sollen ein weißes Beispiel-Würfelbild (Kombination aus Zehner-Strichen und Einer-Würfeln des Beispiels) enthalten, damit die Höhe der Beispielzeile gespiegelt wird.

## Anforderungen
1. **Zahlendiktat (number_dictation)**
   * Für jede Box wird eine zufällige ganze Zahl zwischen 20 und 100 (inklusive) generiert.
   * Die Zahlen erscheinen ausschließlich auf dem Lösungsblatt innerhalb der Zahlendiktat-Kästchen.
   * Anzahl der generierten Zahlen entspricht der Box-Anzahl der Aufgabe.
   * Zufallszahlen nutzen den bestehenden RNG (Seed pro Arbeitsblatt) für Reproduzierbarkeit.

2. **Würfelbild-Höhe (number_word_table)**
   * Aus der Beispielzahl wird das komplette Würfelbild (Zehner-Striche + Einer-Würfel) ein zweites Mal erzeugt.
   * Dieses Beispiel-Würfelbild wird in allen leeren Würfelbild-Zellen (Arbeitsblatt) als "weiß auf weiß"-Platzhalter angezeigt, sodass die Zeilenhöhe der Würfelspalte identisch zur Beispielzeile bleibt.
   * Lösungsblatt zeigt weiterhin die echten Würfelbilder; nur die leeren Zellen des Arbeitsblatts erhalten den weißen Platzhalter.

## Offene Punkte
* Keine offenen Fragen identifiziert; doppelte Zufallszahlen im Zahlendiktat sind aktuell erlaubt.
