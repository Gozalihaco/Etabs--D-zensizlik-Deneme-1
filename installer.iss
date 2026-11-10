; Inno Setup 6 kurulum betigi - build_exe.bat tarafindan derlenir
#define AppName "ETABS Duzensizlik Kontrolu"
#define AppVersion "1.0.0"
#define AppExe "ETABS-Duzensizlik.exe"

[Setup]
AppId={{8F3C2A51-6D4E-4B7A-9C1E-2E5B7D0A4F13}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
DefaultDirName={autopf}\ETABS-Duzensizlik
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
; Yonetici yetkisi gerekmez; kullanici isterse tum kullanicilara kurabilir
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
OutputDir=cikti
OutputBaseFilename=ETABS-Duzensizlik-Kurulum
SetupIconFile=app.ico
UninstallDisplayIcon={app}\{#AppExe}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern

[Languages]
Name: "turkish"; MessagesFile: "compiler:Languages\Turkish.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "dist\ETABS-Duzensizlik\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExe}"; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{localappdata}\ETABS-Duzensizlik"
