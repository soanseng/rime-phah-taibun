; phah_taibun.iss — Inno Setup script for 拍台文輸入法
; Builds a single .exe installer bundling Weasel + phah_taibun schema
;
; Architecture: Inno Setup stages files under {app}/ in standard project layout.
; The existing install_windows.ps1 is invoked with -ProjectRoot "{app}" to handle
; all file operations to the Rime user directory. This avoids duplicating logic.

#define MyAppName "拍台文輸入法 Phah Tai-bun"
#define MyAppVersion "0.1.0"
#define MyAppPublisher "Phah Tai-bun Project"
#define MyAppURL "https://github.com/soanseng/rime-phah-taibun"

[Setup]
AppId={{2A6691AC-0D3E-42AE-A463-91753AEAC832}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
DefaultDirName={autopf}\PhahTaibun
DefaultGroupName={#MyAppName}
OutputBaseFilename=phah-taibun-setup-{#MyAppVersion}
SetupIconFile=..\..\icons\icon.ico
UninstallDisplayIcon={app}\icon.ico
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
; Weasel needs admin; schema install is user-space but we need admin for Weasel
PrivilegesRequired=admin
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesInstallIn64BitMode=x64compatible
LicenseFile=..\..\LICENSE

[Languages]
Name: "tchinese"; MessagesFile: "compiler:Languages\Unofficial\ChineseTraditional.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Files]
; --- Weasel installer (bundled, extracted to temp) ---
Source: "build\weasel-installer.exe"; DestDir: "{tmp}"; Flags: deleteafterinstall; Check: not IsWeaselInstalled

; --- Stage schema files under {app}/schema/ (standard project layout) ---
; install_windows.ps1 will copy these to %APPDATA%\Rime via -ProjectRoot
Source: "..\..\schema\phah_taibun.schema.yaml"; DestDir: "{app}\schema"; Flags: ignoreversion
Source: "..\..\schema\phah_taibun.dict.yaml"; DestDir: "{app}\schema"; Flags: ignoreversion
Source: "..\..\schema\phah_taibun.phrase.dict.yaml"; DestDir: "{app}\schema"; Flags: ignoreversion skipifsourcedoesntexist
Source: "..\..\schema\phah_taibun.custom.dict.yaml"; DestDir: "{app}\schema"; Flags: ignoreversion skipifsourcedoesntexist
Source: "..\..\schema\phah_taibun_reverse.dict.yaml"; DestDir: "{app}\schema"; Flags: ignoreversion
Source: "..\..\schema\hanlo_rules.yaml"; DestDir: "{app}\schema"; Flags: ignoreversion
Source: "..\..\schema\lighttone_rules.json"; DestDir: "{app}\schema"; Flags: ignoreversion
Source: "..\..\schema\hoabun_map.txt"; DestDir: "{app}\schema"; Flags: ignoreversion
Source: "..\..\schema\default.custom.yaml"; DestDir: "{app}\schema"; Flags: ignoreversion

; --- Stage Lua modules under {app}/lua/ ---
Source: "..\..\lua\phah_taibun_*.lua"; DestDir: "{app}\lua"; Flags: ignoreversion

; --- Module registration file at {app}/rime.lua ---
Source: "..\..\rime.lua"; DestDir: "{app}"; Flags: ignoreversion

; --- Icon ---
Source: "..\..\icons\icon.ico"; DestDir: "{app}"; Flags: ignoreversion

; --- Font (installed directly to user fonts, not staged) ---
Source: "build\Iansui-Regular.ttf"; DestDir: "{autofonts}"; FontInstall: "Iansui"; Flags: onlyifdoesntexist uninsneveruninstall

; --- Install + uninstall scripts ---
Source: "..\..\scripts\install_windows.ps1"; DestDir: "{app}\scripts"; Flags: ignoreversion
Source: "pre_uninstall.ps1"; DestDir: "{app}\scripts"; Flags: ignoreversion

[Run]
; Install Weasel if not present (runs with admin via UAC)
Filename: "{tmp}\weasel-installer.exe"; Parameters: "/S"; StatusMsg: "安裝小狼毫 Rime 引擎..."; Check: not IsWeaselInstalled; Flags: waituntilterminated shellexec

; Verify Weasel is installed before proceeding (handles UAC denial)
; This check is done in [Code] CurStepChanged(ssPostInstall)

; Delegate ALL file operations to existing install script
; -ProjectRoot points to {app} where files are staged in standard layout
Filename: "powershell.exe"; Parameters: "-ExecutionPolicy Bypass -File ""{app}\scripts\install_windows.ps1"" -ProjectRoot ""{app}"""; StatusMsg: "設定拍台文輸入法..."; Flags: runhidden waituntilterminated; Check: IsWeaselInstalled

[UninstallRun]
Filename: "powershell.exe"; Parameters: "-ExecutionPolicy Bypass -File ""{app}\scripts\pre_uninstall.ps1"""; Flags: runhidden waituntilterminated

[Code]
function IsWeaselInstalled: Boolean;
var
  path: String;
begin
  Result := RegQueryStringValue(HKLM, 'SOFTWARE\Rime\Weasel', 'WeaselRoot', path)
    or DirExists(ExpandConstant('{autopf}\Rime'))
    or DirExists(ExpandConstant('{autopf32}\Rime'));
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    { Verify Weasel is actually installed after the Weasel installer step }
    if not IsWeaselInstalled then
    begin
      MsgBox('小狼毫 (Weasel) 安裝失敗或已取消。' + #13#10 +
             '拍台文輸入法需要小狼毫 Rime 引擎才能運作。' + #13#10 + #13#10 +
             '請手動安裝小狼毫後，重新執行本安裝程式：' + #13#10 +
             'https://rime.im/download/',
             mbError, MB_OK);
      WizardForm.Close;
    end;
  end;
end;
