# AGENTS.md — rime-phah-taibun 拍台文 專案指引

> 本檔是本專案**唯一的事實來源**（single source of truth）。
> 它優先於全域預設與任何工具的習慣設定。更新專案指引時，改這裡。

## 專案概述

**拍台文** (Phah Tâi-bûn) — 基於 Rime 輸入法引擎的台語（臺灣閩南語）輸入法方案，核心目標是讓「會講台語但不太會打」的人也能輕鬆書寫台文。

**差異化定位**：不同於現有台語 Rime 方案與其他台語輸入法，本方案聚焦於：
1. 漢羅混寫為預設輸出（依 LKK 李江却用字規範）
2. POJ/TL 雙拼音系統**模糊輸入**（不用選系統、聲調可省略）
3. 候選區永遠顯示「漢字 + 拼音註解」，降低使用門檻
4. 多種輸出模式切換（漢羅、全羅 × TL/POJ；Telex 調鍵平行方案）
5. 華語反查台語讀音（注音反查）

**平台**：Linux（fcitx5-rime / ibus-rime 原生）、Windows（小狼毫 Weasel + 安裝包）、macOS（鼠鬚管 Squirrel + curl 腳本）、Android（Trime / fcitx5-android；雙包並行：`PhahTaiBun-Trime.zip`＝拍台文＋注音＋反查依賴，`PhahTaiBun-Trime-liur.zip`＝再加嘸蝦米，附 `LIUR-PROVENANCE.txt` 標示來源）。

## 技術棧

| 層 | 語言 | 用途 |
|---|------|------|
| Rime schema | YAML | 輸入法方案定義、speller algebra、字典格式 |
| Runtime 腳本 | Lua | 候選過濾、輸出模式切換、漢羅轉換、反查、造詞、符號、輕聲、推薦 |
| 資料前處理 | Python 3.10+（uv 管理） | ChhoeTaigi CSV / KipSutian ODS / 7 語料庫 → Rime dict 轉換、詞頻統計、LKK 用字表解析 |
| 發佈 | Shell / PowerShell / Inno Setup | Linux install.sh、macOS install_macos.sh、Windows install_windows.ps1 + .iss |

## 目錄結構

