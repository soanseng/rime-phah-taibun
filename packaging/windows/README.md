# Windows 安裝器

這個目錄提供給發佈者使用，目標是產生一般使用者可雙擊的 `PhahTaiBunSetup.exe`。

## 使用方式

1. 在 Windows 安裝 [Inno Setup](https://jrsoftware.org/isinfo.php)。
2. 從 repo 根目錄執行：

   ```powershell
   $env:PHAH_TAIBUN_VERSION = "0.5.0"
   iscc packaging/windows/phah-taibun.iss
   ```

3. 產物會在 `packaging/windows/Output/PhahTaiBunSetup.exe`。

## 使用者體驗

- 使用者下載 `.exe` 後雙擊安裝。
- 安裝器本身安裝到使用者的 LocalAppData，不要求系統管理員權限。
- 安裝器會呼叫既有 `install_windows.ps1 -ProjectRoot`，使用安裝包內建的 schema、Lua、icon 檔案。
- 仍使用小狼毫 Weasel / Rime 作為輸入法核心。
- 若使用者尚未安裝 Weasel，PowerShell 腳本會顯示下載連結與下一步。
- 安裝過程會保留 `phah_taibun.custom.dict.yaml`、`phah_taibun.phrase.dict.yaml`，不會覆蓋使用者自訂詞庫。
- 既有 `rime.lua` 和 `default.custom.yaml` 會先備份再合併拍台文設定。

## 目前限制

- 未簽章的 `.exe` 可能觸發 Windows SmartScreen。
- 系統輸入法清單仍會顯示小狼毫；進入小狼毫後選「拍台文(台)」。
- 這不是品牌版 Weasel fork。
