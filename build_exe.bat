@echo off
setlocal
title Sales Aura Build

cd /d "%~dp0"

echo.
echo ============================================
echo        Sales Aura - Build and Export
echo        Date: %DATE% %TIME%
echo ============================================
echo.

echo [1/5] Checking Python...
python --version
if errorlevel 1 goto :error

echo.
echo [2/5] Checking PyInstaller...
python -m PyInstaller --version
if errorlevel 1 goto :error

echo.
echo [3/5] Cleaning old build output...
if exist "build" rmdir /s /q "build"
if exist "dist\Sales Aura" rmdir /s /q "dist\Sales Aura"
if exist "Sales Aura.spec" del /q "Sales Aura.spec"

rem Clean stale bytecode
for /d /r . %%d in (__pycache__) do @if exist "%%d" rd /s /q "%%d"

echo Old build artifacts cleaned.
echo.

echo Building Sales Aura (flat layout)...
python -m PyInstaller ^
  --noconfirm --clean --onedir --windowed ^
  --name "Sales Aura" ^
  --icon "icons/sales Aura.ico" ^
  --contents-directory "." ^
  --add-data "dist;dist" ^
  --add-data "resources;resources" ^
  --add-data "icons;icons" ^
  --add-data "tools;tools" ^
  --add-data "data;data" ^
  --hidden-import "PyQt6.sip" ^
  --hidden-import "PyQt6.QtSvg" ^
  --hidden-import "PyQt6.QtWebEngineWidgets" ^
  --hidden-import "PyQt6.QtWebEngineCore" ^
  --hidden-import "PyQt6.QtWebEngineQuick" ^
  --hidden-import "PyQt6.QtPrintSupport" ^
  --collect-all "PyQt6" ^
  main.py

if errorlevel 1 goto :error

if not exist "dist\Sales Aura\Sales Aura.exe" (
    echo ERROR: Expected executable was not created.
    goto :error
)

echo.
echo PyInstaller build completed.
echo Executable: "%CD%\dist\Sales Aura\Sales Aura.exe"
echo.

echo [4/5] Preparing installer output...
if not exist "installer" mkdir "installer"

set "ISCC="

if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" (
    set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
)

if exist "%ProgramFiles%\Inno Setup 6\ISCC.exe" (
    set "ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe"
)

if defined ISCC goto :compile_iss

where iscc.exe >nul 2>&1
if not errorlevel 1 (
    set "ISCC=iscc.exe"
    goto :compile_iss
)

echo Inno Setup was not found.
echo The application build is ready, but the installer was not compiled.
goto :summary

:compile_iss
if not exist "resources\sales_aura.iss" (
    echo ERROR: resources\sales_aura.iss not found.
    goto :error
)

echo Compiling Inno Setup script...
"%ISCC%" "resources\sales_aura.iss"
if errorlevel 1 goto :error

echo Installer compilation completed.
echo.

:summary
echo [5/5] Build summary
echo.
echo Application folder:
echo   dist\Sales Aura\
echo.
echo Executable:
echo   dist\Sales Aura\Sales Aura.exe
echo.
echo Installer output depends on OutputDir in the ISS file.
echo.
pause
exit /b 0

:error
echo.
echo ERROR: Build process failed.
echo Check the messages above.
echo.
pause
exit /b 1