```
rime-phah-taibun/
├── AGENTS.md                     # 本檔（唯一事實來源）
├── PLAN.md                       # 技術規劃（§9 = 改進計畫）
├── roadmap.md                    # 分階段開發路線圖
├── README.md                     # 使用者文件（雙語）
├── CONTRIBUTING.md / SECURITY.md
├── main.py                       # 佔位（尚未使用）
├── pyproject.toml / uv.lock      # Python 專案設定（uv + ruff + pytest）
├── rime.lua                      # Lua 模組註冊（舊版 librime-lua 相容）
│
├── schema/                       # Rime 方案檔（部署到 ~/.config/ibus/rime/ 等）
│   ├── phah_taibun.schema.yaml       # 主方案（漢羅、全羅、TL/POJ 切換）
│   ├── phah_taibun_telex.schema.yaml # Telex 調鍵方案（共用主字典）
│   ├── phah_taibun.dict.yaml         # 主字典（~220K 詞條）
│   ├── hanlo_rules.yaml              # LKK 漢羅分類表
│   ├── hoabun_map.txt                # 華語對照（反查顯示用）
│   ├── lighttone_rules.json          # 輕聲規則（111 條）
│   ├── moe700.yaml                   # 教育部 700 推薦用字
│   └── default.custom.yaml           # 預設配置（含 switcher/save_options）
│
├── lua/                          # 20 個 Lua 模組（一功能一檔）
│   ├── phah_taibun_filter.lua        # 核心：拼音註解 + 輸出模式 + 漢羅轉換
│   ├── phah_taibun_input.lua         # 輸入前處理 processor
│   ├── phah_taibun_commit.lua        # 送出 processor
│   ├── phah_taibun_select_char.lua   # 以詞定字 [ / ]
│   ├── phah_taibun_data.lua          # 共用資料/工具函數
│   ├── phah_taibun_lighttone.lua     # 輕聲候選
│   ├── phah_taibun_long_word.lua     # 長詞優先
│   ├── phah_taibun_recommend.lua     # 推薦用字標記（◆/★）
│   ├── phah_taibun_origin.lua        # 原形輸出
│   ├── phah_taibun_synonym.lua       # 同音選字 '
│   ├── phah_taibun_phrase.lua        # 造詞模式 ;
│   ├── phah_taibun_wildcard.lua      # 萬用查字 ?
│   ├── phah_taibun_lookup.lua        # 查讀音 Ctrl+'
│   ├── phah_taibun_reverse_format.lua# 反查格式
│   ├── phah_taibun_symbols.lua       # 符號選單 `
│   ├── phah_taibun_help.lua          # 按鍵說明 ,,
│   ├── phah_taibun_date.lua          # 台語日期 ,,
│   ├── phah_taibun_speedup.lua       # 簡拼提示 ,,
│   ├── phah_taibun_toneless.lua     # 無調整詞優先（0.8.0）
│   └── phah_taibun_telex.lua         # Telex 解析
│
├── scripts/                      # Python 資料處理（開發用，不隨輸入法部署）
│   ├── build_all.py               # ★ 一鍵管線：語料詞頻 → 字典 → 規則 → 驗證
│   ├── convert_chhoetaigi.py      # ChhoeTaigi CSV → dict.yaml
│   ├── convert_kautian_ods.py     # 教育部 KipSutian ODS → kautian.csv
│   ├── build_frequency.py         # 分層詞頻統計與合併
│   ├── extract_ungian_freq.py     # 楊允言詞頻
│   ├── extract_icorpus_freq.py    # iCorpus 新聞語料詞頻
│   ├── extract_nmtl.py            # NMTL 文學語料
│   ├── extract_pojbh.py           # 白話字文獻館語料（POJ→TL）
│   ├── extract_kipsutian_sentences.py # 教典例句
│   ├── extract_kok4hau7_freq.py   # 康軒教科書詞頻
│   ├── extract_900leku_freq.py    # 900 例句詞頻
│   ├── build_phrases.py           # bigram 詞組
│   ├── build_lighttone_entries.py # 輕聲詞條
│   ├── build_dictionary_supplement.py # 教育部輸入法詞庫增補
│   ├── build_hoabun_map.py        # 華語對照
│   ├── parse_lkk_rules.py         # LKK 用字表 → hanlo_rules.yaml
│   ├── parse_lighttone.py         # 輕聲規則 → lighttone_rules.json
│   ├── parse_moe700.py            # 教育部 700 字 → moe700.yaml
│   ├── tl_poj_convert.py          # TL↔POJ 轉換器
│   ├── validate_dict.py           # 字典品質檢查
│   ├── download_resources.sh      # 18+ 外部資源下載
│   ├── build_trime_package.py     # ★ Trime 一鍵包：拍台文＋注音＋反查依賴（--with-liur 本機自用）
│   └── install_linux.sh / install_macos.sh
│
├── data/                          # 原始資料（gitignore，不下載不進 repo）
├── docs/                          # GitHub Pages 網站 + 使用文件
├── packaging/                     # windows（Inno Setup .iss）/ macos（pkg 腳本）/ android（Trime 包說明＋trime.custom.yaml 排版 patch）
├── install.sh / install_windows.ps1
└── tests/                         # pytest（26 個測試檔＋conftest/rime_smoke.cpp）
    ├── test_real_rime.py          # ★ 真 librime 整合測試（無 librime 則 skip）
    ├── test_android_package.py    # ★ Trime 一鍵包內容＋真引擎部署 smoke（無 liur checkout 則 skip）
    ├── test_lua_filter*.py        # Lua 模組測試
    ├── test_frequency.py / test_validate.py / test_dict_conversion.py …
    └── rime_smoke.cpp             # C++ smoke
