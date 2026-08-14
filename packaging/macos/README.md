# macOS 安裝包

這個目錄提供給發佈者使用，目標是產生一般使用者可雙擊的 `PhahTaiBun.pkg`。

## 使用方式

在 macOS 從 repo 根目錄執行：

```bash
PHAH_TAIBUN_VERSION=0.3.1 packaging/macos/build-pkg.sh
```

產物會在 `packaging/macos/build/PhahTaiBun.pkg`。

## 使用者體驗

- 使用者下載 `.pkg` 後雙擊安裝。
- 安裝包會檢查鼠鬚管 Squirrel 是否存在。
- 安裝包會把拍台文 payload 暫存到 `/Library/Application Support/PhahTaiBun`，再以目前登入使用者身分呼叫既有 `scripts/install_macos.sh --project-root`。
- 仍使用鼠鬚管 Squirrel / Rime 作為輸入法核心。
- 安裝過程會保留 `phah_taibun.custom.dict.yaml`、`phah_taibun.phrase.dict.yaml`，不會覆蓋使用者自訂詞庫。
- 既有 `rime.lua` 和 `default.custom.yaml` 會先備份再合併拍台文設定。

## 目前限制

- 未簽章、未 notarize 的 `.pkg` 可能被 Gatekeeper 擋下。
- 系統輸入法清單仍會顯示鼠鬚管；進入鼠鬚管後選「拍台文(台)」。
- 這不是品牌版 Squirrel fork。

## 簽章方向

正式發佈若要降低 Gatekeeper 警告，需使用 Apple Developer Program 的 `Developer ID Installer` 憑證簽署安裝包，再走 notarization 流程。
