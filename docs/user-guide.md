# 拍台文 Phah Tai-bun 使用說明

**Rime 台語輸入法方案** — 漢羅混寫輸出，POJ/TL 雙拼音系統，聲調可省略。

專為「會講台語但不太會打台文」的人設計。不需要分辨 POJ 和 TL、不需要打聲調、不需要知道漢羅規則，輸入法全部幫你處理。

---

## 一、安裝方式

### 安裝需求

- [Rime 輸入法引擎](https://rime.im/)（fcitx5-rime、ibus-rime、鼠鬚管 或小狼毫）
- `luna_pinyin` 方案（華語反查需要，大部分 Rime 安裝已內建）
- Git

> Python 和 uv 只有在需要從原始資料重新建置字典時才需要，一般使用者不需要。

### 快速安裝

字典檔已包含在 repo 中，clone 即可安裝，不需要另外建置：

```bash
git clone https://github.com/soanseng/rime-phah-taibun.git
cd rime-phah-taibun
./install.sh
```

安裝腳本會自動：
1. 偵測你的輸入法框架（fcitx5-rime、ibus-rime 或鼠鬚管）
2. 複製方案檔、字典、Lua 模組到 Rime 使用者目錄
3. 註冊「拍台文」到方案清單（不會覆蓋你現有的方案）
4. 檢查反查所需的 `luna_pinyin` 方案是否存在
5. 觸發 Rime 重新部署

安裝完成後，在輸入法選單中選擇「拍台文(台)」即可使用。

### 支援平台

| 平台 | 輸入法框架 | 安裝指令 |
|------|-----------|---------|
| Linux | fcitx5-rime | `./install.sh`（自動偵測） |
| Linux | ibus-rime | `./install.sh`（自動偵測） |
| macOS | 鼠鬚管 Squirrel | `./install.sh`（自動偵測） |
| Windows | 小狼毫 Weasel | 見下方手動安裝 |
| 手動指定 | 任意平台 | `./install.sh ~/.local/share/fcitx5/rime` |

macOS 需先安裝鼠鬚管：`brew install --cask squirrel` 或從 [rime.im](https://rime.im/download/) 下載。

### Windows Weasel 安裝

Windows 使用者需先安裝 [小狼毫 Weasel](https://rime.im/download/)，然後手動複製檔案：

1. 下載或 clone 本專案：
   ```
   git clone https://github.com/soanseng/rime-phah-taibun.git
   ```

2. 找到 Rime 使用者目錄（通常在 `%AppData%\Rime`）：
   - 右鍵小狼毫系統匣圖示 → 用戶文件夾

3. 複製以下檔案到使用者目錄：
   ```
   schema/phah_taibun.schema.yaml    → %AppData%\Rime\
   schema/phah_taibun.dict.yaml      → %AppData%\Rime\
   schema/phah_taibun_reverse.dict.yaml → %AppData%\Rime\
   schema/hanlo_rules.yaml           → %AppData%\Rime\
   schema/lighttone_rules.json       → %AppData%\Rime\
   schema/default.custom.yaml        → %AppData%\Rime\
   lua/*                             → %AppData%\Rime\lua\
   rime.lua                          → %AppData%\Rime\
   ```

4. 右鍵小狼毫圖示 → 重新部署

5. 在輸入法選單中選擇「拍台文(台)」

> **注意**：如果你已有 `default.custom.yaml`，請手動將 `phah_taibun` 加入 `schema_list` 而非直接覆蓋。
>
> 英文混打和 Emoji 功能需要 rime-ice 的 `melt_eng` 字典和 `opencc/emoji.json`，Windows 使用者可從 [rime-ice](https://github.com/iDvel/rime-ice) 取得這些檔案。

### 重新部署

安裝後必須重新部署 Rime：

- **fcitx5-rime**：右鍵系統匣圖示 → 重新部署（安裝腳本已自動執行）
- **ibus-rime**：`ibus restart`
- **鼠鬚管**（macOS）：點選選單列圖示 → 重新部署
- **小狼毫**（Windows）：右鍵系統匣圖示 → 重新部署

### 建議字體

安裝 [芫荽 iansui](https://github.com/ChhoeTaigi/iansui) 可獲得最佳台文顯示效果，特別是方音符號和特殊台文漢字。Linux 執行 `install.sh` 時會自動下載；macOS / Windows 請從 [GitHub Releases](https://github.com/ChhoeTaigi/iansui/releases) 手動下載安裝。

安裝字體後，還需要設定輸入法的候選區使用 iansui 字體：

#### fcitx5（Linux）

在 `~/.config/fcitx5/conf/classicui.conf` 加入：

```
Font="Iansui 12"
```

#### ibus（Linux）

開啟 ibus 偏好設定 → 外觀 → 字型 → 選擇「Iansui」。

#### 鼠鬚管 Squirrel（macOS）

建立或編輯 `~/Library/Rime/squirrel.custom.yaml`：

```yaml
patch:
  style/font_face: "Iansui"
  style/font_point: 18
```

儲存後點選選單列圖示 → 重新部署。

#### 小狼毫 Weasel（Windows）

建立或編輯 `%AppData%\Rime\weasel.custom.yaml`：

```yaml
patch:
  style/font_face: "Iansui"
  style/font_point: 14
```

儲存後右鍵系統匣圖示 → 重新部署。

---

## 二、基本輸入

### 台語拼音輸入

用台語拼音打字，候選區會列出漢字和羅馬字的候選：

```
輸入: gua beh khi tshit tho
候選: 我 beh 去 tshit-thô  [guá beh khì tshit-thô]
送出: 我 beh 去 tshit-thô
```

漢羅混寫自動處理：「我」「去」輸出漢字，「beh」「tshit-thô」依 LKK 規範輸出羅馬字。

### POJ 和 TL 都通

拍台文同時支援 POJ（白話字）和 TL（台羅）兩套拼音系統，不需要刻意區分：

```
TL 輸入:  tsiah png  → 食飯
POJ 輸入: chiah png  → 食飯（同樣結果）

TL 輸入:  gua ai li  → 我愛你
POJ 輸入: goa ai li  → 我愛你（同樣結果）
```

**POJ/TL 對照表**

| 音 | TL | POJ | 範例 |
|----|-----|-----|------|
| ㄗ | ts | ch | 食 tsiah / chiah |
| ㄘ | tsh | chh | 出 tshut / chhut |
| ㄐ | j | l | 入 ji̍p / li̍p |
| -ing | ing | eng | 命 miā / mēⁿ |
| -ua | ua | oa | 話 uē / oē |
| -ue | ue | oe | 飛 pue / poe |
| -oo | oo | ou/o͘ | 烏 oo / o͘ |
| 鼻音 | nn | ⁿ | 酸 sng / sⁿg |

### 聲調可省略

輸入時聲調完全可以省略，輸入法會自動列出所有可能的聲調候選：

```
完整拼音: gua2 beh4 khi3  → 我 beh 去
省略聲調: gua beh khi     → 我 beh 去（同樣結果）
```

**聲調數字對照**（寫了更精確，不寫也沒關係）

| 聲調 | 數字 | 範例 | 中文名 |
|------|------|------|--------|
| 第1聲 | 1 | kun1 (君) | 陰平 |
| 第2聲 | 2 | kun2 (滾) | 上聲 |
| 第3聲 | 3 | kun3 (棍) | 陰去 |
| 第4聲 | 4 | kut4 (骨) | 陰入 |
| 第5聲 | 5 | kun5 (群) | 陽平 |
| 第7聲 | 7 | kun7 (郡) | 陽去 |
| 第8聲 | 8 | kut8 (滑) | 陽入 |
| 第9聲 | 9 | 高升調 | （部分腔調） |

### 拼音註解

候選區永遠顯示讀音註解（方括號內），邊打邊學：

```
候選: 食飯 [tsiah8-png7]
      先生 [sian1-sinn1]
      學校 [hak8-hau7]
```

每個候選都標明完整的 TL 拼音和聲調，幫助你記住正確讀音。

---

## 三、輸出模式

### 四種輸出模式

拍台文提供四種輸出模式，用兩個開關組合：

| 開關 | 狀態 | 說明 |
|------|------|------|
| 漢羅/全羅 | 漢羅 | 依 LKK 規範，部分輸出漢字、部分輸出羅馬字 |
| | 全羅 | 全部輸出羅馬字 |
| TL/POJ | TL | 使用台羅拼音 |
| | POJ | 使用白話字拼音 |

組合出四種模式：

| 模式 | 輸出範例 |
|------|---------|
| 漢羅 TL（預設） | 我 beh 去 tshit-thô |
| 漢羅 POJ | 我 beh 去 chhit-thô |
| 全羅 TL | guá beh khì tshit-thô |
| 全羅 POJ | goá beh khì chhit-thô |

### 漢羅混寫

漢羅混寫是拍台文的核心功能。依照 LKK（李江却台語文教基金會）的用字規範：

- **常用漢字**（如：我、你、食、去、來）→ 輸出漢字
- **功能詞/虛詞**（如：beh、kah、hōo）→ 輸出羅馬字
- **無固定漢字**（如：tshit-thô）→ 輸出羅馬字

你不需要記住哪些字該用漢字、哪些用羅馬字——輸入法自動處理。

### 全羅輸出

切換到全羅模式後，候選清單仍顯示漢羅文字（方便辨識），但確定選字後輸出全羅拼音（帶 Unicode 調符）。適合：
- 純羅馬字書寫
- 教學用途（讓學生看到完整拼音）
- 不確定漢字時的替代方案

### 強制輸出羅馬字（`\` 反斜線）

在漢羅模式下，臨時需要某個候選的羅馬拼音？按 `\`（反斜線）即可輸出帶調符的全羅拼音，不需要切換模式。

```
候選: 食飯 [tsia̍h-pn̄g]
按 Space → 送出「食飯」（漢字）
按 \     → 送出「tsia̍h-pn̄g」（羅馬字）
```

輸出的羅馬字會依照目前的 TL/POJ 設定：
- **TL 模式** + `\` → 輸出 TL 拼音（如 `tsia̍h-pn̄g`）
- **POJ 模式** + `\` → 輸出 POJ 拼音（如 `chia̍h-pn̄g`）

切換 TL/POJ：按 `F4` → 選擇 TL 或 POJ。

### 模式切換

按 `F4` 打開方案選單，可以切換：
- 漢羅 ↔ 全羅
- TL ↔ POJ

---

## 四、以詞定字

從候選詞組中精準選取單字。

**用法：**

1. 打拼音，出現候選詞，例如打 `tsiah png` 出現「食飯」
2. 按 `[` 選取 **首字**（食）
3. 或按 `]` 選取 **尾字**（飯）

**範例：**

```
輸入: tsiah png
候選: 食飯 [tsiah8-png7]

按 [ → 送出「食」（首字）
按 ] → 送出「飯」（尾字）
```

這在打不確定的字時特別有用——先打一個包含目標字的詞，再從中選字。例如不確定「飯」怎麼打，但知道「食飯」這個詞，就可以打 `tsiah png` 再按 `]` 取「飯」。

> **注意**：翻頁模式下 `[` 和 `]` 會改為翻頁功能。

---

## 五、長詞優先

輸入法會自動將較長的候選詞提升到更前面的位置，減少逐字選字的次數。

**效果：**

```
輸入: gua beh khi tshit tho
候選排序:
  1. 我 beh 去 tshit-thô    ← 長詞組優先
  2. 我
  3. gua
  4. 食飯                    ← 多字詞被提升
  ...
```

長詞優先從第 4 個候選位置開始生效，最多提升 2 個候選。前 3 個位置保持原始排序，不會打亂你習慣的選字順序。

---

## 六、華語反查

不知道台語怎麼講？按 `~` 進入反查模式，用漢語拼音輸入華語，查看台語讀音。

**用法：**

1. 按 `~` 進入反查模式（候選區顯示「〔華語反查〕」）
2. 用漢語拼音打華語
3. 候選區顯示對應的台語讀音

```
~chi fan    → 食飯 tsia̍h-pn̄g
~piao liang → 媠 suí
~xue xiao   → 學校 ha̍k-hāu
```

按 `'`（單引號）或 `Escape` 結束反查模式。

> 反查功能需要 `luna_pinyin` 方案。如果反查沒反應，請確認已安裝 `librime-data` 或 `luna_pinyin` 方案。

---

## 七、萬用查字

不確定聲母時，用 `?` 代替，列出所有可能的搭配：

```
?iah  → 列出所有 -iah 結尾的字：
        tsiah（食）、siah（削）、jiah（跡）、liah（掠）...

?ang  → 列出所有 -ang 結尾的字：
        pang（放）、tang（當）、kang（工）、lang（人）...
```

**支援的聲母：**

| 類型 | 聲母 |
|------|------|
| 雙唇音 | p, ph, b, m |
| 舌尖音 | t, th, n, l |
| 舌根音 | k, kh, g, ng |
| 齒音 | ts, tsh, s, j |
| 喉音 | h |
| 零聲母 | （直接接韻母） |

---

## 八、造詞功能

按 `;`（分號）進入造詞模式，可以逐字輸入組合新詞：

```
;tsiah-png  → 造詞：tsiah-png (按 Enter 確認)
```

造好的詞會存入使用者詞庫，下次輸入時會自動出現。

---

## 九、符號輸入

按 `` ` ``（反引號）開啟符號選單：

**台羅調號：**
```
á à â ā a̍
é è ê ē e̍
í ì î ī i̍
ó ò ô ō o̍
ú ù û ū u̍
```

**POJ 特殊字母：**
```
o͘  ⁿ
```

**方音符號：**
```
ㆠ ㆣ ㄫ ㆢ ㆦ ㆤ
```

**台文標點：**
```
、。「」『』（）【】
```

---

## 十、Emoji 輸入

輸入台語時，候選區會自動顯示相關的 emoji：

```
輸入: sim  → 心 ❤️ 💜 💛
輸入: hue  → 花 🌸 🌺 💐
輸入: kau  → 狗 🐕 🐶
```

**開關 Emoji：**

按 `F4` 進入方案選單，可以開關 Emoji 候選（💀/😄）。

> Emoji 功能需要 `opencc/emoji.json` 檔案。如果沒有顯示，請確認已安裝 rime-ice 的 OpenCC 檔案。

---

## 十一、英文混打

直接打英文單字，不需要切換輸入法：

```
輸入: hello → hello (英文候選)
輸入: thank → thank, thanks, thanksgiving...
```

英文候選會出現在台語候選之後（較低優先順序），不會干擾正常台語輸入。英文補全自動開啟，打前幾個字母就會出現候選。

> 英文混打需要 `melt_eng` 字典。如果沒有英文候選，請確認已安裝 rime-ice 的 melt_eng 檔案。

---

## 十二、簡拼提示

打 `vvsp` 顯示常用的拼音縮寫對照表：

| 詞 | 完整拼音 | 簡拼 |
|----|----------|------|
| 食飯 | tsiah-png | cp |
| 出去 | tshut-khi | ck |
| 台灣 | tai-oan | to |
| 學校 | hak-hau | hh |
| 先生 | sian-sinn | ss |
| 囡仔 | gin-a | ga |
| 厝裡 | tshu-lai | cl |

簡拼規則：取每個音節的聲母首字母。例如 `tsiah-png` → `cp`（ts 的首字母 c + p）。

---

## 十三、台語日期

打 `vvjit` 輸出今天日期，三種格式可選：

```
vvjit → 2026年3月15 拜六
      → 2026 nî 3 gue̍h 15 Pài-la̍k
      → 2026-03-15
```

---

## 十四、快捷鍵總覽

### 功能鍵

| 按鍵 | 功能 | 說明 |
|------|------|------|
| `F4` | 方案選單 | 切換輸出模式（漢羅/全羅、TL/POJ）、開關 emoji |
| `~` | 華語反查 | 用漢語拼音查台語讀音 |
| `` ` `` | 符號選單 | 台羅調號、方音符號、台文標點 |
| `?` | 萬用字元 | 代替不確定的聲母，列出所有可能 |
| `;` | 造詞模式 | 逐字輸入組合新詞 |
| `[` | 以詞定字（首字） | 選取候選詞的第一個字 |
| `]` | 以詞定字（尾字） | 選取候選詞的最後一個字 |
| `vvh` | 按鍵說明 | 在候選區顯示所有快捷鍵 |
| `vvjit` | 台語日期 | 輸出今天日期 |
| `vvsp` | 簡拼對照 | 顯示聲母縮寫對照表 |

### 編輯鍵

| 按鍵 | 功能 |
|------|------|
| `Space` | 確認選字 |
| `\` | 強制輸出羅馬字（帶調符，任何模式皆可） |
| `Enter` | 直接送出拼音原文 |
| `Ctrl+Enter` | 送出轉換後的文字 |
| `Backspace` | 還原上一步 |
| `Ctrl+Backspace` | 刪除前一個音節 |
| `Escape` | 取消輸入 |
| `Tab` | 跳到下一個音節 |
| `Shift+Tab` | 跳到上一個音節 |

### 翻頁鍵

| 按鍵 | 功能 |
|------|------|
| `[` | 上一頁（翻頁模式） |
| `]` | 下一頁（翻頁模式） |

> 注意：`[` 和 `]` 在組字狀態下是以詞定字，在翻頁狀態下才是翻頁。

---

## 十五、進階設定

### 自訂詞庫

在 Rime 使用者目錄中建立 `phah_taibun_custom.txt`，格式為每行一個詞條：

```
# 自訂詞庫
食飯	tsiah8-png7
```

自訂詞條會優先於內建字典出現。

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

**建置流程**涵蓋 11 個步驟：
1. 從 7 個語料庫提取詞頻（iCorpus、Ungian、康軒課本、900例句、NMTL 文學、KipSutian、白話字文獻）
2. 合併 ChhoeTaigi 9 本辭典 CSV，加上語料庫頻率加權
3. 解析 LKK 漢羅規則和輕聲規則
4. 建置反查字典（KipSutian 65K 筆，或 MOE 24K 筆備用）
5. 從所有語料庫句子提取雙字詞組（bigram phrases）
6. 驗證生成的字典

---

## 十六、疑難排解

### 安裝後找不到「拍台文」方案

1. 確認已重新部署 Rime
2. 按 `F4` 查看方案清單，確認「拍台文(台)」在列表中
3. 檢查 `default.custom.yaml` 是否包含 `phah_taibun`

### 候選區沒有顯示拼音註解

確認 Lua 模組已正確安裝：

```bash
# Linux (fcitx5)
ls ~/.local/share/fcitx5/rime/lua/phah_taibun_*.lua

# macOS
ls ~/Library/Rime/lua/phah_taibun_*.lua

# Windows
dir %AppData%\Rime\lua\phah_taibun_*.lua
```

應該要有 13 個 `phah_taibun_*.lua` 檔案。

### 華語反查 `~` 沒有反應

反查依賴 `luna_pinyin` 方案，確認已安裝：

```bash
# Linux
ls /usr/share/rime-data/luna_pinyin.schema.yaml

# macOS
ls /Library/Input\ Methods/Squirrel.app/Contents/SharedSupport/luna_pinyin.schema.yaml
```

若未安裝，安裝 `librime-data` 套件：

```bash
# Arch Linux
sudo pacman -S librime-data

# Ubuntu/Debian
sudo apt install librime-data-luna-pinyin

# macOS (透過鼠鬚管安裝即包含)
```

### Emoji 或英文混打無效

這兩個功能需要 rime-ice 的額外檔案：

- **Emoji**：需要 `opencc/emoji.json` 和 `opencc/emoji.txt`
- **英文**：需要 `melt_eng.dict.yaml` 和 `melt_eng.schema.yaml`

可以從 [rime-ice](https://github.com/iDvel/rime-ice) 取得這些檔案，放到 Rime 使用者目錄即可。

### Lua 錯誤導致候選區異常

查看 Rime 日誌：

```bash
# Linux
cat /tmp/rime.*.INFO | grep -i "lua\|error"

# macOS
cat /tmp/rime.*.INFO | grep -i "lua\|error"
```

若出現 Lua 載入錯誤，確認 `rime.lua` 已安裝到 Rime 使用者目錄根：

```bash
# Linux (fcitx5)
cat ~/.local/share/fcitx5/rime/rime.lua | grep phah_taibun

# macOS
cat ~/Library/Rime/rime.lua | grep phah_taibun
```

### 重新安裝

```bash
cd rime-phah-taibun
./install.sh
```

安裝腳本會更新所有檔案（不會覆蓋你的自訂詞庫）。

---

## 資料來源與致謝

| 資料 | 用途 |
|------|------|
| [ChhoeTaigi](https://github.com/ChhoeTaigi/ChhoeTaigiDatabase) | 主字典（9 本辭典，170K 條目） |
| [LKK 用字表](https://tsbp.tgb.org.tw/p/bong_8.html) | 漢羅轉換規則 |
| [教育部台語辭典](https://github.com/ChhoeTaigi/KipSutianDataMirror) | 反查字典 + 例句語料 |
| [iCorpus](https://github.com/Taiwanese-Corpus/icorpus_ka1_han3-ji7) | 新聞語料詞頻 |
| [Ungian 2009](https://github.com/Taiwanese-Corpus/Ungian_2009_KIPsupin) | 文學語料詞頻 |
| [康軒課本](https://github.com/Taiwanese-Corpus/kok4hau7-kho3pun2) | 國小台語課本詞頻 |
| [常用900例句](https://github.com/Taiwanese-Corpus/Sin1pak8tshi7_2015_900-le7ku3) | 日常高頻詞彙 |
| [NMTL 文學作品](https://github.com/Taiwanese-Corpus/nmtl_2006_dadwt) | 台語文學語料 |
| [白話字文獻](https://github.com/Taiwanese-Corpus/Khin-hoan_2010_pojbh) | 歷史 POJ 語料 |
| [rime-liur](https://github.com/ryanwuson/rime-liur) | Lua 模組架構參考 |
| [rime-ice](https://github.com/iDvel/rime-ice) | UX 功能參考 |

**致謝：**

- [李江却台語文教基金會](https://www.tgb.org.tw/) — 漢羅用字規範
- [ChhoeTaigi 找台語](https://chhoe.taigi.info/) — 開放辭典平台
- [ryanwuson/rime-liur](https://github.com/ryanwuson/rime-liur) — Lua 模組架構參考
- [iDvel/rime-ice](https://github.com/iDvel/rime-ice) — UX 功能參考
- [教育部臺灣台語常用詞辭典](https://sutian.moe.edu.tw/) — 反查字典資料
- [楊允言教授](http://ip194097.ntcu.edu.tw/Ungian/) — 台語文學語料庫
- [Taiwanese-Corpus](https://github.com/Taiwanese-Corpus) — 多語料庫資料
- [意傳科技 i3thuan5](https://github.com/i3thuan5) — 臺灣言語工具
