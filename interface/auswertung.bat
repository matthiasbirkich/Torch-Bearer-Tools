@echo off
setlocal
REM Optional: set daily constant-light duration, e.g. 16. Empty = no DLI estimate.
set "TB_PHOTOPERIOD_HOURS="
set "TB_DLI_ARGS="
if not "%TB_PHOTOPERIOD_HOURS%"=="" set "TB_DLI_ARGS=--photoperiod-hours %TB_PHOTOPERIOD_HOURS%"
cd /d "%~dp0"
title Torch Bearer - gespeichertes Spektrum auswerten
if "%~1"=="" (
  echo Eine gespeicherte spectrum.csv im Explorer auf diese auswertung.bat ziehen.
  echo Die Kennwerte werden im Ordner der CSV gespeichert.
  pause
  exit /b 1
)
if not exist ".venv\Scripts\python.exe" (
  echo Diese Datei muss im bestehenden interface-Ordner mit .venv liegen.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" "spectral_metrics.py" "%~1" %TB_DLI_ARGS%
set "TB_EXIT=%ERRORLEVEL%"
pause
exit /b %TB_EXIT%
