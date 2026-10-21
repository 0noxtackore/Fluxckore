; Inno Setup script for FluxOptimizer
; Build (after PyInstaller has produced dist/FluxOptimizer/):
;   ISCC.exe /DAppVersion=2.1.0 packaging\FluxOptimizer.iss

#ifndef AppVersion
#define AppVersion "0.0.0"
#endif

[Setup]
AppId={{5B7C2F5A-3C8E-4D2B-9E1A-6F0D4A8C1E97}
AppName=FluxOptimizer
AppVersion={#AppVersion}
AppPublisher=FluxOptimizer Team
DefaultDirName={autopf}\FluxOptimizer
DefaultGroupName=FluxOptimizer
PrivilegesRequired=admin
OutputDir=..\dist\installer
OutputBaseFilename=FluxOptimizer-Setup-{#AppVersion}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible
ArchitecturesAllowed=x64compatible
SetupIconFile=fluxoptimizer.ico
UninstallDisplayIcon={app}\FluxOptimizer.exe

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "..\dist\FluxOptimizer\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs

[Icons]
Name: "{group}\FluxOptimizer"; Filename: "{app}\FluxOptimizer.exe"
Name: "{autodesktop}\FluxOptimizer"; Filename: "{app}\FluxOptimizer.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\FluxOptimizer.exe"; Description: "{cm:LaunchProgram,FluxOptimizer}"; Flags: nowait postinstall skipifsilent
