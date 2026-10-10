#define MyAppName "Whatsapp Automation Tool"
#define MyAppVersion "1.0.0.0"
#define MyAppPublisher "Ant Developer"
#define MyAppExeName "def21.exe"

[Setup]
AppId={{6DAC3768-D4AB-4FCE-AA20-1903AD257917}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}

VersionInfoVersion={#MyAppVersion}
VersionInfoDescription={#MyAppName} Installer
VersionInfoProductName={#MyAppName}
VersionInfoCompany={#MyAppPublisher}
VersionInfoCopyright=© 2025 {#MyAppPublisher}

DefaultDirName={autopf}\{#MyAppName}
DisableDirPage=no      
UninstallDisplayIcon={app}\{#MyAppExeName}
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64
DisableProgramGroupPage=no
DisableWelcomePage=no

PrivilegesRequired=admin 
PrivilegesRequiredOverridesAllowed=dialog
OutputBaseFilename=Whatsapp Automation Tool
SetupIconFile=C:\Users\Hacker\PycharmProjects\pythonProject2\icons\desk-icon.ico
SolidCompression=yes
WizardStyle=modern
LicenseFile=C:\Users\Hacker\PycharmProjects\pythonProject2\resources\license.txt


[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Files]
; Main exe
Source: "C:\Users\Hacker\PycharmProjects\pythonProject2\dist\def21.exe"; DestDir: "{app}"; Flags: ignoreversion

; Resources
Source: "C:\Users\Hacker\PycharmProjects\pythonProject2\resources\*"; DestDir: "{app}\resources"; Flags: ignoreversion recursesubdirs

[Icons]
; Start Menu shortcut only
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"

[UninstallDelete]
Type: filesandordirs; Name: "{app}"

[Run]
Filename: "{app}\{#MyAppExeName}"; \
Description: "Launch {#MyAppName}"; \
Flags: nowait postinstall skipifsilent unchecked
