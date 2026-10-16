@echo off
setlocal
cd /d "%~dp0"
title Torch Bearer Y2 - IR Feldkorrektur 1.0.0
where node >nul 2>nul
if errorlevel 1 (
 echo Node.js 22 wurde nicht gefunden. Bitte Node.js installieren.
 pause
 exit /b 1
)
echo Pruefe und korrigiere den bestehenden Patcher ...
node "%~dp0y2_irfix.mjs"
if errorlevel 1 goto fail
if not exist "node_modules" (
 echo Installiere die Abhaengigkeiten des Original-Patchers ...
 call npm ci
 if errorlevel 1 goto fail
)
echo Baue und signiere die APK mit dem vorhandenen Schluessel ...
call npm run assemble
if errorlevel 1 goto fail
if not exist "data\flameeye-signed.apk" goto fail
copy /y "data\flameeye-signed.apk" "data\flameeye-Y2-IRfix-1.0.0.apk" >nul
if errorlevel 1 goto fail
echo.
echo Fertig: data\flameeye-Y2-IRfix-1.0.0.apk
echo Diese Datei auf das Telefon kopieren und als App-Update installieren.
echo Danach eine NEUE Messung speichern und kontrollieren.
echo Die alte Messung wird durch das Update nicht nachtraeglich korrigiert.
explorer "%~dp0data"
pause
exit /b 0
:fail
echo.
echo ABBRUCH. Es wurde keine erfolgreich neu gebaute APK bestaetigt.
echo Bitte den Fehlertext fotografieren oder kopieren.
echo data und keystore.jks NICHT loeschen.
pause
exit /b 1
