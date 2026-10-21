; Inno Setup script for Fluxop
; Build (after the final onedir has been placed in dist/Fluxop-app/):
;   ISCC.exe /DAppVersion=8.0.2 packaging\Fluxop.iss

#ifndef AppVersion
#define AppVersion "0.0.0"
#endif

[Setup]
AppId={{5B7C2F5A-3C8E-4D2B-9E1A-6F0D4A8C1E97}
AppName=Fluxop
AppVersion={#AppVersion}
AppPublisher=Fluxop Team
DefaultDirName={autopf}\Fluxop
DefaultGroupName=Fluxop
PrivilegesRequired=admin
OutputDir=..\dist\installer
OutputBaseFilename=Fluxop-Setup-{#AppVersion}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible
ArchitecturesAllowed=x64compatible
SetupIconFile=fluxop.ico
UninstallDisplayIcon={app}\Fluxop.exe

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "..\dist\Fluxop-app\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs

[Icons]
Name: "{group}\Fluxop"; Filename: "{app}\Fluxop.exe"
Name: "{autodesktop}\Fluxop"; Filename: "{app}\Fluxop.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\Fluxop.exe"; Description: "{cm:LaunchProgram,Fluxop}"; Flags: nowait postinstall skipifsilent
