# CLAUDE.md — rime-phah-taibun 拍台文 專案指引

## 專案概述

**拍台文** (Phah Tâi-bûn) — 基於 Rime 輸入法引擎的台語（臺灣閩南語）輸入法方案，核心目標是讓「會講台語但不太會打」的人也能輕鬆書寫台文。

**差異化定位**：不同於現有台語 Rime 方案（glll4678/rime-taigi、YuRen-tw/rime-taigi-tps、i3thuan5/rime-taigi），本方案聚焦於：
1. 漢羅混寫為預設輸出（依 LKK 李江却用字規範）
2. POJ/TL 雙拼音系統模糊輸入（聲調可省略）
3. 候選區永遠顯示「漢字 + 拼音註解」，降低使用門檻
4. 多種輸出模式切換（漢羅、全羅、IVS標音、HTML ruby）
5. 華語反查台語讀音

## 技術棧

| 層 | 語言 | 用途 |
|---|------|------|
| Rime schema | YAML | 輸入法方案定義、speller algebra、字典格式 |
| Runtime 腳本 | Lua | 候選過濾、輸出模式切換、漢羅轉換、反查邏輯、造詞、符號 |
| 資料前處理 | Python 3.10+（uv 管理） | ChhoeTaigi CSV→Rime dict 轉換、詞頻統計、LKK用字表解析 |

## 目錄結構

```
rime-phah-taibun/
├── CLAUDE.md                      # 本檔案
├── PLAN.md                        # 詳細技術規劃
├── roadmap.md                     # 分階段開發路線圖
├── pyproject.toml                 # Python 專案設定（uv + ruff + pytest）
├── uv.lock                        # uv 鎖定檔（需進 repo）
├── LICENSE                        # 授權（待決定，建議 MIT 或 Apache-2.0）
├── README.md                      # 使用者文件
│
├── schema/                        # Rime 方案檔（最終部署到 ~/.config/ibus/rime/ 或 fcitx5 對應路徑）
│   ├── phah_taibun.schema.yaml    # 主方案
│   ├── phah_taibun.dict.yaml      # 主字典（iTaigi CC0 + 台華線頂 CC BY-SA）
│   ├── phah_taibun.phrase.dict.yaml # 詞組字典
│   ├── phah_taibun.custom.dict.yaml # 使用者可擴充字典
│   ├── phah_taibun_reverse.dict.yaml    # 反查字典（漢字→台語讀音）
│   ├── hanlo_rules.yaml           # LKK 漢羅分類表（哪些詞輸出漢字/羅馬字）
│   └── default.custom.yaml        # 預設配置
│
├── lua/                           # Rime Lua 腳本
│   ├── phah_taibun_filter.lua           # 核心：候選拼音註解 + 輸出模式切換 + 漢羅轉換
│   ├── phah_taibun_reverse.lua          # 華語反查台語
│   ├── phah_taibun_lookup.lua           # 查台語讀音 Ctrl+'（移植自 rime-liur 查碼模組）
│   ├── phah_taibun_wildcard.lua         # 萬用查字 ?（移植自 rime-liur）
│   ├── phah_taibun_symbols.lua          # 台語符號選單 `（移植自 rime-liur）
│   ├── phah_taibun_help.lua             # 按鍵說明 ,,h（移植自 rime-liur）
│   ├── phah_taibun_date.lua             # 台語日期 ,,jit（移植自 rime-liur）
│   ├── phah_taibun_phrase.lua           # Phase 2：造詞模式 ;（移植自 rime-liur）
│   ├── phah_taibun_synonym.lua          # Phase 2：文白讀切換 '（移植自 rime-liur）
│   └── phah_taibun_speedup.lua          # Phase 2：簡拼提示 ,,sp（移植自 rime-liur）
│
├── scripts/                       # Python 資料處理腳本（開發時使用，不隨輸入法部署）
│   ├── convert_chhoetaigi.py      # ChhoeTaigi CSV → Rime dict.yaml
│   ├── build_frequency.py         # 詞頻統計與合併
│   ├── parse_lkk_rules.py         # LKK 用字表 → hanlo_rules.yaml
│   ├── build_reverse_dict.py      # 建立漢字→台語讀音反查字典
│   └── validate_dict.py           # 字典品質檢查
│
├── data/                          # 原始資料（gitignore，不進 repo，用 scripts/download_resources.sh 下載）
│   ├── ChhoeTaigiDatabase/        # 9 本辭典 CSV，353K 筆
│   ├── rime-taigi-glll4678/       # 現有 Rime 台語方案（參考 schema + 方言碼）
│   ├── rime-liur/                 # 蝦米 Rime 方案（參考 Lua 模組架構）
│   ├── rime-taigi-tps/            # 方音符號台語方案（參考字典格式）
│   ├── taigivs/                   # 字咍字型（Phase 2 IVS 對照表）
│   ├── Taiwanese-Corpus-hue7jip8/ # 語料彙整清單（楊允言詞頻指引）
│   ├── moedict-data-twblg/        # 教育部辭典開放資料（反查用）
│   ├── lkk_yongji.csv             # LKK 用字表（自動從 Google Sheets 下載 CSV）
│   ├── lkk_suji.csv               # LKK 數字用法（自動下載）
│   ├── Ungian_2009_KIPsupin/      # 楊允言詞頻資料（自動下載）
│   ├── tai5-uan5_gian5-gi2_kang1-ku7/ # 意傳臺灣言語工具原始碼
│   ├── KipSutianDataMirror/       # 教育部台語辭典鏡像（ODS + 音檔）
│   ├── KeSi/                      # POJ↔TL 轉換工具（MIT）
│   ├── icorpus_ka1_han3-ji7/      # iCorpus 臺華平行新聞語料（真實詞頻）
│   ├── nmtl_2006_dadwt/           # 台語漢羅全羅文學 2,169 篇
│   ├── moe_minkalaok/             # 閩南語卡拉OK正字字表
│   ├── Khin-hoan_2010_pojbh/      # 白話字文獻館（歷史 POJ 語料）
│   └── Kam-Ui-lim_1913_Kam-Ji-tian/ # 甘字典 CSV 原始版
│
├── opencc/                        # OpenCC 設定（如需正簡轉換）
├── fonts/                         # 推薦字體說明（字咍台語字型等）
└── tests/                         # 測試
    ├── test_dict_conversion.py
    ├── test_hanlo_rules.py
    └── test_lua_filter.py         # Lua 腳本的整合測試
