# 寫台文瀏覽器擴充功能 — 商店上架資料（Chrome Web Store ＋ Firefox AMO）

擴充功能原始碼 `extension/`，打包 `uv run python scripts/build_extension.py` →
`dist/extension/phah-taibun-chrome-<ver>.zip`、`dist/extension/phah-taibun-firefox-<ver>.zip`。

## 名稱

- **zh-Hant**：寫台文 Siá Tâi-bûn 輸入法
- **en**：Siá Tâi-bûn — Taiwanese Hokkien Input Method

## 簡短說明（商店列表一句話，<100 字）

- **zh-Hant**：在任何網頁輸入框直接拍台文。漢羅／全羅輸出、TL 台羅／POJ 白話字拼音、Telex 調鍵，攏會使換。
- **en**: Type Taiwanese Hokkien directly in any web page text field. Han-roman / full romanization output, Tâi-lô / POJ spelling, Telex tones.

## 完整說明（商店列表長文）

**zh-Hant**

拍台文毋免安裝軟體——裝這个擴充功能，佇 Google、Facebook、Gmail、YouTube 評論……逐所在ê輸入框就直接拍台文。

- **模糊拼音輸入**：TL（台羅）抑是 POJ（白話字）攏使直接拍，聲調未拍嘛會使
- **漢羅／全羅輸出**：預設漢羅（漢字＋羅馬字），一鍵切做全羅
- **Telex 方案**：慣習 VietTeX 調鍵（a7→á）嘛有
- **候選看拼音**：逐个候選攏附讀音註解，會曉講袂曉寫嘛免驚
- **教育部 700 推薦用字**＋ LKK 台文基金會用字規範

快捷鍵 Ctrl+Shift+Space（會使改）開關輸入；工具列圖示會使設方案佮輸出模式。

全部運算攏在你家己的電腦頂——無網路連線、無資料收集。

**en**

Write Taiwanese Hokkien (Tâi-bûn) directly in any text field on the web — search boxes, comments, email, forums.

- Fuzzy romanization input: type in Tâi-lô (TL) or Pe̍h-ōe-jī (POJ), tones optional
- Han-roman (mixed) or full-romanization output, switchable
- Optional Telex-style tone keys (a7 → á)
- Every candidate shows its romanization
- Based on Taiwan MOE's 700 recommended characters and LKK foundation conventions

Toggle with Ctrl+Shift+Space (rebindable). All processing is local — no network requests, no data collection.

## 截圖指引

1. 1920×1080，深色抑是淺色主題，至少 2 張（1280×800 以上）：
   - 設置頁（popup）：啟用開關＋方案／輸出／拼音下拉
   - 實拍：Google 搜尋框拍 `goasitaioanlang`，候選框反白「我是台灣人」（游標邊）
   - 實拍：textarea 拍 `chiahpng`＋空白鍵了「食飯」入框，逗號變全形「，」
2. 圖示縮圖 440×280：icon-128.png 放大。

## 權限說明（審核用）

|權限|理由|
|---|---|
|`<all_urls>`（content script，Chrome MV3 `host_permissions` 免——manifest 用 content_scripts matches）|輸入法愛佇使用者拍字ê任何一个輸入框攔鍵、顯示候選。無這个，使用者就無法度佇逐所在拍台文。擴充功能干焦佇「啟用」時才處理按鍵，無看無改頁面其他內容。|
|`storage`|記啟用狀態佮方案／輸出設定（storage.local，無上傳）|
|`offscreen`（干焦 Chrome）|wasm 輸入引擎（My RIME）愛佇 Web Worker 佮 IndexedDB 裡走，MV3 service worker 無法度長時間維持|

## 隱私聲明（商店「資料使用」聲明用）

- 無網路請求（引擎、字典攏包佇擴充功能內；`worker.js` 內底一个 jsdelivr URL 是 My RIME 上游內建方案的路徑，本包固定方案、永遠毋會去揣）
- 無收集、無上傳任何資料；無 analytics、無 tracker
- 使用者辭典（揀過ê字）佮設定攏存佇本機（extension IndexedDB／storage.local）
- 輸入ê鍵干焦佇啟用時處理，用來產生候選；無記錄

