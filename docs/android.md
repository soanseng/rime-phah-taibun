# Android 部署（同文 / fcitx5-android）

拍台文是標準 Rime 方案，**不必改 schema 或 Lua**。Windows 有安裝包；macOS／Linux 用指令或複製檔案；Android **沒有 APK**。把發行包裡的方案檔放進現成的 Rime 前端，再在 App 裡重新部署。

最快的方式是下載 Releases 的 **`PhahTaiBun-Trime.zip` 一鍵包**（拍台文＋注音，含 `~` 反查依賴），解壓到 Rime 使用者資料夾後重新部署；想逐檔自己控制就往下看「最快路徑」。

兩個前端都內建 **librime-lua**（拼音註解、漢羅、Telex 都靠它）：

| 前端 | 性質 | 下載 |
|------|------|------|
| [同文 Trime](https://github.com/osfans/trime) | 完整 Rime 前端，鍵盤主題可自訂 | [F-Droid](https://f-droid.org/packages/com.osfans.trime)（可自動更新）、[Releases](https://github.com/osfans/trime/releases)（下載 APK 手動裝） |
| [fcitx5-android](https://github.com/fcitx5-android/fcitx5-android) + **RIME 外掛** | 小企鵝輸入法 5，Rime 是外掛 | 主程式與 `org.fcitx.fcitx5.android.plugin.rime` 都要裝；[說明](https://fcitx5-android.github.io/faq/) |

社群手動部署，不是官方支援等級。第一次部署會編譯約 5 MB 主字典，可能要數分鐘，不要把 App 滑掉。

---

## 一鍵包：`PhahTaiBun-Trime.zip`／`PhahTaiBun-Trime-liur.zip`

先用下表裝好一個前端——**同文 Trime 不是手機內建，要自己安裝**：在 [F-Droid](https://f-droid.org/packages/com.osfans.trime) 安裝可以自動更新，或到 [同文自己的 Releases](https://github.com/osfans/trime/releases) 下載 APK 手動裝；裝完在系統設定啟用該輸入法。

然後從 [Releases](https://github.com/soanseng/rime-phah-taibun/releases) 下載其中一種包，解壓到 **Rime 使用者資料夾**根目錄（見下節），再在 App 裡重新部署。**兩種包，自己選**：

| 包 | 內容 | 大小 |
|----|------|------|
| `PhahTaiBun-Trime.zip` | 拍台文（漢羅＋Telex）＋注音 `bopomofo_tw`＋`~` 反查依賴 | 約 3.5 MB |
| `PhahTaiBun-Trime-liur.zip` | 再加嘸蝦米 `liur`（含 `easy_en` 英文詞庫） | 約 20 MB |

共同內容：

- `default.custom.yaml` 以 `@next` 追加方案，不動前端內建清單（嘸蝦米版多註冊 `liur`／`easy_en`）
- `THIRD-PARTY-NOTICES.txt`＋`licenses/`（LGPL-3.0／GPL-3.0 全文）＋`LICENSE-PhahTaiBun.txt`：terra_pinyin 與 bopomofo 為 LGPL-3.0，隨包附授權全文與逐檔來源
- `trime.custom.yaml`（排版範例，預設不生效）與 `INSTALL-Trime.md` 逐步說明

**不含**字體與使用者詞庫。

**嘸蝦米版的來源標示**：檔案集來自 [soanseng/rime-liur-arch](https://github.com/soanseng/rime-liur-arch)（fork 自 `ryanwuson/rime-liur`）。上游未附具名授權檔，README 宣告「本專案基於開源授權發佈，歡迎使用和改進」；本專案依該宣告隨包散布，並以包內 `LIUR-PROVENANCE.txt` 記錄來源 repo、commit 與此宣告。若上游日後補上正式授權條款，以其條款為準。不想用嘸蝦米就下載輕量版。

已經有自己的 `default.custom.yaml` 或 `rime.lua` 時先備份，不要整檔覆蓋（見「註冊方案」與「更新」）。

---

## 最快路徑（逐檔手動）

1. 裝同文，**或**小企鵝 + RIME 外掛，並在系統設定啟用該輸入法。
2. 從 [Releases](https://github.com/soanseng/rime-phah-taibun/releases) 下載 `PhahTaiBun-source.zip`，解壓。
3. 把 zip 裡的 `schema/` 檔案（`default.custom.yaml` 除外）、`lua/`、`rime.lua` 複製到該前端的 **Rime 使用者資料夾**（見下節）。`lua/` 維持子目錄。
4. 註冊方案（見「註冊方案」）。不要整檔覆蓋已有的 `default.custom.yaml` / `rime.lua`。
5. **在 App 裡重新部署**（同文選單 → 重新部署；小企鵝 Rime 設定 → Deploy）。
6. 系統輸入法選同文或小企鵝，再**在 App 的方案清單**選「拍台文(台)」。Android **不是**按 `F4`。

測試：`gua beh khi tshit tho` →「我 beh 去 tshit-thô」。點候選即可，不必 `Tab` + `asdf`。

`~` 注音反查是可選功能；**一鍵包已內含**所需檔案。逐檔手動複製時不含 terra_pinyin / bopomofo，沒另拷那些檔時 `~` 不會有反應，主打字仍可用。見「可選：注音反查」。

---

## 使用者資料夾在哪

用 App 自己顯示的路徑，不要猜絕對路徑（工作資料夾、Android 版本都會變）。

**同文 Trime**：來源是 `getExternalFilesDir(null)/rime`，一般是

`Android/data/com.osfans.trime/files/rime`

Android 11+ 多數檔案總管**進不了** `Android/data`。用電腦 USB/MTP、同文內建檔案管理，或能存取該目錄的工具。

**fcitx5-android**：輸入法設定 → **輸入法 → Rime** → 齒輪 → **User data dir**。自訂方案放在該目錄下的 `data/rime`（維護者：[discussion #808](https://github.com/fcitx5-android/fcitx5-android/discussions/808)）。也可用系統檔案總管側欄「小企鵝輸入法5」。不要硬記 `/sdcard/Android/data/...`。

GitHub / F-Droid / Jenkins 的小企鵝簽名相同；**Google Play 版簽名不同**，不能和外掛混裝。

---

## 要複製哪些檔

zip / repo 對應 Linux 安裝器會鋪的內容：

| 來源 | 放到使用者資料夾 |
|------|------------------|
| `schema/phah_taibun.schema.yaml` | 根目錄 |
| `schema/phah_taibun_telex.schema.yaml` | 根目錄 |
| `schema/phah_taibun.dict.yaml` | 根目錄 |
| `schema/phah_taibun.wordlist` | 根目錄（全羅整句詞界格式需要） |
| `schema/hanlo_rules.yaml` | 根目錄 |
| `schema/lighttone_rules.json` | 根目錄 |
| `schema/moe700.yaml` | 根目錄 |
| `schema/hoabun_map.txt` | 根目錄 |
| `lua/phah_taibun_*.lua` | `lua/` 子目錄（只覆蓋這些檔） |
| `rime.lua` | 根目錄：沒有就複製；已有就**追加合併** |

`schema/default.custom.yaml`：**不要直接覆蓋**既有檔。見下一節。

自訂詞庫 `phah_taibun.custom.dict.yaml`、`phah_taibun.phrase.dict.yaml` 若已存在就保留。

---

## 註冊方案

編輯使用者資料夾的 `default.custom.yaml`。

**還沒有這個檔**：複製 `schema/default.custom.yaml`。

**已經有**：在既有 `patch:` 底下追加（不要另開第二個 `patch:` 根）。若檔裡已是完整 `schema_list:` 陣列，在末尾加兩項：

```yaml
patch:
  schema_list:
    - schema: luna_pinyin          # 你原本的方案，保留
    - schema: phah_taibun
    - schema: phah_taibun_telex
```

若用 `@next` 附加、不想重寫清單：

```yaml
patch:
  schema_list/@next:
    schema: phah_taibun
  schema_list/@next 1:
    schema: phah_taibun_telex
  switcher/save_options/@before 0: poj_mode
  switcher/save_options/@next: full_romanization
```

`poj_mode` / `full_romanization` 讓漢羅／全羅、TL／POJ 會記住。檔裡已有就不必再加。

切方案：同文的方案選單，或小企鵝 Rime 狀態列／設定。不是桌面的 `F4`。

---

## 可選：注音反查 `~`

主打字**不需要**這一步。schema 的 `~` 反查讀的是檔案，不是「前端有沒有注音鍵盤」：

| 檔案 | 用途 | 來源 |
|------|------|------|
| `terra_pinyin.dict.yaml` | `reverse_lookup.dictionary` | [rime/rime-terra-pinyin](https://github.com/rime/rime-terra-pinyin) |
| `bopomofo_tw.schema.yaml`（及其依賴的 bopomofo 方案檔） | `reverse_lookup.prism` | [rime/rime-bopomofo](https://github.com/rime/rime-bopomofo) |

放到**同一個** Rime 使用者資料夾後重新部署。沒拷這些檔時，`~` 會沒反應，看起來像壞掉。

前端差異：

- **fcitx5-android** 的 Rime 外掛共享資料有 **luna_pinyin**，**沒有** terra_pinyin / bopomofo。`~` 仍要自己拷上表。
- **同文** 也不會自動帶 terra_pinyin / bopomofo_tw。一樣要拷。luna_pinyin 對 `~` 不夠。

---

## Android 按鍵與排版

桌面快捷鍵在手機上不存在，但功能都在：`[`／`]`（以詞定字）＝長按 `u`／`i`，`?`（萬用查字）＝長按 `/`，`~`（**華語注音反查**：輸入注音查漢字候選，候選附台語讀音）＝長按 `b`，`` ` ``（符號選單）＝長按 `z`，`\`（漢羅↔全羅）＝長按 `y`；`;`、`'`（上屏後同音選字，取回該字詞台語讀音重組）、`,`、`.` 是直鍵。方案選單／模式開關（漢羅/全羅、TL/POJ）改在 App 的方案選單與**開關面板**切換，中英切換用中英鍵（`toggle: ascii_mode`）。手機上唯一真的缺的是 `Tab` 逐音節選取（桌面工作流），請直接點候選或用 `[`／`]` 以詞定字；`Ctrl+Enter`、`Ctrl+Backspace` 在 Trime 有現成預設鍵（`CommitRawInput`、`BackToPreviousSyllable`）可放上鍵盤。完整對照表見一鍵包內的 `INSTALL-Trime.md`。

一鍵包附 `trime.custom.yaml`，**預設不生效**（空 patch，不替你改外觀）。拍台文的候選註解（拼音＋推薦標記）比一般方案長，檔內附兩組範例：A 只把註解字級 10→12sp（維持右側註解，列高不變，低風險）；B 改成註解置頂整列（`comment_position: top`），此時 `candidate_view_height` 要同時容納 22sp 候選字與註解列，**48 只是保守起點、非保證**（預設 28／12 是 right 模式的數值，搭 top 幾乎一定不足）。兩者都需自行取消註解、上機確認沒有裁切後再重新部署。

---

## 更新

沒有 Android 安裝器。每次發新版：

1. 下載最新 `PhahTaiBun-Trime.zip`（一鍵包）覆蓋，或再下載 `PhahTaiBun-source.zip` 逐檔更新。
2. 覆蓋正式的 `phah_taibun*` schema、主字典、規則檔與 `lua/phah_taibun_*.lua`；嘸蝦米是你自己裝的，一鍵包不會動它。
3. **不要**覆蓋 `phah_taibun.custom.dict.yaml`、`phah_taibun.phrase.dict.yaml`、你改過的 `default.custom.yaml` / `rime.lua`。
4. 在 App 裡重新部署。

---

## 限制

- **沒有官方 APK。** 系統層選同文或小企鵝，再在 Rime 方案清單選拍台文。
- **虛擬鍵盤 ≠ 桌面快捷鍵。** 點候選；方案在 App 選單切。fcitx5-android 鍵盤目前不能自訂佈局。
- **Lua 必須在。** 候選沒拼音註解、漢羅沒轉：先看 `lua/phah_taibun_*.lua` 是否在 `lua/`，再部署。
- 同文芫荽字體可放使用者資料夾 `fonts/`，再於主題指定：[iansui](https://github.com/ButTaiwan/iansui)。
- 依公開文件整理，**未做官方真機簽核**。路徑以 App 內顯示為準。

打字方式見[快速上手小卡](https://taigi.anatomind.com/guide.html#/quickstart-card)與[完整使用說明](https://taigi.anatomind.com/guide.html)。