```

## 關鍵外部資料來源

| 資料 | 來源 | 授權 | 狀態 |
|------|------|------|------|
| iTaigi 華台對照典 | ChhoeTaigi/ChhoeTaigiDatabase | CC0 | ✅ 已取得，19,775 筆 |
| 台華線頂對照典 | ChhoeTaigi/ChhoeTaigiDatabase | CC BY-SA 4.0 | ✅ 已取得，91,339 筆 |
| 教育部台語辭典 | ChhoeTaigi/ChhoeTaigiDatabase | CC BY-ND 3.0 | ✅ 已取得，24,608 筆（僅可做反查） |
| 台日大辭典 | ChhoeTaigi/ChhoeTaigiDatabase | CC BY-NC-SA 3.0 | ✅ 已取得，69,515 筆 |
| 甘字典 | ChhoeTaigi/ChhoeTaigiDatabase | CC BY-NC-SA 3.0 | ✅ 已取得，24,367 筆 |
| rime-liur Lua 模組 | ryanwuson/rime-liur | 開源（待確認具體 license） | ✅ 下載，移植 7 個模組 |
| ~~意傳 Rime 台語詞表~~ | ~~i3thuan5/rime-taigi~~ | — | ❌ repo 已刪除 |
| ~~意傳 POJ 漢羅方案~~ | ~~i3thuan5/rime_taigi_poj_hanlo~~ | — | ❌ repo 已刪除 |
| 意傳輕聲分析器 | i3thuan5/khin1siann1-hun1sik4 | 不明 | ✅ 下載，參考詞頻書寫規範 |
| 臺灣言語工具 | i3thuan5/tai5-uan5_gian5-gi2_kang1-ku7 | MIT | ✅ 原始碼已下載，`uv add` 待執行 |
| 教育部辭典開放資料 | g0v/moedict-data-twblg | CC BY-ND 3.0 | ✅ 下載，反查字典 |
| LKK 用字表 | 李江却基金會 Google Sheets | 待確認 | ✅ 自動從 pubhtml 下載 CSV（字表 + 數字用法） |
| 楊允言詞頻 (2009) | Taiwanese-Corpus/Ungian_2009_KIPsupin | 待確認 | ✅ 已自動下載 |
| 字咍字型 IVS 對照 | ButTaiwan/taigivs | OFL / CC-by 4.0 | ✅ 下載，Phase 2 |
| 現有 rime-taigi | glll4678/rime-taigi | 不明 | ✅ 已分析，參考 schema 結構 |
| 教育部台語辭典鏡像 | ChhoeTaigi/KipSutianDataMirror | CC BY-ND 3.0 | ✅ 下載，比 moedict-data-twblg 更完整 |
| POJ↔TL 轉換工具 | i3thuan5/KeSi | MIT | ✅ 下載，輕量版音標轉換 |
| iCorpus 臺華平行新聞語料 | Taiwanese-Corpus/icorpus_ka1_han3-ji7 | 待確認 | ✅ 下載，真實詞頻來源 |
| 台語漢羅全羅文學語料 | Taiwanese-Corpus/nmtl_2006_dadwt | 待確認 | ✅ 下載，漢羅書寫慣例黃金參考 |
| 閩南語卡拉OK正字字表 | Taiwanese-Corpus/moe_minkalaok | 待確認 | ✅ 下載，教育部用字規範參考 |
| 白話字文獻館 | Taiwanese-Corpus/Khin-hoan_2010_pojbh | 待確認 | ✅ 下載，歷史 POJ 語料 |
| 甘字典 CSV 原始版 | ChhoeTaigi/Kam-Ui-lim_1913_Kam-Ji-tian | CC BY-NC-SA | ✅ 下載，歷史辭典參考 |
| 芫荽字體 | ChhoeTaigi/iansui | SIL OFL 1.1 | 🔲 建議使用者安裝 |

## ChhoeTaigi CSV 欄位對照

各資料庫共通的關鍵欄位：
- `KipInput`: 教育部羅馬拼音（數字調號，如 `tsit8-e7`）
- `PojInput`: 白話字（數字調號，如 `chit8-e7`）
- `KipUnicode`: 教育部羅馬拼音（Unicode 調號，如 `tsi̍t-ē`）
- `PojUnicode`: 白話字（Unicode 調號，如 `chi̍t-ē`）
- `HanLoTaibunKip`: 漢羅台文（教育部版）
- `HanLoTaibunPoj`: 漢羅台文（白話字版）
- `HoaBun`: 對應華文

KipInput 格式注意事項：
- 2.8% 含斜線 `/` 分隔的多音變體
- 0.8% 含 `(替)` 標記的替代音
- 1.1% 含 `--` 雙連字號表示連讀
- 聲調數字 1-9（1、4 無標記的情況存在）

## 編碼與設計原則

1. **字典以 TL (教育部羅馬字) 為內部正規化格式**，POJ 透過 speller algebra derive 規則對應
2. **聲調在字典中以數字存儲**，去調號版本透過 derive 規則自動生成（`derive/[1-9]$//`）
3. **漢羅轉換是 Lua filter 層的責任**，不改動字典本身
4. **詞頻以整數權重存在字典第三欄**，數值越大越優先
5. **反查字典獨立於主字典**，教育部 CC BY-ND 資料只進反查不進主字典