## 授權

- 擴充功能程式碼（`extension/`）：MIT（同 repo LICENSE）
- `rime.js`／`rime.wasm`／`rime.data`／`worker.js`：**GPL-3.0**，未修改的
  [My RIME](https://github.com/LibreService/my_rime) 0.10.9 build（隨包附 `LICENSE-my-rime.txt`）。
  → 兩个商店攏愛佇「開源」欄位標 GPL-3.0-only／or-later 並附 source 連結（下節）。
- `pack/`（方案、字典、Lua、規則）：由本 repo 管線產生；來源授權對照表見 repo `LICENSE`
  （教典 CC BY-ND 3.0、iCorpus CC BY 4.0 等；**含 NC 來源 → 擴充功能免費、非商業**）。

## AMO 審核：原始碼說明（Original Sources）

> `rime.js`、`worker.js` 是 minified／build 產物，來源：

1. 引擎：https://github.com/LibreService/my_rime （GPL-3.0，tag 0.10.9）
   - build 指令照 upstream `web/`：emcc 編譯 librime＋librime-lua → `dist/`（rime.js、rime.wasm、rime.data、worker.js）。本擴充功能未修改內容，原封複製。
2. 方案／詞庫／Lua（`pack/`）：https://github.com/soanseng/rime-phah-taibun
   - 重製指令（貼佇 AMO「Original Sources」）：
   ```bash
   git clone https://github.com/soanseng/rime-phah-taibun && cd rime-phah-taibun
   uv sync
   chmod +x scripts/download_resources.sh && ./scripts/download_resources.sh  # 下載外部資料（gitignored）
   uv run python scripts/build_all.py            # 語料→字典→規則
   uv run python scripts/build_web_playground.py # 產生 docs/try/（引擎＋pack）
   uv run python scripts/build_extension.py      # 產生 dist/extension/*.zip
   ```
   - 提交審核的 zip = `phah-taibun-firefox-<ver>.zip`。
   - **每次送審必填**：zip 對應的來源 commit hash —— 送審前佇 repo 跑 `git rev-parse HEAD`，
     共 hash 抄佇 AMO 表單（例：`a1b2c3d…`）。無這項，審核員無法度對來源。

## 上架步驟摘要

### Chrome Web Store（一次性 US$5 開發者費）
1. https://chrome.google.com/webstore/devconsole → New item → 上傳 `phah-taibun-chrome-<ver>.zip`
2. 類別 Productivity；語言 Chinese (Traditional)；GPL-3.0-only
3. 貼說明文、傳截圖／縮圖
4. Privacy：勾「不收集資料」；single purpose：輸入法；`<all_urls>` 理由抄頂表格
5. Submit for review

### Firefox AMO（https://addons.mozilla.org/developers/）
1. Submit a New Add-on → 上傳 `phah-taibun-firefox-<ver>.zip`（已含 gecko id `phah-taibun@taigi.anatomind.com`）
2. 「Original Sources」填頂節說明（GPL 引擎連結＋本 repo build 指令＋zip 對應的 commit）
3. Data collection：none
4. Self-distribution 抑是 Listed 由你揀（Listed 才會出佇搜尋）

> **MV2 說明**：Firefox 包用 MV2 persistent background page——MV3 event page 歇睏會刣掉
> wasm Worker，拍字拍一半愛閣重新部署字典。若 AMO 審核毋接受 MV2，改
> `extension/manifest.firefox.json` 做 MV3（`background.scripts`，程式免改）閣重打包。

## 已知限制（說明頁會使提）

- Google Docs、Monaco／CodeMirror 6 這款家己 canvas 畫編輯器的欄位未支援（無實體 text node 予 `insertText`）——請用網頁試拍 https://taigi.anatomind.com/try/
- Firefox 上架前本機試：`about:debugging#/runtime/this-firefox` → Load Temporary Add-on → `dist/extension/firefox/manifest.json`
