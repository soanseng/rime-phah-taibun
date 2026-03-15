# roadmap.md — 拍台文 Phah Tâi-bûn 開發路線圖

## 功能評估與分階段規劃

### 評估標準

每項功能以三個維度評分（1-5）：

- **使用者價值 (V)**：對「會講不太會打」的目標使用者有多重要
- **技術複雜度 (C)**：實作難度與工時
- **依賴風險 (R)**：是否依賴尚未取得的資料或第三方元件

**優先度 = V × 2 - C - R**（越高越優先）

---

## Phase 1：可用的 MVP（目標：2-3 週）— 完成 ✅

> 讓使用者能裝起來、打得出台語、看得到拼音。
> **進度**：Week 1-3 全部完成，實機驗證通過（2026-03-15）

### ✅ 收入 Phase 1

| 功能 | V | C | R | 優先度 | 說明 |
|------|---|---|---|--------|------|
| ChhoeTaigi → Rime 字典轉換 | 5 | 3 | 1 | 6 | **基礎建設**，沒有字典一切免談。用意傳 `tai5-uan5_gian5-gi2_kang1-ku7` 做音標轉換 |
| 啟發式詞頻權重 | 4 | 2 | 1 | 5 | 分層權重。參考意傳 `khin1siann1-hun1sik4` 的分詞邏輯做前處理 |
| POJ/TL 雙系統 speller algebra | 5 | 2 | 0 | 8 | **核心差異化**。約 15 條 derive 規則 |
| 候選區拼音註解 (comment) | 5 | 2 | 0 | 8 | Lua filter 在 comment 附加 TL/POJ 讀音 |
| 華語反查（注音/拼音→台語）| 4 | 2 | 0 | 6 | 用 Rime `reverse_lookup` + g0v/moedict-data-twblg 資料 |
| 漢羅混寫輸出 | 5 | 3 | 2 | 5 | **核心差異化**。LKK 用字表 + 意傳 `rime_taigi_poj_hanlo` 邏輯交叉參考 |
| 輸出模式切換（漢羅/全羅）| 4 | 3 | 0 | 5 | Lua filter 依 switch 狀態決定輸出 |
| 查台語讀音 `Ctrl+'` | 4 | 2 | 0 | 6 | **移植 rime-liur 查碼模式**，改查表為台語讀音表。學習者殺手功能 |
| 萬用查字 `?` | 4 | 2 | 0 | 6 | **移植 rime-liur 萬用字元**。拼音不確定時用 `?` 代替，初學者友善 |
| 台語符號選單 `` ` `` | 3 | 1 | 0 | 5 | **移植 rime-liur 符號清單**，替換為台羅調號/方音符號/輕聲符 |
| 按鍵說明 `,,h` | 3 | 1 | 0 | 5 | **移植 rime-liur**，幾乎直接複製改文字 |
| 台語日期 `,,jit` | 2 | 1 | 0 | 3 | **移植 rime-liur 日期模組**，改為拜一～拜日格式。工時極低所以收入 |
| 基本 schema + 安裝腳本 | 5 | 2 | 0 | 8 | schema.yaml + install.sh |

### ❌ 不收入 Phase 1 的原因

| 功能 | V | C | R | 優先度 | 不收入原因 |
|------|---|---|---|--------|-----------|
| IVS 標音輸出 | 3 | 4 | 3 | -1 | 依賴字咍字型 IVS 對照表提取、使用者和接收端都需安裝字體 |
| HTML ruby 輸出 | 2 | 2 | 0 | 2 | 小眾需求，Phase 2 |
| 造詞模式 `;` | 3 | 3 | 0 | 3 | **移植 rime-liur 造詞模組，但需改寫為拼音流程**。Phase 1 先用 custom_phrase 手動加詞 |
| 同音字/文白讀切換 `'` | 3 | 3 | 1 | 2 | **移植 rime-liur 同音模組，但需額外文白讀標記資料**。Phase 2 |
| 簡拼提示 `,,sp` | 2 | 3 | 0 | 1 | **移植 rime-liur 快打模式**，但使用者尚在學完整拼音階段 |
| 學習模式 `,,learn` | 3 | 4 | 0 | 2 | 需特殊候選延遲機制，Rime 原生不太支援 |
| 楊允言詞頻精確化 | 3 | 2 | 3 | 1 | 依賴尚未取得的 yaml。Phase 1 啟發式權重已堪用 |

