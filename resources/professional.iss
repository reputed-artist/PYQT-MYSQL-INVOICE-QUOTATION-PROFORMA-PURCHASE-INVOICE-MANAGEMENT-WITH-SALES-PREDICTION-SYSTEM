#define MyAppName "Whatsapp Automation Tool"
#define MyAppVersion "2.0.1.1"
#define MyAppPublisher "Ant Developer"
#define MyAppExeName "def22.exe"

[Code]
function GetUninstallString(out UninstPath: string): Boolean;
var
  RegKey: string;
begin
  Result := False;
  RegKey := 'Software\Microsoft\Windows\CurrentVersion\Uninstall\' + ExpandConstant('{#SetupSetting("AppName")}') + '_is1';
  // Try 64-bit HKLM first
  if RegQueryStringValue(HKLM64, RegKey, 'UninstallString', UninstPath) then
  begin
    Result := True;
    Exit;
  end;
  // Then try 32-bit HKLM
  if RegQueryStringValue(HKLM32, RegKey, 'UninstallString', UninstPath) then
  begin
    Result := True;
    Exit;
  end;
end;

procedure StripQuotesAndParams(const Full: string; out ExePath, Params: string);
var
  s: string;
  p: Integer;
begin
  s := Trim(Full);
  // If starts with quote, find matching quote
  if (Length(s) > 0) and (s[1] = '"') then
  begin
    p := Pos('"', Copy(s, 2, MaxInt));
    if p > 0 then
    begin
      ExePath := Copy(s, 2, p-1);
      Params := Trim(Copy(s, p+2, MaxInt));
      Exit;
    end;
  end;
  // No leading quote — split on first space
  p := Pos(' ', s);
  if p > 0 then
  begin
    ExePath := Copy(s, 1, p-1);
    Params := Trim(Copy(s, p+1, MaxInt));
  end else
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
  Result := True; // default allow install to continue
  if GetUninstallString(UninstString) then
  begin
    StripQuotesAndParams(UninstString, ExePath, Params);
    // If file doesn't exist (or UninstallString contains extra args), try to just extract exe name
    if not FileExists(ExePath) then
    begin
      // try maybe the UninstallString is like: "C:\path\unins000.exe" /something
      // anyway we'll still try calling the UninstallString via ShellExecute
      if ShellExec('', UninstString, '', '', SW_SHOW, ewWaitUntilTerminated, ResultCode) then
      begin
        if ResultCode <> 0 then
        begin
          MsgBox('Previous version uninstaller returned code: ' + IntToStr(ResultCode), mbError, MB_OK);
          Result := False;
        end;
      end
      else
      begin
        // couldn't execute
        Result := False;
      end;
      Exit;
    end;

    // Run uninstaller silently
    if Exec(ExePath, '/VERYSILENT /SUPPRESSMSGBOXES', '', SW_SHOW, ewWaitUntilTerminated, ResultCode) then
    begin
      if ResultCode <> 0 then
      begin
        MsgBox('Failed to uninstall previous version. Uninstaller returned code: ' + IntToStr(ResultCode), mbError, MB_OK);
        Result := False;
      end;
    end
    else
    begin
      MsgBox('Failed to run previous uninstaller at: ' + ExePath, mbError, MB_OK);
      Result := False;
    end;
  end;
end;

// Run uninstaller at the start of installation (before files are streamed)
function InitializeSetup(): Boolean;
begin
  // Return False to abort setup
  Result := True;
  if UninstallPreviousVersion() = False then
  begin
    // Ask user whether to abort or continue
    if MsgBox('Previous version could not be uninstalled automatically.'#13#10 +
              'Do you want to continue the installation anyway?', mbConfirmation, MB_YESNO) = IDNO then
    begin
      Result := False;
    end;
  end;
end;

[Setup]
AppId={{6DAC3768-D4AB-4FCE-AA20-1903AD257917}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}

VersionInfoVersion={#MyAppVersion}
PrivilegesRequired=admin
UpdateUninstallLogAppName=yes

VersionInfoDescription={#MyAppName} Installer
VersionInfoProductName={#MyAppName}
VersionInfoCompany={#MyAppPublisher}
VersionInfoCopyright=© 2025 {#MyAppPublisher}

DefaultDirName={autopf}\{#MyAppName}
UninstallDisplayIcon={app}\{#MyAppExeName}
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
DisableProgramGroupPage=no 
DisableWelcomePage=no

AppMutex=WhatsappAutomationMutex2025

PrivilegesRequiredOverridesAllowed=dialog
OutputBaseFilename=Whatsapp Automation Tool
SetupIconFile=C:\Users\Hacker\PycharmProjects\pythonProject2\icons\desk-icon.ico
SolidCompression=yes
WizardStyle=modern
LicenseFile=C:\Users\Hacker\PycharmProjects\pythonProject2\resources\license.txt 

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; Main exe
Source: "C:\Users\Hacker\PycharmProjects\pythonProject2\dist\def22.exe"; DestDir: "{app}"; Flags: ignoreversion

; Resources
Source: "C:\Users\Hacker\PycharmProjects\pythonProject2\resources\*"; DestDir: "{app}\resources"; Flags: ignoreversion recursesubdirs

[Icons]
; Start Menu shortcut
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"

; Desktop shortcut
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[UninstallDelete]
Type: filesandordirs; Name: "{app}"

[Run]
Filename: "{app}\{#MyAppExeName}"; \
Description: "Launch {#MyAppName}"; \
Flags: nowait postinstall skipifsilent unchecked
