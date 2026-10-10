# 📦 Sales Aura - Export & Installation Guide

> **Version:** 1.0.0
> **Date:** 2026-10-09
> **Author:** Tejas Chavda

---

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Export to Executable](#export-to-executable)
4. [Create Windows Installer (Inno Setup)](#create-windows-installer-inno-setup)
5. [Post-Export Path Verification](#post-export-path-verification)
6. [Installation Steps](#installation-steps)
7. [File Structure After Installation](#file-structure-after-installation)
8. [Troubleshooting](#troubleshooting)
9. [FAQ](#faq)

---

## Overview

This guide walks you through exporting the **Sales Aura** PyQt6 application to a Windows executable, creating an Inno Setup installer (`.iss`), and verifying that all paths work correctly after export.

### Key Features of This Export

| Feature | How it works |
|---------|--------------|
| **SQLite Database** | `data/sales aura.db` created automatically
| **User Data** | Written to `%LOCALAPPDATA%\Sales Aura\` (always writable) |
| **Bundle Files** | Images, resources, and tools copied to `{app}\` |
| **No MySQL/XAMPP** | Zero-setup local SQLite storage |
| **Inno Setup Installer** | One-click Windows installer with desktop shortcut |

---

## Prerequisites

### 1. Required Software

| Software | Version | Purpose |
|----------|---------|---------|
| **Python** | 3.9+ | Running the build script |
| **PyInstaller** | Latest | Converting Python to EXE |
| **Inno Setup** | Latest | Creating the Windows installer |

### 2. Install Prerequisites

```bash
# Install Python from https://www.python.org/downloads/
# Make sure "Add Python to PATH" is checked!

# Install PyInstaller
pip install pyinstaller

# Install Inno Setup (optional)
# Download from: https://jrsoftware.org/isdl.php
# Run the installer and ensure "iscc.exe" is added to PATH
```

### 3. Verify Installation

```bash
python --version
pip show pyinstaller
where iscc  # Should show the path to Inno Setup compiler
```

---

## Export to Executable

### Method A: Using the Automated Build Script (Recommended)

1. Open a terminal in the project folder:
   ```bash
   cd c:\xampp\htdocs\pyqt_app_sqlite
   ```

2. Run the build script:
   ```bash
   build_exe.bat
   ```

3. The script will:
   - Clean previous build artifacts
   - Build the EXE using PyInstaller
   - Compile the Inno Setup installer (if installed)
   - Show a summary of the output

### Method B: Manual PyInstaller Build

1. Clean previous builds:
   ```bash
   rmdir /s /q build
   rmdir /s /q dist
   ```


### Method C: Using the Existing Spec File

The project already includes a PyInstaller spec file that:

- Includes all required `hiddenimports` for PyQt6 modules
- Bundles `dist`, `resources`, `icons`, and `tools` folders
- Produces a windowed (non-console) EXE
- Includes the application icon (`sales Aura.ico`)

> **Note:** The compiled EXE is located at `build\Sales Aura\Sales Aura.exe`

---

## Create Windows Installer (Inno Setup)

### 1. Build the Application

```bash
cd c:\xampp\htdocs\pyqt_app_sqlite
build_exe.bat
```

The build script will:
- Build the EXE using PyInstaller (output: `build\Sales Aura\Sales Aura.exe`)
- Copy the executable to `installer\Sales Aura.exe`

### 2. Compile the ISS File

```bash
# Open a command prompt with Inno Setup in PATH
cd c:\xampp\htdocs\pyqt_app_sqlite\resources
iscc sales_aura.iss
```

### 3. Output

The compiled installer will be saved as:

```
c:\xampp\htdocs\pyqt_app_sqlite\installer\Sales Aura Setup 1.0.0.exe
```

### 4. Customize the Installer

Edit these sections in **`sales_aura.iss`** before compiling:

| Setting | Location | Description |
|---------|----------|-------------|
| `AppPublisher` | `[Setup]` | Company name shown in installer |
| `DefaultDirName` | `[Setup]` | Installation directory |
| `OutputBaseFilename` | `[Setup]` | Name of the output installer |
| `SetupIconFile` | `[Setup]` | Icon shown in the installer |
| `LicenseFile` | `[Setup]` | EULA displayed during installation |
| `Source` paths | `[Files]` | Paths to bundled files |

---

## Post-Export Path Verification

### How Path Handling Works

The application uses a dual-path system to ensure everything works both in development and after export:

```
┌─────────────────────────────────────────────────────────────┐
│  - SQLite DB:  C:\...\pyqt_app_sqlite\data\sales_aura.db    │
│  - User data:  C:\...\pyqt_app_sqlite\dist\img\             │
│  - Reads:      Project files                            │
└─────────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│  - SQLite DB:  %LOCALAPPDATA%\Sales Aura\sales aura.db          │
│  - User data:  %LOCALAPPDATA%\Sales Aura\ (writable)        │
│  - Reads:      {app}\ (bundle)                              │
└─────────────────────────────────────────────────────────────┘
```

### Critical Paths to Verify

| Path | In Source | In EXE | In Installer |
|------|-----------|--------|--------------|
| **Database** | `data/sales aura.db` | `%LOCALAPPDATA%\Sales Aura\sales aura.db` | `{app}\sales aura.db` |
| **User uploads** | `dist/img/` | `%LOCALAPPDATA%\Sales Aura\uploads\` | `{app}\uploads\` |
| **Bundle images** | `dist/img/` | `{app}\dist\img\` | `{app}\` |
| **Tools** | `tools/` | `{app}\tools\` | `{app}\` |
| **Resources** | `resources/` | `{app}\resources\` | `{app}\` |

### Test the Exported Application

1. **Run the EXE directly:**
   ```bash
   build\Sales Aura\Sales Aura.exe
   ```

2. **Run the compiled installer:**
   ```bash


## Installation Steps

### Step 1: Build the Application

```bash
cd c:\xampp\htdocs\pyqt_app_sqlite
build_exe.bat
```

### Step 2: Generate Installer (Optional)

1. Install Inno Setup
2. Compile the ISS file:
   ```bash
   cd c:\xampp\htdocs\pyqt_app_sqlite\resources
   iscc sales_aura.iss
   ```

### Step 3: Install the Application

1. Run the installer: `installer\Sales Aura Setup 1.0.0.exe`
2. Follow the installation wizard:
   - Accept the EULA
   - Choose installation directory (default: `C:\Program Files\Sales Aura`)
   - Select shortcuts (Start Menu, Desktop, Quick Launch)
3. Click **Finish**

### Step 4: First Launch

1. Launch Sales Aura from the Start Menu or desktop shortcut
2. The application will:
   - Create the SQLite database if it doesn't exist
   - Seed the database with initial data
   - Show the login screen
3. Login with:
   ```
   Email: admin@gmail.com
   Password: admin@123
   ```

### Step 5: Verify Everything Works

- [ ] Application launches without errors
- [ ] Dashboard loads correctly
- [ ] Database is created and seeded
- [ ] Login works with default credentials
- [ ] Create a test invoice
- [ ] Export a report


## Troubleshooting

### Issue: "Failed to create database" or "Permission denied"

**Cause:** The application tried to write the database to a read-only location.

**Solution:** This is handled automatically. The app maps the database to the correct writable location. If you're using a custom installation path, ensure you have write permissions.

### Issue: "Missing module" or ImportError

**Cause:** PyInstaller didn't include required modules.

**Solution:** Check the spec file. The `hiddenimports` list includes:
- `PyQt6.sip`
- `PyQt6.QtSvg`
- `PyQt6.QtWebEngineWidgets`
- `PyQt6.QtWebEngineCore`
- `PyQt6.QtWebEngineQuick`
- `PyQt6.QtPrintSupport`

### Issue: Application launches but crashes immediately

**Cause:** Common causes:
1. Missing DLL (try running Win+R, type `mdSched` to check Windows Error Reporting)
2. The SQLite database file is locked
3. Missing Python runtime (isolate from system Python)

**Solution:** Run the EXE from the full path (not double-clicking from a shortcut) to see the error message.

### Issue: Images not loading after export

**Cause:** Path resolution for bundle images.



### Issue: Inno Setup compiler not found

**Cause:** Inno Setup is not installed or not in PATH.

**Solution:** 
1. Download Inno Setup from https://jrsoftware.org/isdl.php
2. Run the installer
3. Add `iscc.exe` to PATH if needed
4. Restart your terminal

### Issue: Database not created after installation

**Cause:** The `data` folder is not included in the build, or the app can't write to it.


- `{app}\data\sales_aura.db`
- `%LOCALAPPDATA%\Sales Aura\data\sales_aura.db`

### Issue: EXE doesn't run after installation ("system cannot find specified file")

**Cause:** This typically happens when:
1. The ISS file has hardcoded paths to non-existent files
2. The installer points to the wrong file location
3. The executable wasn't built correctly

**Solution:**
1. Ensure the build script was run successfully
2. Verify `installer\Sales Aura.exe` exists
3. Rebuild using `build_exe.bat`
4. Recompile the ISS file with the corrected paths

---

## FAQ

**Q: Can I use a custom installation directory?**
A: Yes. During installation, you can choose any directory. The app handles path mapping automatically.

**Q: Where is the database stored?**
A: In the user writable local app data folder `%LOCALAPPDATA%\Sales Aura\sales aura.db` (created automatically on first launch).

**Q: Does the application work without admin rights?**
A: The installer requires admin rights by default, but the app itself runs fine without. Admin rights are only needed for installation.

**Q: Do I need to re-build for every version?**
A: Yes. Regenerate the EXE and recompile the ISS file whenever you make changes.

**Q: Can I distribute the EXE without the installer?**
A: Yes. The frozen EXE works standalone, but you need to ensure the `data` folder exists for the database.

**Q: How do I backup the database?**
A: Use the app's built-in Backup feature in Settings. Or simply copy `%LOCALAPPDATA%\Sales Aura\sales aura.db` to another location.

**Q: Can I add more languages?**
A: Yes. The ISS file currently supports English. Add additional languages in the `[Languages]` section of the ISS file.

---

## Quick Reference

```bash
# Build the EXE
cd c:\xampp\htdocs\pyqt_app_sqlite
build_exe.bat

# Build the EXE manually
python -m PyInstaller "Sales Aura.spec"

# Compile the ISS (if Inno Setup is installed)
iscc resources\sales_aura.iss

# Clean build artifacts
rmdir /s /q build
rmdir /s /q dist
```

---

## Need Help?

- **Email:** Tejaschavda2020@gmail.com
- **Project:** https://github.com/reputed-artist/PYQT-MYSQL-INVOICE-QUOTATION-PROFORMA-PURCHASE-INVOICE-MANAGEMENT-WITH-SALES-PREDICTION-SYSTEM
- **Issues:** Report bugs or request features on the project repository

---

> **Thank you for using Sales Aura!** 🎉

- [ ] Logout and login back

---

## File Structure After Installation

```
C:\Program Files\Sales Aura\          (or custom path)
│
├── Sales Aura.exe                     (main application)
├── Uninstall.exe                      (uninstaller)
├── resources\                         (license, version info)
│   ├── license.txt
│   └── file_version.txt
│
â”‚   â””â”€â”€ sales aura.db
│   └── sales_aura.db
│
├── img\                               (bundle images)
│   ├── sales-aura-icon.png
│   └── sales-aura.png
│
└── tools\                             (utility scripts)
```

### User-Specific Writable Locations

```
%LOCALAPPDATA%\Sales Aura\            (C:\Users\<you>\AppData\Local\Sales Aura)
│
├── uploads\                           (user uploads - avatars, logos, images)
└── database\                          (runtime database backups)
```

> **Note:** The app automatically creates these writable directories on first use. You do not need to pre-create them.

   installer\Sales Aura Setup 1.0.0.exe
   ```

3. **After installation, verify:**
   - Application launches without errors
   - SQLite database is created at `C:\Sales Aura\data\sales_aura.db`
   - User uploads directory is created at `%LOCALAPPDATA%\Sales Aura\uploads\`
   - Log out and check that login works with default credentials:
     ```
     Email: admin@gmail.com
     Password: admin@123
     ```


2. Build with PyInstaller:
   ```bash
   python -m PyInstaller "Sales Aura.spec"
   ```

3. Verify the output:
   ```bash
   dir build\Sales Aura\Sales Aura.exe
   ```

### Method C: Using the Existing Spec File

The project already includes a PyInstaller spec file that:

- Includes all required `hiddenimports` for PyQt6 modules
- Bundles `dist`, `resources`, `icons`, and `tools` folders
- Produces a windowed (non-console) EXE
- Includes the application icon (`sales Aura.ico`)

> **Note:** The compiled EXE is located at `build\Sales Aura\Sales Aura.exe`