---

## Phase 2：功能完善（Phase 1 上線後 1-2 個月）

> 使用者回饋驅動，精進輸入體驗。

| 功能 | 狀態 | 說明 |
|------|------|------|
| LKK 漢羅規則 → Lua filter | ✅ 已整合 | hanlo_rules.yaml 893 條 → `phah_taibun_data.lua` 查表 → `phah_taibun_filter.lua` 漢羅轉換 |
| Ungian/iCorpus 詞頻 → dict 權重 | ✅ 已整合 | 93K+57K 詞頻經 `--corpus-freq` 進入 `compute_weights()`，如 食飯 960→1446 |
| KipSutian 反查字典 | ✅ 已整合 | `build_all.py` 優先使用 KipSutian 27K（含解說），MOE 為 fallback |
| 輕聲規則 → build pipeline | ✅ 已整合 | `lighttone_rules.json` 111 條，隨 install 部署到 Rime |
| 查讀音 TL+POJ 雙標註 | ✅ 已實作 | `phah_taibun_lookup.lua` 為候選加 `[TL:xxx POJ:yyy]` |
| 萬用查字 `?` | ✅ 已實作 | `phah_taibun_wildcard.lua` 展開所有可能聲母匹配 |
| 造詞模式 `;` | ✅ 基礎版 | `phah_taibun_phrase.lua` 基礎造詞引導，進階版需 per-syllable lookup |
| 簡拼提示 `,,sp` | ✅ 已實作 | `phah_taibun_speedup.lua` 17 個聲母對照表 + 用法提示 |
| 文白讀標記 | 🔲 scaffold | `phah_taibun_synonym.lua` 架構就位，需反查字典加入 wen_bai 欄位 |
| IVS 標音輸出 | 🔲 待開始 | 確認字咍字型 IVS 對照表可提取後 |
| 查讀音進階 | 🔲 待開始 | 整合教育部辭典例句、解說 |

## Phase 3：生態擴展（3-6 個月後）

> 從工具變成平台。

| 功能 | 說明 |
|------|------|
| HTML ruby 輸出 | 網頁寫作者的需求 |
| 簡拼提示 + 快打模式 | 進階使用者加速 |
| 台語日期時間 | 趣味性功能 |
| 學習模式 | 邊打邊學，顯示華語對照 |
| Android/iOS 支援 | 透過 Trime（同文）/ iRime 部署 |
| 與意傳輸入法互通詞庫 | 如果社群有需求 |
| 台語語音輸入整合 | 搭配 Whisper 或意傳 ASR |

---

## Phase 1 工作拆解

### ✅ Week 0：環境準備 + 資源下載（完成）

| 任務 | 輸出 |
|------|------|
| `scripts/download_resources.sh` — 20 個資源全部下載 | `data/` 目錄完備 |
| `uv sync` 安裝依賴 | `pyproject.toml` + `uv.lock` |

### ✅ Week 1：資料處理 + 字典生成（完成）

| 任務 | 輸出 |
|------|------|
| `convert_chhoetaigi.py` + `build_frequency.py` | `phah_taibun.dict.yaml`（2MB，含 Ungian + iCorpus 詞頻加權） |
| `build_reverse_dict.py` + `build_kipsutian_reverse.py` | `phah_taibun_reverse.dict.yaml`（65K 條目） |
| `parse_lkk_rules.py` | `hanlo_rules.yaml`（893 條漢羅分類） |
| 131 個 Python 測試通過，71% 覆蓋率 | TDD 品質保證 |

