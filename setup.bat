@echo off
REM obs-quickstart — Windows Installer
REM Run this script to install dependencies and set up obs-quickstart

echo.
echo ============================================
echo   obs-quickstart - Windows Setup
echo   Plug-and-Play OBS Studio Auto-Configurator
echo ============================================
echo.

REM Check Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed!
    echo Download Python from https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation.
    pause
    exit /b 1
)
echo [OK] Python found: 
python --version

REM Install dependencies
echo.
echo [..] Installing dependencies...
python -m pip install --upgrade pip
python -m pip install obsws-python
python -m pip install speedtest-cli

REM Done
echo.
echo ============================================
echo   Setup complete!
echo.
echo   USAGE:
echo     python -m obs_quickstart.main
echo.
echo   Make sure OBS Studio is running with
echo   WebSocket enabled (Tools -> WebSocket Server Settings)
echo ============================================
echo.
pause