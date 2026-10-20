@echo off
setlocal enabledelayedexpansion
title PixelCut Local - Development Mode

echo ========================================================
echo  PixelCut Local - Starting in Development Mode
echo ========================================================

:: Check for virtual environment
if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment not found at .venv\Scripts\python.exe
    echo Please create it using:
    echo   py -3.12 -m venv .venv
    echo   .\.venv\Scripts\pip install -r requirements.txt
    pause
    exit /b 1
)

:: Activate virtual environment
call .venv\Scripts\activate.bat

:: Add src to PYTHONPATH
set "PYTHONPATH=%~dp0..\src;%PYTHONPATH%"

:: Run application
echo Launching PixelCut Local...
python "%~dp0..\src\pixelcut_local\main.py" %*

if %errorlevel% neq 0 (
    echo [WARNING] Application exited with error code %errorlevel%
    pause
)
