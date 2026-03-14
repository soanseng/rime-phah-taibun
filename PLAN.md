# PLAN.md — rime-phah-taibun 拍台文 技術規劃

## 1. 專案定位

### 目標使用者
「會講台語但不太會打台文」的人。他們可能：
- 不確定拼音怎麼拼（POJ 和 TL 分不清楚）
- 不想花力氣打聲調
- 不知道哪些詞該寫漢字、哪些該寫羅馬字
- 想要一邊打字一邊學台語讀音

### 核心體驗
```
使用者打 gua beh khi tshit tho
→ 候選區顯示：我 beh 去 tshit-thô [guá beh khì tshit-thô]
→ 確認是想要的意思
→ 送出漢羅混寫：我 beh 去 tshit-thô
```

不需要打聲調、不需要分辨 POJ/TL、不需要知道漢羅規則，輸入法全部幫你處理。

## 2. Phase 0：準備階段 — 外部資源下載

所有外部資源下載到 `data/` 目錄下，此目錄列入 `.gitignore`，不進 repo。

### 2-0a. 下載腳本

**腳本**: `scripts/download_resources.sh`

一鍵下載 18 個資源（17 個 GitHub repo + 1 個 Google Sheets CSV），移除 `.git` 目錄（只取檔案不留歷史）。

```bash
chmod +x scripts/download_resources.sh
./scripts/download_resources.sh
```

下載清單（共 18 個資源）：

| # | repo | 用途簡述 |
|---|------|---------|
| 1 | ChhoeTaigi/ChhoeTaigiDatabase | 主字典：9 本辭典 CSV |
| 2 | glll4678/rime-taigi | 參考 schema 結構、方言碼 |
| 3 | ryanwuson/rime-liur | **Lua 模組移植來源**：查碼、符號、日期、說明、萬用字元 |
| 4 | YuRen-tw/rime-taigi-tps | 參考方音符號字典 |
| 5 | ButTaiwan/taigivs | 字咍字型 IVS（Phase 2） |
| 6 | Taiwanese-Corpus/hue7jip8 | 語料清單、詞頻路徑指引 |
| 7 | g0v/moedict-data-twblg | 教育部辭典開放資料（反查） |
| 8 | i3thuan5/khin1siann1-hun1sik4 | **詞頻書寫規範**，分詞邏輯參考 |
| 11 | LKK 用字表 (Google Sheets CSV) | **漢羅轉換規則核心**（自動從 pubhtml 下載 CSV） |
| 12 | Taiwanese-Corpus/Ungian_2009_KIPsupin | 楊允言詞頻資料（教育部字詞頻調查） |
| 13 | i3thuan5/tai5-uan5_gian5-gi2_kang1-ku7 | 意傳臺灣言語工具原始碼（音標轉換） |
| 14 | ChhoeTaigi/KipSutianDataMirror | 教育部台語辭典鏡像（ODS + 音檔），CC BY-ND 3.0 |
| 15 | i3thuan5/KeSi | POJ↔TL 轉換 Python 工具（MIT），輕量版 |
| 16 | Taiwanese-Corpus/icorpus_ka1_han3-ji7 | **iCorpus 臺華平行新聞語料**，可算真實詞頻 |
| 17 | Taiwanese-Corpus/nmtl_2006_dadwt | **台語漢羅及全羅文學 2,169 篇**，漢羅書寫慣例黃金參考 |
| 18 | Taiwanese-Corpus/moe_minkalaok | 閩南語卡拉OK正字字表，教育部用字規範參考 |
| 19 | Taiwanese-Corpus/Khin-hoan_2010_pojbh | 白話字文獻館（歷史 POJ 語料） |
| 20 | ChhoeTaigi/Kam-Ui-lim_1913_Kam-Ji-tian | 甘字典 CSV 原始版（CC BY-NC-SA） |

另需手動處理：
1. **意傳臺灣言語工具**：`uv add tai5-uan5_gian5-gi2_kang1-ku7`
2. **芫荽字體**（ChhoeTaigi/iansui）：建議安裝以獲得最佳台文顯示效果

### 2-0b. 各資源用途對照

