# 拍台文 Phah Tai-bun

Rime 台語輸入法方案 — 漢羅混寫輸出，POJ/TL 雙拼音系統，聲調可省略。

## 特色

- **漢羅混寫**：依 LKK 李江却用字規範，自動輸出漢字+羅馬字混寫
- **POJ/TL 雙系統**：打 `tsiah` 或 `chiah` 都能輸入「食」
- **聲調可省略**：打 `gua beh khi` 就能找到「我 beh 去」
- **拼音註解**：候選區永遠顯示讀音，邊打邊學
- **多種輸出模式**：漢羅TL、漢羅POJ、全羅TL、全羅POJ

## 使用範例

```
輸入: gua beh khi tshit tho
候選: 我 beh 去 tshit-tho  [gua beh khi tshit-tho]
送出: 我 beh 去 tshit-tho
```

## 安裝

### 前置需求

- [Rime 輸入法引擎](https://rime.im/)（fcitx5-rime / ibus-rime / 鼠鬚管）
- Python 3.10+（資料前處理用）
- [uv](https://docs.astral.sh/uv/)（Python 套件管理）

### 快速安裝

```bash
# 1. Clone 專案
git clone https://github.com/user/rime-phah-taibun.git
cd rime-phah-taibun

# 2. 安裝 Python 依賴
uv sync

# 3. 下載外部資料（18 個語言資源，約 2GB）
chmod +x scripts/download_resources.sh
./scripts/download_resources.sh

# 4. 建置字典（處理 CSV → Rime 字典格式）
uv run python scripts/build_all.py

# 5. 安裝到 Rime
./install.sh
# 或指定路徑：./install.sh ~/.local/share/fcitx5/rime
```

安裝完成後，在輸入法設定中重新部署 Rime。

## 快捷鍵

| 按鍵 | 功能 |
|------|------|
| `Ctrl+Shift+T` | 切換輸出模式（漢羅/全羅） |
| `~` | 華語拼音反查台語 |
| `` ` `` | 符號選單（調號/方音/標點） |
| `,,h` | 按鍵說明 |
| `,,jit` | 台語日期時間 |
| `?` | 萬用字元（代替不確定的拼音） |

## 目錄結構

```
schema/          Rime 方案檔（安裝到 Rime 使用者目錄）
lua/             Lua 腳本（候選過濾、符號、日期等）
scripts/         Python 資料前處理腳本
tests/           測試
data/            外部資料（gitignore，用 download_resources.sh 下載）
```

## 開發

```bash
# 安裝開發依賴
uv sync

# 跑測試
uv run pytest

# 跑測試含覆蓋率
uv run pytest --cov=scripts --cov-report=term-missing

# Lint
uv run ruff check scripts/ tests/

# 格式化
uv run ruff format scripts/ tests/

# 重新建置字典
uv run python scripts/build_all.py
```

本專案採用 TDD 開發流程。所有 Python 程式碼需先寫測試。

## 資料來源

| 資料 | 授權 | 用途 |
|------|------|------|
| [ChhoeTaigi](https://github.com/ChhoeTaigi/ChhoeTaigiDatabase) | CC0 / CC BY-SA 4.0 | 主字典（iTaigi + 台華線頂） |
| [LKK 用字表](https://github.com/ChhoeTaigi) | 待確認 | 漢羅轉換規則 |
| [教育部辭典](https://github.com/g0v/moedict-data-twblg) | CC BY-ND 3.0 | 反查字典 |
| [iCorpus](https://github.com/Taiwanese-Corpus/icorpus_ka1_han3-ji7) | CC BY 4.0 | 詞頻統計 |
| [Ungian 2009](https://github.com/Taiwanese-Corpus/Ungian_2009_KIPsupin) | 待確認 | 文學語料詞頻 |
| [rime-liur](https://github.com/ryanwuson/rime-liur) | 開源（「歡迎使用和改進」） | Lua 模組架構參考 |

## 授權

- **程式碼**（scripts/、lua/、schema/*.schema.yaml）：[MIT License](LICENSE)
- **主字典** phah_taibun.dict.yaml：CC BY-SA 4.0（繼承台華線頂）
- **反查字典** phah_taibun_reverse.dict.yaml：CC BY-ND 3.0（繼承教育部辭典）

詳見 [LICENSE](LICENSE)。
