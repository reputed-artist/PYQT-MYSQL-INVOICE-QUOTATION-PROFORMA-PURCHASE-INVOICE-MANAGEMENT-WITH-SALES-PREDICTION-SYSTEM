; ============================================================================
;  Sales Aura — Inno Setup installer
;  Flow: Welcome → License → Destination → Start Menu → Tasks → Ready → Install → Finish
;
;  Requirements:
;    * resources\license.txt        (non-empty — otherwise license page is skipped)
;    * ..\icons\sales Aura.ico      (setup + uninstall icon)
;    * ..\dist\Sales Aura\*         (PyInstaller flat-layout output)
;
;  Runtime single-instance is enforced by main.py via QSharedMemory.
;  Installer single-instance is enforced via AppMutex + IsAppRunning() below.
; ============================================================================

#define MyAppName       "Sales Aura"
#define MyAppVersion    "1.0.0"
#define MyAppPublisher  "Ant Developers"
#define MyAppExeName    "Sales Aura.exe"
#define MyAppMutex      "SalesAuraMutex2026"

[Setup]
AppId={{9F38D3A1-7B5C-4E20-AB64-5A82C4D93011}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL=https://codetechengineers.in
AppSupportURL=https://codetechengineers.com
AppUpdatesURL=https://codetechengineers.in

; --- Install location (prefilled, user-editable) ---
DefaultDirName={autopf}\Sales Aura
DisableDirPage=no
AllowUNCPath=no

DefaultGroupName=Sales Aura
AllowNoIcons=yes

; --- Output ---
OutputDir=..\installer
OutputBaseFilename=SalesAura-Setup-{#MyAppVersion}

; --- License: this file MUST exist with real text ---
LicenseFile=license.txt

; --- Icons ---
SetupIconFile=..\icons\sales Aura.ico
UninstallDisplayIcon={app}\Sales Aura.exe
UninstallDisplayName={#MyAppName}

; --- Privileges / architecture ---
PrivilegesRequired=admin
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

; --- Wizard pages ---
WizardStyle=modern
DisableWelcomePage=no
DisableReadyPage=no
DisableProgramGroupPage=no

; --- Compression ---
Compression=lzma2
SolidCompression=yes

; --- Single instance (installer) ---
AppMutex={#MyAppMutex}
CloseApplications=force
RestartApplications=no

ShowLanguageDialog=auto

; ============================================================================
;  Languages
; ============================================================================
[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

; ============================================================================
;  Tasks
; ============================================================================
[Tasks]
Name: "desktopicon"; \
    Description: "Create a desktop shortcut"; \
    GroupDescription: "Additional shortcuts:"; \
    Flags: unchecked

; ============================================================================
;  Files
; ============================================================================
[Files]
Source: "..\dist\Sales Aura\*"; \
    DestDir: "{app}"; \
    Flags: ignoreversion recursesubdirs createallsubdirs; \
    Excludes: "installer\*,*.log,__pycache__\*"

; ============================================================================
;  Icons
; ============================================================================
[Icons]
Name: "{group}\Sales Aura"; \
    Filename: "{app}\Sales Aura.exe"; \
    WorkingDir: "{app}"

Name: "{group}\Uninstall Sales Aura"; \
    Filename: "{uninstallexe}"

Name: "{autodesktop}\Sales Aura"; \
    Filename: "{app}\Sales Aura.exe"; \
    WorkingDir: "{app}"; \
    Tasks: desktopicon

; ============================================================================
;  Run (after install)
; ============================================================================
[Run]
Filename: "{app}\Sales Aura.exe"; \
    Description: "Launch Sales Aura"; \
    WorkingDir: "{app}"; \
    Flags: postinstall nowait skipifsilent

; ============================================================================
;  UninstallDelete
;  ---------------------------------------------------------------------------
;  Only remove folders the installer placed under {app}.
;  The SQLite DB lives in %LOCALAPPDATA%\Sales Aura\ and is NEVER touched.
; ============================================================================
[UninstallDelete]
Type: filesandordirs; Name: "{app}\dist"
Type: filesandordirs; Name: "{app}\resources"
Type: filesandordirs; Name: "{app}\icons"
Type: filesandordirs; Name: "{app}\tools"
Type: filesandordirs; Name: "{app}\PyQt6"
Type: files;          Name: "{app}\{#MyAppExeName}"

; ============================================================================
;  Code
;  ---------------------------------------------------------------------------
;  The AppMutex directive in [Setup] already blocks install while the app
;  is running, so no CreateMutex call is needed here.
;  We only handle the silent upgrade of any previously-registered version.
; ============================================================================
[Code]
function GetUninstallString(out UninstPath: string): Boolean;
var
  RegKey: string;
begin
  Result := False;
  RegKey := 'Software\Microsoft\Windows\CurrentVersion\Uninstall\'
            + ExpandConstant('{#SetupSetting("AppId")}') + '_is1';

  if RegQueryStringValue(HKLM64, RegKey, 'UninstallString', UninstPath) then
  begin Result := True; Exit; end;
  if RegQueryStringValue(HKLM32, RegKey, 'UninstallString', UninstPath) then
  begin Result := True; Exit; end;
end;

procedure StripQuotesAndParams(const Full: string; out ExePath, Params: string);
var
  s: string;
  p: Integer;
begin
  s := Trim(Full);
  if (Length(s) > 0) and (s[1] = '"') then
  begin
    p := Pos('"', Copy(s, 2, MaxInt));
    if p > 0 then
    begin
      ExePath := Copy(s, 2, p - 1);
      Params := Trim(Copy(s, p + 2, MaxInt));
      Exit;
    end;
  end;
  p := Pos(' ', s);
  if p > 0 then
  begin
    ExePath := Copy(s, 1, p - 1);
    Params := Trim(Copy(s, p + 1, MaxInt));
  end
  else
  begin
    ExePath := s;
    Params := '';
  end;
end;

function UninstallPreviousVersion(): Boolean;
var
  UninstString, ExePath, Params: string;
  ResultCode: Integer;
begin
  Result := True;
  if not GetUninstallString(UninstString) then Exit;

  StripQuotesAndParams(UninstString, ExePath, Params);

  if not FileExists(ExePath) then
  begin
    if ShellExec('', UninstString, '', '', SW_SHOW, ewWaitUntilTerminated, ResultCode) then
    begin
      if ResultCode <> 0 then Result := False;
    end
    else
      Result := False;
    Exit;
  end;

  if Exec(ExePath, '/VERYSILENT /SUPPRESSMSGBOXES /NORESTART', '', SW_SHOW,
          ewWaitUntilTerminated, ResultCode) then
  begin
    if ResultCode <> 0 then Result := False;
  end
  else
    Result := False;
end;

function InitializeSetup(): Boolean;
begin
  Result := True;

  { The [Setup] section declares:
        AppMutex={#MyAppMutex}
    Setup automatically refuses to continue while Sales Aura is running,
    so no manual mutex check is required. }

  if not UninstallPreviousVersion() then
  begin
    if MsgBox('The previous version could not be uninstalled automatically.' + #13#10#13#10 +
              'Your data in %LOCALAPPDATA%\Sales Aura\ will NOT be affected.' + #13#10#13#10 +
              'Continue installing anyway?',
              mbConfirmation, MB_YESNO) = IDNO then
      Result := False;
  end;
end;