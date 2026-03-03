; Inno Setup script for Naturtag
; Build with: iscc /DAppVersion=<version> packaging\naturtag.iss

#ifndef AppVersion
  #error "AppVersion must be defined via /DAppVersion=x.y.z"
#endif

[Setup]
AppId={{01329D81-576C-42FE-9850-9C4C03F161FB}
AppName=Naturtag
AppVersion={#AppVersion}
AppPublisher=Jordan Cook
AppPublisherURL=https://naturtag.readthedocs.io
AppSupportURL=https://naturtag.readthedocs.io
AppCopyright=Copyright (C) 2026 Jordan Cook
DefaultDirName={autopf}\Naturtag
DefaultGroupName=Naturtag
UninstallDisplayIcon={app}\_internal\assets\icons\logo.ico
; SourceDir is relative to the .iss file location; set to repo root
SourceDir=..
SetupIconFile=assets\icons\logo.ico
OutputDir=dist
OutputBaseFilename=naturtag-installer
Compression=lzma2
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=admin

[Files]
Source: "dist\naturtag\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Tasks]
Name: addtopath; Description: "Add nt CLI to PATH"; GroupDescription: "Command-line tools:"

[Registry]
Root: HKLM; Subkey: "SYSTEM\CurrentControlSet\Control\Session Manager\Environment"; ValueType: expandsz; ValueName: "Path"; ValueData: "{olddata};{app}"; Check: NeedsAddPath('{app}'); Tasks: addtopath

[Code]
function NeedsAddPath(Param: string): boolean;
var
  OrigPath: string;
begin
  if not RegQueryStringValue(HKEY_LOCAL_MACHINE,
    'SYSTEM\CurrentControlSet\Control\Session Manager\Environment',
    'Path', OrigPath)
  then begin
    Result := True;
    exit;
  end;
  Result := Pos(';' + Param + ';', ';' + OrigPath + ';') = 0;
end;

[Icons]
Name: "{group}\Naturtag"; Filename: "{app}\naturtag.exe"; IconFilename: "{app}\_internal\assets\icons\logo.ico"; Comment: "A tool for tagging image files with iNaturalist taxonomy & observation metadata"
Name: "{group}\Uninstall Naturtag"; Filename: "{uninstallexe}"
