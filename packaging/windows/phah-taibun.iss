#define MyAppName "Phah Tai-bun"
#define MyAppPublisher "Phah Tai-bun"
#define MyAppVersion GetEnv("PHAH_TAIBUN_VERSION")
#if MyAppVersion == ""
#define MyAppVersion "0.9.0"
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
  MsgBox('拍台文使用小狼毫 Weasel / Rime 作為輸入法核心。安裝程式會保留既有 Rime 方案與自訂詞庫。' + #13#10 + #13#10 +
    '需要一併安裝嘸蝦米，或選擇保留哪些既有輸入法（含注音），請改用命令列：' + #13#10 +
    'irm https://raw.githubusercontent.com/soanseng/rime-phah-taibun/main/install_windows.ps1 | iex', mbInformation, MB_OK);
  Result := True;
end;

procedure RunPhahTaiBunInstaller();
var
  ResultCode: Integer;
  PowerShellPath: String;
  Params: String;
begin
  PowerShellPath := ExpandConstant('{sys}\WindowsPowerShell\v1.0\powershell.exe');
  { install_windows.ps1 不含 BOM，PowerShell 5.1 以 -File 讀取會用 ANSI 解碼；
    改以 ReadAllText(UTF8) 讀進來再 iex，與單行安裝 (irm | iex) 走同一條解析路徑。
    參數用環境變數傳（iex 沒有參數綁定）；路徑由 $env:LOCALAPPDATA 組合，
    避免把可能含引號的使用者名稱塞進命令字串。 }
  Params := '-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -Command "' +
    '$app = Join-Path $env:LOCALAPPDATA ''Phah Tai-bun''; ' +
    '$env:PHAH_TAIBUN_PROJECT_ROOT = $app; ' +
    '$env:PHAH_TAIBUN_SCHEMAS = ''phah''; ' +
    'iex ([System.IO.File]::ReadAllText((Join-Path $app ''install_windows.ps1''), [System.Text.Encoding]::UTF8))"';

  if not Exec(PowerShellPath, Params, ExpandConstant('{app}'), SW_HIDE, ewWaitUntilTerminated, ResultCode) then
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
