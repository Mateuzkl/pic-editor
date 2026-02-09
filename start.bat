@echo off
title Tibia PIC Editor
echo Starting Tibia PIC Editor...
echo.

py main.py

if errorlevel 1 (
    echo.
    echo ==============================================
    echo   Application crashed or closed with error.
    echo ==============================================
    pause
    exit /b
)
