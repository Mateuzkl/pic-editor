@echo off
title Tibia PIC Editor
color 0A

echo ============================================
echo   Tibia PIC Editor - Launcher
echo ============================================
echo.

:: Check Python
echo [1/3] Checking Python installation...
py --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo [ERROR] Python not found!
    echo Please install Python 3.13+ from https://python.org
    echo.
    pause
    exit /b 1
)

echo       Python found!
echo.

:: Check and install dependencies
echo [2/3] Checking dependencies...
py -c "import PyQt6" >nul 2>&1
if errorlevel 1 (
    echo       Installing dependencies...
    py -m pip install -r requirements.txt --quiet
    if errorlevel 1 (
        echo.
        echo [ERROR] Failed to install dependencies!
        pause
        exit /b 1
    )
    echo       Dependencies installed!
) else (
    echo       All dependencies OK!
)
echo.

:: Run application
echo [3/3] Starting Tibia PIC Editor...
echo.
echo ============================================
echo.

py main.py

if errorlevel 1 (
    echo.
    echo ============================================
    echo   Application crashed or closed with error.
    echo ============================================
    pause
    exit /b 1
)
