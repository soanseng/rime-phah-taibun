# Rime-Ice UX Adoption for Phah-Taibun

## Goal

Adopt 5 proven UX features from rime-ice (雾凇拼音) into phah-taibun, adapted for Taiwanese Hokkien Han-Lo mixed output. Approach: port features natively as phah-taibun modules (no runtime dependency on rime-ice).

## Features

### 1. 以詞定字 (Select Character from Phrase)

Press `[` to pick the first character or `]` to pick the last character from the current candidate.

**Example:** Type `tsiah-png`, candidate shows `食飯`. Press `[` → commits `食`. Press `]` → commits `飯`.

**Implementation:**
- New file: `lua/phah_taibun_select_char.lua` — key processor
- Intercepts `bracketleft` / `bracketright` during composition
- **Must check** `context:is_composing() or context:has_menu()` before intercepting — otherwise `[` `]` won't work in ASCII mode
- Handles UTF-8 correctly for multi-byte漢字
- Preserves remaining input after cursor position
- Config keys: `phah_taibun_select_char/first_key` and `phah_taibun_select_char/last_key` (under its own namespace, not key_binder)
- Registered **after** `ascii_composer` in engine processors so ASCII mode is handled first

**台語 behavior:** Works on output text regardless of mode. In全羅 mode, picks the first/last romanization word — still useful for grabbing a specific syllable.

### 2. 長詞優先 (Long Word Priority Filter)

Promote longer candidates to more visible positions in the candidate list.

**Behavior:** After position `idx` (default 4), find candidates longer than the first candidate and move `count` (default 2) of them up to position `idx`. Lookahead is capped at 50 candidates to avoid performance issues with the 170K-entry dictionary.

**Implementation:**
- New file: `lua/phah_taibun_long_word.lua` — candidate filter
- Configurable: `long_word_filter/count: 2`, `long_word_filter/idx: 4`
- Skips ASCII-only candidates (English words should not be promoted)
- Placed in filters after `phah_taibun_synonym` but before `simplifier@emoji` and `uniquifier`
- Complements existing quality boost (quality affects scoring; this does positional reordering)

**Length metric:** Uses `utf8.len` on the candidate's `.text` field (which has already been transformed by `phah_taibun_filter` at this point in the pipeline). This means:
- 漢羅 mode: `食飯` = 2, `食pn̄g` = 4 — mixed text measured by Unicode character count
- 全羅 mode: `tsia̍h-pn̄g` = 10 — romanization is longer in character count, so it naturally promotes multi-syllable romanization over single-syllable

This is the same approach rime-ice uses (`utf8.len`). No special syllable counting needed.

### 3. Editor Key Bindings

Customized key behavior for fluency_editor continuous input.

**Schema config (no Lua needed):**

```yaml
editor:
  bindings:
    space: confirm
    Return: commit_raw_input
    Control+Return: commit_script_text
    BackSpace: revert
    Control+BackSpace: back_syllable
    Escape: cancel

key_binder:
  import_preset: default
  bindings:
    # Tab/Shift+Tab 在音節間跳轉
    - { when: composing, accept: Tab, send: Shift+Right }
    - { when: composing, accept: Shift+Tab, send: Shift+Left }
    # [ ] 翻頁（不與以詞定字衝突：以詞定字的 processor 先處理，
    #     只在有候選時攔截；翻頁只在 paging 時觸發）
    - { when: paging, accept: bracketleft, send: Page_Up }
    - { when: paging, accept: bracketright, send: Page_Down }
```

