@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Diese Datei muss im bestehenden interface-Ordner mit .venv liegen.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" -m pip uninstall -y color-science
".venv\Scripts\python.exe" -m pip install "colour-science==0.4.7" "scipy>=1.13,<2" "matplotlib>=3.9" pyserial
set "TB_EXIT=%ERRORLEVEL%"
if "%TB_EXIT%"=="0" echo Fertig. Jetzt start.bat doppelklicken.
pause
exit /b %TB_EXIT%
