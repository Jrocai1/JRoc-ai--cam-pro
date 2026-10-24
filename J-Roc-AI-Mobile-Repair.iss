#define MyAppName "J-Roc AI Mobile Repair"
#define MyAppVersion "0.4.0"
#define MyAppPublisher "J-ROC AI"
#define MyAppExeName "J-Roc AI Mobile Repair.exe"

[Setup]
AppId={{8D3AF627-0D9B-4C0D-9A2D-4E8A77F2D0A1}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\J-Roc AI\Mobile Repair
DefaultGroupName=J-Roc AI Mobile Repair
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64
PrivilegesRequired=lowest
OutputDir=release
OutputBaseFilename=J-Roc-AI-Mobile-Repair-v{#MyAppVersion}-Setup-x64
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\{#MyAppExeName}
DisableProgramGroupPage=yes
CloseApplications=yes
RestartApplications=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

[Files]
Source: "dist\J-Roc AI Mobile Repair\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\J-Roc AI Mobile Repair"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\J-Roc AI Mobile Repair"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch J-Roc AI Mobile Repair"; Flags: postinstall nowait skipifsilent
