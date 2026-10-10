# -*- coding: utf-8 -*-
"""Rewrite build_exe.bat with clean, working structure."""

path = 'build_exe.bat'

content = r'''@echo off
rem ============================================================================
rem  Sales Aura - Build Script (Windows)
rem  ================================
rem  Builds the PyInstaller EXE and prepares the installable package.
rem
rem  Usage:
rem    1. Open this folder in a terminal:  cd c:\xampp\htdocs\pyqt_app_sqlite
rem    2. Run:  build_exe.bat
rem
rem  Output:
rem    - build\Sales Aura\Sales Aura.exe    (the frozen application)
rem    - dist\                              (PyInstaller bundle - kept!)
rem    - installer\SalesAura_Setup_*.exe    (Inno Setup compiled installer)
rem ============================================================================

echo.
echo  ============================================================
echo   Sales Aura - Build & Export Tool
echo   Date: %DATE% %TIME%
echo  ============================================================
echo.

echo  [1/6] Checking Python and PyInstaller...
python --version
if %ERRORLEVEL% neq 0 (
    echo.
    echo  ERROR: Python not found. Please install Python 3.9+ from:
    echo    https://www.python.org/downloads/
    pause
    exit /b 1
)

python -c "import PyInstaller" 2>nul
if %ERRORLEVEL% neq 0 (
    echo.
    echo  PyInstaller not found. Installing...
    python -m pip install --upgrade pip
    python -m pip install pyinstaller
    if %ERRORLEVEL% neq 0 (
        echo.
        echo  ERROR: Failed to install PyInstaller.
        pause
        exit /b 1
    )
    echo  PyInstaller installed successfully.
)

echo  PyInstaller version: %PYINSTALLER_VERSION%
echo.

echo  [2/6] Cleaning previous build artifacts...
if exist build rmdir /s /q build
# dist folder is preserved - it contains images and resources
if exist __pycache__ rmdir /s /q __pycache__
echo  Build artifacts cleaned.
echo.

echo  [3/6] Building the application with PyInstaller...
echo.

python -m PyInstaller "Sales Aura.spec"

if %ERRORLEVEL% neq 0 (
    echo.
    echo  ERROR: PyInstaller build failed.
    echo  Check the error messages above for details.
    pause
    exit /b 1
)

echo.
echo  PyInstaller build completed successfully.
echo.

echo  [4/6] Copying executable to installer folder...
if not exist "installer" mkdir installer
copy /Y "build\Sales Aura\Sales Aura.exe" "installer\Sales Aura.exe"
echo  Copied to installer\Sales Aura.exe
echo.

echo  [5/6] Compiling Inno Setup installer (if Inno Setup is installed)...

where iscc >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo.
    echo  Inno Setup (iscc.exe) not found on PATH.
    echo  To compile the installer, download and install Inno Setup from:
    echo    https://jrsoftware.org/isdl.php
    echo.
    echo  Skipping installer compilation. The frozen EXE is ready at:
    echo    build\Sales Aura\Sales Aura.exe
) else (
    echo  Inno Setup found. Compiling installer...
    echo.

    set "PROJECT_ROOT=C:\xampp\htdocs\pyqt_app_sqlite"

    echo  Compiling: %PROJECT_ROOT%\resources\sales_aura.iss
    echo.

    iscc "%PROJECT_ROOT%\resources\sales_aura.iss"

    if %ERRORLEVEL% neq 0 (
        echo.
        echo  ERROR: Inno Setup compilation failed.
        echo  Check the error messages above.
        pause
        exit /b 1
    )

    echo.
    echo  Inno Setup completed successfully.
    echo  Installer created in: %PROJECT_ROOT%\installer\
)
echo.

echo  [6/6] Build summary:
echo.
echo  Frozen Application:
echo    build\Sales Aura\Sales Aura.exe
echo.
echo  Bundled Resources (KEEP):
echo    dist\                      (PyInstaller bundle - resources, images)
echo.
echo  Database:
echo    Created at runtime in %LOCALAPPDATA%\Sales Aura\sales aura.db
echo.
echo  Installation:
echo    1. Run 'installer\Sales Aura Setup 1.0.0.exe'
echo    2. The installer will place files in:
echo       C:\Program Files\Sales Aura\
echo    3. Run 'Sales Aura.exe' to launch the application.
echo.

echo  ============================================================
echo.

pause

echo  Done. All builds completed successfully.
'''
with open(path, 'w', encoding='utf-8', newline='') as f:
    f.write(content)
print('build_exe.bat rewritten successfully')
