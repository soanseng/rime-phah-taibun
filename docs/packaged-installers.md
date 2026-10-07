# Windows 安裝包

拍台文仍使用 Rime 作為輸入法核心。Windows 可以用雙擊安裝包；macOS 與 Linux 用指令或複製檔案，不提供 `.pkg`（無法在本專案驗證 Gatekeeper／notarize）。

## 給一般使用者

到 [GitHub Releases](https://github.com/soanseng/rime-phah-taibun/releases) 下載：

| 系統 | 方式 |
|------|------|
| Windows | `PhahTaiBunSetup.exe`，或 PowerShell：`irm https://raw.githubusercontent.com/soanseng/rime-phah-taibun/main/install_windows.ps1 \| iex` |
| macOS（best-effort，維護者未實機測試） | 先裝鼠鬚管，再 `curl -fsSL https://raw.githubusercontent.com/soanseng/rime-phah-taibun/main/scripts/install_macos.sh \| bash`。也可 `git clone` 後執行 `./install.sh`，或把 `schema/`、`lua/`、`rime.lua` 複製到 `~/Library/Rime/` 後重新部署。見[完整使用說明](user-guide.md#進階使用者指令安裝)。 |
| Linux | `git clone` 後 `./install.sh` |
| Android | 從 Releases 下載 `PhahTaiBun-Trime.zip`（拍台文＋注音）或 `PhahTaiBun-Trime-liur.zip`（再加嘸蝦米），解壓到同文 Trime 或小企鵝 RIME 外掛的 Rime 使用者資料夾後重新部署。**同文要先自己裝**（F-Droid 或它自己的 Releases），見[Android 部署](android.md)。 |

Windows 的 PowerShell 指令安裝是互動式的：可選裝拍台文、嘸蝦米（`rime-liur`）或兩者；改寫 `default.custom.yaml` 前會先做時間戳備份，並詢問要保留哪些既有輸入法（可保留注音 `bopomofo`）。`PhahTaiBunSetup.exe` 走非互動模式，只安裝拍台文。

`PhahTaiBunSetup.exe` 內附小狼毫 Weasel 0.17.4（未修改，GPL-3.0，原始碼 <https://github.com/rime/weasel/tree/0.17.4>）：電腦上還沒有小狼毫時，安裝包會跳一次系統管理員權限確認，自動安裝繁體版小狼毫，再裝拍台文。PowerShell 單行指令則仍需先自行安裝小狼毫。安裝失敗時，詳細記錄在 `%LOCALAPPDATA%\Phah Tai-bun\install.log`。macOS 請先裝[鼠鬚管 Squirrel](https://github.com/rime/squirrel/releases)。

Windows 安裝器會保留既有 Rime 輸入法、自訂詞庫和設定檔。安裝完成後，系統輸入法仍先選小狼毫（圖示【中】），再按 `F4`（或 `` Ctrl+` ``）選「拍台文(台)」；熟台羅的使用者可改選「拍台文(Telex)」。

## 更新拍台文

- Windows：重新執行 `PhahTaiBunSetup.exe`，或重跑 PowerShell 指令。
- macOS：重跑 `curl .../scripts/install_macos.sh | bash`，或在 clone 裡 `git pull --ff-only && ./install.sh`。
- Linux：在既有 clone 執行 `git pull --ff-only && ./install.sh`。

更新會保留自訂詞庫、其他 Rime 輸入方案與設定。若曾直接修改正式的 `phah_taibun` 檔案，請先備份。詳見[完整使用說明](user-guide.md#更新拍台文)。

Android 用一鍵包，**兩種自己選**：`PhahTaiBun-Trime.zip`（拍台文＋注音，含 `~` 反查依賴）或 `PhahTaiBun-Trime-liur.zip`（再加嘸蝦米，包內附 `LIUR-PROVENANCE.txt` 來源標示）——解壓到同文（Trime）或 fcitx5-android 的 Rime 使用者資料夾後重新部署，見[Android 部署](android.md)。

## 給維護者

### Windows

Windows 安裝器使用 Inno Setup：

```powershell
$env:PHAH_TAIBUN_VERSION = "0.9.4"
iscc packaging/windows/phah-taibun.iss
```

產物：`packaging/windows/Output/PhahTaiBunSetup.exe`。本機建置前，先把 `weasel-0.17.4.0-installer.exe`（核對 SHA-256 `cf509534…5c29`）與 `weasel-LICENSE.txt` 放進 `packaging/windows/vendor/`（git 忽略）；CI（`release.yml` 的 `package-windows`）會自動下載並驗證。升級小狼毫時，`release.yml` 的 `WEASEL_VERSION`／`WEASEL_SHA256` 與 `.iss` 的 `WeaselVersion`／`WeaselInstaller` 要一起改，`tests/test_packaging.py` 會檢查兩邊一致。

正式發佈前若要降低安全性警告，Windows 需要 code signing。macOS `.pkg` 不再隨 release 發佈。

### Android（Trime 一鍵包）

```bash
uv run python scripts/build_trime_package.py              # 產物：dist/PhahTaiBun-Trime.zip
uv run python scripts/build_trime_package.py --with-liur  # 產物：dist/PhahTaiBun-Trime-liur.zip（隨 release 並行發佈）
```

需要本機 `rime-liur-arch` checkout（預設 `~/projects/rime-liur-arch`，可用 `--liur-dir` 或 `PHAH_TAIBUN_LIUR_DIR` 覆寫）與系統 rime 共享資料夾（`/usr/share/rime-data`，提供 `terra_pinyin.dict.yaml` 與 bopomofo 反查檔）。同一份輸入重複建包會得到位元組相同的 zip；`tests/test_android_package.py` 會用真 librime 部署整份 overlay 驗證。

## 驗證下載（0.7.0 起）

每個 Release 附 `SHA256SUMS`（涵蓋 `PhahTaiBunSetup.exe`、`PhahTaiBun-source.zip`、`PhahTaiBun-Trime.zip` 與 `PhahTaiBun-Trime-liur.zip`），發佈時 CI 會以匿名下載自動核對一次。自行核對方式：

```bash
# Linux / macOS（在下載目錄）
sha256sum -c SHA256SUMS        # macOS 改用：shasum -a 256 -c SHA256SUMS
```

```powershell
# Windows PowerShell
Get-FileHash PhahTaiBunSetup.exe -Algorithm SHA256
# 再與 SHA256SUMS 內對應行比對
```
