# Windows 安裝包

拍台文仍使用 Rime 作為輸入法核心。Windows 可以用雙擊安裝包；macOS 與 Linux 用指令或複製檔案，不提供 `.pkg`（無法在本專案驗證 Gatekeeper／notarize）。

## 給一般使用者

到 [GitHub Releases](https://github.com/soanseng/rime-phah-taibun/releases) 下載：

| 系統 | 方式 |
|------|------|
| Windows | `PhahTaiBunSetup.exe`，或 PowerShell：`irm https://raw.githubusercontent.com/soanseng/rime-phah-taibun/main/install_windows.ps1 \| iex` |
| macOS | 先裝鼠鬚管，再 `curl -fsSL https://raw.githubusercontent.com/soanseng/rime-phah-taibun/main/scripts/install_macos.sh \| bash`。也可 `git clone` 後執行 `./install.sh`，或把 `schema/`、`lua/`、`rime.lua` 複製到 `~/Library/Rime/` 後重新部署。見[完整使用說明](user-guide.md#進階使用者指令安裝)。 |
| Linux | `git clone` 後 `./install.sh` |

Windows 的 PowerShell 指令安裝是互動式的：可選裝拍台文、嘸蝦米（`rime-liur`）或兩者；改寫 `default.custom.yaml` 前會先做時間戳備份，並詢問要保留哪些既有輸入法（可保留注音 `bopomofo`）。`PhahTaiBunSetup.exe` 走非互動模式，只安裝拍台文。

Windows 尚未安裝小狼毫時，安裝器會提示先裝 Weasel。macOS 請先裝[鼠鬚管 Squirrel](https://github.com/rime/squirrel/releases)。

Windows 安裝器會保留既有 Rime 輸入法、自訂詞庫和設定檔。安裝完成後，系統輸入法仍先選小狼毫（圖示【中】），再按 `F4`（或 `` Ctrl+` ``）選「拍台文(台)」；熟台羅的使用者可改選「拍台文(Telex)」。

## 更新拍台文

- Windows：重新執行 `PhahTaiBunSetup.exe`，或重跑 PowerShell 指令。
- macOS：重跑 `curl .../scripts/install_macos.sh | bash`，或在 clone 裡 `git pull --ff-only && ./install.sh`。
- Linux：在既有 clone 執行 `git pull --ff-only && ./install.sh`。

更新會保留自訂詞庫、其他 Rime 輸入方案與設定。若曾直接修改正式的 `phah_taibun` 檔案，請先備份。詳見[完整使用說明](user-guide.md#更新拍台文)。

Android 沒有安裝包。同一套 Rime 方案可手動放進同文（Trime）或 fcitx5-android 的 Rime 外掛，見[Android 部署](android.md)。

## 給維護者

### Windows

Windows 安裝器使用 Inno Setup：

```powershell
$env:PHAH_TAIBUN_VERSION = "0.6.2"
iscc packaging/windows/phah-taibun.iss
```

產物：`packaging/windows/Output/PhahTaiBunSetup.exe`

正式發佈前若要降低安全性警告，Windows 需要 code signing。macOS `.pkg` 不再隨 release 發佈。
