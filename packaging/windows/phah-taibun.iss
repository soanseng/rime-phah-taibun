#define MyAppName "Phah Tai-bun"
#define MyAppPublisher "Phah Tai-bun"
#define MyAppVersion GetEnv("PHAH_TAIBUN_VERSION")
#if MyAppVersion == ""
#define MyAppVersion "0.3.0"
#endif

[Setup]
AppId={{7D1D0D7A-CA7A-4D42-8A7D-2F3E4F6A5E91}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={localappdata}\Phah Tai-bun
DisableProgramGroupPage=yes
OutputBaseFilename=PhahTaiBunSetup
OutputDir=packaging/windows/Output
SourceDir=..\..
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\icons\icon.ico

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Files]
Source: "install_windows.ps1"; DestDir: "{app}"; Flags: ignoreversion
Source: "rime.lua"; DestDir: "{app}"; Flags: ignoreversion
Source: "schema\*"; DestDir: "{app}\schema"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "lua\*"; DestDir: "{app}\lua"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "icons\*"; DestDir: "{app}\icons"; Flags: ignoreversion recursesubdirs createallsubdirs

[Code]
function InitializeSetup(): Boolean;
begin
  MsgBox('拍台文使用小狼毫 Weasel / Rime 作為輸入法核心。安裝程式會保留既有 Rime 方案與自訂詞庫。', mbInformation, MB_OK);
  Result := True;
end;

procedure RunPhahTaiBunInstaller();
var
  ResultCode: Integer;
  PowerShellPath: String;
  Params: String;
begin
  PowerShellPath := ExpandConstant('{sys}\WindowsPowerShell\v1.0\powershell.exe');
  Params := '-NoProfile -ExecutionPolicy Bypass -File "' + ExpandConstant('{app}\install_windows.ps1') +
    '" -ProjectRoot "' + ExpandConstant('{app}') + '"';

  if not Exec(PowerShellPath, Params, ExpandConstant('{app}'), SW_SHOW, ewWaitUntilTerminated, ResultCode) then
  begin
    RaiseException('無法啟動 PowerShell 安裝拍台文：' + SysErrorMessage(ResultCode));
  end;

  if ResultCode <> 0 then
  begin
    RaiseException('拍台文安裝失敗，PowerShell 結束碼：' + IntToStr(ResultCode));
  end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    RunPhahTaiBunInstaller();
  end;
end;