```

## 關鍵外部資料來源（授權摘要）

| 資料 | 來源 | 授權 |
|------|------|------|
| iTaigi 華台對照典 | ChhoeTaigi/ChhoeTaigiDatabase | CC0 |
| 台華線頂對照典 | 同上 | CC BY-SA 4.0 |
| 教育部台語辭典（KipSutian） | ChhoeTaigi/KipSutianDataMirror | CC BY-ND 3.0 |
| 台日大辭典 | ChhoeTaigi/ChhoeTaigiDatabase | CC BY-NC-SA 3.0（非商用） |
| 甘字典 | ChhoeTaigi/Kam-Ui-lim_1913_Kam-Ji-tian | CC BY-NC-SA |
| iCorpus 臺華平行新聞語料 | Taiwanese-Corpus/icorpus_ka1_han3-ji7 | CC BY 4.0（README 明載） |
| NMTL 台語文學 2,169 篇 | Taiwanese-Corpus/nmtl_2006_dadwt | 待確認 |
| 白話字文獻館 | Taiwanese-Corpus/Khin-hoan_2010_pojbh | 待確認 |
| 楊允言詞頻 (2009) | Taiwanese-Corpus/Ungian_2009_KIPsupin | 待確認 |
| LKK 用字表 | 李江却基金會 Google Sheets | 已確認可用，需註明出處 |
| rime-liur Lua 模組 | ryanwuson/rime-liur | 已確認可使用，需註明出處（PLAN §8） |
| KeSi POJ↔TL | i3thuan5/KeSi | MIT |
| rime-emoji（opencc 詞庫） | rime/rime-emoji | LGPL-3.0 |
| emoji-test.txt（分類選單） | Unicode.org emoji-test 15.1 | Unicode License |
| 教育部輸入法詞庫增補 | luke871016/Taigi-Input-method-dictionary-supplement | 待確認 |
| 芫荽字體 | ChhoeTaigi/iansui | SIL OFL 1.1（建議安裝） |

**授權原則**：字典資料 per-source 保持分離標示；NC 來源（台日大辭典、甘字典）不得進入商業發佈版本。LICENSE 檔內含 per-source 對照表。

## ChhoeTaigi CSV 欄位對照

- `KipInput`: 教育部羅馬拼音（數字調號，如 `tsit8-e7`）
- `PojInput`: 白話字（數字調號，如 `chit8-e7`）
- `KipUnicode` / `PojUnicode`: Unicode 調號版
- `HanLoTaibunKip` / `HanLoTaibunPoj`: 漢羅台文
- `HoaBun`: 對應華文

KipInput 注意：2.8% 含 `/` 多音變體、0.8% 含 `(替)` 替代音、1.1% 含 `--` 連讀輕聲、聲調 1-9（1、4 有無標記情況）。

## 編碼與設計原則

1. **字典以 TL 為內部正規化格式**，POJ 透過 speller algebra derive 對應。
2. **聲調以數字存儲**，去調版由 derive 自動生成（`derive/[1-9]$//`）。
3. **漢羅轉換是 Lua filter 層的責任**，不改字典。
4. **詞頻以整數權重存字典第三欄**，越大越優先。
5. **教育部 CC BY-ND 資料可進主字典與反查字典**，保留來源標示。
6. **詞身份 = (漢字文本, 正規化 TL 讀音) 成對**。只有漢字或只有讀音都不構成身份——`重/tîng` 與 `重/tāng` 是兩個詞，任何去重、推薦、學習計數不得合併。（PLAN §9-D）
7. **長詞不敗**：字典內 n 音節整詞權重必須 ≥ K×其逐音節拆分和（K>1），保證連續輸入不被碎切。（PLAN §9-A）
8. **使用者字典只學你選過的詞**（enable_encoder 關閉），不從輸入歷史造新詞。

## 開發環境

- OS: Linux（輸入法框架 fcitx5-rime 或 ibus-rime）
- Python: 3.10+（**uv** 管理虛擬環境與依賴）
- Linter/Formatter: **ruff**（設定在 pyproject.toml）
- 測試: **pytest**（`uv run pytest`）；librime 整合測試需系統 librime（否則 skip）
- 系統依賴：華語反查需 `terra_pinyin.dict.yaml` 與 `bopomofo_tw` 方案（`bopomofo.schema` 的字典就是 terra_pinyin，上游無獨立 bopomofo dict）（Arch: `rime-terra-pinyin` + `rime-bopomofo`；Debian: `rime-data-*`；CI 於 release.yml 安裝）

## TDD 開發流程（強制）

Red → Green → Refactor：

