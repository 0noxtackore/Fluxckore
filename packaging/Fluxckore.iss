; Inno Setup script for Fluxckore
; Build (after the final onedir has been placed in dist/Fluxckore-app/):
;   ISCC.exe /DAppVersion=9.0.0 packaging\Fluxckore.iss

#ifndef AppVersion
#define AppVersion "0.0.0"
#endif

[Setup]
AppId={{5B7C2F5A-3C8E-4D2B-9E1A-6F0D4A8C1E97}
AppName=Fluxckore
AppVersion={#AppVersion}
AppPublisher=0noxtackore
DefaultDirName={autopf}\Fluxckore
DefaultGroupName=Fluxckore
PrivilegesRequired=admin
OutputDir=..\dist\installer
OutputBaseFilename=Fluxckore-Setup-{#AppVersion}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible
ArchitecturesAllowed=x64compatible
SetupIconFile=fluxckore.ico
UninstallDisplayIcon={app}\Fluxckore.exe

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "..\dist\Fluxckore-app\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs

[Icons]
Name: "{group}\Fluxckore"; Filename: "{app}\Fluxckore.exe"
Name: "{autodesktop}\Fluxckore"; Filename: "{app}\Fluxckore.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\Fluxckore.exe"; Description: "{cm:LaunchProgram,Fluxckore}"; Flags: nowait postinstall skipifsilent
