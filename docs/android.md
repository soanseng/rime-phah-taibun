# Android 部署（同文 / fcitx5-android）

拍台文是標準 Rime 方案，**不必改 schema 或 Lua**。Windows / macOS / Linux 仍是官方安裝包路徑；Android 沒有 APK，要把同一套檔案放進現成的 Rime 前端，再重新部署。

兩個可用前端都內建 **librime-lua**（拍台文的拼音註解、漢羅轉換、Telex 都靠它）：

| 前端 | 性質 | 下載 |
|------|------|------|
| [同文 Trime](https://github.com/osfans/trime) | 完整 Rime 前端，鍵盤主題可自訂 | [F-Droid](https://f-droid.org/packages/com.osfans.trime)、[Google Play](https://play.google.com/store/apps/details?id=com.osfans.trime)、[Releases](https://github.com/osfans/trime/releases) |
| [fcitx5-android](https://github.com/fcitx5-android/fcitx5-android) + **RIME 外掛** | 小企鵝輸入法 5，Rime 是外掛 | 主程式與 `org.fcitx.fcitx5.android.plugin.rime` 都要裝；[說明](https://fcitx5-android.github.io/faq/) |

這是社群手動部署，不是官方支援等級。第一次部署會編譯約 5 MB 主字典，手機上可能要等數分鐘，過程中不要把 App 滑掉。

---

## 要複製哪些檔

從 [Releases](https://github.com/soanseng/rime-phah-taibun/releases) 下載 `PhahTaiBun-source.zip`，或 clone 本 repo。下列檔案對應 Linux 安裝器會鋪的內容。

放到 **Rime 使用者資料夾根目錄**：

| 來源 | 目的檔名 |
|------|----------|
| `schema/phah_taibun.schema.yaml` | `phah_taibun.schema.yaml` |
| `schema/phah_taibun_telex.schema.yaml` | `phah_taibun_telex.schema.yaml` |
| `schema/phah_taibun.dict.yaml` | `phah_taibun.dict.yaml` |
| `schema/hanlo_rules.yaml` | `hanlo_rules.yaml` |
| `schema/lighttone_rules.json` | `lighttone_rules.json` |
| `schema/moe700.yaml` | `moe700.yaml` |
| `schema/hoabun_map.txt` | `hoabun_map.txt` |

放到 **`lua/` 子目錄**（只覆蓋 `phah_taibun_*.lua`，不要整包蓋掉別人的模組）：

- `lua/phah_taibun_*.lua`

`rime.lua`：使用者資料夾根目錄若還沒有就複製；若已有，把本專案 `rime.lua` 的內容**追加合併**，不要整檔覆蓋。

`schema/default.custom.yaml`：**不要直接覆蓋**既有檔。Trime 常已有一份列出拼音方案的 `default.custom.yaml`。請改走下一節的註冊方式。

自訂詞庫 `phah_taibun.custom.dict.yaml`、`phah_taibun.phrase.dict.yaml` 若已存在就保留，不要覆蓋。

---

## 註冊方案

編輯使用者資料夾的 `default.custom.yaml`。

**還沒有這個檔**：複製 `schema/default.custom.yaml`。

**已經有**：在既有 `patch:` 底下追加（不要另開第二個 `patch:` 根），並把兩個 schema 加進方案清單。若檔裡已經是完整的 `schema_list:` 陣列，在陣列末尾加兩項即可：

```yaml
patch:
  schema_list:
    - schema: luna_pinyin          # 你原本的方案，保留
    - schema: phah_taibun
    - schema: phah_taibun_telex
```

若清單是用 `@next` 附加、不想重寫整份清單：

```yaml
patch:
  schema_list/@next:
    schema: phah_taibun
  schema_list/@next 1:
    schema: phah_taibun_telex
  switcher/save_options/@before 0: poj_mode
  switcher/save_options/@next: full_romanization
```

`poj_mode` / `full_romanization` 讓漢羅／全羅、TL／POJ 選擇會記住。檔裡若已有這兩行就不必再加。

---

## 同文 Trime

1. 安裝同文，在系統設定啟用為輸入法。
2. 打開同文設定，確認 Rime **使用者資料夾**位置。目前 develop 版預設是 App 專屬目錄：
   `Android/data/com.osfans.trime/files/rime`
   （完整路徑常是 `/storage/emulated/0/Android/data/com.osfans.trime/files/rime`。）Android 11 之後系統檔案總管可能看不到 `Android/data`，請用同文內建檔案管理、電腦 USB、或能存取該目錄的檔案 App。
3. 依上一節複製檔案並註冊方案。
4. 同文選單 → **重新部署**。等部署結束。
5. 切到同文後，用方案選單選「拍台文(台)」。沒有實體鍵盤時，點候選列比按 `Tab` + `asdf` 實際。
6. 測試輸入 `gua beh khi tshit tho`，應出現「我 beh 去 tshit-thô」。

同文可改鍵盤佈局（`trime.yaml` / 主題）。若要桌面那套 `F4`、`` Ctrl+` ``，需自己在主題裡綁鍵；多數情況用同文的方案切換與候選點選即可。說明見 [Trime wiki](https://github.com/osfans/trime/wiki/UserGuide)。

芫荽字體可放進同文使用者資料夾的 `fonts/`，再於主題指定；見 [芫荽 iansui](https://github.com/ButTaiwan/iansui)。

---

## fcitx5-android（小企鵝 + Rime 外掛）

1. 安裝 **Fcitx5 for Android**，再安裝 **RIME Plugin**。GitHub / F-Droid / Jenkins 簽名相同，可互升；**Google Play 版簽名不同**，不能和外掛混裝。見 [fcitx5-android README](https://github.com/fcitx5-android/fcitx5-android)。
2. 系統設定啟用小企鵝輸入法。
3. 輸入法設定 → **輸入法 → Rime** → 齒輪 → **User data dir**。自訂方案放在該目錄下的 `data/rime`（維護者說明：[discussion #808](https://github.com/fcitx5-android/fcitx5-android/discussions/808)）。
   也可用系統檔案總管側欄選「小企鵝輸入法5」，對應 `/sdcard/Android/data/org.fcitx.fcitx5.android/files/`。工作資料夾路徑會不同，以 App 顯示的 User data dir 為準。
4. 依上面清單把拍台文檔案放進 `data/rime`，Lua 放 `data/rime/lua/`，並註冊 `default.custom.yaml`。
5. Rime 設定裡執行 **Deploy**。等編譯結束。
6. 輸入法清單把 Rime 打開（必要時拖到前面）。切到 Rime 後選「拍台文(台)」。
7. 測試 `gua beh khi tshit tho`。

fcitx5-android 虛擬鍵盤目前**不能自訂佈局**。`F4`、`` Ctrl+` ``、`Tab` + `asdfghjkl;` 在螢幕鍵盤上常常沒有對應鍵；請用狀態列／候選列點選，或接實體鍵盤。這是前端限制，不是拍台文缺檔。

---

## 更新

沒有 Android 安裝器。每次發新版：

1. 再下載最新 `PhahTaiBun-source.zip`（或 `git pull --ff-only`）。
2. 覆蓋正式的 `phah_taibun*` schema、主字典、規則檔與 `lua/phah_taibun_*.lua`。
3. **不要**覆蓋 `phah_taibun.custom.dict.yaml`、`phah_taibun.phrase.dict.yaml`、你改過的 `default.custom.yaml` / `rime.lua`。
4. 重新部署。

---

## 限制（請先讀）

- **沒有官方 APK**，也不會在系統輸入法清單單獨出現「拍台文」；系統層選同文或小企鵝，Rime 裡再選方案。
- **虛擬鍵盤 ≠ 桌面快捷鍵。** 點候選即可選字；數字調若鍵盤沒有數字列，可省略聲調（這本來就是預設打法）。
- **Lua 必須在。** 兩個前端目前都有 librime-lua。若候選沒有拼音註解、漢羅沒轉，先確認 `lua/phah_taibun_*.lua` 在使用者資料夾的 `lua/`，然後重新部署。
- **注音反查 `~`** 需要前端也有 `bopomofo_tw`（或同等注音方案）。沒有就略過這功能。
- 這份說明依 Trime / fcitx5-android 公開文件整理，**未做官方真機簽核**。路徑或選單文案隨 App 版本可能改名；以 App 內「使用者資料夾 / User data dir」為準。

打字方式與電腦版相同，見[快速上手小卡](quickstart-card.md)與[完整使用說明](user-guide.md)。
