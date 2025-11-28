# Zahlenraum- und Visualisierungsanpassungen

## Hintergrund
Um die Arbeitsblätter näher an die gewünschten Übungsformate anzupassen, müssen mehrere Aufgabentypen hinsichtlich Zahlenraum, Zehnerübergang und visueller Darstellung überarbeitet werden.

## Anforderungen
1. **Plus-/Minus-Aufgaben (arithmetic_list)**
   - Zehnerübergang nur dann als solcher zählen, wenn die Einerstellen einen Übertrag **über 10** erzwingen (Addition) bzw. ein **echtes Entbündeln** stattfindet.
   - Rechenaufgaben wie `15 + 5` oder `10 - 2` dürfen nicht als Zehnerübergang gelten.

2. **Zahlen vergleichen & Vorgänger/Nachfolger**
   - Zahlenraum auf maximal 0–100 begrenzen (Konfigurationen sollen nicht darüber hinausgehen).

3. **Zahlwort – Würfelbild – Zahl**
   - Jede volle Zehn als senkrechter Strich im Würfelbild darstellen; Höhe mindestens wie die Würfelaugen.
   - Striche bei mehr als fünf Zehnern in 5er-Gruppen gruppieren.
   - Würfelbilder ohne äußeren Rahmen rendern, nur die Augen bleiben sichtbar.

4. **Rechentabellen (operation_table)**
   - Zeilen- und Spaltenköpfe ausschließlich mit Zehnerzahlen (Vielfache von 10) darstellen.

5. **Zahlenstrahl (number_line)**
   - Ticks vertikal um die Achse zentrieren; zusätzliche mittlere Ticks bei 5, 15, 25… größer als Nebenticks, aber kleiner als Hauptticks und unbeschriftet.
   - Beschriftung der Hauptticks ist Teil der Aufgabe: auf dem Arbeitsblatt unbeschriftet, im Lösungsblatt ausgefüllt.
   - Standardinstruktion: „Trage zuerst die Zehnerzahlen an den Zahlenstrahl. Trage dann die Zahlen ein.“
   - Verbindungslinien von den Eingabeboxen sollen am oberen Tick-Ende ansetzen.

## Offene Fragen
- Sollen Zehnerzwang in Rechentabellen durch Rundung, Auf- oder Abwertung erreicht werden, falls die Konfiguration Nicht-Zehner enthält? Aktuell wird auf Aufwärtsrundung zu erwarteten Vielfachen von 10 gesetzt.