| 目錄 | 來源 | 用途 | Phase |
|------|------|------|-------|
| `data/ChhoeTaigiDatabase/` | ChhoeTaigi/ChhoeTaigiDatabase | **主要字典來源**：9 本辭典 CSV，共 353K 筆 | 1 |
| `data/rime-taigi-glll4678/` | glll4678/rime-taigi | 參考現有 schema 結構（speller algebra、方言碼 EI/EE/OO）、字典格式 | 1 |
| `data/rime-liur/` | ryanwuson/rime-liur | **Lua 模組直接移植**：查碼→查讀音、符號選單、按鍵說明、日期時間。93.7% Lua，模組化設計清晰 | 1 |
| `data/rime-taigi-tps/` | YuRen-tw/rime-taigi-tps | 參考方音符號鍵盤配置、字典格式 | 1 |
| `data/taigivs/` | ButTaiwan/taigivs | 字咍字型 IVS 對照表（`readings/` 資料夾）、漢字→讀音映射 | 2 |
| `data/Taiwanese-Corpus-hue7jip8/` | Taiwanese-Corpus/hue7jip8 | 語料庫匯入清單、楊允言詞頻研究的路徑指引 | 2 |
| `data/moedict-data-twblg/` | g0v/moedict-data-twblg | 教育部台語辭典開放資料，建反查字典（華語→台語） | 1 |
| ~~`data/rime-taigi-ithuan/`~~ | ~~i3thuan5/rime-taigi~~ | ❌ repo 已刪除 | — |
| ~~`data/rime_taigi_poj_hanlo/`~~ | ~~i3thuan5/rime_taigi_poj_hanlo~~ | ❌ repo 已刪除 | — |
| `data/khin1siann1-hun1sik4/` | i3thuan5/khin1siann1-hun1sik4 | **詞頻書寫規範**：分詞邏輯、輕聲處理規則，計算詞頻的前處理參考 | 1 |
| `data/lkk_yongji.csv` | 李江却基金會 Google Sheets | **漢羅轉換規則核心**（自動從 pubhtml 下載 CSV） | 1 |
| `data/lkk_suji.csv` | 李江却基金會 Google Sheets | LKK 數字用法規範（自動下載） | 1 |
| `data/Ungian_2009_KIPsupin/` | Taiwanese-Corpus/Ungian_2009_KIPsupin | 楊允言教育部詞頻調查 | 2 |
| `data/tai5-uan5_gian5-gi2_kang1-ku7/` | i3thuan5/tai5-uan5_gian5-gi2_kang1-ku7 | 意傳臺灣言語工具原始碼，音標轉換參考 | 1 |
| `data/KipSutianDataMirror/` | ChhoeTaigi/KipSutianDataMirror | 教育部台語辭典鏡像（ODS + 音檔），CC BY-ND 3.0 | 1 |
| `data/KeSi/` | i3thuan5/KeSi | POJ↔TL 轉換 Python 工具（MIT），輕量版 | 1 |
| `data/icorpus_ka1_han3-ji7/` | Taiwanese-Corpus/icorpus_ka1_han3-ji7 | **iCorpus 臺華平行新聞語料**，真實詞頻來源 | 1 |
| `data/nmtl_2006_dadwt/` | Taiwanese-Corpus/nmtl_2006_dadwt | **台語漢羅及全羅文學 2,169 篇**，漢羅書寫慣例黃金參考 | 1 |
| `data/moe_minkalaok/` | Taiwanese-Corpus/moe_minkalaok | 閩南語卡拉OK正字字表，教育部用字規範參考 | 1 |
| `data/Khin-hoan_2010_pojbh/` | Taiwanese-Corpus/Khin-hoan_2010_pojbh | 白話字文獻館（歷史 POJ 語料） | 2 |
| `data/Kam-Ui-lim_1913_Kam-Ji-tian/` | ChhoeTaigi/Kam-Ui-lim_1913_Kam-Ji-tian | 甘字典 CSV 原始版（CC BY-NC-SA） | 2 |

### 2-0c. .gitignore 設定

```gitignore
# 外部資料（不進 repo，用 download_resources.sh 重新下載）
data/

# Rime 編譯產物
*.bin
*.userdb/
sync/

# Python
__pycache__/
*.pyc
.venv/
*.egg-info/
```