## 開發環境

- OS: Arch Linux（使用者的 ThinkPad X1 Carbon Gen 12）
- 輸入法框架: fcitx5-rime 或 ibus-rime
- Python: 3.10+（**uv** 管理虛擬環境與依賴）
- Linter/Formatter: **ruff**（設定在 pyproject.toml）
- 測試: **pytest**（`uv run pytest`）
- 開發方法: **TDD（Red → Green → Refactor）**
- 編輯器: Neovim
- 終端: Ghostty + Zellij

## TDD 開發流程

本專案嚴格遵循 **Red-Green-Refactor** 循環，所有 Python 程式碼必須先寫測試：

### 流程

```
1. RED    — 先寫一個會失敗的測試，定義期望行為
2. GREEN  — 寫最少的程式碼讓測試通過（不多不少）
3. REFACTOR — 測試通過後重構，保持測試綠燈
```

### 規則

- **永遠先寫測試**，再寫實作。不允許先寫實作再補測試。
- **每次只加一個測試**，通過後才寫下一個。不要一次寫一堆測試。
- **GREEN 階段寫最簡單的實作**，不要過度設計。醜的程式碼沒關係，先讓測試通過。
- **REFACTOR 階段必須保持綠燈**，每次重構後跑 `uv run pytest`。
- **每 ~50 行新邏輯跑一次完整測試**，確保沒有回歸。
- **覆蓋率目標 80%+**，用 `uv run pytest --cov=scripts` 檢查。

