Torch Bearer Y2 Android Korrektur 1.0.0
======================================
Fuer Modell Y21B7W10034CCPD, Flameeye 1.6.4 mit Zoid Patch 0.4.
Dies ist eine gezielte Korrektur des Patchers, keine fertig gebaute APK.
Die konkret verwendete APK 1.6.4 wurde hier nicht bereitgestellt. Deshalb
wurde das Paket nicht auf dem Redmi oder dem angeschlossenen Y2 getestet.

Installation unter Windows 11
----------------------------
1. ZIP vollstaendig entpacken.
2. y2_irfix.mjs und y2_irfix_build.bat in Deinen vorhandenen Ordner
   app-patcher kopieren. Dort liegen package.json, patches.json, source,
   tools und normalerweise data. NICHT in interface kopieren.
3. Den bestehenden data-Ordner und dessen keystore.jks behalten.
   Dieser Schluessel ermoeglicht das Update Deiner bisher damit signierten App.
4. y2_irfix_build.bat doppelklicken. Node.js 22 und die bisher fuer den
   Zoid-Patcher verwendete Java-Installation muessen verfuegbar sein.
5. Die Batchdatei prueft die Quelldateien, sichert geaenderte Dateien und
   die alte signierte APK und baut dann mit npm run assemble neu.
   Bei Bedarf werden die Original-Abhaengigkeiten mit npm ci installiert.
6. Ergebnis: app-patcher\data\flameeye-Y2-IRfix-1.0.0.apk
7. APK auf das Redmi kopieren und dort antippen. Installation/Update
   bestaetigen; blosses Kopieren aktualisiert die installierte App nicht.
   Falls Android das Update ablehnt, nicht sofort deinstallieren, sondern
   die genaue Meldung pruefen. Moegliche Ursache: anderer Signierschluessel.
8. App neu starten. Unter About sollte zusaetzlich Y2-IRfix:1.0.0 stehen.
   Geraet wie bisher per USB verbinden und eine NEUE Messung speichern.

Was korrigiert wird
-------------------
Nur fuer Y21B7W10034CCPD wird die Zoid-Modulliste
  SPEC_V2, BL, IR, PPFD, TM30
zu
  SPEC_V2, BL, PPFD, TM30
geaendert. Der zusaetzliche IR-Block mit drei Werten wird damit entfernt.
Die urspruenglichen Zoid-Freischaltungen bleiben ansonsten erhalten.
Das Paket korrigiert sowohl patches.json fuer zukuenftige Neubauten als
auch data/patched/.../app-service.js fuer den bestehenden Build-Cache.
Das ist noetig, weil der Original-Patcher vorhandenes data wiederverwendet.
Die spektralen Messwerte, die USB-Verbindung und Kalibrationsdaten werden
durch diese Korrektur nicht veraendert. Andere Modelle werden nicht geaendert.

Kontrolle nach einer neuen Messung
---------------------------------
Messung an einer stabilen Lichtquelle und identischer Position wiederholen.
PAR ist als Energie in W/m2 zu lesen, PPFD als umol/(m2*s).
Lux, CRI, Farbtemperatur und die spektrale Kurve sollten unveraendert bleiben.
Die drei zuvor falsch belegten IR-Anzeigen sollen entfallen.

Fuer den ALTEN Datensatz MergedData.csv ergab die Neuzuordnung:
  PAR Energie: 1.6122 W/m2, zuvor faelschlich Red_Ee.
  PPFD gesamt: 7.3235 umol/(m2*s), zuvor faelschlich Ey.
Unabhaengige Trapezintegration desselben Spektrums:
  PAR Energie: 1.6085965 W/m2; PPFD: 7.3151956 umol/(m2*s).
Dies sind Vergleichswerte fuer genau diese alte Messung. Eine neue Messung
bei veraendertem Sonnenlicht muss nicht dieselben Zahlen ergeben.
Bereits gespeicherte CSV/PDF-Berichte werden nicht nachtraeglich berichtigt.

Grenzen und weitere offene Punkte
---------------------------------
Dies ist ein begruendeter und technisch gepruefter Kandidat fuer die
Feldzuordnung; die Abnahme am realen Geraet steht aus.
Einzelne Farbband-Summen/Prozente koennen weiter wegen interner Bandgrenzen
abweichen. Sie werden nicht mit einem pauschalen Faktor drei korrigiert.
Dieses Paket implementiert KEINE neue McCree- oder CIE-Berechnung.
Insbesondere sind melanopische EDI, EML, YPFD und die Blaulicht-Risikogruppe
damit nicht automatisch validiert oder repariert. Hierfuer sind weitere
Pruefungen des nativen Berechnungsteils erforderlich.
Aktuelle andere Flameeye-Versionen sind kein Ersatz fuer APK 1.6.4.

Rueckweg und Sicherung
---------------------
Vor Aenderungen wird ein Ordner y2-irfix-backup-<UTC-Zeitstempel> angelegt.
Er enthaelt patches.json und gegebenenfalls die zuvor vorhandene gepatchte
app-service.js unter derselben Unterordnerstruktur. Zum Ruecksetzen diese
Dateien an die urspruenglichen Stellen kopieren und neu bauen. Eine vorhandene
alte signierte APK liegt dort als flameeye-signed-before-irfix.apk.
keystore.jks bleibt am bisherigen Ort und wird nicht neu erzeugt/geloescht.
Nicht allein auf eine APK-Datei im data-Ordner vertrauen: Nur nach der
Erfolgsmeldung des aktuellen Build-Laufs die neue Datei installieren.

Nur vorab pruefen ohne Dateien zu aendern
----------------------------------------
PowerShell im app-patcher-Ordner oeffnen:
  node .\y2_irfix.mjs --check

PC-Software
-----------
Die gepruefte main_export.py 1.2.1 mit spectral_metrics.py aus unserem
PC-Exportpaket dekodiert das Spektrum und berechnet Lux, PPFD, PAR und CRI
selbst. Sie liest diese Werte NICHT aus den hier verschobenen App-Feldern.
Sie hat daher diesen spezifischen Fehler nicht. Der Nachweis bezieht sich
auf diese Dateien und bestaetigt keine unabhaengige Geraetekalibration.

Quellen und Lizenz
------------------
Original: https://github.com/ZoidTechnology/Torch-Bearer-Tools
Herstellerprotokolle: https://www.torchbearer.tech/support/developer.html
Korrektur erstellt am 15.10.2026. Lizenz: GPL-3.0-or-later, siehe LICENSE.
Das Zusatzpaket stammt nicht vom Hersteller oder von ZoidTechnology.