注意：`uv.lock` 和 `pyproject.toml` 需要進 repo。

### 2-0d. 資源重點檔案索引

下載完之後，開發時最常需要查看的檔案：

```
data/
├── ChhoeTaigiDatabase/ChhoeTaigiDatabase/
│   ├── ChhoeTaigi_iTaigiHoataiTuichiautian.csv    # iTaigi CC0，19K筆
│   ├── ChhoeTaigi_TaihoaSoanntengTuichiautian.csv  # 台華線頂 CC BY-SA，91K筆，最大宗
│   ├── ChhoeTaigi_KauiokpooTaigiSutian.csv         # 教育部 CC BY-ND，24K筆（僅反查用）
│   ├── ChhoeTaigi_TaijitToaSutian.csv               # 台日大辭典，69K筆，無華文對照
│   └── ...
├── rime-taigi-glll4678/
│   ├── taigi.schema.yaml    # 現有 schema，speller algebra 有方言碼處理
│   └── taigi.dict.yaml      # 53K 筆，32K 有讀音，20K 無讀音
├── rime-liur/
│   └── lua/                 # ★ 重點：直接移植的 Lua 模組
│       ├── (查碼模組)       # → 改寫成查台語讀音模式 (Ctrl+')
│       ├── (造詞模組)       # → Phase 2 移植，台語造詞
│       ├── (符號模組)       # → 改寫成台語符號選單 (`)
│       ├── (日期模組)       # → 改寫成台語日期 (,,jit)
│       ├── (說明模組)       # → 移植為按鍵說明 (,,h)
│       └── ...
├── khin1siann1-hun1sik4/    # ★ 重點：詞頻書寫規範
│   └── ...                  # 分詞規則、輕聲處理邏輯
├── taigivs/
│   └── readings/            # Phase 2：IVS 漢字→讀音對照表
├── moedict-data-twblg/      # 教育部辭典 JSON/CSV 格式
├── lkk_yongji.csv           # ★ LKK 字表（自動從 Google Sheets 下載 CSV）
├── lkk_suji.csv             # LKK 數字用法（自動下載）
├── Ungian_2009_KIPsupin/    # 楊允言詞頻資料
├── tai5-uan5_gian5-gi2_kang1-ku7/  # 意傳臺灣言語工具原始碼
├── KipSutianDataMirror/     # 教育部台語辭典鏡像（ODS + 音檔）
├── KeSi/                    # POJ↔TL 轉換工具（MIT）
├── icorpus_ka1_han3-ji7/    # ★ iCorpus 臺華平行新聞語料（真實詞頻來源）
├── nmtl_2006_dadwt/         # ★ 台語漢羅及全羅文學 2,169 篇
├── moe_minkalaok/           # 閩南語卡拉OK正字字表
├── Khin-hoan_2010_pojbh/    # 白話字文獻館（歷史 POJ 語料）
└── Kam-Ui-lim_1913_Kam-Ji-tian/  # 甘字典 CSV 原始版

意傳 Python 套件（uv add，不在 data/ 內）：
  tai5-uan5_gian5-gi2_kang1-ku7   # 臺灣言語工具：拆文分析器、音標轉換（TL↔POJ）
  安裝：uv add tai5-uan5_gian5-gi2_kang1-ku7
  文件：https://i3thuan5.github.io/tai5-uan5_gian5-gi2_kang1-ku7/

建議安裝字體：
  ChhoeTaigi/iansui (芫荽)        # 專為台文設計的字體，SIL OFL 授權
  https://github.com/ChhoeTaigi/iansui
