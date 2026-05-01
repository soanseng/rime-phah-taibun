# 拍台文快速上手小卡

這張小卡給第一次安裝、第一次打台文的人。先照這張打得出來，再看[完整使用說明](user-guide.md)。

---

## 先裝起來

一般使用者先到 [Releases](https://github.com/soanseng/rime-phah-taibun/releases) 下載安裝包：

| 系統 | 安裝拍台文 | 需要先有 |
|------|------------|----------|
| Windows | 下載 `PhahTaiBunSetup.exe`，雙擊安裝 | 小狼毫 Weasel |
| macOS | 下載 `PhahTaiBun.pkg`，雙擊安裝 | 鼠鬚管 Squirrel |
| Linux | `git clone https://github.com/soanseng/rime-phah-taibun.git && cd rime-phah-taibun && ./install.sh` | fcitx5-rime 或 ibus-rime |

裝好後重新部署 Rime，按 `F4`，選「拍台文(台)」。

進階使用者也可以用指令安裝：macOS 執行 `curl -fsSL https://raw.githubusercontent.com/soanseng/rime-phah-taibun/main/scripts/install_macos.sh | bash`；Windows PowerShell 執行 `irm https://raw.githubusercontent.com/soanseng/rime-phah-taibun/main/install_windows.ps1 | iex`。

---

## 第一分鐘：直接打

| 想打 | 輸入 | 會看到 |
|------|------|--------|
| 我 beh 去 tshit-thô | `gua beh khi tshit tho` | 我 beh 去 tshit-thô |
| 食飯 | `tsiah png` | 食飯 |
| 食飯 | `chiah png` | 食飯 |
| 台灣 / 臺灣 | `tai uan` | 臺灣、台灣 |
| 好 | `ho` 或 `ho2` | 好 |

不用先背聲調。想縮小候選範圍時，再補數字調：`ho2`、`tsiah8 png7`。

---

## 拼音規則：TL / POJ 都會通

| TL | POJ | 例 |
|----|-----|----|
| `ts` | `ch` | `tsiah` / `chiah` |
| `tsh` | `chh` | `tshut` / `chhut` |
| `ua` | `oa` | `gua` / `goa` |
| `ue` | `oe` | `ue` / `oe` |
| `oo` | `ou` / `o͘` | `oo` / `ou` |
| `nn` | `ⁿ` | 鼻化音 |

可以混打，例如 `goa beh khi` 一樣能找到「我 beh 去」。

---

## 常用按鍵

| 按鍵 | 用途 |
|------|------|
| `Space` | 確認目前候選 |
| `Tab` | 有候選時進入 asdf 選字；打拼音時跳下一音節 |
| `a s d f g h j k l ;` | Tab 選字模式中的第 1-10 候選 |
| `F4` | 切換漢羅/全羅、TL/POJ、emoji |
| `Ctrl+Space` | 台文/英文模式 |
| `Shift+字母` | 打大寫字母，不切英文模式 |
| `~` | 注音反查華語，再轉台語候選 |
| `?` | 萬用查字，例如 `?iah` |
| `` ` `` | 台羅調號、POJ 特殊字母、台文標點 |
| `[` / `]` | 取候選詞首字/尾字 |
| `\` | 目前候選改用另一種輸出形式 |
| `vvh` | 在候選區顯示按鍵說明 |
| `vvjit` | 台語日期 |
| `vvsp` | 簡拼對照 |

---

## 三個好用情境

### 不知道台語怎麼講

按 `~` 進入注音反查：

```text
~ㄔ → 選「吃」→ 回到台語候選「食」
```

### 忘記聲母

用 `?` 查音節：

```text
?iah → 選 tsiah → 食、炸、即、脊...
```

### 想選單字

先打詞，再用 `[` / `]` 取字：

```text
tsiah png → 食飯
按 [ → 食
按 ] → 飯
```

---

## 出問題先看這裡

| 狀況 | 先檢查 |
|------|--------|
| 找不到「拍台文(台)」 | 重新部署 Rime，再按 `F4` 看方案清單 |
| 沒有拼音註解 | 確認 `lua/phah_taibun_*.lua` 已安裝到 Rime 使用者資料夾 |
| `~` 注音反查沒反應 | 確認有 `bopomofo_tw` 方案 |
| emoji / 英文候選沒有出現 | 確認已安裝對應的 rime-ice 檔案 |

完整排錯看[使用說明的疑難排解](user-guide.md#十八疑難排解)。
