; SQLShell Inno Setup Script
; Creates a professional Windows installer
;
; Requirements:
;   - Inno Setup 6.x (https://jrsoftware.org/isinfo.php)
;   - Built SQLShell in dist\SQLShell\
;
; Build command:
;   iscc sqlshell_inno.iss

#define MyAppName "SQLShell"
#define MyAppVersion "0.5.1"
#define MyAppPublisher "SQLShell Team"
#define MyAppURL "https://github.com/oyvinrog/SQLShell"
#define MyAppExeName "SQLShell.exe"
#define MyAppAssocName "SQLShell Project"
#define MyAppAssocExt ".sqlproj"
#define MyAppAssocKey StringChange(MyAppAssocName, " ", "") + MyAppAssocExt

[Setup]
; Application info
AppId={{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}/releases
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes

; Output settings
OutputDir=..\..\dist
OutputBaseFilename=SQLShell-{#MyAppVersion}-win64-setup
SetupIconFile=..\..\sqlshell\resources\icon.ico
UninstallDisplayIcon={app}\{#MyAppExeName}

; Compression
; Note: ultra64 compression makes smaller installers but slower decompression
; For faster installation (especially in CI), consider lzma2/normal or lzma2/fast
Compression=lzma2/ultra64
SolidCompression=yes
LZMAUseSeparateProcess=yes
; Reduce memory usage during decompression to speed up installation
LZMADictionarySize=65536

; Appearance
WizardStyle=modern
WizardSizePercent=120
DisableWelcomePage=no

; Privileges
PrivilegesRequired=admin
PrivilegesRequiredOverridesAllowed=dialog

; Misc
ChangesAssociations=yes
ArchitecturesInstallIn64BitMode=x64
MinVersion=10.0

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "quicklaunchicon"; Description: "{cm:CreateQuickLaunchIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked; OnlyBelowVersion: 6.1; Check: not IsAdminInstallMode
Name: "associatefiles"; Description: "Associate .sqlproj files with SQLShell"; GroupDescription: "File associations:"; Flags: unchecked

[Files]
; Main application files
Source: "..\..\dist\SQLShell\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
; Start Menu
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"

; Desktop icon (optional)
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

; Quick Launch (optional, legacy)
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: quicklaunchicon

[Registry]
; File association (optional)
Root: HKA; Subkey: "Software\Classes\{#MyAppAssocExt}\OpenWithProgids"; ValueType: string; ValueName: "{#MyAppAssocKey}"; ValueData: ""; Flags: uninsdeletevalue; Tasks: associatefiles
Root: HKA; Subkey: "Software\Classes\{#MyAppAssocKey}"; ValueType: string; ValueName: ""; ValueData: "{#MyAppAssocName}"; Flags: uninsdeletekey; Tasks: associatefiles
Root: HKA; Subkey: "Software\Classes\{#MyAppAssocKey}\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\{#MyAppExeName},0"; Tasks: associatefiles
Root: HKA; Subkey: "Software\Classes\{#MyAppAssocKey}\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""; Tasks: associatefiles

; App paths for command-line access
Root: HKA; Subkey: "Software\Microsoft\Windows\CurrentVersion\App Paths\{#MyAppExeName}"; ValueType: string; ValueName: ""; ValueData: "{app}\{#MyAppExeName}"; Flags: uninsdeletekey

[Run]
; Launch application after install (optional)
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[Code]
// Custom code for additional setup logic
// NOTE: Keep these functions simple to avoid installation delays

function InitializeSetup(): Boolean;
begin
  Result := True;
  // Add any pre-installation checks here
  // Keep this fast - no network calls or long operations
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    // Post-installation tasks
    // Keep this fast to avoid delays during silent install
  end;
end;

[UninstallDelete]
; Clean up any user data on uninstall (optional)
Type: filesandordirs; Name: "{localappdata}\SQLShell"