```

### 2-0e. 意傳科技 (i3thuan5) 資源整合策略

意傳已經做了大量台語 NLP 基礎建設，我們應該最大化利用而非重造輪子：

**詞頻數據**：意傳已將楊允言的兩份詞頻研究數位化為 yaml：
- `Ungian_2005_guliau-supin`（台語書面語音節詞頻統計）
- `Ungian_2009_KIPsupin`（教育部字詞頻調查）
- 託管在 Taiwanese-Corpus GitHub Pages，可直接下載
- 用意傳的臺灣言語工具解析即得教育部級詞頻數據

**漢羅分類邏輯**：~~`rime_taigi_poj_hanlo`~~ repo 已刪除。
改從 LKK 用字表 CSV + nmtl_2006_dadwt 漢羅文學語料中提取漢羅分類規則。

**音標轉換**：`tai5-uan5_gian5-gi2_kang1-ku7` 的拆文分析器可：
- TL ↔ POJ 自動轉換
- 漢字+音標自動對齊
- 漢羅混寫文的解析與重組
- 在我們的 Python 前處理腳本中直接 `import` 使用

**分詞邏輯**：`khin1siann1-hun1sik4` 的詞頻書寫規範定義了
輕聲符、連字號的處理方式——計算詞頻前的標準化步驟。

### 2-0f. rime-liur Lua 模組移植計畫

rime-liur (ryanwuson/rime-liur) 93.7% 是 Lua，模組化設計清晰。
以下功能可直接改寫移植（不是從零寫，是改寫已有的 Lua 為台語版）：

| rime-liur 功能 | 我們的台語版 | 移植策略 | Phase |
|---------------|-------------|---------|-------|
| 查碼模式 `Ctrl+'` | **查台語讀音模式**：選字後顯示 TL+POJ 讀音 | 改寫查表邏輯：蝦米碼表→台語讀音表 | 1 |
| 符號清單 `` ` `` | **台語符號選單**：台羅調號、方音符號、輕聲符 | 替換符號表內容，保留選單 UI 邏輯 | 1 |
| 按鍵說明 `,,h` | **台語版按鍵說明** | 幾乎直接複製，改說明文字 | 1 |
| 日期時間 `,,dt` | **台語日期** `,,jit`：拜一～拜日、正月～十二月 | 改寫日期格式化函數 | 1 |
| 萬用查字 `?` | **模糊拼音查字**：`ts?ah` 匹配 tsiah/tsuah | 改寫匹配邏輯為拼音模式 | 1 |
| 造詞模式 `;` | **台語造詞**：逐字拼打組合新詞 | 改寫為拼音輸入+漢字選字流程 | 2 |
| 同音選字 `'` | **文白讀切換**：顯示同音的文讀/白讀 | 需額外文白讀標記資料 | 2 |
| 快打模式 `,,sp` | **簡拼提示**：提示可用的拼音縮寫 | 改寫提示邏輯為拼音縮寫 | 2 |

**移植注意事項**：
- rime-liur 的 Lua 是 MIT 風格（README 寫「開源授權」），可自由改寫
- 保留 rime-liur 的模組命名慣例（一個功能一個 lua 檔）
- 改寫時保留原始來源的 credit（在每個 lua 檔開頭加 comment）

---

## 3. 資料處理流程 (Python)

### 3-1. ChhoeTaigi → Rime 字典轉換

**腳本**: `scripts/convert_chhoetaigi.py`

**輸入**: ChhoeTaigi CSV 檔案（UTF-8 with BOM）
**輸出**: `phah_taibun.dict.yaml`

處理步驟：
1. 讀取 iTaigi (CC0) + 台華線頂 (CC BY-SA) 兩份 CSV
2. 提取 `KipInput`, `HanLoTaibunKip`, `HoaBun` 欄位
3. 清理 KipInput：
   - 移除 `(替)` 標記
   - 斜線 `/` 分隔的多音分割為多筆條目
   - `--` 連讀標記保留（輕聲處理）
4. 生成無調號版本作為 Rime 輸入鍵：`tsit8-e7` → `tsit e`
5. 去重合併（同漢字同拼音只保留一筆）
6. 寫入 Rime dict.yaml 格式：
   ```yaml
   # 漢字\t拼音(無調)\t權重
   食飯	tsiah png	500
   ```

**授權合規**：
- iTaigi (CC0)：自由使用，無限制
- 台華線頂 (CC BY-SA)：需在 README 標示來源
- 教育部辭典 (CC BY-ND)：**不可改作**，只能用於反查字典（原樣引用讀音資訊）
- 台日大辭典 (CC BY-NC-SA)：非商用，可做補充字典

### 3-2. 詞頻建立

**腳本**: `scripts/build_frequency.py`

**策略：分層啟發式權重**（無現成可直接下載的頻率表）

