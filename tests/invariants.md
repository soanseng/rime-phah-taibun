# 行為不變量清單 Behavioral Invariants

> PLAN §9-3I。每一項 = 觸發輸入 → 預期輸出，附狀態與釘住它的測試。
> 修 bug 前先在此加一項（或把 pending 改成 reproduce），修好後狀態改 ✅。
> 語料例句可從 7 個語料庫（iCorpus、NMTL、教典例句等）抽取。
> 狀態：✅ 通過｜🔴 待修（附 issue/重現）｜⏸ 未實作（PLAN 排程中）

## 組字與排序

| ID | 觸發 | 預期 | 測試 | 狀態 |
|----|------|------|------|------|
| INV-01 | 打 `tsiah8` | 候選含「食」 | tests/test_real_rime.py::test_main_dictionary_produces_taiwanese_candidates | ✅ |
| INV-02 | 打 `tai5-uan5`（連字符整詞） | 候選含整詞「台灣」 | tests/test_real_rime.py::test_known_hyphenated_phrase_still_matches_dictionary | ✅ |
| INV-03 | 打字典詞全讀 `tsiah8-png7` | 整詞「食飯」出現且排名高於任何單字碎片 | tests/test_real_rime.py::test_dictionary_word_outranks_fragments | ✅ |
| INV-04 | 熱字＋字典詞 `gua2-tsiah8-png7` | 前排候選中「食飯」保持完整不被拆 | tests/test_real_rime.py::test_hot_single_chars_do_not_fragment_dictionary_word | ✅ |
| INV-05 | 字典外詞 `kio-tiann` | 逐音節組字，候選含「橋」 | tests/test_real_rime.py::test_unknown_phrase_with_hyphen_break_composes_per_syllable | ✅ |
| INV-06 | `kio`→Tab→`d`→`tiann`→Tab→`d`→空白 | 送出「橋鼎」（選字即選調） | tests/test_real_rime.py::test_word_by_word_selection_commits_chosen_hanzi | ✅ |
| INV-07 | 字典內任一 n≥2 音節詞 W | weight(W) ≥ ⌈1.2×最強單音節和⌉ | tests/test_frequency.py::TestEnforceLongWordInvariant、TestCommittedDictInvariant | ✅ |

## 模式與輸出

| ID | 觸發 | 預期 | 測試 | 狀態 |
|----|------|------|------|------|
| INV-08 | `` ` `` | 開符號選單（候選非 `` ` `` 本身） | tests/test_real_rime.py::test_backtick_opens_symbol_menu | ✅ |
| INV-09 | `,,h` | 說明文字不被羅馬字化 | tests/test_real_rime.py::test_help_descriptions_are_not_rewritten_as_romanization | ✅ |
| INV-10 | Telex `taid`/`ziahv`/`zhiahv` | 等同 `tai5`/`tsiah8`/`tshiah8` 候選 | tests/test_real_rime.py（telex 系列） | ✅ |
| INV-11 | 漢羅規則詞（如 ê） | 依 hanlo_rules 輸出羅馬字 | tests/test_lua_filter_behavior.py（hanlo replacement 系列） | ✅ |
| INV-12 | origin 模式各觸發 | 原形輸出行為（跳過特殊模式、單次大寫等） | tests/test_lua_filter_behavior.py（origin 系列） | ✅ |
| INV-13 | 輸出模式切換（TL/POJ、漢羅/全羅） | 跨 session 記憶（switcher/save_options） | tests/test_schema_config.py | ✅ |
| INV-21 | 全羅模式整句連打，句中 Tab→asdf 選字後續打→空白 | 不中途送出；已選詞保留在組句，最後整句羅馬字一次上屏（詞界保留） | tests/test_real_rime.py::test_full_roman_tab_selection_keeps_composition | ✅ |
| INV-22 | 手動漢羅整句，Tab 反白詞按 \\ 標記→Space | 標記詞輸出羅馬字（隨 TL/POJ 開關），其餘詞漢字；Escape 取消後不殘留 | tests/test_real_rime.py（manual_mix 系列） | ✅ |

## 資料管線

| ID | 觸發 | 預期 | 測試 | 狀態 |
|----|------|------|------|------|
| INV-14 | build 時 moe_poj 候選 ≠ tl_to_poj(moe_tl 兄弟) | build 立即失敗 | tests/test_validate.py::TestVerifyPojIntegrity、test_dict_conversion.py::TestPojIntegrityGate | ✅ |
| INV-15 | 大寫音節輸入 tl_to_poj（Tsuí、Ing-ko） | 轉換且保留字首大寫（Chuí、Eng-ko） | tests/test_tl_poj_convert.py::TestTlToPojCapitalized | ✅ |
| INV-16 | known-keys fixture 任一 key 命中數低於門檻 | validate 失敗（exit 1） | tests/test_validate.py::TestVerifyKnownKeys | ✅ |
| INV-17 | 詞身份 | (漢字, 正規化讀音) 成對——重/tîng ≠ 重/tāng；Uan5-A2 = uan5 a2 | tests/test_lua_filter_behavior.py（word_identity 系列）、tests/test_frequency.py | ✅ |
| INV-18 | 字典格式 | 無 editorial marker、鍵合法、無重複 | tests/test_validate.py::TestValidateDictFormat | ✅ |

## 排程中（⏸）

| ID | 內容 | PLAN |
|----|------|------|
| INV-19 | 使用者學習飽和＋時間衰減行為 | §9-1B |
| INV-20 | Slot-0 原文候選（無效拼音第一步照送） | §9-1E |
