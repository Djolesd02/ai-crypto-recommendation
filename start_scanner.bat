@echo off
title RADAR crypto skener
cd /d "%~dp0"

REM Koristi .venv ako postoji, inace globalni python
if exist ".venv\Scripts\activate.bat" call ".venv\Scripts\activate.bat"

echo ============================================
echo   RADAR skener - pokrecem...
echo   Ostavi ovaj prozor otvoren dok skenira.
echo   Prekid: Ctrl+C  ili  zatvori prozor.
echo ============================================
echo.

python -m scanner.main

echo.
echo Skener je zaustavljen.
pause
