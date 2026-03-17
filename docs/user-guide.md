# 拍台文 Phah Tai-bun 使用說明

**Rime 台語輸入法方案** — 漢羅混寫輸出，POJ/TL 雙拼音系統，聲調可省略。

專為「會講台語但不太會打台文」的人設計。不需要分辨 POJ 和 TL、不需要打聲調、不需要知道漢羅規則，輸入法全部幫你處理。

---

## 一、安裝方式

### 安裝需求

- [Rime 輸入法引擎](https://rime.im/)（fcitx5-rime、ibus-rime、鼠鬚管 或小狼毫）
- `bopomofo_tw` 方案（注音反查需要，大部分 Rime 安裝已內建）
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
4. 檢查反查所需的 `bopomofo_tw` 方案是否存在
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

Windows 使用者需先安裝 [小狼毫 Weasel](https://rime.im/download/)。

#### 自動安裝（推薦）

```
git clone https://github.com/soanseng/rime-phah-taibun.git
cd rime-phah-taibun
powershell -ExecutionPolicy Bypass -File scripts\install_windows.ps1
```

安裝腳本會自動：
1. 複製方案檔和 Lua 腳本到 `%AppData%\Rime`
2. 註冊拍台文到方案清單（不覆蓋現有方案）
3. 下載芫荽 iansui 字體
4. 提示手動重新部署

#### 手動安裝

如果 PowerShell 腳本無法執行，也可以手動安裝：

1. 下載或 clone 本專案
2. 找到 Rime 使用者目錄：右鍵小狼毫系統匣圖示 → 用戶文件夾（通常在 `%AppData%\Rime`）
3. 複製以下檔案：
   ```
   schema/phah_taibun.schema.yaml       → %AppData%\Rime\
   schema/phah_taibun.dict.yaml         → %AppData%\Rime\
   schema/phah_taibun_reverse.dict.yaml → %AppData%\Rime\
   schema/hanlo_rules.yaml              → %AppData%\Rime\
   schema/lighttone_rules.json          → %AppData%\Rime\
   lua/phah_taibun_*.lua                → %AppData%\Rime\lua\
   rime.lua                             → %AppData%\Rime\
   ```
4. 編輯 `%AppData%\Rime\default.custom.yaml`，在 `schema_list` 中加入 `- schema: phah_taibun`
5. 右鍵小狼毫圖示 → 重新部署
6. 在輸入法選單中選擇「拍台文(台)」

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

加上聲調數字可以縮小候選範圍，更精準找到目標字：

```
to  → 列出所有聲調：多(to1)、倒(to2)、度(to7)...
to1 → 只列出第1聲：多、刀...
to2 → 只列出第2聲：倒、島...
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
| 全羅 POJ | góa beh khì chhit-thô |

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

全羅模式特有功能：
- **半形標點**：標點符號自動輸出半形（`.` `,` `!` `?` 等），符合羅馬字書寫慣例
- **句首大寫**：句號、驚嘆號、問號後自動大寫下一個字的首字母
- **調符規則**：遵循[教育部台羅拼音方案](https://language.moe.gov.tw/001/Upload/FileUpload/3677-15601/Documents/tshiutsheh_1081017.pdf)標記規則

### 反斜線 `\`：切換輸出模式（當前候選）

按 `\` 可以臨時切換當前候選的輸出模式，不需要切換全局設定：

**漢羅模式下按 `\`** → 輸出全羅拼音（帶調符）：

```
候選: 食飯 [tsia̍h-pn̄g]
按 Space → 送出「食飯」（漢羅）
按 \     → 送出「tsia̍h-pn̄g」（全羅）
```

**全羅模式下按 `\`** → 輸出漢羅混寫：

```
候選: 食飯 [tsia̍h-pn̄g]
按 Space → 送出「tsia̍h-pn̄g」（全羅）
按 \     → 送出「食飯」（漢羅）
```

輸出的羅馬字會依照目前的 TL/POJ 設定：
- **TL 模式** + `\` → TL 拼音（如 `tsia̍h-pn̄g`）
- **POJ 模式** + `\` → POJ 拼音（如 `chia̍h-pn̄g`）

切換 TL/POJ：按 `F4` → 選擇 TL 或 POJ。

### 模式切換

按 `F4` 打開方案選單，可以切換：
- 漢羅 ↔ 全羅
- TL ↔ POJ

### 台文/英文切換

按 `Ctrl+Space` 切換台文和英文輸入模式。

> 注意：Shift 鍵**不會**切換到英文模式。Shift+字母 是用來打大寫字母的（見下方「大寫字母」）。

---

## 三之一、選字模式（Tab）

打完拼音後，按 `Tab` 進入選字模式，用 **asdf** 從候選清單中選字。

### 流程

```
Step 1: 打拼音 tsiah8png7 → 候選字出現
Step 2: 按 Tab → 進入選字模式（顯示「選字：asdf 選字／Esc 取消」提示）
Step 3: 按 a 選第一個、s 選第二個、d 選第三個...
        或按 Space 確認目前高亮的候選（通常是第一個）
```

### 選字模式中的按鍵

| 按鍵 | 功能 |
|------|------|
| `a s d f g h j k l ;` | 選取第 1-10 個候選 |
| `Space` | 確認目前高亮的候選 |
| `↑ ↓ PgUp PgDn` | 翻頁瀏覽 |
| `0-9` | 退出選字模式，當作聲調數字輸入 |
| `Escape` | 退出選字模式，回到拼音編輯 |
| 其他字母 | 自動退出選字模式，繼續輸入 |

> **Tab 的雙重功能**：候選字出現時按 Tab 進入選字模式；候選字沒出現時（還在打拼音），Tab 跳到下一個音節。
>
> **數字鍵保留給聲調**：選字模式中按數字鍵會退出選字模式並加入聲調（例如按 `1` 加入第一聲），不會當作選字鍵。需要選字請用 `asdf`。

### 大寫字母

在台文模式下，按 Shift+字母可以打出大寫字母，不會切換到英文模式。適合：

- **句首大寫**：全羅模式寫句子時的句首
- **專有名詞**：如 Tâi-pak（台北）、Hàn-jī（漢字）

> Caps Lock 維持系統預設功能，可以鎖定連續大寫（例如打 "HTML"）。

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

## 六、注音反查（華→台）

不知道台語怎麼講？按 `~` 進入反查模式，用注音找華語字，選字後自動轉換成台語候選。

### 基本流程

1. 按 `~` 進入反查模式（候選區顯示「〔注音反查〕」）
2. 用注音打華語（使用標準注音鍵盤配置）
3. 候選區出現華語字，並標注台語 TL 讀音
4. **選字後，自動把台語拼音送回主輸入**，出現台語漢字候選
5. 從台語候選中選字輸出

### 範例

```
Step 1: 按 ~ 進入反查
Step 2: 打 ㄔ → 出現「吃」（標注台語讀音）
Step 3: 選「吃」→ 自動轉換：查到台語 tsiah8
Step 4: 主輸入出現 tsiah8 的候選：食、炸、即...
Step 5: 選「食」→ 輸出
```

### 華→台自動轉換

拍台文內建 **77,000 筆華語→台語對照表**（從 ChhoeTaigi 資料庫建置），即使華語字和台語字不同也能正確轉換：

| 華語字 | 台語對應 | TL 碼 |
|--------|---------|-------|
| 吃 | 食 | tsiah8 |
| 好 | 好 | ho2 |
| 飯 | 飯 | png7 |
| 漂亮 | 媠 | sui2 |
| 學校 | 學校 | hak8 hau7 |
| 謝謝 | 多謝 | to sia7 |
| 朋友 | 朋友 | ping5 iu2 |

如果某個華語字在對照表中找不到，會直接輸出該字（不做轉換）。

> 反查功能需要 `bopomofo_tw` 方案。如果反查沒反應，請確認已安裝 `librime-data` 或 `bopomofo_tw` 方案。

---

## 七、萬用查字（二段式）

不確定聲母時，用 `?` 代替。拍台文採用**二段式查字**，先選音節再選字：

### 流程

```
Step 1: 打 ?iah
        → 列出所有可能的音節模式：
          tsiah (18個字)
          siah  (9個字)
          liah  (12個字)
          giah  (8個字)
          ...

Step 2: 選 tsiah
        → 拼音送回主輸入，出現所有 tsiah 的字：
          食、炸、即、脊、隻...

Step 3: 選字輸出
```

### 使用情境

**情境 1**：知道韻母但不確定聲母
```
?ang → 看到 lang (12字) → 選 lang → 出現「人、郎、狼...」
```

**情境 2**：想找某個韻尾的所有字
```
?oo → 看到 hoo (25字)、boo (8字)、koo (15字)...
     → 一覽所有 -oo 韻的字
```

### 支援的聲母

| 類型 | 聲母 |
|------|------|
| 雙唇音 | p, ph, b, m |
| 舌尖音 | t, th, n, l |
| 舌根音 | k, kh, g, ng |
| 齒音 | ts, tsh, s, j |
| 喉音 | h |
| 零聲母 | （直接接韻母） |

---

## 八、造詞模式

按 `;`（分號）+ 拼音，直接從字典查字，逐字選取組詞。

### 基本用法

```
;tsiah → 從字典查 tsiah，出現候選：
         食、炸、即、脊、隻、跡...
       → 選字輸出
```

### 使用情境

**逐字組詞**：想打一個字典裡沒有的新詞，可以用造詞模式一個字一個字選：

```
;tsiah → 選「食」→ 輸出「食」
;png   → 選「飯」→ 輸出「飯」
結果：食飯
```

**查找單字**：不確定某個拼音對應哪些字時，用造詞模式快速瀏覽：

```
;ho → 出現所有 ho 開頭的字：好、虎、府、湖...
```

> 造詞模式不會影響你的使用者詞庫。若想永久保存新詞，請編輯 Rime 使用者目錄中的自訂詞庫。

---

## 八之一、同音選字

輸入後按 `'`（單引號）查看同音字。

### 用法

1. 正常打字，選字送出（例如打 `ho2` 選「好」）
2. **緊接著**按 `'`
3. 輸入法查詢「好」的台語讀音（ho2），列出所有同音字
4. 從同音字中選取

### 使用情境

**選錯字時快速修正**：打了「好」但其實要「虎」（同樣是 ho2），按 `'` 就能看到所有 ho2 的字。

> 注意：`'` 同音選字只在**剛送出一個字之後**有效（一次性觸發）。如果中間按了其他鍵，效果會消失。

---

## 八之二、輕聲（Light Tone）

台語的輕聲會改變語意，拍台文自動辨識並提供輕聲候選。

### 輕聲是什麼

台語中某些後綴詞（如「來」「去」「起來」等）在特定語法位置會失去原調，以 `--` 標記。輕聲與非輕聲的語意不同：

| 原詞 | 輕聲形式 | 意思差異 |
|------|---------|---------|
| 後日 āu-ji̍t | 後--日 āu--ji̍t | 以後 → 後天 |
| 轉來 tńg-lâi | 轉--來 tńg--lâi | 回來（強調動作 → 輕聲語法） |
| 食飽 tsia̍h-pá | 食--飽 tsia̍h--pá | 吃飽（結果補語） |

### 使用方式

輸入時不需要特別標記輕聲，輸入法會自動提供輕聲候選：

```
輸入: au jit
候選: 後日 [āu-ji̍t]        ← 以後、將來
      後--日 [āu--ji̍t]     ← 後天（輕聲變體，自動產生）

輸入: tng lai
候選: 轉來 [tńg-lâi]       ← 回來
      轉--來 [tńg--lâi]    ← 回來（輕聲）
```

### 輕聲候選來源

1. **字典內建**：29,000+ 筆輕聲詞條，從 7 個語料庫自動擷取，涵蓋常見的輕聲搭配
2. **即時產生**：根據 111 條輕聲規則（教育部資料），動態為候選詞加上輕聲變體

---

## 八之三、調符標記規則

全羅模式輸出的調符位置遵循[教育部台羅拼音方案使用手冊](https://language.moe.gov.tw/001/Upload/FileUpload/3677-15601/Documents/tshiutsheh_1081017.pdf)：

**優先順序**：`a > oo > e > o`；`i` 和 `u` 同時出現時，前者為介音，後者為主要元音（標在後者）。

| 拼音 | 調符位置 | 說明 |
|------|---------|------|
| `gua2` | guá | 有 a → 標在 a |
| `ue2` | ué | 有 e → 標在 e |
| `io2` | ió | 有 o → 標在 o |
| `ui7` | uī | i,u 同時出現 → 標在後者 i |
| `iu5` | iû | i,u 同時出現 → 標在後者 u |
| `oo7` | ōo | oo 標在第一個 o |
| `ng2` | ńg | 韻化輔音 |
| `ere5` | erê | 三字母雙元音 → 標在後面的 e |

**POJ 差異**：POJ 的調符位置在部分韻母與 TL 不同：

| 韻母 | TL | POJ | 規則 |
|------|-----|-----|------|
| ua/oa（開音節） | guā | gōa | POJ 標在 o |
| ua/oa（有韻尾） | kuán | koán | 有韻尾時標在 a |
| ua/oa + ⁿ | khuàⁿ | khòaⁿ | ⁿ 是鼻化不是韻尾，標在 o |
| ue/oe | hué | hōe | POJ 標在 o |
| ui | uī | ūi | POJ 標在前者 u |
| iu | iû | îu | POJ 標在前者 i |

**羅馬字書寫規則**：
- 句首第一個字母大寫（全羅模式自動處理）
- 專有名詞第一個字母大寫
- 逗號、句點使用半形（全羅模式自動處理）

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

## 十四、實戰教學

### 教學一：打一段台語短文

目標文字（漢羅TL模式）：

> 今仔日天氣真好，我 beh 去公園散步。

打字步驟：

| 步驟 | 輸入 | 候選 | 說明 |
|------|------|------|------|
| 1 | `kin a jit` | 今仔日 [kin-á-ji̍t] | 聲調省略，直接打 |
| 2 | `thinn khi` | 天氣 [thinn-khì] | 選候選 |
| 3 | `tsin` | 真 [tsin] | 單字 |
| 4 | `ho` | 好 [hó] | 聲調省略 |
| 5 | `,` | ， | 標點 |
| 6 | `gua` | 我 [guá] | |
| 7 | `beh` | beh [beh] | 自動輸出羅馬字（LKK 規範） |
| 8 | `khi` | 去 [khì] | |
| 9 | `kong hng` | 公園 [kong-hn̂g] | 多字詞 |
| 10 | `san poo` | 散步 [sàn-pōo] | |

注意第 7 步：`beh` 自動輸出羅馬字而非漢字。這是因為 LKK 規範將 `beh` 分類為「應使用羅馬字」的功能詞。你不需要記住這些規則——輸入法自動處理。

### 教學二：用注音反查找台語字

情境：你想打「漂亮」的台語，但不知道台語怎麼說。

```
Step 1: 按 ~ 進入反查模式
Step 2: 打注音 ㄆㄧㄠˋ ㄌㄧㄤˋ
Step 3: 出現「漂亮」→ 選它
Step 4: 自動查到台語 sui2 khui3 → 出現台語候選
Step 5: 選「媠氣」→ 輸出
```

### 教學三：用萬用查字找忘記的字

情境：你記得一個字的韻母是 `-iah`，但忘記聲母了。

```
Step 1: 打 ?iah
Step 2: 看到音節列表：tsiah (18字), liah (12字), siah (9字)...
Step 3: 選 liah → 出現：掠、拿、略...
Step 4: 選「掠」→ 輸出
```

### 教學四：POJ 使用者無痛轉移

如果你習慣 POJ，完全不需要改變打字習慣：

| POJ 輸入 | TL 輸入 | 結果 |
|----------|---------|------|
| `chiah png` | `tsiah png` | 食飯 |
| `goa ai li` | `gua ai li` | 我愛你 |
| `chhut khi` | `tshut khi` | 出去 |
| `chit8 tho5` | `tshit tho` | tshit-thô |

兩套拼音混打也沒問題：`goa beh khi`（POJ 的 goa + TL 的 khi）一樣能找到「我 beh 去」。

---

## 十五、與其他台語輸入法的比較

### 比較表

| 功能 | 拍台文 | 信望愛台語輸入法 | 教育部台語輸入法 |
|------|--------|-----------------|----------------|
| **平台** | Linux / macOS / Windows | Windows / macOS | Windows / macOS / 手機 |
| **Linux 支援** | fcitx5 + ibus | 無 | 無 |
| **開源** | MIT 授權 | 非開源 | 政府專案 |
| **拼音系統** | TL + POJ 雙系統，可混打 | TL + POJ | TL（自動轉換） |
| **聲調** | **完全可省略** | 需輸入 | 需輸入 |
| **漢羅混寫** | **自動（LKK 規範）** | 有 | 無（純漢字或純羅馬字） |
| **字典規模** | 170K 條目 | 未公開 | ~24K 條目 |
| **語料庫詞頻** | **7 語料庫加權** | 無 | 基本頻率 |
| **注音反查** | **華→台自動轉換** | 無 | 無 |
| **萬用查字** | **?（二段式）** | 無 | 無 |
| **以詞定字** | **[ 首字 ] 尾字** | 無 | 無 |
| **同音選字** | **' 鍵** | 無 | 無 |
| **Emoji** | 自動顯示 | 無 | 有 |
| **英文混打** | 內建 | 無 | 無 |
| **輕聲辨識** | **29K 詞條 + 即時產生** | 無 | 無 |
| **自訂擴充** | Lua 模組（14 個） | 無 | 無 |

### 拍台文的核心差異

**1. 聲調完全可省略**

其他輸入法都需要輸入聲調數字（1-8），例如打「食飯」要輸入 `tsiah8 png7`。拍台文允許直接打 `tsiah png`，甚至只打聲母 `cp`，大幅降低打字門檻。

**2. 漢羅混寫自動化**

信望愛輸入法有漢羅模式，但需要使用者自行判斷哪些字用漢字、哪些用羅馬字。拍台文依據 LKK 李江却台語文教基金會的用字規範，自動決定——使用者打同一串拼音，輸出時「食」用漢字、「beh」用羅馬字。

**3. 華→台反查轉換**

教育部和信望愛都沒有「用華語查台語」的功能。拍台文的注音反查不只是「看到華語字旁邊標台語讀音」——選了華語字後會**自動把台語拼音送回主輸入**，讓你直接從台語候選中選字。內建 77K 筆華→台對照表。

**4. 語料庫智慧排序**

字典的候選排序不只是靠辭典的基本頻率，而是整合 7 個台語語料庫（新聞、文學、課本、例句、辭典例句、白話字文獻）的實際使用頻率，用對數加權計算。日常用語排更前面。

**5. Linux 原生支援**

拍台文是目前**唯一支援 Linux 桌面**的台語輸入法（fcitx5-rime 和 ibus-rime），適合使用 Linux 的開發者、學生和台文工作者。

### 誰適合用哪個

| 你的需求 | 推薦 |
|---------|------|
| 會講台語但不太會打台文 | **拍台文**（聲調可省、漢羅自動） |
| 台文寫作（文學、報導） | **拍台文**（LKK 規範）或 **信望愛**（漢羅模式） |
| 台語學習中 | **拍台文**（拼音註解、注音反查、萬用查字） |
| Linux 使用者 | **拍台文**（唯一選擇） |
| 不想裝 Rime、只要簡單打字 | **教育部**（官方維護、手機也能用） |
| Windows 使用者，不想折騰 | **信望愛**（安裝簡單） |

---

## 十六、快捷鍵總覽

### 功能鍵

| 按鍵 | 功能 | 說明 |
|------|------|------|
| `Ctrl+Space` | 台文/英文切換 | 切換台文和英文輸入模式 |
| `F4` | 方案選單 | 切換輸出模式（漢羅/全羅、TL/POJ）、開關 emoji |
| `~` | 注音反查 | 用注音輸入華語→自動轉台語候選 |
| `` ` `` | 符號選單 | 台羅調號、方音符號、台文標點 |
| `?` | 萬用查字 | 二段式：先選音節再選字 |
| `;` | 造詞模式 | 查字典選字（;拼音） |
| `'` | 同音選字 | 輸入後按 ' 查同音字 |
| `[` | 以詞定字（首字） | 選取候選詞的第一個字 |
| `]` | 以詞定字（尾字） | 選取候選詞的最後一個字 |
| `vvh` | 按鍵說明 | 在候選區顯示所有快捷鍵 |
| `vvjit` | 台語日期 | 輸出今天日期 |
| `vvsp` | 簡拼對照 | 顯示聲母縮寫對照表 |

### 編輯鍵

| 按鍵 | 功能 |
|------|------|
| `Space` | 確認選字 |
| `Tab` | 候選出現時：進入選字模式（asdf/數字鍵選字）；否則：跳到下一個音節 |
| `Shift+字母` | 打大寫字母（不會切換到英文） |
| `\` | 強制輸出羅馬字（帶調符，任何模式皆可） |
| `Enter` | 直接送出拼音原文 |
| `Ctrl+Enter` | 送出轉換後的文字 |
| `Backspace` | 還原上一步 |
| `Ctrl+Backspace` | 刪除前一個音節 |
| `Escape` | 取消輸入（選字模式中：退出選字模式） |
| `Shift+Tab` | 跳到上一個音節 |

### 翻頁鍵

| 按鍵 | 功能 |
|------|------|
| `[` | 上一頁（翻頁模式） |
| `]` | 下一頁（翻頁模式） |

> 注意：`[` 和 `]` 在組字狀態下是以詞定字，在翻頁狀態下才是翻頁。

---

## 十七、進階設定

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

## 十八、疑難排解

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

應該要有 15 個 `phah_taibun_*.lua` 檔案。

### 注音反查 `~` 沒有反應

反查依賴 `bopomofo_tw` 方案，確認已安裝：

```bash
# Linux
ls /usr/share/rime-data/bopomofo_tw.schema.yaml

# macOS
ls /Library/Input\ Methods/Squirrel.app/Contents/SharedSupport/bopomofo_tw.schema.yaml
```

若未安裝，安裝 `librime-data` 套件：

```bash
# Arch Linux
sudo pacman -S librime-data

# Ubuntu/Debian
sudo apt install librime-data-bopomofo

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
| [教育部台羅拼音方案使用手冊](https://language.moe.gov.tw/001/Upload/FileUpload/3677-15601/Documents/tshiutsheh_1081017.pdf) | 調符標記規則、羅馬字書寫規範 |
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

---

*最後更新：2026-03-17*
