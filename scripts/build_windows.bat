@echo off
setlocal enabledelayedexpansion
title Build PixelCut Local - Windows Executable

echo ========================================================
echo  PixelCut Local - Windows Packaging (PyInstaller onedir)
echo ========================================================

:: Check for virtual environment
if not exist ".venv\Scripts\pyinstaller.exe" (
    echo [ERROR] PyInstaller not found in .venv.
    echo Please install dependencies first:
    echo   .\.venv\Scripts\pip install -r requirements.txt
    pause
    exit /b 1
)

:: Clean previous dist/build directories
echo Cleaning previous build artifacts...
if exist "dist\PixelCutLocal" rd /s /q "dist\PixelCutLocal"
if exist "build\PixelCutLocal" rd /s /q "build\PixelCutLocal"

:: Run PyInstaller build
echo Building Windows standalone package...
call .venv\Scripts\pyinstaller.exe --noconfirm --clean PixelCutLocal.spec

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Build failed! Check the output logs above.
    pause
    exit /b %errorlevel%
)

echo.
echo ========================================================
echo  BUILD SUCCESSFUL!
echo ========================================================
echo  Deliverable Location:
echo    dist\PixelCutLocal\PixelCutLocal.exe
echo.
echo  Note: Run the executable from dist\PixelCutLocal\,
echo  NEVER from the intermediate build\ folder.
echo ========================================================

:: Clean intermediate build directory to prevent confusion
if exist "build" rd /s /q "build"
