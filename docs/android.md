# Android 部署（同文 / fcitx5-android）

拍台文是標準 Rime 方案，**不必改 schema 或 Lua**。Windows / macOS / Linux 仍是官方安裝包；Android **沒有 APK**。把發行包裡的方案檔放進現成的 Rime 前端，再在 App 裡重新部署。

兩個前端都內建 **librime-lua**（拼音註解、漢羅、Telex 都靠它）：

| 前端 | 性質 | 下載 |
|------|------|------|
| [同文 Trime](https://github.com/osfans/trime) | 完整 Rime 前端，鍵盤主題可自訂 | [F-Droid](https://f-droid.org/packages/com.osfans.trime)、[Google Play](https://play.google.com/store/apps/details?id=com.osfans.trime)、[Releases](https://github.com/osfans/trime/releases) |
| [fcitx5-android](https://github.com/fcitx5-android/fcitx5-android) + **RIME 外掛** | 小企鵝輸入法 5，Rime 是外掛 | 主程式與 `org.fcitx.fcitx5.android.plugin.rime` 都要裝；[說明](https://fcitx5-android.github.io/faq/) |

社群手動部署，不是官方支援等級。第一次部署會編譯約 5 MB 主字典，可能要數分鐘，不要把 App 滑掉。

---

## 最快路徑

1. 裝同文，**或**小企鵝 + RIME 外掛，並在系統設定啟用該輸入法。
2. 從 [Releases](https://github.com/soanseng/rime-phah-taibun/releases) 下載 `PhahTaiBun-source.zip`，解壓。
3. 把 zip 裡的 `schema/` 檔案（`default.custom.yaml` 除外）、`lua/`、`rime.lua` 複製到該前端的 **Rime 使用者資料夾**（見下節）。`lua/` 維持子目錄。
4. 註冊方案（見「註冊方案」）。不要整檔覆蓋已有的 `default.custom.yaml` / `rime.lua`。
5. **在 App 裡重新部署**（同文選單 → 重新部署；小企鵝 Rime 設定 → Deploy）。
6. 系統輸入法選同文或小企鵝，再**在 App 的方案清單**選「拍台文(台)」。Android **不是**按 `F4`。

測試：`gua beh khi tshit tho` →「我 beh 去 tshit-thô」。點候選即可，不必 `Tab` + `asdf`。

`~` 注音反查是可選功能，預設 zip **不含** terra_pinyin / bopomofo；沒另拷那些檔時 `~` 不會有反應，主打字仍可用。見「可選：注音反查」。

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

## 更新

沒有 Android 安裝器。每次發新版：

1. 再下載最新 `PhahTaiBun-source.zip`。
2. 覆蓋正式的 `phah_taibun*` schema、主字典、規則檔與 `lua/phah_taibun_*.lua`。
3. **不要**覆蓋 `phah_taibun.custom.dict.yaml`、`phah_taibun.phrase.dict.yaml`、你改過的 `default.custom.yaml` / `rime.lua`。
4. 在 App 裡重新部署。

---

## 限制

- **沒有官方 APK。** 系統層選同文或小企鵝，再在 Rime 方案清單選拍台文。
- **虛擬鍵盤 ≠ 桌面快捷鍵。** 點候選；方案在 App 選單切。fcitx5-android 鍵盤目前不能自訂佈局。
- **Lua 必須在。** 候選沒拼音註解、漢羅沒轉：先看 `lua/phah_taibun_*.lua` 是否在 `lua/`，再部署。
- 同文芫荽字體可放使用者資料夾 `fonts/`，再於主題指定：[iansui](https://github.com/ButTaiwan/iansui)。
- 依公開文件整理，**未做官方真機簽核**。路徑以 App 內顯示為準。

打字方式見[快速上手小卡](https://soanseng.github.io/rime-phah-taibun/quickstart-card.html)與[完整使用說明](https://soanseng.github.io/rime-phah-taibun/guide.html)。