| 層級 | 來源 | 基礎權重 | 筆數 |
|------|------|---------|------|
| L1 核心常用 | 教育部辭典收錄詞 | 1000 | ~24K |
| L2 群眾驗證 | iTaigi (多人贊同) | 800 | ~19K |
| L3 線頂對照 | 台華線頂獨有詞 | 500 | ~50K |
| L4 文言補充 | 台日大辭典獨有詞 | 200 | ~40K |

權重修正因子：
- 詞長 2-3 字：×1.2（最常用的詞長）
- 詞長 1 字：×0.8（單字通常是組詞元素）
- 詞長 4+ 字：×0.6（成語俗諺，使用頻率較低）
- 多資料庫重疊收錄：每多一個來源 ×1.1

**已取得的詞頻精進資料**：
- 楊允言 `Ungian_2009_KIPsupin`（教育部詞頻調查）→ 已自動下載
- 意傳科技 `khin1siann1-hun1sik4` 的詞頻書寫規範 → 已下載，參考其分詞邏輯
- `icorpus_ka1_han3-ji7`（iCorpus 臺華平行新聞語料 2008-2014）→ **真實詞頻來源**
- `nmtl_2006_dadwt`（台語漢羅及全羅文學 2,169 篇）→ **漢羅書寫慣例統計**

### 3-3. LKK 用字表解析

**腳本**: `scripts/parse_lkk_rules.py`

**輸入**: LKK用字_雲端版_台羅正式版_2024/5/10更新（自動從 Google Sheets 下載 CSV）
**輸出**: `hanlo_rules.yaml`

預期格式：
```yaml
# hanlo_rules.yaml
# type: han = 輸出漢字, lo = 輸出羅馬字, context = 視語境
#
# 虛詞助詞（輸出羅馬字）
ê:
  type: lo
  kip: ê
  poj: ê
  note: 的

kap:
  type: lo
  kip: kap
  poj: kap
  note: 和、與

beh:
  type: lo
  kip: beh
  poj: beh
  note: 要

# 實詞（輸出漢字）
食飯:
  type: han
  kip: tsia̍h-pn̄g
  poj: chia̍h-pn̄g
  note: 吃飯
```

**備用方案**：若 LKK 表未能取得，從 ChhoeTaigi 的 `HanLoTaibunKip` 欄位逆向工程：
- 統計所有漢羅混寫條目中，哪些音節保留為羅馬字
- 出現次數高的羅馬字音節即為「應寫羅馬字」的虛詞/固有詞

### 3-4. 反查字典建立

**腳本**: `scripts/build_reverse_dict.py`

建立兩本反查字典：
1. **華語→台語**：從 ChhoeTaigi 的 `HoaBun` 欄位反向索引
   ```yaml
   # phah_taibun_reverse_hoabun.dict.yaml
   吃飯	chi fan	# 華語拼音鍵
   # → comment 顯示：食飯 tsia̍h-pn̄g
   ```
2. **漢字→台語讀音**：單字級的讀音對照
   ```yaml
   # phah_taibun_reverse_hanji.dict.yaml
   食	tsia̍h, si̍t  # 白讀, 文讀
   飯	pn̄g, huān
   ```

## 4. Rime Schema 設計

### 5-1. Speller Algebra（POJ/TL 雙系統 + 模糊拼音）

```yaml
speller:
  alphabet: 'zyxwvutsrqponmlkjihgfedcba1234567890-?'
  initials: zyxwvutsrqponmlkjihgfedcba
  delimiter: " '"
  algebra:
    # === 聲調完全可省略 ===
    - derive/[1-9]$//

    # === POJ → TL 對應（核心約 15 條）===
    - derive/^ts/ch/           # TL ts → POJ ch
    - derive/^tsh/chh/         # TL tsh → POJ chh
    - derive/^j/l/             # 部分人 j/l 不分
    - derive/ing/eng/          # TL ing → POJ eng
    - derive/ik/ek/            # TL ik → POJ ek
    - derive/ua/oa/            # TL ua → POJ oa
    - derive/ue/oe/            # TL ue → POJ oe
    - derive/oo/ou/            # TL oo → POJ ou (部分)
    - derive/nn/ⁿ/             # 鼻化音

    # === 進一步模糊（降低門檻）===
    - derive/ph/f/             # 有人會打 f 代替 ph
    - derive/nng/ng/           # 簡化
    - derive/h$//              # 入聲尾可省略

    # === 萬用字元支援 ===
    # ? 由 Lua 處理，不在 algebra 層

    # === 簡拼（首字母縮寫）===
    - abbrev/^([ptkmnbglsjhiuc]g?s?h?h?).*/$1/
```

