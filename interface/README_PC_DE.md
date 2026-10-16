# Windows-PC: Y2-Spektraldaten erfassen und auswerten

Diese Erweiterung baut auf dem seriellen Protokoll von
[ZoidTechnology/Torch-Bearer-Tools](https://github.com/ZoidTechnology/Torch-Bearer-Tools)
auf. Grafikstand: `main_export.py` **1.2.2**; Kennwertmodule aus dem Exportpaket
1.2.0. Erprobt mit Python 3.13 unter Windows 11. Lizenz: GPL-3.0-or-later,
siehe `../license.md`. Die ursprüngliche `main.py` bleibt als Minimalbeispiel erhalten.

## Installation

1. Das gesamte Repository herunterladen und entpacken.
2. Python 3.13 (64 Bit) mit pip sowie Tcl/Tk installieren. Im Installer
   `Add python.exe to PATH` aktivieren.
3. Den Ordner `interface` im Explorer öffnen. Alt+D drücken, `powershell`
   eingeben und Enter drücken.
4. Einmalig eine virtuelle Umgebung anlegen und pip aktualisieren:

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\python.exe -m pip install --upgrade pip
   ```

5. `install_dependencies.bat` doppelklicken. Das Paket heißt **colour-science**
   mit „u“; `color-science` ist ein anderes Platzhalterpaket.
6. Gerät mit einem USB-Datenkabel anschließen. COM-Nummer im Geräte-Manager
   unter „Anschlüsse (COM & LPT)“ prüfen.

## Messen

`start.bat` doppelklicken. Standardport in diesem Paket: **COM5**.
Falls nötig in `start.bat` die Zeile `set "TB_PORT=COM5"` anpassen.
Eine eventuell anders konfigurierte eigene start.bat kann beibehalten werden.

Die Software wartet auf die erste NORMAL-Messung nach der automatischen
Belichtungsanpassung und legt einen neuen Ordner unter `Messungen` an.
Das Grafikfenster zum Beenden schließen. Für die nächste Messung erneut starten.

Enthalten sind unter anderem:

- vollständige spektrale Bestrahlungsstärke (`spectrum.csv`);
- farbig unterlegtes Spektrum (`spectrum.png`), UV/NIR schematisch eingefärbt;
- Lux, PPFD 400–700 nm, energetisches PAR, ePAR 400–750 nm, xPAR;
- CRI Ra, R1–R14 sowie CCT und Duv, soweit berechenbar;
- Energie-/Photonenbänder und Bandverhältnisse;
- JSON-Metadaten und Rohkommunikation für technische Prüfungen.

10-nm-Teilstriche sind eine Ablesehilfe, keine Angabe der optischen Auflösung.
Die Rechnung setzt spektrale Eingabewerte in **W/m²/nm** voraus und normiert
die Intensität nicht. Formeln, Voraussetzungen und Grenzen stehen im Handbuch
unter `../docs/`.

## Gespeicherte Spektren nachberechnen

Eine von diesem PC-Export erzeugte `spectrum.csv` auf `auswertung.bat` ziehen.
Die Kennwertdateien werden im Ordner der CSV neu geschrieben.
**Diese Nachberechnung erzeugt derzeit keine neue Grafik und aktualisiert
measurement.json nicht.**

Der derzeitige Import erwartet die Spalten `wavelength_nm` und
`spectral_irradiance_W_m2_nm` (alternativ das ältere `spectral_value`).
Originale Android-Exporte mit vorangestellten Metadaten werden noch nicht
automatisch eingelesen. Originaldateien unverändert aufbewahren.

## Tageslichtintegral

In start.bat bzw. auswertung.bat kann `TB_PHOTOPERIOD_HOURS` auf z. B. `16`
gesetzt werden. Das ist eine Hochrechnung für **konstantes** Licht während
16 Stunden, keine gemessene Tageszeitreihe. Leer bedeutet keine DLI-Schätzung.

## Einordnung

Die PC-Auswertung ist unabhängig von der Android-App. Der Android-IRfix wird
für die direkte USB-Messung am PC nicht benötigt. Ein korrekter Rechenweg
ersetzt keine Prüfung der absoluten Messgenauigkeit. Die erweiterten
Herstellerkennzahlen der Android-App sind nicht alle im PC-Export enthalten.