**Why NOT `-`/`=` for paging:** The hyphen `-` is part of the speller alphabet (`zyxwvutsrqponmlkjihgfedcba1234567890-`) and is essential for台語 syllable separators (e.g., `tsiah-png`, `tshit-tho`). Using `-` as Page_Up would break multi-syllable input when `has_menu` is true (which it always is under `fluency_editor`). Instead, we keep the default Page_Up/Page_Down keys and optionally add `[`/`]` for paging when in paging state (which doesn't conflict with select_char since select_char only triggers during `composing`).

**Note on `editor/bindings`:** This is a valid Rime config section for the `editor` component (including `fluency_editor`). These bindings define what each key does within the editor context. The `fluency_editor` inherits from `editor` and reads this config. See [librime source: editor.cc](https://github.com/rime/librime/blob/master/src/rime/gear/editor.cc).

**Rationale:**
- Tab/Shift+Tab: jump between syllables to correct mistakes in long input
- Return: commits raw romanization (useful when user wants TL/POJ text itself)
- Ctrl+Backspace: delete one syllable instead of one character

### 4. Emoji Support

Emoji suggestions triggered by漢字 output via OpenCC simplifier.

**Implementation (no Lua needed):**
- Reuses rime-ice's OpenCC files: `opencc/emoji.json`, `opencc/emoji.txt`
- New switch: `emoji` with states `[ 💀, 😄 ]`, default on
- New filter: `simplifier@emoji` placed after `phah_taibun_long_word`, before `uniquifier`
- Config:
  ```yaml
  emoji:
    option_name: emoji
    opencc_config: emoji.json
    inherit_comment: false
    tips: char           # Only show emoji tip for single-char matches
    tags: [ abc ]        # Only apply to abc segment, not reverse lookup
  ```

**台語 behavior:** The `simplifier` matches on漢字 in the candidate text. In漢羅 modes, candidates contain漢字 so emoji triggers normally. In全羅 modes, candidates are pure romanization (ASCII + tone marks) which won't match any emoji dictionary entries (emoji.txt maps漢字→emoji, not romanization→emoji).

**Edge case — romanization substrings:** The OpenCC emoji dictionary maps multi-character漢字 phrases to emoji (e.g., `心` → ❤️). Single Latin letters or romanization tokens like `sim` or `png` do not appear in the emoji dictionary, so false matches on romanization text are not a concern.

### 5. 英文混輸 (Inline English Input)

Type English words without switching input mode.

**Implementation (no Lua needed):**
- Reuses rime-ice's dictionary: `melt_eng.dict.yaml`, `melt_eng.schema.yaml`
- Schema dependency: `melt_eng`
- New translator: `table_translator@melt_eng`
- Full config block:
  ```yaml
  melt_eng:
    dictionary: melt_eng
    enable_sentence: false
    enable_user_dict: false
    enable_completion: true
    initial_quality: 0.5
    comment_format:
      - xform/.*//
  ```

**Behavior:** English candidates appear when input matches English words, but always ranked below台語 matches due to `initial_quality: 0.5` (台語 translator defaults to ~1.0). `enable_sentence: false` prevents the English dictionary from trying to compose sentences. `enable_completion: true` allows partial-word completion (e.g., `hel` → `hello`).

## Schema Changes Summary

### Engine pipeline (final order)

```yaml
engine:
  processors:
    - ascii_composer
    - lua_processor@*phah_taibun_select_char  # NEW: 以詞定字 (after ascii_composer)
    - recognizer
    - key_binder
    - speller
    - punctuator
    - selector
    - navigator
    - fluency_editor
  segmentors:
    - ascii_segmentor
    - matcher
    - abc_segmentor
    - punct_segmentor
    - fallback_segmentor
  translators:
    - echo_translator
    - punct_translator
    - script_translator
    - reverse_lookup_translator
    - table_translator@custom_phrase
    - table_translator@melt_eng              # NEW: 英文混輸
    - lua_translator@*phah_taibun_help
    - lua_translator@*phah_taibun_date
    - lua_translator@*phah_taibun_symbols
    - lua_translator@*phah_taibun_wildcard
    - lua_translator@*phah_taibun_phrase
    - lua_translator@*phah_taibun_speedup
  filters:
    - lua_filter@*phah_taibun_filter
    - lua_filter@*phah_taibun_lookup
    - lua_filter@*phah_taibun_synonym
    - lua_filter@*phah_taibun_long_word      # NEW: 長詞優先
    - simplifier@emoji                        # NEW: Emoji
    - uniquifier
```

### New config sections

```yaml
switches:
  - name: emoji
    states: [ 💀, 😄 ]
    reset: 1

schema:
  dependencies:
    - melt_eng

phah_taibun_select_char:
  first_key: bracketleft
  last_key: bracketright

long_word_filter:
  count: 2
  idx: 4

melt_eng:
  dictionary: melt_eng
  enable_sentence: false
  enable_user_dict: false
  enable_completion: true
  initial_quality: 0.5
  comment_format:
    - xform/.*//

emoji:
  option_name: emoji
  opencc_config: emoji.json
  inherit_comment: false
  tips: char
  tags: [ abc ]

editor:
  bindings:
    space: confirm
    Return: commit_raw_input
    Control+Return: commit_script_text
    BackSpace: revert
    Control+BackSpace: back_syllable
    Escape: cancel
```

## New Files

| File | Type | Purpose |
|------|------|---------|
| `lua/phah_taibun_select_char.lua` | Lua processor | 以詞定字 `[` `]` |
| `lua/phah_taibun_long_word.lua` | Lua filter | 長詞優先 positional boost |

## Modified Files

| File | Changes |
|------|---------|
| `schema/phah_taibun.schema.yaml` | Add processor, translator, filters, switches, editor, key_binder, emoji, melt_eng, select_char, long_word_filter config |
| `rime.lua` | Register `phah_taibun_select_char` and `phah_taibun_long_word` modules |

## Dependencies

- `melt_eng.dict.yaml` and `melt_eng.schema.yaml` must be present in Rime data directory
- `opencc/emoji.json` and `opencc/emoji.txt` must be present
- Install script should copy these files alongside the schema, or document that users can obtain them from rime-ice

## Features NOT adopted (and why)

| Feature | Reason |
|---------|--------|
| 錯音錯字提示 (corrector) | Mandarin-specific pronunciation corrections, not applicable to台語 |
| 自動糾錯 speller rules | Pinyin-specific typo corrections; our POJ↔TL fuzzy derive rules already serve this purpose |
| 置頂候選 (pin_cand_filter) | Could add later but not essential for initial adoption |
| 中英自動空格 (cn_en_spacer) | Not needed since台語 Han-Lo already has natural spacing |