### 5-2. Translator + Lua Filter

```yaml
engine:
  processors:
    - ascii_composer
    - recognizer
    - key_binder
    - speller
    - punctuator
    - selector
    - navigator
    - express_editor
  segmentors:
    - ascii_segmentor
    - matcher
    - abc_segmentor
    - punct_segmentor
    - fallback_segmentor
  translators:
    - echo_translator
    - punct_translator
    - script_translator          # 主翻譯器
    - reverse_lookup_translator  # 反查
    - table_translator@custom_phrase  # 使用者自訂
    - lua_translator@phah_taibun_date  # 日期時間
  filters:
    - lua_filter@phah_taibun_filter    # 核心：漢羅轉換 + 拼音註解
    - uniquifier

switches:
  - name: ascii_mode
    reset: 0
    states: [ 台文, ABC ]
  - name: output_mode
    reset: 0  # 0=漢羅TL, 1=漢羅POJ, 2=全羅TL, 3=全羅POJ, 4=IVS
    states: [ 漢羅TL, 漢羅POJ, 全羅TL, 全羅POJ, IVS標音 ]
```

### 5-3. Lua Filter 核心邏輯 (phah_taibun_filter.lua)

```
輸入候選(漢字 + 拼音) 
  → 讀取 output_mode 開關
  → 查 hanlo_rules 表
  → 根據模式轉換輸出文字
  → 在 comment 附加拼音註解
  → yield 修改後的候選
```

漢羅轉換的查表邏輯：
1. 將候選的漢字逐字/逐詞比對 hanlo_rules
2. 標記為 `lo` 的詞 → 替換成對應的帶調號拼音
3. 標記為 `han` 的詞 → 保留漢字
4. 未在表中的詞 → 預設保留漢字（保守策略）

## 5. 功能模組設計

所有 Lua 模組遵循 rime-liur 的設計模式：一個功能一個獨立 lua 檔。
標記「移植自 rime-liur」的模組，以 `data/rime-liur/lua/` 對應檔案為基礎改寫。

### 5-1. 輸出模式切換

觸發：`Ctrl+Shift+T` 循環切換，或 `F4` 選單選擇

| 模式 | 輸出範例 | 實現方式 |
|------|---------|---------|
| 漢羅 TL | 我 beh 去 tshit-thô | 查 hanlo_rules，lo 詞換 TL Unicode |
| 漢羅 POJ | 我 beh 去 chhit-thô | 查 hanlo_rules，lo 詞換 POJ Unicode |
| 全羅 TL | guá beh khì tshit-thô | 所有詞都輸出 TL Unicode |
| 全羅 POJ | goá beh khì chhit-thô | 所有詞都輸出 POJ Unicode |
| IVS 標音 | 我beh去tshit-thô + IVS碼 | Phase 2 |

### 5-2. 候選區顯示

每個候選項顯示為：
```
1. 我 beh 去 tshit-thô  [guá beh khì tshit-thô]  吃飯→食飯
   ↑ 主文字（漢羅混寫）   ↑ comment（完整拼音）    ↑ 華語對照
```

### 5-3. 反查模式

| 模式 | 觸發 | 流程 | 來源 |
|------|------|------|------|
| 注音→台語 | `';` + 注音 | 注音輸入華語字 → 查 reverse dict → 顯示台語讀音 | 參考 rime-liur 注音輸入 `';` |
| 拼音→台語 | `~` + 拼音 | 漢語拼音輸入 → 查 reverse dict → 顯示台語讀音 | 參考 rime-liur 拼音輸入 `;'` |
| 查讀音 | `Ctrl+'` | 選字後 comment 顯示完整台語讀音（TL+POJ+華語） | **移植自 rime-liur 查碼模式** |

### 5-4. 查台語讀音模式 `Ctrl+'`（移植自 rime-liur 查碼模式）