### ✅ Week 2：Schema + Lua 核心 + rime-liur 移植（完成）

| 任務 | 輸出 |
|------|------|
| `phah_taibun.schema.yaml` — POJ/TL 雙系統、`@*` Lua 載入語法 | 完整 schema |
| `rime.lua` — 舊版 librime-lua 相容 | 模組註冊檔 |
| 7 個 Phase 1 Lua 模組 + 3 個 Phase 2 stubs | `lua/` 目錄 10 個 .lua 檔 |
| `install.sh` + `scripts/install_linux.sh` | 一鍵安裝（fcitx5/ibus 自動偵測） |

### ✅ Week 3：實機測試 + 調校（完成，2026-03-15）

| 任務 | 狀態 |
|------|------|
| fcitx5-rime 實機安裝測試 | ✅ 通過 — Rime 部署 8 schema 0 failure，build 產物齊全 |
| 字典檔改為隨 repo 發佈（從 .gitignore 移除） | ✅ 已修復 |
| `luna_pinyin` 反查依賴檢查 | ✅ install.sh 已加檢測 |
| 10 個 Lua 模組語法驗證 | ✅ 全部通過（Lua 5.5 loadfile 無錯誤） |
| Python 測試 127 個（123 passed, 4 skipped） | ✅ 通過 |
| 安裝檔案完整性（source ↔ installed 比對） | ✅ 10 個 Lua + 5 個 schema 檔案一致 |
| Rime 日誌無錯誤（phah_taibun dictionary is ready） | ✅ 確認 |
| 詞頻微調 | 🔲 待使用者實際打字體驗後決定 |
| README.md 更新 | ✅ 已重寫（快速安裝、使用範例、疑難排解） |

**Week 3 結束交付**：MVP 已可發佈

---

## 待使用者提供的資料

以下資料已全部自動取得，不再需要手動處理：

| 資料 | 狀態 | 說明 |
|------|------|------|
| **LKK 用字表** | ✅ 已自動下載 | 從 Google Sheets pubhtml 自動下載 CSV（字表 + 數字用法） |
| **楊允言詞頻** | ✅ 已自動下載 | Taiwanese-Corpus/Ungian_2009_KIPsupin |
| **iCorpus 新聞語料** | ✅ 已自動下載 | 臺華平行新聞語料，真實詞頻來源 |
| **漢羅文學語料** | ✅ 已自動下載 | 2,169 篇台語漢羅及全羅文學作品 |
| **芫荽字體** | 🔲 建議安裝 | ChhoeTaigi/iansui，專為台文設計 |

---

## 語言與工具選擇說明

### 為什麼 Rime runtime 用 Lua？
- Rime 引擎原生支援的腳本語言只有 Lua
- `lua_filter` 和 `lua_translator` 是 Rime 提供的標準擴展機制
- rime-liur 的 93.7% Lua 實作證明了 Lua 可以做到非常複雜的功能
- 效能好：Lua 查表是 O(1)，不影響打字流暢度

### 為什麼資料處理用 Python？
- ChhoeTaigi CSV 解析（`csv` 模組原生支援 UTF-8 BOM）
- 正規表達式處理拼音格式（`re` 模組）
- YAML 輸出（`pyyaml`）
- 如果要用意傳的臺灣言語工具做音標轉換，它是 Python package（`uv add tai5-uan5_gian5-gi2_kang1-ku7`）
- 統計和去重用 `collections.Counter` + `pandas`（可選）

### 不建議的替代方案
- **全部用 Lua**：Lua 缺乏 CSV 解析、Unicode 正規化等工具，不適合做資料前處理
- **用 Go 做資料處理**：過度工程化，Python 的 csv/re/yaml 生態完全夠用，微調規則時改 Python 腳本也比改 Go 快得多
- **用 Node.js**：沒有特別優勢，而且意傳的工具鏈是 Python
