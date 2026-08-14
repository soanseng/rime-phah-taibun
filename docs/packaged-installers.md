# Windows / macOS 安裝包

拍台文仍使用 Rime 作為輸入法核心，但 Windows 和 macOS 可以用比較接近一般軟體的安裝方式。

## 給一般使用者

到 [GitHub Releases](https://github.com/soanseng/rime-phah-taibun/releases) 下載：

| 系統 | 下載檔案 | 你會看到 |
|------|----------|----------|
| Windows | `PhahTaiBunSetup.exe` | 一般 Windows 安裝精靈 |
| macOS | `PhahTaiBun.pkg` | 一般 macOS 安裝包 |

如果電腦尚未安裝 Rime 核心：

- Windows 需要先安裝小狼毫 Weasel。
- macOS 需要先安裝鼠鬚管 Squirrel。

安裝器會保留既有 Rime 輸入法、自訂詞庫和設定檔。安裝完成後，系統輸入法仍先選小狼毫/鼠鬚管（Windows 圖示【中】、macOS 圖示【ㄓ】），再按 `F4`（或 `` Ctrl+` ``）選「拍台文(台)」。

## 更新拍台文

已有舊版時，到 [GitHub Releases](https://github.com/soanseng/rime-phah-taibun/releases) 下載最新版安裝包，直接執行覆蓋安裝：

- Windows：重新執行 `PhahTaiBunSetup.exe`。
- macOS：重新執行 `PhahTaiBun.pkg`。

更新會保留自訂詞庫、其他 Rime 輸入方案與設定，更新正式的拍台文檔案，並自動重新部署 Rime。若曾直接修改正式的 `phah_taibun` 檔案，請先備份。PowerShell、終端機與 Linux 更新方式見[完整使用說明](user-guide.md#更新拍台文)。

## 給維護者

### Windows

Windows 安裝器使用 Inno Setup：

```powershell
$env:PHAH_TAIBUN_VERSION = "0.3.0"
iscc packaging/windows/phah-taibun.iss
```

產物：`packaging/windows/Output/PhahTaiBunSetup.exe`

### macOS

macOS 安裝包使用 Apple 內建的 `pkgbuild` 和 `productbuild`：

```bash
PHAH_TAIBUN_VERSION=0.3.0 packaging/macos/build-pkg.sh
```

產物：`packaging/macos/build/PhahTaiBun.pkg`

正式發佈前若要降低安全性警告，Windows 需要 code signing，macOS 需要 Developer ID Installer 簽章和 notarization。
