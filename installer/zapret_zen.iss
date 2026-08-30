; Zapret-Zen Inno Setup script
; Build via scripts/build_inno_installer.ps1:
;   & ISCC.exe /DAppVersion=2.5.1 /DX64Src=... /DArm64Src=... installer\zapret_zen.iss

#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif

#ifndef VersionInfoVer
  #define VersionInfoVer AppVersion
#endif

#ifndef MyAppName
  #define MyAppName "Zapret-Zen"
#endif

#ifndef MyAppPublisher
  #define MyAppPublisher "peshk0v"
#endif

#ifndef MyAppExeName
  #define MyAppExeName "zapret_zen.exe"
#endif

[Setup]
AppId={{F5A2C73E-9B11-4E6B-8C2D-1A7E5D0B3F91}
AppName={#MyAppName}
AppVersion={#AppVersion}
AppVerName={#MyAppName} {#AppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={code:GetInstallPath}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
PrivilegesRequired=admin
ArchitecturesAllowed=x64compatible arm64
ArchitecturesInstallIn64BitMode=x64compatible arm64
OutputDir=dist_installer
OutputBaseFilename=install_zapretzen_{#AppVersion}_universal
SetupLogging=yes
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallDisplayName={#MyAppName}
VersionInfoVersion={#VersionInfoVer}
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription={#MyAppName} Installer
VersionInfoProductName={#MyAppName}
VersionInfoProductVersion={#VersionInfoVer}
#ifndef SignToolCmd
#else
SignedUninstaller=yes
SignTool={#SignToolCmd} $f
#endif
#ifdef SetupIcon
SetupIconFile={#SetupIcon}
#endif

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
#ifdef X64Src
Source: "{#X64Src}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs; Check: IsX64
#endif
#ifdef Arm64Src
Source: "{#Arm64Src}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs; Check: IsArm64
#endif

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; IconFilename: "{app}\{#MyAppExeName}"; IconIndex: 0
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon; IconFilename: "{app}\{#MyAppExeName}"; IconIndex: 0

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#MyAppName}}"; Flags: nowait postinstall skipifsilent

[Code]
const
  LEGACY_UNINSTALL_KEY = 'Software\Microsoft\Windows\CurrentVersion\Uninstall\ZapretZen';
  RUN_KEY = 'Software\Microsoft\Windows\CurrentVersion\Run';

procedure KillAppImages();
var
  ResultCode: Integer;
begin
  Exec('taskkill.exe', '/F /T /IM zapret_zen.exe', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  Exec('taskkill.exe', '/F /T /IM winws.exe', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  Exec('taskkill.exe', '/F /T /IM TgWsProxy_windows.exe', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  Exec('taskkill.exe', '/F /T /IM tg-ws-proxy.exe', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
end;

procedure RemoveAutostart();
var
  ResultCode: Integer;
begin
  Exec('schtasks.exe', '/Delete /F /TN ZapretZen', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  RegDeleteValue(HKCU, RUN_KEY, 'ZapretZen');
  RegDeleteValue(HKCU, RUN_KEY, 'ZapretHub');
  RegDeleteValue(HKCU, RUN_KEY, 'Zapret-Zen');
  RegDeleteValue(HKLM64, RUN_KEY, 'ZapretZen');
  RegDeleteValue(HKLM64, RUN_KEY, 'ZapretHub');
  RegDeleteValue(HKLM64, RUN_KEY, 'Zapret-Zen');
  Exec('sc.exe', 'stop zapret', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  Exec('sc.exe', 'delete zapret', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
end;

function GetInstallPath(Param: String): String;
var
  InstallDir: String;
begin
  if RegQueryStringValue(HKLM64, LEGACY_UNINSTALL_KEY, 'InstallLocation', InstallDir) then
  begin
    Result := InstallDir;
    Exit;
  end;
  if RegQueryStringValue(HKCU64, LEGACY_UNINSTALL_KEY, 'InstallLocation', InstallDir) then
  begin
    Result := InstallDir;
    Exit;
  end;
  Result := ExpandConstant('{autopf}\Zapret-Zen');
end;

function IsX64(): Boolean;
begin
  Result := not IsARM64();
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssInstall then
  begin
    KillAppImages();
    RemoveAutostart();
  end;
end;

procedure CurUninstallStepChanged(CurStep: TUninstallStep);
begin
  if CurStep = usUninstall then
  begin
    KillAppImages();
    RemoveAutostart();
  end;
  if CurStep = usPostUninstall then
  begin
    RegDeleteKeyIncludingSubkeys(HKLM64, LEGACY_UNINSTALL_KEY);
    DelTree(ExpandConstant('{app}'), True, True, True);
  end;
end;