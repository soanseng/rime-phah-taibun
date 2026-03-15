# 拍台文 Phah Tai-bun

[![GitHub release](https://img.shields.io/github/v/release/soanseng/rime-phah-taibun?style=flat-square&label=release)](https://github.com/soanseng/rime-phah-taibun/releases)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue?style=flat-square)](LICENSE)
[![Dict Entries](https://img.shields.io/badge/dict-170K%20entries-green?style=flat-square)](#)
[![Lua Modules](https://img.shields.io/badge/lua-13%20modules-orange?style=flat-square)](#)
[![Corpora](https://img.shields.io/badge/corpora-7%20sources-purple?style=flat-square)](#)
[![Docs](https://img.shields.io/badge/docs-GitHub%20Pages-blue?style=flat-square)](https://soanseng.github.io/rime-phah-taibun/)
[![Platform](https://img.shields.io/badge/platform-Linux%20%7C%20macOS%20%7C%20Windows-lightgrey?style=flat-square)](#支援平台)

Rime 台語輸入法方案 — 漢羅混寫輸出，POJ/TL 雙拼音系統，聲調可省略。

> **[使用說明 User Guide](https://soanseng.github.io/rime-phah-taibun/)**

專為「會講台語但不太會打台文」的人設計。不需要分辨 POJ 和 TL、不需要打聲調、不需要知道漢羅規則，輸入法全部幫你處理。

## 特色

- **漢羅混寫**：依 LKK 李江却用字規範，自動輸出漢字+羅馬字混寫
- **POJ/TL 雙系統**：打 `tsiah` (TL) 或 `chiah` (POJ) 都能輸入「食」
- **聲調可省略**：打 `gua beh khi` 就能找到「我 beh 去」
- **拼音註解**：候選區永遠顯示讀音，邊打邊學
- **多種輸出模式**：漢羅TL、漢羅POJ、全羅TL、全羅POJ 一鍵切換
- **華語反查**：不知道台語怎麼講？用拼音打華語就能查到台語讀音
- **萬用字元**：拼音不確定？用 `?` 代替，列出所有可能
- **以詞定字**：按 `[` 取首字、`]` 取尾字，從詞組精準選字
- **長詞優先**：自動提升多字詞排序，減少逐字選字
- **Emoji 輸入**：候選區自動顯示相關 emoji（可開關）
- **英文混打**：直接打英文單字，台語英文無縫切換
- **170K 詞條**：整合 ChhoeTaigi 9 本辭典 + 7 語料庫頻率加權，涵蓋日常到文學用語

## 使用範例

### 基本輸入

```
輸入: gua beh khi tshit tho
候選: 我 beh 去 tshit-thô  [guá beh khì tshit-thô]
送出: 我 beh 去 tshit-thô
```

漢羅混寫自動處理：「我」「去」輸出漢字，「beh」「tshit-thô」依 LKK 規範輸出羅馬字。

### POJ / TL 都可以打

```
TL 輸入:  tsiah png  → 食飯
POJ 輸入: chiah png  → 食飯（同樣結果）

TL 輸入:  gua ai li  → 我愛你
POJ 輸入: goa ai li  → 我愛你（同樣結果）
```

### 聲調完全可省

```
完整拼音: gua2 beh4 khi3  → 我 beh 去
省略聲調: gua beh khi     → 我 beh 去（同樣結果）
```

### 華語反查台語

按 `~` 進入反查模式，用漢語拼音輸入華語，查看台語讀音：

```
~chi fan  → 食飯 tsia̍h-pn̄g
~piao liang → 媠 suí
```

### 萬用字元 `?`

不確定聲母？用 `?` 代替：

```
?iah  → 列出所有 -iah 結尾的字：
        食 tsiah、削 siah、跡 jiah ...
```

### 輸出模式切換

按 `F4` 或 `Ctrl+Shift+T` 切換：

| 模式 | 輸出範例 |
|------|---------|
| 漢羅 TL | 我 beh 去 tshit-thô |
| 漢羅 POJ | 我 beh 去 chhit-thô |
| 全羅 TL | guá beh khì tshit-thô |
| 全羅 POJ | goá beh khì chhit-thô |

### 符號選單

按 `` ` `` (反引號) 開啟符號選單：

- 台羅調號：á à â ā a̍
- POJ 特殊字母：o͘ ⁿ
- 方音符號：ㆠ ㆣ ㄫ ㆢ ㆦ ㆤ
- 台文標點：、。「」『』

### 台語日期

```
,,jit  → 2026年3月15 拜六
       → 2026 nî 3 gue̍h 15 Pài-la̍k
       → 2026-03-15
```

## 安裝

### 快速安裝（推薦）

字典檔已包含在 repo 中，clone 即可安裝，不需要另外建置。

```bash
git clone https://github.com/soanseng/rime-phah-taibun.git
cd rime-phah-taibun
./install.sh
```

安裝腳本會自動：
1. 偵測你的輸入法框架（fcitx5-rime 或 ibus-rime）
2. 複製方案檔、字典、Lua 模組到 Rime 使用者目錄
3. 註冊「拍台文」到方案清單（不會覆蓋你現有的方案）
4. 檢查反查所需的 `luna_pinyin` 方案是否存在
5. 觸發 Rime 重新部署

安裝完成後，在輸入法選單中選擇「拍台文」即可使用。

### 支援平台

| 平台 | 輸入法框架 | 安裝指令 |
|------|-----------|---------|
| Linux | fcitx5-rime | `./install.sh` （自動偵測） |
| Linux | ibus-rime | `./install.sh` （自動偵測） |
| macOS | 鼠鬚管 Squirrel | `./install.sh` （自動偵測） |
| 手動指定 | 任意平台 | `./install.sh ~/.local/share/fcitx5/rime` |

macOS 需先安裝鼠鬚管：`brew install --cask squirrel` 或從 [rime.im](https://rime.im/download/) 下載。

### 重新部署

安裝後必須重新部署 Rime：

- **fcitx5-rime**：右鍵系統匣圖示 → 重新部署（安裝腳本已自動執行）
- **ibus-rime**：`ibus restart`
- **鼠鬚管**：點選選單列圖示 → 重新部署

### 前置需求

- [Rime 輸入法引擎](https://rime.im/)（fcitx5-rime、ibus-rime 或鼠鬚管）
- `luna_pinyin` 方案（華語反查需要，大部分 Rime 安裝已內建）
- Git

> Python 和 uv 只有在需要從原始資料重新建置字典時才需要，一般使用者不需要。

### 建議字體

安裝 [芫荽 iansui](https://github.com/ChhoeTaigi/iansui)（SIL OFL 授權）可獲得最佳台文顯示效果，特別是方音符號和特殊台文漢字。

## 快捷鍵

| 按鍵 | 功能 | 說明 |
|------|------|------|
| `F4` | 方案選單 | 切換輸出模式（漢羅TL/漢羅POJ/全羅TL/全羅POJ） |
| `Ctrl+Shift+T` | 快速切換 | 循環切換輸出模式 |
| `~` | 華語反查 | 用漢語拼音查台語讀音 |
| `` ` `` | 符號選單 | 台羅調號、方音符號、台文標點 |
| `?` | 萬用字元 | 代替不確定的聲母，列出所有可能 |
| `;` | 造詞模式 | 逐字輸入組合新詞 |
| `,,h` | 按鍵說明 | 在候選區顯示所有快捷鍵 |
| `,,jit` | 台語日期 | 輸出今天日期（漢字/羅馬字/ISO） |
| `,,sp` | 簡拼對照 | 顯示聲母縮寫對照表 |
| `[` | 以詞定字（首字） | 選取候選詞的第一個字 |
| `]` | 以詞定字（尾字） | 選取候選詞的最後一個字 |
| `Shift+Space` | 強制輸出羅馬字 | 漢羅模式下輸出候選的全羅拼音（帶調符） |
| `Tab` | 音節跳轉 | 組字時跳到下一個音節 |
| `Ctrl+Backspace` | 刪除音節 | 刪除前一個音節 |

## 疑難排解

### 安裝後找不到「拍台文」方案

1. 確認已重新部署 Rime
2. 按 `F4` 查看方案清單，確認「拍台文(台)」在列表中
3. 檢查 `~/.local/share/fcitx5/rime/default.custom.yaml` 是否包含 `phah_taibun`

### 候選區沒有顯示拼音註解

確認 Lua 模組已正確安裝：
```bash
ls ~/.local/share/fcitx5/rime/lua/phah_taibun_*.lua
```
應該要有 13 個 `phah_taibun_*.lua` 檔案。

### 華語反查 `~` 沒有反應

反查依賴 `luna_pinyin` 方案，確認已安裝：
```bash
ls /usr/share/rime-data/luna_pinyin.schema.yaml
# 或
ls ~/.local/share/fcitx5/rime/luna_pinyin.schema.yaml
```

若未安裝，安裝 `librime-data` 套件：
```bash
# Arch Linux
sudo pacman -S librime-data

# Ubuntu/Debian
sudo apt install librime-data-luna-pinyin
```

### Lua 錯誤導致候選區異常

查看 Rime 日誌：
```bash
cat /tmp/rime.*.INFO | grep -i "lua\|error"
```

若出現 Lua 載入錯誤，確認 `rime.lua` 已安裝到 Rime 使用者目錄根：
```bash
cat ~/.local/share/fcitx5/rime/rime.lua | grep phah_taibun
```

### 重新安裝

```bash
cd rime-phah-taibun
./install.sh
```

安裝腳本會更新所有檔案（不會覆蓋你的自訂詞庫）。

## 目錄結構

```
schema/                        Rime 方案檔（安裝到 Rime 使用者目錄）
  phah_taibun.schema.yaml        方案定義（speller algebra、engine 設定）
  phah_taibun.dict.yaml           主字典（170K 條目）
  phah_taibun_reverse.dict.yaml   反查字典（26K 條目）
  hanlo_rules.yaml                LKK 漢羅分類規則
  lighttone_rules.json            輕聲規則
  default.custom.yaml             Rime 方案註冊
lua/                           Lua 擴充模組（13 個）
  phah_taibun_filter.lua          核心：漢羅轉換 + 輸出模式切換 + 調符顯示
  phah_taibun_commit.lua          全羅輸出處理器 + Shift+Space 強制羅馬字
  phah_taibun_data.lua            漢羅規則載入器 + 聲調調符轉換
  phah_taibun_lookup.lua          TL+POJ 雙標註
  phah_taibun_select_char.lua     以詞定字（[ 首字、] 尾字）
  phah_taibun_long_word.lua       長詞優先排序
  phah_taibun_wildcard.lua        萬用字元 ?
  phah_taibun_symbols.lua         符號選單
  phah_taibun_help.lua            按鍵說明
  phah_taibun_date.lua            台語日期
  phah_taibun_phrase.lua          造詞模式
  phah_taibun_synonym.lua         文白讀切換（開發中）
  phah_taibun_speedup.lua         簡拼對照
rime.lua                       Lua 模組註冊（舊版 librime 相容）
scripts/                       Python 資料處理腳本（18 個）
tests/                         pytest 測試（18 個測試檔）
```

## 開發

### 從原始資料重新建置

若需要修改字典內容或更新詞頻：

```bash
# 安裝 Python 依賴
uv sync

# 下載外部資料（20 個語言資源，約 2GB）
./scripts/download_resources.sh

# 建置字典
uv run python scripts/build_all.py

# 重新安裝
./install.sh
```

### 測試

```bash
uv run pytest                                          # 跑測試
uv run pytest --cov=scripts --cov-report=term-missing  # 含覆蓋率
uv run ruff check scripts/ tests/                      # Lint
uv run ruff format scripts/ tests/                     # 格式化
```

### 新增 Lua 模組

1. 建立 `lua/phah_taibun_xxx.lua`（回傳 `{init, func}` table）
2. 在 `rime.lua` 加入 `phah_taibun_xxx = require("phah_taibun_xxx")`
3. 在 `schema/phah_taibun.schema.yaml` 的 engine 區加入對應的 `lua_translator` 或 `lua_filter`
4. 執行 `./install.sh` 部署

## 資料來源

| 資料 | 授權 | 用途 |
|------|------|------|
| [ChhoeTaigi](https://github.com/ChhoeTaigi/ChhoeTaigiDatabase) | CC0 / CC BY-SA 4.0 | 主字典（iTaigi + 台華線頂） |
| [LKK 用字表](https://docs.google.com/spreadsheets/d/e/2PACX-1vR6sABIf13wvn95hKApMWmEYYD-vDL62mVAYBE1jycBRTkiJQush3-HCkkaPMSsv2cOcPZ0blNODFpx/pubhtml) | 已授權使用（需註明出處） | 漢羅轉換規則 |
| [教育部台語辭典](https://github.com/ChhoeTaigi/KipSutianDataMirror) | CC BY-ND 3.0 | 反查字典（65K 條目） |
| [教育部辭典 (g0v)](https://github.com/g0v/moedict-data-twblg) | CC BY-ND 3.0 | 反查字典 fallback |
| [iCorpus](https://github.com/Taiwanese-Corpus/icorpus_ka1_han3-ji7) | CC BY 4.0 | 詞頻統計（57K 詞） |
| [Ungian 2009](https://github.com/Taiwanese-Corpus/Ungian_2009_KIPsupin) | 待確認 | 文學語料詞頻（93K 詞） |
| [康軒課本](https://github.com/Taiwanese-Corpus/kok4hau7-kho3pun2) | 待確認 | 國小台語課本詞頻（1K 詞） |
| [常用900例句](https://github.com/Taiwanese-Corpus/Sin1pak8tshi7_2015_900-le7ku3) | 待確認 | 日常高頻詞彙（2.8K 詞） |
| [NMTL 文學作品](https://github.com/Taiwanese-Corpus/nmtl_2006_dadwt) | 待確認 | 台語文學語料（2K+ 篇） |
| [KipSutian 辭典](https://github.com/ChhoeTaigi/KipSutianDataMirror) | CC BY-ND 3.0 | 例句語料 + 反查字典 |
| [白話字文獻](https://github.com/Taiwanese-Corpus/Khin-hoan_2010_pojbh) | 待確認 | 歷史 POJ 語料（POJ→TL 轉換） |
| [rime-liur](https://github.com/ryanwuson/rime-liur) | 開源 | Lua 模組架構參考 |
| [rime-ice](https://github.com/iDvel/rime-ice) | GPL-3.0 | UX 功能參考（以詞定字、長詞優先、emoji） |

## 致謝

- [李江却台語文教基金會](https://www.tgb.org.tw/) — 漢羅用字規範（LKK 用字表），為本方案的漢羅混寫輸出提供核心依據
- [ChhoeTaigi 找台語](https://chhoe.taigi.info/) — 整合多本辭典的開放資料平台
- [ryanwuson/rime-liur](https://github.com/ryanwuson/rime-liur) — Lua 模組架構參考
- [教育部臺灣台語常用詞辭典](https://sutian.moe.edu.tw/) — 反查字典資料
- [楊允言教授](http://ip194097.ntcu.edu.tw/Ungian/) — 台語文學語料庫與詞頻資料
- [Taiwanese-Corpus](https://github.com/Taiwanese-Corpus) — iCorpus、康軒課本、900例句、NMTL 文學、白話字文獻等語料
- [意傳科技 i3thuan5](https://github.com/i3thuan5) — 臺灣言語工具、分詞邏輯參考
- [iDvel/rime-ice](https://github.com/iDvel/rime-ice) — 以詞定字、長詞優先等 UX 功能參考

## 授權

- **程式碼**（scripts/、lua/、schema/*.schema.yaml）：[MIT License](LICENSE)
- **主字典** phah_taibun.dict.yaml：CC BY-SA 4.0（繼承台華線頂）
- **反查字典** phah_taibun_reverse.dict.yaml：CC BY-ND 3.0（繼承教育部辭典）

詳見 [LICENSE](LICENSE)。
