# roadmap.md — 拍台文 Phah Tâi-bûn 開發路線圖

## 功能評估與分階段規劃

### 評估標準

每項功能以三個維度評分（1-5）：

- **使用者價值 (V)**：對「會講不太會打」的目標使用者有多重要
- **技術複雜度 (C)**：實作難度與工時
- **依賴風險 (R)**：是否依賴尚未取得的資料或第三方元件

**優先度 = V × 2 - C - R**（越高越優先）

---

## Phase 1：可用的 MVP（目標：2-3 週）

> 讓使用者能裝起來、打得出台語、看得到拼音。

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

| 功能 | 觸發條件 |
|------|---------|
| LKK 用字表正式整合 | LKK CSV 已自動下載，待格式分析後整合 |
| 楊允言詞頻精確化 | Ungian_2009 已下載，待格式分析後整合 |
| 造詞模式 `;` | 移植 rime-liur 造詞模組，改寫為拼音流程 |
| 同音字/文白讀切換 `'` | 移植 rime-liur 同音模組，取得文白讀標記資料後 |
| 簡拼提示 `,,sp` | 移植 rime-liur 快打模組 |
| IVS 標音輸出 | 確認字咍字型 IVS 對照表可提取後 |
| 查讀音模式進階 | 整合教育部辭典例句、解說 |

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

### Week 0：環境準備 + 資源下載

| 任務 | 工時 | 輸出 |
|------|------|------|
| `scripts/download_resources.sh` 完成並執行 | 0.5天 | `data/` 下 18 個資源（17 repo + 1 Google Sheets CSV） |
| 瀏覽各資源的關鍵檔案，確認格式無誤 | 0.5天 | 對各資料源的欄位、編碼、授權有具體理解 |
| `uv sync` 安裝依賴 | 0.5天 | `pyproject.toml` + `uv.lock`（pyyaml, ruff, pytest 等） |

**Week 0 結束交付**：所有原始資料就位、開發環境可用

### Week 1：資料處理 + 字典生成

| 任務 | 工時 | 輸出 |
|------|------|------|
| `convert_chhoetaigi.py` 完成 | 2天 | `phah_taibun.dict.yaml` (~110K 筆) |
| `build_frequency.py` 完成 | 1天 | 字典含啟發式權重 |
| `build_reverse_dict.py` 完成 | 1天 | `phah_taibun_reverse.dict.yaml` |
| 從 ChhoeTaigi HanLoTaibun 欄位提取初版漢羅規則 | 1天 | `hanlo_rules.yaml` (初版) |

**Week 1 結束交付**：可部署的 Rime 字典檔（無 Lua，純字典匹配可用）

### Week 2：Schema + Lua 核心 + rime-liur 移植

| 任務 | 工時 | 輸出 |
|------|------|------|
| `phah_taibun.schema.yaml` 完成 | 1天 | POJ/TL 雙系統 algebra + 基本配置 |
| `phah_taibun_filter.lua` 核心功能 | 2天 | 候選註解 + 漢羅轉換 + 輸出模式切換 |
| `phah_taibun_reverse.lua` 反查 | 1天 | 注音/拼音→台語反查 |
| 移植 rime-liur：查讀音 `phah_taibun_lookup.lua` | 0.5天 | `Ctrl+'` 顯示台語讀音 |
| 移植 rime-liur：萬用查字 `phah_taibun_wildcard.lua` | 0.5天 | `?` 模糊拼音匹配 |
| 移植 rime-liur：符號 + 說明 + 日期 | 0.5天 | `` ` `` 符號、`,,h` 說明、`,,jit` 日期 |

**Week 2 結束交付**：功能完整的輸入法方案（含 7 個 Lua 模組）

### Week 3：測試 + 調校 + 文件

| 任務 | 工時 | 輸出 |
|------|------|------|
| fcitx5-rime 實機測試 | 2天 | Bug 修復、algebra 調整 |
| 詞頻微調 | 1天 | 常用詞排序優化 |
| README.md + 安裝說明 | 0.5天 | 使用者文件 |
| install.sh 安裝腳本 | 0.5天 | 一鍵安裝 |

**Week 3 結束交付**：可發佈的 MVP

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
- **用 Go 做資料處理**：過度工程化，Python 的 csv/re/yaml 生態完全夠用，而且你如果想微調規則時改 Python 腳本比改 Go 快得多
- **用 Node.js**：沒有特別優勢，而且意傳的工具鏈是 Python
