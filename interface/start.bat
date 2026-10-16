@echo off
setlocal
REM Optional: set daily constant-light duration, e.g. 16. Empty = no DLI estimate.
set "TB_PHOTOPERIOD_HOURS="
set "TB_DLI_ARGS="
if not "%TB_PHOTOPERIOD_HOURS%"=="" set "TB_DLI_ARGS=--photoperiod-hours %TB_PHOTOPERIOD_HOURS%"
cd /d "%~dp0"
title Torch Bearer - Lux CRI PAR ePAR xPAR
set "TB_PORT=COM5"
if not "%~1"=="" set "TB_PORT=%~1"
if not exist ".venv\Scripts\python.exe" (
  echo Bitte diese Dateien in den bestehenden interface-Ordner kopieren.
  echo Dort muss der Unterordner .venv vorhanden sein.
  pause
  exit /b 1
)
if not exist "photobiology_metrics.py" (
  echo photobiology_metrics.py fehlt. Bitte alle Dateien aus der ZIP kopieren.
  pause
  exit /b 1
)
if not exist "spectral_metrics.py" (
  echo spectral_metrics.py fehlt. Bitte alle Dateien aus der ZIP kopieren.
  pause
  exit /b 1
)
if exist "%LOCALAPPDATA%\Programs\Python\Python313\tcl\tcl8.6\init.tcl" set "TCL_LIBRARY=%LOCALAPPDATA%\Programs\Python\Python313\tcl\tcl8.6"
if exist "%LOCALAPPDATA%\Programs\Python\Python313\tcl\tk8.6\tk.tcl" set "TK_LIBRARY=%LOCALAPPDATA%\Programs\Python\Python313\tcl\tk8.6"
".venv\Scripts\python.exe" -c "import colour, scipy, matplotlib, serial; assert hasattr(colour, 'SpectralDistribution')"
if errorlevel 1 (
  echo Bibliotheken fehlen. Bitte einmal install_dependencies.bat ausfuehren.
  pause
  exit /b 1
)
echo.
echo Messung an %TB_PORT% - Werte werden in Messungen gespeichert.
echo Grafikfenster nach der Messung schliessen, um den Lauf zu beenden.
echo.
".venv\Scripts\python.exe" "main_export.py" "%TB_PORT%" --show %TB_DLI_ARGS%
set "TB_EXIT=%ERRORLEVEL%"
echo.
if not "%TB_EXIT%"=="0" echo Messung mit Fehler beendet. Ausgabe oben beachten.
echo Fuer eine neue Messung diese Datei erneut doppelklicken.
pause
exit /b %TB_EXIT%