1. **RED** — 先寫會失敗的測試，定義期望行為
2. **GREEN** — 寫最少程式碼讓測試通過（不多不少）
3. **REFACTOR** — 保持綠燈下重構

規則：
- 永遠先寫測試再寫實作；PR 不接受沒有對應測試的實作。
- 每次只加一個測試，通過後才寫下一個。
- GREEN 寫最簡實作；醜沒關係，先過。
- REFACTOR 後必跑 `uv run pytest`。
- 每 ~50 行新邏輯跑一次完整測試。
- 覆蓋率目標 80%+（`uv run pytest --cov=scripts`）。

## 常用指令

```bash
# === 環境 ===
uv sync                                # 安裝所有依賴

# === 測試 / 品質 ===
uv run pytest                          # 全部測試
uv run pytest tests/test_xxx.py -x     # 單檔，遇錯即停
uv run pytest --cov=scripts --cov-report=term-missing
uv run ruff check scripts/ tests/      # lint
uv run ruff format scripts/ tests/     # format

# === 資料前處理（首次需先下載資源）===
chmod +x scripts/download_resources.sh && ./scripts/download_resources.sh
uv run python scripts/build_all.py     # 一鍵管線（語料→字典→規則→驗證）
#   --data-dir / --output-dir 可覆寫路徑

# === 安裝（自動偵測 fcitx5/ibus）===
./install.sh                           # Linux
# Windows: install_windows.ps1（需 Weasel）
# macOS:  scripts/install_macos.sh（需 Squirrel）
```

## 文件網站本機預覽與部署

- 文件網站來源在 `docs/`；改首頁或 Docsify 使用說明前，先本機預覽並確認首頁與 `guide.html` 可用：
  `python3 -m http.server 8000 --directory docs`，開啟 `http://localhost:8000/` 與 `http://localhost:8000/guide.html`。
- 確認使用者能從首頁看懂：安裝步驟、快捷鍵與完整操作請前往「使用說明」；Docsify 連結須能正確載入對應章節。
- 本機確認後，提交並 push 到 `main`；Cloudflare 的 Git 部署設定會執行 `npx wrangler deploy`，`wrangler.jsonc` 將 `docs/` 發佈為靜態資產。
- push 後到正式站 `https://taigi.anatomind.com/` 驗證首頁與 `https://taigi.anatomind.com/guide.html` 的 Docsify 渲染及導航。不可只以 push 成功當作部署成功。

## Rime Lua 模組載入機制

兩種載入方式**都要支援**：
1. 新式 `@*` 語法（librime-lua ≥ 2021）：schema 寫 `lua_translator@*phah_taibun_help`，自動載入 `lua/phah_taibun_help.lua`（模組回傳 `{init, func}` table）。
2. 舊式 `rime.lua` 全域註冊：使用者資料夾放 `rime.lua`，`require()` 註冊為全域變數。

新增模組 checklist：`lua/phah_taibun_xxx.lua` → `rime.lua` 加 require → schema engine 區加 `@*phah_taibun_xxx`。

## 注意事項

- Lua 檔案路徑相對於 Rime 使用者資料夾；Lua 環境是沙箱，只能用 Rime API。
- 字典 `.dict.yaml` 修改後需重新部署。
- `hanlo_rules.yaml` 等規則檔由 Lua 初始化時載入記憶體。
- 台語一字多音（文白讀）：白讀優先，文讀次要候選。
- librime 的 `script_translator` 對「查無整詞、≥2 音節」一律自動組句（與 `enable_sentence` 旗標無關；1.6.0–1.13.1 原始碼驗證，見 tests/test_schema_config.py）；逐音節選字行為由 `tests/test_real_rime.py` 以真引擎釘住。
- 輸出模式（TL/POJ、漢羅/全羅）自 0.4.0 起跨 session 記憶（`default.custom.yaml` 的 `switcher/save_options`）。

## 改進計畫

目前的改進路線見 **PLAN.md §9**：演算法不變量（整詞優先權重、學習飽和/衰減、詞身份統一）、資料管線驗證閘（fatal TL→POJ 完整性、known-keys fixture、鍵集 release-diff）、品質紀律（行為不變量清單、SHA256SUMS）。Non-goals：不做方音符號輸入、不自研引擎、不做原生 App。
