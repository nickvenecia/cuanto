; Inno Setup script — builds Cuanto-Setup.exe (per-user install, no admin needed)
#ifndef MyAppVersion
  #define MyAppVersion "0.0.0"
#endif

[Setup]
AppId={{D48A87F0-0CCB-49F7-A5D3-1CE1114D6A53}
AppName=Cuanto
AppVersion={#MyAppVersion}
AppPublisher=Cuanto
DefaultDirName={localappdata}\Programs\Cuanto
DefaultGroupName=Cuanto
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputBaseFilename=Cuanto-Setup
SetupIconFile=..\..\build\icon.ico
UninstallDisplayIcon={app}\Cuanto.exe
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Shortcuts:"

[Files]
Source: "..\..\dist\Cuanto\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion

[Icons]
Name: "{group}\Cuanto"; Filename: "{app}\Cuanto.exe"
Name: "{userdesktop}\Cuanto"; Filename: "{app}\Cuanto.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\Cuanto.exe"; Description: "Open Cuanto now"; Flags: nowait postinstall skipifsilent
