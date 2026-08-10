# Schwalbenschwanz – Fusion 360 Add-In

Deutsche Kurzanleitung. Die vollständige Projektdokumentation steht auf
Englisch in der [README.md](../README.md) im Wurzelverzeichnis.

Aus einer gewählten Skizzenlinie wird eine Verzahnung: die **Nennkontur**
direkt auf der Linie und eine um die **Toleranz** verkleinerte
**Gegenkontur** darin.

## Installation

Diesen Ordner nach

```
%APPDATA%\Autodesk\Autodesk Fusion 360\API\AddIns\
```

kopieren. In Fusion: **Dienstprogramme → ADD-INS → Add-Ins** → Eintrag
markieren → *Beim Start ausführen* anhaken → **Ausführen**. Der Button
erscheint im Reiter **SKIZZE** in der Gruppe **ERSTELLEN**.

## Bedienung

1. Skizze öffnen oder bearbeiten.
2. Eine Linie anklicken.
3. Auf das Icon klicken – die Linie ist im Dialog schon vorausgewählt.
4. Werte einstellen, Vorschau prüfen, **OK**.

## Felder

| Feld | Bedeutung |
|---|---|
| **Linie** | Die Skizzenlinie, auf der die Verzahnung sitzt. |
| **Anzahl** | 1 – 500 Zähne, mittig auf der Linie verteilt. |
| **Form** | `Trapez` (Standard, echter Schwalbenschwanz mit Hinterschnitt), `Dreieck`, `Rechteck` (Fingerzinken). |
| **Breite (Basis)** | Breite des Zahns an der Linie. |
| **Tiefe** | Wie weit der Zahn absteht. |
| **Flankenwinkel** | Nur beim Trapez: Aufweitung nach außen, Standard 15°, Bereich ±89°. Bei 0° wird ein Rechteck daraus. |
| **Abstand (Mitte-Mitte)** | Ab 2 Zähnen: Mittenabstand. |
| **Verschiebung** | Versatz der Gruppe entlang der Linie, 0 = mittig. |
| **Schrittweite** | Wie weit ein Klick auf ◀ / ▶ bewegt, Standard 1 mm. |
| **Verschieben ◀ ▮ ▶** | ◀ Richtung Startpunkt, ▶ Richtung Endpunkt, Mitte setzt zurück. |
| **Toleranz** | Spiel zwischen den Teilen, Standard **0,25 mm**. 0 lässt die Gegenkontur weg. |
| **Richtung umkehren** | Zähne auf die andere Seite der Linie. |
| **Gegenkontur erzeugen** | Zweite, kleinere Kontur mitzeichnen. |
| **Originallinie ersetzen** | An: Linie wird gelöscht, Nennkontur läuft durchgehend. Aus: Linie bleibt, nur die Zahnkonturen werden gezeichnet. |

## Ausrichtung

Die Gruppe liegt immer spiegelsymmetrisch zum **Mittelpunkt der Linie**:

| Anzahl | Lage relativ zur Mitte (Abstand 30 mm) |
|---|---|
| 1 | `0` |
| 2 | `−15 / +15` |
| 3 | `−30 / 0 / +30` |
| 4 | `−45 / −15 / +15 / +45` |
| 5 | `−60 / −30 / 0 / +30 / +60` |

Ungerade Anzahl → ein Zahn auf der Mitte, gerade Anzahl → die Lücke liegt
dort. Die **Verschiebung** weicht davon ab; die Buttons begrenzen sich auf
den Bereich, in dem die Verzahnung noch komplett auf der Linie liegt, und
starten bei jedem Aufruf wieder bei 0.

## Toleranz

Die Gegenkontur ist ein echter Parallelversatz der Nennkontur – gleichzeitig
auf allen Flächen: die Grundlinie wandert um die Toleranz unter die Linie,
die Flanken rücken nach innen, die Spitze wird flacher.

- **Nennkontur** (auf der Linie) → Teil mit der **Tasche**
- **Gegenkontur** (die kleinere) → Teil mit dem **Zapfen**

Dreieck 10 × 6 mm mit 0,25 mm: die Gegenspitze liegt bei 5,609 mm statt
6,000 mm, das Spiel beträgt an jeder Flanke exakt 0,25 mm.

## Sprache

Die Oberfläche folgt **Voreinstellungen → Allgemein → Benutzersprache** in
Fusion. Enthalten sind Deutsch, Englisch, Spanisch, Französisch und
Italienisch; alles andere fällt auf Englisch zurück. Die Texte liegen in
`lang/<code>.xml` und lassen sich dort direkt ändern.

## Hinweise

- Bei *Originallinie ersetzen* gehen Bemaßungen und Abhängigkeiten der
  Originallinie verloren. Die Endpunkte der neuen Kontur liegen exakt auf
  den alten, angrenzende Geometrie schließt weiterhin zu einem Profil.
- Ein Dreieck hat keinen Hinterschnitt – es ist ein Keil und rutscht unter
  Zug auseinander. Für belastete Verbindungen das Trapez nehmen.
- Unsinnige Kombinationen sperren den OK-Button und nennen den Grund.
- Die zuletzt benutzten Werte bleiben innerhalb der Fusion-Sitzung erhalten,
  die Verschiebung ausgenommen.