**原始功能**：rime-liur 按 `Ctrl+'` 進入查碼模式，選字後顯示蝦米拆碼。
**台語版改寫**：選字後顯示台語讀音（TL + POJ）+ 華語對照。

使用場景：不知道「蝴蝶」台語怎麼講？打華語選字，直接看到 `ôo-tia̍p / o͘-tia̍p`。

實作：改寫 rime-liur 的查碼 Lua，將查表從蝦米碼表改成 `phah_taibun_reverse.dict.yaml`。

### 5-5. 萬用查字 `?`（移植自 rime-liur 萬用字元 `,,wc`）

**原始功能**：rime-liur 在 `,,wc` 模式下用 `?` 代替未知字碼。
**台語版改寫**：直接在正常輸入中支援 `?` 代替未知音節部分。

使用場景：不確定「食」的聲母？打 `?iah` 匹配 `tsiah`（食）、`siah`（削）等。

實作：Lua translator 攔截含 `?` 的輸入，展開為所有可能的音節匹配。

### 5-6. 符號選單 `` ` ``（移植自 rime-liur 符號清單）

**原始功能**：rime-liur 按 `` ` `` 開啟 50+ 分類符號選單。
**台語版改寫**：替換符號內容為台語專用，保留選單 UI 邏輯。

```
台羅調號: á é í ó ú / à è ì ò ù / â ê î ô û / ā ē ī ō ū / a̍ e̍ i̍ o̍ u̍
方音符號: ㆠ ㆣ ㄫ ㆢ ㆦ ㆤ ㆰ ㆱ ㆲ ㆬ ㆭ
輕聲符號: -- (雙連字號)
台文標點: 、。！？「」『』（）——
特殊字母: ⁿ (鼻化上標) / o͘ (POJ 的 oo)
```

### 5-7. 按鍵說明 `,,h`（移植自 rime-liur）

**原始功能**：rime-liur 打 `,,h` 顯示所有快捷鍵。
**台語版改寫**：幾乎直接複製，修改說明文字為拍台文的功能。

候選區顯示：
```
[拍台文 Phah Tâi-bûn 按鍵說明]
Ctrl+Shift+T  切換輸出模式（漢羅/全羅/IVS）
Ctrl+'        查台語讀音
';            華語注音反查台語
~             華語拼音反查台語
`             符號選單（調號/方音/標點）
?             萬用字元（代替不確定的拼音）
;             造詞模式
,,h           本說明
,,jit         台語日期時間
```

### 5-8. 台語日期時間 `,,jit`（移植自 rime-liur 日期時間）

**原始功能**：rime-liur 打 `,,dt` 輸出當前日期時間。
**台語版改寫**：輸出台語格式日期。

```
,,jit  → 2026年3月14 拜六
,,jit2 → 2026 nî 3 gue̍h 14 Pài-la̍k
,,si   → 下晡 3點15分 (ē-poo 3 tiám 15 hun)
```

Lua 改寫重點：星期映射（拜一～拜日）、月份可選漢字/羅馬字。

### 5-9. 造詞模式 `;`（Phase 2，移植自 rime-liur）

**原始功能**：rime-liur 按 `;` 進入造詞模式。
**台語版改寫**：逐字打拼音選字，組合成新詞條存入使用者字典。

Phase 1 先用 Rime 內建的 `custom_phrase` 手動加詞。
Phase 2 再移植 rime-liur 的 Lua 造詞模組。

### 5-10. 同音字切換 `'`（Phase 2，移植自 rime-liur）

**原始功能**：rime-liur 選字後按 `'` 顯示同音字。
**台語版改寫**：顯示文讀/白讀的同音字切換。

需要額外的文白讀標記資料（ChhoeTaigi 部分有 `Others` 欄位可利用）。

### 5-11. 簡拼提示 `,,sp`（Phase 2，移植自 rime-liur 快打模式）

**原始功能**：rime-liur 開啟快打模式，提示可用簡碼。
**台語版改寫**：打完整拼音時，comment 提示縮寫。

例如打 `tshit-tho` 時提示「簡拼：ct」。

### 5-12. 華語即時翻詞 `';`（台語專屬擴展）

