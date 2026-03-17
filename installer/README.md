# 拍台文 Bundle Installer 打包指南

本目錄包含 Windows (.exe) 和 macOS (.pkg) 的一鍵安裝打包工具。

## 架構

```
installer/
├── windows/
│   ├── phah_taibun.iss         # Inno Setup 主腳本
│   ├── download_weasel.ps1     # 下載小狼毫 Weasel
│   ├── pre_uninstall.ps1       # 解除安裝清理
│   └── build/                  # 建構產物（gitignore）
│       ├── weasel-installer.exe
│       └── Iansui-Regular.ttf
├── macos/
│   ├── build_pkg.sh            # 打包 .pkg 腳本
│   ├── distribution.xml        # macOS installer 設定
│   ├── scripts/
│   │   ├── preinstall          # 檢查鼠鬚管
│   │   └── postinstall         # 委派給 install_macos.sh
│   └── build/                  # 建構產物（gitignore）
└── README.md                   # 本檔案
```

**核心設計：** Installer 將檔案 staging 到標準專案結構（`schema/`, `lua/`, `rime.lua`），
然後呼叫現有的 `scripts/install_*.ps1|sh --project-root` 完成所有實際安裝工作。
不重複實作安裝邏輯。

## Windows 本地打包

**需求：** [Inno Setup 6+](https://jrsoftware.org/isinfo.php)、PowerShell

```powershell
# 1. 下載 Weasel
cd installer/windows
mkdir build
pwsh download_weasel.ps1 -OutputDir build

# 2. 下載芫荽字體
Invoke-WebRequest "https://github.com/ChhoeTaigi/iansui/releases/latest/download/Iansui-Regular.ttf" `
    -OutFile "build/Iansui-Regular.ttf"

# 3. 用 Inno Setup 編譯
iscc phah_taibun.iss
# 產出：Output/phah-taibun-setup-1.0.0.exe
```

## macOS 本地打包

**需求：** macOS + Xcode Command Line Tools（`pkgbuild`, `productbuild`）

```bash
cd installer/macos
bash build_pkg.sh 1.0.0
# 產出：build/phah-taibun-1.0.0.pkg
```

字體會自動從 GitHub 下載。

## CI 自動打包

GitHub Actions 在 push tag 時自動觸發：

```bash
git tag v1.0.0
git push origin v1.0.0
# → GitHub Actions 自動打包 Windows + macOS
# → 建立 Draft Release 附帶 .exe 和 .pkg
```

也可手動觸發：Actions → Build Installers → Run workflow → 輸入版本號

## 更新版本

1. 修改 `installer/windows/phah_taibun.iss` 中的 `MyAppVersion`
2. 修改 `installer/macos/distribution.xml` 中的 `version`
3. 更新 `.github/workflows/release.yml` 中的 `WEASEL_VERSION` / `IANSUI_VERSION`（如需升級上游依賴）
4. **首次使用前**：填入 `release.yml` 中的 `TODO_FILL_IN_SHA256_HASH`
5. Push tag 觸發 CI

## Linux

Linux 使用者直接執行 `./install.sh` 即可，不需要 bundle installer。
