#define MyAppName "寫台文 Siá Tâi-bûn"
#define MyAppPublisher "寫台文開發團隊"
#define MyAppVersion GetEnv("PHAH_TAIBUN_VERSION")
#if MyAppVersion == ""
#define MyAppVersion "0.9.4"
#endif
; Bundled unmodified Weasel (GPL-3.0). CI downloads and SHA-256-verifies it
; into packaging/windows/vendor (release.yml WEASEL_VERSION must match).
#define WeaselVersion "0.17.4"
#define WeaselInstaller "weasel-0.17.4.0-installer.exe"

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
Source: "opencc\*"; DestDir: "{app}\opencc"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "packaging\windows\vendor\{#WeaselInstaller}"; Flags: dontcopy
Source: "packaging\windows\vendor\weasel-LICENSE.txt"; DestDir: "{app}\licenses"; Flags: ignoreversion
Source: "packaging\windows\WEASEL-SOURCE.txt"; DestDir: "{app}\licenses"; Flags: ignoreversion

[Code]
function WeaselInstalled(): Boolean;
begin
  { Weasel's NSIS installer writes HKLM\SOFTWARE\Rime\Weasel (32-bit view). }
  Result := RegKeyExists(HKLM32, 'SOFTWARE\Rime\Weasel');
  if (not Result) and IsWin64 then
    Result := RegKeyExists(HKLM64, 'SOFTWARE\Rime\Weasel');
end;

function InitializeSetup(): Boolean;
var
  WeaselNote: String;
begin
  if WeaselInstalled() then
    WeaselNote := '寫台文使用小狼毫 Weasel / Rime 作為輸入法核心。安裝程式會保留既有 Rime 方案與自訂詞庫。'
  else
    WeaselNote := '這台電腦還沒有小狼毫 Weasel（Rime 輸入法核心），安裝程式會一併安裝小狼毫 {#WeaselVersion}。' + #13#10 +
      '安裝小狼毫需要系統管理員權限，接下來會跳出 Windows 的權限確認視窗，請按「是」。';
  MsgBox(WeaselNote + #13#10 + #13#10 +
    '需要一併安裝嘸蝦米，或選擇保留哪些既有輸入法（含注音），請改用命令列：' + #13#10 +
    'irm https://raw.githubusercontent.com/soanseng/rime-phah-taibun/main/install_windows.ps1 | iex', mbInformation, MB_OK);
  Result := True;
end;

procedure InstallWeaselIfMissing();
var
  ResultCode: Integer;
begin
  if WeaselInstalled() then
    exit;
  ExtractTemporaryFile('{#WeaselInstaller}');
  { /S = silent (installs, then runs WeaselDeployer /deploy); /T = 繁體中文.
    runas elevates only this child: the 寫台文 payload stays per-user. }
  if not ShellExec('runas', ExpandConstant('{tmp}\{#WeaselInstaller}'), '/S /T', '',
                   SW_HIDE, ewWaitUntilTerminated, ResultCode) then
  begin
    if ResultCode = 1223 then
      RaiseException('需要系統管理員權限才能安裝小狼毫。請重新執行安裝程式，並在權限確認視窗按「是」。');
    RaiseException('無法啟動小狼毫安裝程式：' + SysErrorMessage(ResultCode));
  end;
  if not WeaselInstalled() then
    RaiseException('小狼毫安裝失敗（代碼 ' + IntToStr(ResultCode) + '）。' + #13#10 +
      '可改從 https://github.com/rime/weasel/releases 手動安裝小狼毫，再重新執行本程式。');
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
    避免把可能含引號的使用者名稱塞進命令字串。
    視窗隱藏，所以輸出另存 install.log，失敗時告訴使用者去哪裡看。 }
  Params := '-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -Command "' +
    '$app = Join-Path $env:LOCALAPPDATA ''Phah Tai-bun''; ' +
    '$env:PHAH_TAIBUN_PROJECT_ROOT = $app; ' +
    '$env:PHAH_TAIBUN_SCHEMAS = ''phah''; ' +
    'Start-Transcript -Path (Join-Path $app ''install.log'') -Force | Out-Null; ' +
    'try { iex ([System.IO.File]::ReadAllText((Join-Path $app ''install_windows.ps1''), [System.Text.Encoding]::UTF8)) } ' +
    'finally { Stop-Transcript | Out-Null }"';

  if not Exec(PowerShellPath, Params, ExpandConstant('{app}'), SW_HIDE, ewWaitUntilTerminated, ResultCode) then
  begin
    RaiseException('無法啟動 PowerShell 安裝寫台文：' + SysErrorMessage(ResultCode));
  end;

  if ResultCode <> 0 then
  begin
    RaiseException('寫台文安裝失敗，PowerShell 結束碼：' + IntToStr(ResultCode) + #13#10 +
      '詳細記錄：' + ExpandConstant('{app}\install.log'));
  end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    InstallWeaselIfMissing();
    RunPhahTaiBunInstaller();
  end;
end;
