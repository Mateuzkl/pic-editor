@echo off
setlocal

:: Always run from the directory that contains this launcher.
:: This keeps requirements.txt and main.py resolvable when started elsewhere.
cd /d "%~dp0"
if errorlevel 1 (
    echo [ERROR] Could not access the application directory:
    echo %~dp0
    pause
    exit /b 1
)

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
py -c "import PyQt6, PIL, numpy" >nul 2>&1
if errorlevel 1 (
    echo       Installing dependencies...
    py -m pip install -r "%~dp0requirements.txt" --quiet
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

py "%~dp0main.py"

if errorlevel 1 (
    echo.
    echo ============================================
    echo   Application crashed or closed with error.
    echo ============================================
    pause
    exit /b 1
)
