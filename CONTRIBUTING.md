# 貢獻指南 Contributing Guide

## 技術棧

| 層 | 語言 | 用途 |
|---|------|------|
| Rime schema | YAML | 輸入法方案定義、speller algebra、字典格式 |
| Runtime 腳本 | Lua | 候選過濾、輸出模式切換、漢羅轉換、反查邏輯、造詞、符號 |
| 資料前處理 | Python 3.10+（uv 管理） | ChhoeTaigi CSV→Rime dict 轉換、詞頻統計、LKK用字表解析 |

## 編碼與設計原則

1. **字典以 TL (教育部羅馬字) 為內部正規化格式**，POJ 透過 speller algebra derive 規則對應
2. **聲調在字典中以數字存儲**，去調號版本透過 derive 規則自動生成（`derive/[1-9]$//`）
3. **漢羅轉換是 Lua filter 層的責任**，不改動字典本身
4. **詞頻以整數權重存在字典第三欄**，數值越大越優先
5. **反查字典獨立於主字典**，教育部 CC BY-ND 資料只進反查不進主字典

## 開發環境設定

```bash
# 安裝依賴
uv sync

# 下載外部資料（18 個語言資源）
chmod +x scripts/download_resources.sh
./scripts/download_resources.sh
```

## TDD 開發流程

本專案遵循 **Red-Green-Refactor** 循環：

```
1. RED    — 先寫一個會失敗的測試，定義期望行為
2. GREEN  — 寫最少的程式碼讓測試通過
3. REFACTOR — 測試通過後重構，保持測試綠燈
```

```bash
# 跑單一測試
uv run pytest tests/test_xxx.py -x

# 全部測試
uv run pytest

# 含覆蓋率（目標 80%+）
uv run pytest --cov=scripts --cov-report=term-missing

# Lint + 格式化
uv run ruff check scripts/ tests/
uv run ruff format scripts/ tests/
```

### 測試檔案對照

| 實作 | 測試 |
|------|------|
| `scripts/convert_chhoetaigi.py` | `tests/test_dict_conversion.py` |
| `scripts/build_frequency.py` | `tests/test_frequency.py` |
| `scripts/parse_lkk_rules.py` | `tests/test_hanlo_rules.py` |
| `scripts/build_reverse_dict.py` | `tests/test_reverse_dict.py` |
| `scripts/validate_dict.py` | `tests/test_validate.py` |
| `scripts/build_moe_reverse.py` | `tests/test_moe_reverse.py` |
| `scripts/extract_icorpus_freq.py` | `tests/test_icorpus_freq.py` |
| `scripts/extract_ungian_freq.py` | `tests/test_ungian_freq.py` |

## ChhoeTaigi CSV 欄位對照

各資料庫共通的關鍵欄位：
- `KipInput`: 教育部羅馬拼音（數字調號，如 `tsit8-e7`）
- `PojInput`: 白話字（數字調號，如 `chit8-e7`）
- `KipUnicode`: 教育部羅馬拼音（Unicode 調號，如 `tsi̍t-ē`）
- `PojUnicode`: 白話字（Unicode 調號，如 `chi̍t-ē`）
- `HanLoTaibunKip`: 漢羅台文（教育部版）
- `HanLoTaibunPoj`: 漢羅台文（白話字版）
- `HoaBun`: 對應華文

KipInput 格式注意事項：
- 2.8% 含斜線 `/` 分隔的多音變體
- 0.8% 含 `(替)` 標記的替代音
- 1.1% 含 `--` 雙連字號表示連讀
- 聲調數字 1-9（1、4 無標記的情況存在）

## 注意事項

- Lua 腳本中的檔案路徑需要相對於 Rime 使用者資料夾
- Rime 的 Lua 環境是沙箱化的，只能用 Rime 提供的 API
- 字典 `.dict.yaml` 修改後需要重新部署才會生效
- `hanlo_rules.yaml` 由 Lua 在初始化時載入記憶體，查表效能無問題
- 台語一字多音（文白讀）的處理策略：白讀優先，文讀作為次要候選
