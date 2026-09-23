# 拍台文 Trime 包（Android）

解壓後就是要放進 **Rime 使用者資料夾**的內容。Releases 提供**兩種包，自己選**：

| 包 | 內容 | 適合 |
|----|------|------|
| `PhahTaiBun-Trime.zip`（輕量版） | 拍台文（漢羅＋Telex）、注音 `bopomofo_tw`、`~` 反查依賴 | 只想打台文，下載快（約 3.5 MB） |
| `PhahTaiBun-Trime-liur.zip`（嘸蝦米版） | 再加嘸蝦米 `liur`＋`easy_en` 英文詞庫（約 20 MB） | 台文＋中文都用嘸蝦米打 |

兩種包的拍台文內容完全相同；差別只在嘸蝦米版多出 `liur.*`、`lua/liu_*.lua`、`opencc/` 與 `LIUR-PROVENANCE.txt`（記錄檔案集來源與 commit）。`~` 反查所需的 `terra_pinyin.dict.yaml` 與 bopomofo 方案檔兩種都附，不需另外下載。

**不含**：字體（要芫荽字體請自行放 `fonts/`，見 [iansui](https://github.com/ButTaiwan/iansui)）、使用者詞庫與學習紀錄。

---

## 嘸蝦米版的來源標示

嘸蝦米檔案集來自 [soanseng/rime-liur-arch](https://github.com/soanseng/rime-liur-arch)（fork 自 `ryanwuson/rime-liur`）。上游未附具名授權檔，README 宣告「本專案基於開源授權發佈，歡迎使用和改進」；本專案依該宣告隨包散布，並以 `LIUR-PROVENANCE.txt` 標示來源 repo、commit 與此宣告。若上游日後補上正式授權條款，以其條款為準。不想用嘸蝦米就下載輕量版；已裝了想移除，刪掉 `liur*`、`easy_en*`、`allbpm*`、`Mount_bopomo*`、`liur_symbols*`、`terra_pinyin_onion*`、`openxiami*`、`phrases.chtp.dict.yaml`、`essay-zh-hant-*`、`lua/liu_*.lua`、`lua/lunar_calendar/`、`opencc/`，並把 `default.custom.yaml` 裡的 `liur`／`easy_en` 兩行刪掉即可。

---

## 一、解壓到使用者資料夾

先看 App 顯示的路徑，不要猜。

**同文 Trime**：`Android/data/com.osfans.trime/files/rime`（Trime 3.3.12 起可用 App 內的 SAF 匯入流程，選這個資料夾即可）。
Android 11+ 多數檔案總管進不去 `Android/data`，請用電腦 USB／MTP，或 Trime 內建的檔案管理。

**fcitx5-android**：輸入法設定 → Rime → 齒輪 → **User data dir**，把內容放進該目錄下的 `data/rime`。

解壓後結構（`lua/` 要維持子目錄）：

```
rime/
├── phah_taibun.schema.yaml   phah_taibun_telex.schema.yaml
├── phah_taibun.dict.yaml     hanlo_rules.yaml  hoabun_map.txt
├── lighttone_rules.json      moe700.yaml
├── bopomofo.schema.yaml      bopomofo_tw.schema.yaml  zhuyin.yaml
├── terra_pinyin.dict.yaml
├── default.custom.yaml       rime.lua           INSTALL-Trime.md
├── trime.custom.yaml         THIRD-PARTY-NOTICES.txt   LICENSE-PhahTaiBun.txt
├── licenses/  （LGPL-3.0.txt、GPL-3.0.txt）
└── lua/       （拍台文 19 個模組；嘸蝦米版另含 liu_* 與 lunar_calendar/）
```

（嘸蝦米版在此之上另有 `liur.schema.yaml`、`liur.custom.yaml`、詞表與 `opencc/`、`LIUR-PROVENANCE.txt`。）

## 二、重新部署

同文：選單 → **重新部署**；小企鵝：Rime 設定 → **Deploy**。
第一次部署要編譯約 5 MB 主字典，可能數分鐘，**不要把 App 滑掉**。

## 三、選方案

系統輸入法選同文或小企鵝，再**在 App 的方案清單**選「拍台文（台）」、「拍台文（Telex）」或「注音·臺灣正體」。

Android **不是**桌面的 `F4`，也不要用桌面快捷鍵。

測試：拍台文打 `gua beh khi tshit tho` → 應出現「我 beh 去 tshit-thô」。

---

## 四、Android 按鍵對照

桌面快捷鍵在手機上不存在。下表是每個功能在**同文內建「拼音」鍵盤**的位置（長按＝按住該鍵）；括號內是 Trime 的設定來源，已對 Trime v3.3.12 內建 `trime.yaml` 核對。

| 功能 | 桌面 | Android（同文） |
|------|------|-----------------|
| 方案選單 | `F4`／`` Ctrl+` `` | App 的方案選單（長按中英鍵）；或自訂鍵 `Schema_switch` |
| 台文↔英文 | `Ctrl+Space` | 中英鍵（`Mode_switch`，內建即 `toggle: ascii_mode`） |
| 確認候選 | `Space` | 空白鍵；或直接**點候選** |
| 候選換頁 | `PageUp/Down` | 候選列左右滑；內建鍵盤 `f`／`g` 長按 |
| 以詞定字（首字／尾字） | `[`／`]` | 長按 `u`／`i` |
| 目前候選切漢羅↔全羅 | `\` | 長按 `y` |
| 華語注音反查（輸入注音查漢字，候選附台語讀音） | `~` | 長按 `b` |
| 上屏後同音選字（取回該字詞台語讀音重新組音） | `'` | `'` |
| 符號選單 | `` ` `` | 長按 `z` |
| 萬用查字 | `?` | 長按 `/` |
| 造詞模式 | `;` | `;` |
| 句首／專名大寫 | `Shift+字母` | Shift 鍵（單按切換、長按鎖定） |
| 全羅模式直送 | `Enter` | Enter |
| 按鍵說明／日期／簡拼 | `vvh`／`vvjit`／`vvsp` | 連打 v v h 等 |

**模式開關**（漢羅／全羅、TL／POJ、半形／全形、台文／英文）走 schema 的 `switches`，在 App 的**開關面板**切換（Trime 的 `SwitchOptionWindow`），不是桌面的 `F4`。切過的狀態會記住。

**手機上唯一真的缺的**是 `Tab`／`Shift+Tab` 逐音節選取（那是桌面工作流）：請直接點候選，或用上表的 `[`／`]` 以詞定字。

另外兩個桌面組合鍵在 Trime 有現成的預設鍵可放上鍵盤（`preset_keys`，需自己加到鍵盤定義才會出現）：`Ctrl+Enter`（送出轉換後文字）對應 `CommitRawInput`，`Ctrl+Backspace`（刪前一個音節）對應 `BackToPreviousSyllable`。

（`Ctrl+'` 查讀音不是本方案的功能——那是移植註解留下的舊文案。本方案有兩條讀音相關流程，別混用：`~` 是**華語注音反查**，用注音輸入華語讀音去查 terra_pinyin 的漢字候選（候選再附台語讀音）；`'` 是**上屏後同音選字**，按一次取回該字詞的台語讀音重新組音。）

---

## 五、排版

本包附 `trime.custom.yaml`，**預設不生效**（空 patch）：拍台文的候選註解（拼音＋◆／★ 標記）比一般方案長，但版面觀感牽涉機型與字型，安裝包不替你決定。想調就照檔內範例取消註解，再到 App 重新部署。兩組範例都在檔內以註解寫好：

- **選項 A（低風險）**：只把註解字級 10→12sp，維持右側註解；列高不變。
- **選項 B（需自行實機確認）**：註解改成上方整列（`comment_position: top`），窄螢幕不會擠掉註解；但 top 模式下 `comment_height` 是**註解列**高度，`candidate_view_height` 必須同時容納 22sp 候選字與註解列。**48 只是保守起點，不是保證**——實際行高取決於 Trime 的版面與字型，內建 28／12（right 模式數值）拿去搭 top 模式幾乎一定不足。

以上數值以 Trime v3.3.12 的 `style` 參數推導，**未經真機渲染驗證**；改完請自行確認候選列沒有被裁切再微調。

橫屏與左右分離鍵盤是 App 自己的設定（`keyboard_landscape_mode`、`split_space_percent`），不在本包內。

---

## 覆蓋與更新

- `default.custom.yaml` 用 `@next` 附加方案，不動前端內建清單。**若你已經有自己的 `default.custom.yaml`**，不要整檔覆蓋，改成手動追加本包同名檔裡的 `patch:` 內容（見 `docs/android.md` 的「註冊方案」）。
- `rime.lua` 是拍台文的註冊檔；若你改過自己的 `rime.lua`，先備份。
- 更新時覆蓋 `phah_taibun*`、`lua/phah_taibun_*.lua` 等正式檔；**不要**覆蓋 `phah_taibun.custom.dict.yaml`、`phah_taibun.phrase.dict.yaml`、你自己的 `default.custom.yaml`／`rime.lua`。
- 每次更新後都要重新部署。

## 授權

- 拍台文本體：MIT，全文見 `LICENSE-PhahTaiBun.txt`。
- `terra_pinyin`／`bopomofo`／`zhuyin`：LGPL-3.0，來自 [rime/rime-terra-pinyin](https://github.com/rime/rime-terra-pinyin)、[rime/rime-bopomofo](https://github.com/rime/rime-bopomofo)，著作權人 GONG Chen、Kunki Chiu。本包附 `licenses/LGPL-3.0.txt`、`licenses/GPL-3.0.txt` 全文與 `THIRD-PARTY-NOTICES.txt`（逐檔來源、版本與 sha256）。
- 嘸蝦米：僅 `-liur` 版內含；上游無具名授權檔，依其 README「基於開源授權發佈」宣告散布，來源標示見 `LIUR-PROVENANCE.txt` 與上節。

打字方式見[快速上手小卡](https://soanseng.github.io/rime-phah-taibun/quickstart-card.html)與[完整使用說明](https://soanseng.github.io/rime-phah-taibun/guide.html)。