### 範例循環

```bash
# 1. RED — 寫測試（預期失敗）
# tests/test_convert.py
# def test_strip_tone_number():
#     assert strip_tone("tsit8") == "tsit"

uv run pytest tests/test_convert.py    # ❌ FAIL（函數不存在）

# 2. GREEN — 最小實作
# scripts/convert_chhoetaigi.py
# def strip_tone(kip_input: str) -> str:
#     return re.sub(r"[1-9]$", "", kip_input)

uv run pytest tests/test_convert.py    # ✅ PASS

# 3. REFACTOR — 整理程式碼
uv run ruff check scripts/ tests/      # lint
uv run ruff format scripts/ tests/     # format
uv run pytest                          # ✅ 全部通過，安全重構
```

### 測試檔案對照

| 實作 | 測試 | 測試重點 |
|------|------|---------|
| `scripts/convert_chhoetaigi.py` | `tests/test_dict_conversion.py` | CSV 解析、多音分割、聲調去除、去重 |
| `scripts/build_frequency.py` | `tests/test_frequency.py` | 分層權重計算、詞長修正、來源加權 |
| `scripts/parse_lkk_rules.py` | `tests/test_hanlo_rules.py` | 虛詞→lo、實詞→han、YAML 輸出格式 |
| `scripts/build_reverse_dict.py` | `tests/test_reverse_dict.py` | 華語→台語反查、一字多音處理 |
| `scripts/validate_dict.py` | `tests/test_validate.py` | 字典格式驗證、重複偵測 |

## 常用指令

```bash
# === 環境設定 ===
uv sync                           # 安裝所有依賴（含 dev group）

# === TDD 循環 ===
uv run pytest tests/test_xxx.py -x      # RED/GREEN：跑單一測試檔，遇錯即停
uv run pytest                            # 全部測試
uv run pytest --cov=scripts              # 含覆蓋率
uv run pytest --cov=scripts --cov-report=term-missing  # 顯示未覆蓋行號

# === 程式碼品質（REFACTOR 階段）===
uv run ruff check scripts/ tests/        # lint 檢查
uv run ruff format scripts/ tests/       # 自動格式化
uv run ruff check --fix scripts/ tests/  # lint + 自動修復

# === Phase 0: 下載外部資源（首次設定，共 18 個資源）===
chmod +x scripts/download_resources.sh
./scripts/download_resources.sh
# 建議：安裝芫荽字體 https://github.com/ChhoeTaigi/iansui

# === 資料前處理 ===
uv run python scripts/convert_chhoetaigi.py --input data/ChhoeTaigiDatabase/ --output schema/
uv run python scripts/build_frequency.py --output schema/phah_taibun.dict.yaml
uv run python scripts/parse_lkk_rules.py --input data/lkk_yongji.csv --output schema/hanlo_rules.yaml

# === 部署到 Rime（fcitx5）===
cp schema/*.yaml ~/.local/share/fcitx5/rime/
cp lua/*.lua ~/.local/share/fcitx5/rime/lua/
# 然後在 fcitx5 重新部署

# === 部署到 Rime（ibus）===
cp schema/*.yaml ~/.config/ibus/rime/
cp lua/*.lua ~/.config/ibus/rime/lua/
```

## 注意事項

- **TDD 是強制的**：PR 不接受沒有對應測試的實作程式碼
- Lua 腳本中的檔案路徑需要相對於 Rime 使用者資料夾
- Rime 的 Lua 環境是沙箱化的，只能用 Rime 提供的 API
- 字典 `.dict.yaml` 修改後需要重新部署才會生效
- `hanlo_rules.yaml` 由 Lua 在初始化時載入記憶體，查表效能無問題
- 台語一字多音（文白讀）的處理策略：白讀優先，文讀作為次要候選
