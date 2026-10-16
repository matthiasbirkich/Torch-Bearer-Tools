# Torch Bearer Tools – Y2: Android und Windows

Dieser Fork erweitert die Arbeit von
[ZoidTechnology/Torch-Bearer-Tools](https://github.com/ZoidTechnology/Torch-Bearer-Tools)
für das **Torch Bearer Y2-Spektrometer**. Er enthält eine Korrektur der
Android-App-Auswertung und eine Windows-PC-Auswertung mit vollständigem
Spektralexport und nachvollziehbaren Berechnungen.

Die Erweiterungen entstanden für einen **MINT-Tag** zum Thema Lichtmessung:
Spektren untersuchen, Kenngrößen selbst berechnen und Ergebnisse kritisch prüfen.

## Schnellzugriff

| Ich möchte … | Einstieg |
|---|---|
| Am Windows-PC messen und Daten exportieren | [PC-Anleitung](interface/README_PC_DE.md) |
| Den Android-Patch für das Y2 korrigieren | [Android-Anleitung](app-patcher/README_DE.txt) |
| Installation, Bedienung und Formeln nachlesen | [Handbuch als PDF](docs/Torch_Bearer_Handbuch_DE_v1.4.0.pdf) |
| Die Android-Korrektur technisch prüfen | [Prüfbericht](app-patcher/TEST_REPORT.txt) |
| Das ursprüngliche Projekt ansehen | [ZoidTechnology auf GitHub](https://github.com/ZoidTechnology/Torch-Bearer-Tools) |

## 1. Windows-PC-Auswertung

**Erprobt mit Windows 11 und Python 3.13 (64 Bit).** Das Y2 wird direkt über
USB Serial angeschlossen. Die Android-App ist dafür nicht erforderlich.

### Einrichtung

1. Dieses Repository über **Code → Download ZIP** herunterladen und vollständig
   entpacken.
2. Python 3.13 einschließlich pip sowie Tcl/Tk installieren. Im Installer
   **Add python.exe to PATH** aktivieren.
3. Im Explorer den Ordner `interface` öffnen. Mit **Alt+D** die Adresszeile
   auswählen, `powershell` eingeben und Enter drücken.
4. Einmalig ausführen:

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\python.exe -m pip install --upgrade pip
   ```

5. In `interface` die Datei **install_dependencies.bat** doppelklicken.
6. Spektrometer per USB-Datenkabel anschließen. Die COM-Nummer im Geräte-Manager
   prüfen und gegebenenfalls in `start.bat` anpassen:

   ```bat
   set "TB_PORT=COM5"
   ```

7. **start.bat** doppelklicken.

Das Startskript verwendet COM5 als Vorgabe. Windows kann dem Gerät je nach
USB-Anschluss eine andere Nummer zuweisen.

### Was wird gespeichert?

Ein neuer Ordner unter `interface/Messungen` enthält unter anderem:

- **spectrum.csv**: vollständige ausgewählte NORMAL-Messung;
- **spectrum.png**: Grafik mit schematischer Farbunterlegung;
- **metrics.txt / metrics.csv / metrics.json**: berechnete Kennwerte;
- **bands.csv / ratios.csv**: Energie-/Photonenintegrale und Bandverhältnisse;
- **cri_samples.csv**: CRI-Einzelindizes R1–R14;
- **measurement.json**: Geräte-, Belichtungs- und Erfassungsinformationen;
- Rohkommunikation und weitere empfangene Messblöcke zur technischen Prüfung.

Berechnet werden unter anderem Lux, PPFD (400–700 nm), energetisches PAR,
ePAR (400–750 nm), xPAR nach dokumentierter Definition, CRI Ra, R9, CCT und
Duv. Eine optionale DLI-Hochrechnung setzt konstantes Licht über die eingestellte
Beleuchtungsdauer voraus. Formeln und Grenzen stehen im Handbuch.

**Grafikstand 1.2.2:** deutsche Achsentitel, UV/NIR in schematischen Farben,
Teilstriche alle 10 nm und Hilfslinien alle 50 nm. Diese Teilung verbessert das
Ablesen; sie verändert weder Messraster noch optische Auflösung.

### Gespeicherte Spektren nachrechnen

Eine von dieser PC-Auswertung erzeugte `spectrum.csv` auf **auswertung.bat**
ziehen. Die Kennwertdateien im CSV-Ordner werden neu geschrieben.

**Aktueller Funktionsumfang:** Diese Nachberechnung erzeugt keine neue Grafik
und aktualisiert `measurement.json` nicht. Originale Android-CSV-Dateien mit
vorangestellten Metadaten werden noch nicht automatisch importiert. Die
unterstützten Spaltennamen und Details stehen in der
[PC-Anleitung](interface/README_PC_DE.md).

### Ursprüngliches Minimalbeispiel

Die ursprüngliche `interface/main.py` bleibt erhalten. Im eingerichteten
`interface`-Ordner kann sie beispielsweise so gestartet werden:

```powershell
.\.venv\Scripts\python.exe main.py COM5
```

Die erweiterte Erfassung erfolgt über `main_export.py` beziehungsweise `start.bat`.

## 2. Android: Flameeye und Y2-IRfix

Der ursprüngliche App-Patcher von ZoidTechnology modifiziert die offizielle
Flameeye-App. Die zusätzliche Korrektur **Y2-IRfix 1.0.0** behebt eine fehlerhafte
Datenblock-Zuordnung beim exakt unterstützten Modell `Y21B7W10034CCPD`.

Im bisherigen Patch wurde ein IR-Block erwartet, der im betroffenen
Y2-Datenstrom an dieser Stelle nicht vorhanden ist. Nachfolgende Felder wie
PAR und PPFD waren dadurch falsch zugeordnet. Die Korrektur entfernt diesen
IR-Eintrag für dieses Modell. Es wird **kein pauschaler
Umrechnungsfaktor** auf die Messwerte angewendet.

### Voraussetzungen und Bau unter Windows

- Node.js 22 einschließlich npm;
- Java 8 wie im ursprünglichen Projekt vorgesehen;
- originale **Flameeye-APK 1.6.4** aus den
  [Herstellerdownloads](https://www.torchbearer.tech/support/download.html).

1. Die originale APK als **flameeye.apk** in `app-patcher` ablegen.
2. Bei der ersten Einrichtung ein Terminal in `app-patcher` öffnen und
   `npm install` ausführen.
3. **y2_irfix_build.bat** doppelklicken.
4. Nach erfolgreichem Bau die erzeugte Datei
   `app-patcher/data/flameeye-Y2-IRfix-1.0.0.apk` auf das Android-Gerät übertragen
   und dort installieren.

Bei einem Update den bisherigen Signaturschlüssel beibehalten. Das Skript
berücksichtigt sowohl `patches.json` als auch bereits zwischengespeicherte
Patchdateien. Details und Sicherungsablauf:
[Android-Anleitung](app-patcher/README_DE.txt).

Die Verbindung zum Y2 erfolgt über USB mit geeignetem Host/OTG-Anschluss und
Android-USB-Freigabe. Im erprobten App-Dialog konnte die USB-Geräteauswahl
irreführend unter „Bluetooth“ erscheinen. USB-Tethering wird dafür nicht benötigt.

**Erprobt:** Redmi Note 13 Pro mit Android 16. Nach dem Update stimmten PAR und
PPFD des geprüften LED-Exports mit der spektralen Nachrechnung innerhalb von
0,1 % überein. Alte Exporte werden durch das Update nicht nachträglich korrigiert.

### Ursprünglicher App-Patcher

Die ursprünglichen Befehle bleiben verfügbar:

```text
npm install
npm run assemble
npm run create-patches
```

`assemble` baut und signiert die App. `create-patches` erzeugt Patches aus
modifizierten Dateien. Für die zusätzliche Y2-Korrektur den oben beschriebenen
IRfix-Bauweg verwenden.

## 3. Einheiten, Nachvollziehbarkeit und Grenzen

- Die PC-Auswertung setzt **spektrale Bestrahlungsstärke in W/m²/nm** voraus.
  Eine falsche Eingabeeinheit skaliert die absoluten Ergebnisse entsprechend.
- PAR, PPFD und ePAR sind unterschiedliche Größen bzw. Integrationsbereiche;
  die Einheit gehört immer zum Ergebnis.
- Die Rechnung aus den exportierten Spektralwerten ist im Python-Code einsehbar.
  Das bedeutet keine vollständige Offenlegung der geräteinternen Kalibrierung.
- Übereinstimmung zwischen App und Nachrechnung desselben Spektrums prüft die
  Datenverarbeitung; sie ist kein unabhängiger Kalibriernachweis.
- Y2-IRfix behebt die geprüfte Feldzuordnung. Andere Herstellerkennzahlen,
  insbesondere die melanopischen Ausgaben und YPFD, sind damit nicht pauschal
  validiert. Nicht alle App-Kennwerte werden im PC-Export berechnet.
- Messbedingungen dokumentieren: Quelle, Abstand, Orientierung, Bewölkung,
  Abschattung und gegebenenfalls Fensterscheiben beeinflussen das Ergebnis.

Das [Handbuch als Worddatei](docs/Torch_Bearer_Handbuch_DE_v1.4.0.docx) bleibt editierbar.

## 4. Projektstruktur

| Ordner | Inhalt |
|---|---|
| [app-patcher](app-patcher/) | Ursprünglicher APK-Patcher und zusätzliche Y2-IRfix-Skripte |
| [interface](interface/) | Serielles Protokoll, ursprüngliches Beispiel und erweiterte PC-Auswertung |
| [docs](docs/) | Handbuch und zugehörige Dokumentation |

## Herkunft und Lizenz

**Grundlage:** [ZoidTechnology/Torch-Bearer-Tools](https://github.com/ZoidTechnology/Torch-Bearer-Tools).
Dessen serielles Protokoll und App-Patcher ermöglichen diese Erweiterungen.

**Fork:** [matthiasbirkich/Torch-Bearer-Tools](https://github.com/matthiasbirkich/Torch-Bearer-Tools).
Windows-Auswertung, Y2-Korrektur und Dokumentation wurden mit Unterstützung von
ChatGPT/Codex entwickelt.

Für den Programmcode gilt die [vorhandene GPL-3.0-Lizenz](license.md);
entsprechende Quelldateien enthalten gegebenenfalls zusätzliche Lizenzhinweise.
Die offizielle Flameeye-App ist Software des Geräteherstellers und wird hier
nicht mitgeliefert. Abbildungen Dritter in der Dokumentation behalten ihre
jeweiligen Quellen- und Lizenzangaben.