超越 rime-liur 注音輸入的台語場景延伸：
按 `';` 進入華語模式 → 用注音打「吃飯」→ 候選區顯示 `食飯 tsia̍h-pn̄g` →
選了就送出漢羅混寫版 `食飯`。

### 5-13. 學習模式 `,,learn`（Phase 3，台語專屬）

開啟後，每次送出文字時候選區多顯示完整拼音 + 華語對照。
需要特殊的候選延遲機制，Rime 原生支援度不確定。

## 6. Lua 檔案對照表

| 我們的 lua 檔 | 對應 rime-liur | 功能 | Phase |
|--------------|---------------|------|-------|
| `phah_taibun_filter.lua` | (新寫) | 核心：漢羅轉換 + 拼音註解 + 輸出切換 | 1 |
| `phah_taibun_reverse.lua` | (新寫) | 華語反查台語 | 1 |
| `phah_taibun_lookup.lua` | 查碼模組 | 查台語讀音 `Ctrl+'` | 1 |
| `phah_taibun_wildcard.lua` | 萬用查字模組 | `?` 模糊拼音 | 1 |
| `phah_taibun_symbols.lua` | 符號模組 | 台語符號選單 `` ` `` | 1 |
| `phah_taibun_help.lua` | 說明模組 | 按鍵說明 `,,h` | 1 |
| `phah_taibun_date.lua` | 日期模組 | 台語日期 `,,jit` | 1 |
| `phah_taibun_phrase.lua` | 造詞模組 | 造詞模式 `;` | 2 |
| `phah_taibun_synonym.lua` | 同音模組 | 文白讀切換 `'` | 2 |
| `phah_taibun_speedup.lua` | 快打模組 | 簡拼提示 `,,sp` | 2 |

## 7. 測試策略

### 單元測試 (Python)
- `test_dict_conversion.py`: 驗證 CSV→dict.yaml 轉換正確性
  - 多音分割（斜線處理）
  - (替) 標記移除
  - 聲調去除
  - 去重邏輯
- `test_hanlo_rules.py`: 驗證 LKK 規則解析
  - 已知虛詞必須標記為 `lo`
  - 已知實詞必須標記為 `han`

### 整合測試 (手動 + 腳本)
- 在 fcitx5-rime 上實際輸入測試
- 測試案例清單：
  1. `gua beh khi tshit tho` → 我 beh 去 tshit-thô
  2. `tsiah png` → 食飯
  3. `chiah png` (POJ) → 同樣匹配食飯
  4. `gua ai li` (無聲調) → 我愛你
  5. 反查：`';` + ㄔ ㄈ → 食飯 tsia̍h-pn̄g

## 8. 待決事項

- [x] LKK 用字表：已自動從 Google Sheets 下載 CSV（字表 + 數字用法）
- [x] 授權選擇：MIT（程式碼）+ CC BY-SA 4.0（主字典）+ CC BY-ND 3.0（反查字典）
- [x] 楊允言詞頻：已自動下載，JSON 格式（1,093 檔），已用 extract_ungian_freq.py 提取 93K 詞頻
- [x] ~~意傳 `rime_taigi_poj_hanlo` 的字典生成邏輯深入分析~~ — repo 已刪除，改用 LKK CSV + nmtl 語料
- [x] 意傳 `khin1siann1-hun1sik4` 的分詞規則提取 — 111 條輕聲規則已用 parse_lighttone.py 解析
- [x] rime-liur Lua 模組授權確認：README 聲明「本專案基於開源授權發佈，歡迎使用和改進」，已標註出處
- [ ] 字咍字型 IVS 對照表提取（Phase 2）
- [ ] 與李江却基金會確認 LKK 用字表在輸入法中使用的授權
- [ ] `tai5-uan5_gian5-gi2_kang1-ku7` 在 Arch Linux 上的安裝測試
- [x] iCorpus 新聞語料：已用 extract_icorpus_freq.py 提取 57K 詞、302K tokens
- [x] nmtl_2006_dadwt 格式分析：2,169 篇 .tbk 純文字（POJ），含 25M nmtl.json 已對齊版
- [x] KipSutianDataMirror 比對：65K 條目（含解說、例句、又音），比 moedict 的 27K 多 2.4 倍，已建 build_kipsutian_reverse.py
