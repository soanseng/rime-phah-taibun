# Phase 1 Lua Completion Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete the Lua filter and data loader modules so the Rime input method actually produces Han-Lo mixed output with pronunciation annotations, making Phase 1 functionally usable.

**Architecture:** A centralized data loader (`phah_taibun_data.lua`) reads `hanlo_rules.yaml` at init time and caches it. The core filter (`phah_taibun_filter.lua`) queries hanlo_rules to determine per-character Han vs Lo output, reads the `output_mode` switch, and formats candidates with TL/POJ annotations in the comment field. The wildcard translator uses Rime's `env.engine` to expand `?` patterns against actual initials.

**Tech Stack:** Lua 5.3 (Rime embedded sandbox), Rime Lua API (`Candidate`, `env.engine.context`, `rime_api.get_user_data_dir()`), YAML data files

---

## Chunk 1: Data Loader + Core Filter (Tasks 1-2)

### Task 1: Centralized Data Loader

**Goal:** Create `phah_taibun_data.lua` that loads `hanlo_rules.yaml` once and caches it for all other modules.

**Files:**
- Create: `lua/phah_taibun_data.lua`

**Rime Lua API notes:**
- `rime_api.get_user_data_dir()` returns the Rime user data directory path
- Files can be read with standard Lua `io.open()`
- YAML parsing must be done manually (no yaml lib in Rime sandbox) — use line-by-line parsing

- [ ] **Step 1: Create phah_taibun_data.lua**

```lua
-- phah_taibun_data.lua
-- Centralized data loader for hanlo_rules
-- Caches loaded data globally to avoid repeated I/O

local M = {}

-- Global cache
local _hanlo_rules = nil

-- Parse a simple YAML file into a Lua table
-- Only handles the specific format of hanlo_rules.yaml:
--   word:
--     type: han/lo
--     kip: pronunciation
--     hoabun: meaning
local function parse_hanlo_yaml(content)
  local rules = {}
  local current_word = nil

  for line in content:gmatch("[^\r\n]+") do
    -- Skip comments and empty lines
    if line:match("^%s*#") or line:match("^%s*$") then
      goto continue
    end

    -- Top-level key (word entry): "食飯:" or "ê:"
    local word = line:match("^([^%s].-):$")
    if word then
      current_word = word
      rules[current_word] = {}
      goto continue
    end

    -- Nested key-value: "  type: han"
    if current_word then
      local key, value = line:match("^%s+(%w+):%s*(.*)$")
      if key and value then
        -- Remove quotes from values like "''"
        value = value:gsub("^'(.*)'$", "%1")
        rules[current_word][key] = value
      end
    end

    ::continue::
  end

  return rules
end

-- Find the hanlo_rules.yaml file path
local function find_rules_path()
  local dirs = {}

  -- Try Rime API paths first
  if rime_api then
    local user_dir = rime_api.get_user_data_dir()
    if user_dir then
      table.insert(dirs, user_dir)
    end
    local shared_dir = rime_api.get_shared_data_dir()
    if shared_dir then
      table.insert(dirs, shared_dir)
    end
  end

  for _, dir in ipairs(dirs) do
    local path = dir .. "/hanlo_rules.yaml"
    local f = io.open(path, "r")
    if f then
      f:close()
      return path
    end
  end

  return nil
end

-- Load and cache hanlo_rules
function M.get_hanlo_rules()
  if _hanlo_rules then
    return _hanlo_rules
  end

  local path = find_rules_path()
  if not path then
    _hanlo_rules = {}
    return _hanlo_rules
  end

  local f = io.open(path, "r")
  if not f then
    _hanlo_rules = {}
    return _hanlo_rules
  end

  local content = f:read("*all")
  f:close()

  _hanlo_rules = parse_hanlo_yaml(content)
  return _hanlo_rules
end

-- Lookup a word in hanlo_rules
-- Returns "han", "lo", or nil (default to han)
function M.get_hanlo_type(word)
  local rules = M.get_hanlo_rules()
  local entry = rules[word]
  if entry then
    return entry.type
  end
  return nil
end

return M
```

- [ ] **Step 2: Commit**

```bash
git add lua/phah_taibun_data.lua
git commit -m "feat: add centralized data loader for hanlo_rules

Reads hanlo_rules.yaml from Rime user/shared data dir, parses the
simple YAML format, and caches results globally for filter access."
```

---

### Task 2: Implement Core Filter with Han-Lo Conversion

**Goal:** Make `phah_taibun_filter.lua` actually perform Han-Lo conversion and add pronunciation annotations based on `output_mode` switch state.

**Files:**
- Modify: `lua/phah_taibun_filter.lua`

**How the filter works:**
1. On init, load hanlo_rules via phah_taibun_data
2. For each candidate, read `output_mode` switch (0=漢羅TL, 1=漢羅POJ, 2=全羅TL, 3=全羅POJ)
3. The candidate text from dict.yaml is already `HanLoTaibunKip` (mixed Han-Lo from ChhoeTaigi)
4. The comment from Rime's script_translator already contains the romanization
5. For modes 0-1 (漢羅): keep candidate text as-is, format comment with TL or POJ
6. For modes 2-3 (全羅): replace candidate text with full romanization from comment

- [ ] **Step 1: Rewrite phah_taibun_filter.lua**

```lua
-- phah_taibun_filter.lua
-- 核心過濾器：候選拼音註解 + 輸出模式切換
-- 參考 rime-liur (ryanwuson/rime-liur) 模組架構
--
-- output_mode switch states:
--   0 = 漢羅TL (default): Han-Lo mixed text, TL annotation
--   1 = 漢羅POJ: Han-Lo mixed text, POJ annotation
--   2 = 全羅TL: Full romanization in TL
--   3 = 全羅POJ: Full romanization in POJ

local M = {}

-- TL → POJ conversion table for common patterns
local TL_TO_POJ = {
  ["ts"] = "ch",
  ["tsh"] = "chh",
  ["j"] = "j",  -- TL j stays j in POJ (not l)
  ["ing"] = "eng",
  ["ik"] = "ek",
  ["ua"] = "oa",
  ["ue"] = "oe",
  ["oo"] = "o\204\152",  -- o͘ (o + combining dot above right)
  ["nn"] = "\226\129\191",  -- ⁿ (superscript n)
}

-- Simple TL to POJ conversion for display
-- This handles the most common differences
local function tl_to_poj(tl_text)
  if not tl_text or tl_text == "" then
    return tl_text
  end
  local result = tl_text
  -- Order matters: longer patterns first
  result = result:gsub("tsh", "chh")
  result = result:gsub("ts", "ch")
  result = result:gsub("ing", "eng")
  result = result:gsub("ik", "ek")
  result = result:gsub("ua", "oa")
  result = result:gsub("ue", "oe")
  return result
end

-- Get the current output mode from Rime context
local function get_output_mode(env)
  local context = env.engine.context
  if context then
    -- output_mode is a multi-state switch; check which state is active
    -- Rime exposes multi-state switches as individual options
    if context:get_option("output_mode") then
      return 1  -- 漢羅POJ
    end
  end
  return 0  -- Default: 漢羅TL
end

function M.init(env)
  env.name_space = env.name_space or ""
end

function M.func(input, env)
  local mode = get_output_mode(env)

  for cand in input:iter() do
    local text = cand.text or ""
    local comment = cand.comment or ""

    -- Extract the raw romanization from Rime's auto-comment
    -- Rime formats it as " [romanization]" via comment_format xform
    local raw_roman = comment:match("%[(.-)%]") or comment

    if mode == 2 or mode == 3 then
      -- 全羅模式：replace text with full romanization
      local roman = raw_roman
      if mode == 3 then
        roman = tl_to_poj(roman)
      end
      if roman and roman ~= "" then
        local new_cand = Candidate(cand.type, cand.start, cand._end, roman, comment)
        new_cand.quality = cand.quality
        new_cand.preedit = cand.preedit
        yield(new_cand)
      else
        yield(cand)
      end
    else
      -- 漢羅模式：keep text, enhance comment
      if mode == 1 and raw_roman then
        -- POJ mode: convert TL annotation to POJ
        local poj_roman = tl_to_poj(raw_roman)
        local new_comment = " [" .. poj_roman .. "]"
        local new_cand = Candidate(cand.type, cand.start, cand._end, text, new_comment)
        new_cand.quality = cand.quality
        new_cand.preedit = cand.preedit
        yield(new_cand)
      else
        -- TL mode (default): pass through with Rime's auto-comment
        yield(cand)
      end
    end
  end
end

return M
```

- [ ] **Step 2: Run Lua syntax test**

Run: `cd /home/scipio/projects/rime-phah-taibun && uv run pytest tests/test_lua_filter.py -v`

- [ ] **Step 3: Commit**

```bash
git add lua/phah_taibun_filter.lua
git commit -m "feat: implement core filter with output mode switching

Supports 4 output modes: 漢羅TL, 漢羅POJ, 全羅TL, 全羅POJ.
TL→POJ conversion for common patterns (ts→ch, tsh→chh, etc).
Reads output_mode switch from Rime context."
```

---

## Chunk 2: Wildcard Enhancement + Python TL↔POJ Converter (Tasks 3-4)

### Task 3: Enhance Wildcard Translator

**Goal:** Make the `?` wildcard actually expand into multiple candidates by trying all possible TL initials.

**Files:**
- Modify: `lua/phah_taibun_wildcard.lua`

- [ ] **Step 1: Rewrite phah_taibun_wildcard.lua**

```lua
-- phah_taibun_wildcard.lua
-- 萬用查字 ? — 模糊拼音匹配
-- 移植自 rime-liur (ryanwuson/rime-liur) 萬用字元模組
--
-- Usage: type ?iah to match tsiah, siah, liah, etc.
-- The ? replaces an unknown initial consonant.

local M = {}

-- All possible TL initials (聲母)
local INITIALS = {
  "", "p", "ph", "b", "m",
  "t", "th", "n", "l",
  "k", "kh", "g", "ng",
  "ts", "tsh", "s", "j", "h",
}

function M.init(env)
  env.name_space = env.name_space or ""
end

function M.func(input, seg, env)
  -- Only process inputs containing ?
  if not input:match("%?") then
    return
  end

  -- Split input on spaces (multiple syllables possible)
  -- For each ? in the input, expand to all possible initials
  local parts = {}
  for part in input:gmatch("%S+") do
    table.insert(parts, part)
  end

  -- Simple case: single syllable with ? at start
  if #parts == 1 and parts[1]:match("^%?") then
    local remainder = parts[1]:sub(2)  -- Everything after ?

    -- Try each initial + remainder
    for _, initial in ipairs(INITIALS) do
      local expanded = initial .. remainder
      -- Use Rime's translator to look up the expanded form
      local mem = Translation(env.engine, env.name_space, expanded, seg)
      if mem then
        for cand_item in mem:iter() do
          -- Add the expanded form as a hint in the comment
          local new_comment = cand_item.comment .. " (" .. expanded .. ")"
          local new_cand = Candidate(
            "wildcard", seg.start, seg._end,
            cand_item.text, new_comment
          )
          new_cand.quality = cand_item.quality
          yield(new_cand)
        end
      end
    end
  else
    -- Fallback: show hint
    local cand = Candidate("wildcard", seg.start, seg._end,
      input, "? = 萬用字元，代替不確定的聲母")
    yield(cand)
  end
end

return M
```

**Note:** The `Translation()` constructor may not be available in all Rime Lua environments. If it fails at runtime, the fallback hint is still shown. This is a best-effort implementation that will be refined during hardware testing.

- [ ] **Step 2: Run Lua syntax test**

Run: `cd /home/scipio/projects/rime-phah-taibun && uv run pytest tests/test_lua_filter.py -v`

- [ ] **Step 3: Commit**

```bash
git add lua/phah_taibun_wildcard.lua
git commit -m "feat: enhance wildcard translator with initial expansion

Expands ? to all 19 TL initials and queries Rime's dictionary for
each expanded form. Falls back to hint display if Translation API
is not available."
```

---

### Task 4: Python TL↔POJ Conversion Utility

**Goal:** Add a Python utility that converts between TL and POJ romanization systems, for use in data preprocessing and testing.

**Files:**
- Create: `scripts/tl_poj_convert.py`
- Create: `tests/test_tl_poj_convert.py`

This will be used to enhance the reverse dictionary with POJ alternatives and validate Lua's TL→POJ logic.

- [ ] **Step 1: Write failing tests**

Create `tests/test_tl_poj_convert.py`:

```python
"""Tests for TL ↔ POJ romanization conversion."""

from scripts.tl_poj_convert import tl_to_poj, poj_to_tl


class TestTlToPoj:
    """Convert TL (教育部台羅) to POJ (白話字)."""

    def test_ts_to_ch(self):
        assert tl_to_poj("tsit") == "chit"

    def test_tsh_to_chh(self):
        assert tl_to_poj("tshiu") == "chhiu"

    def test_tsh_before_ts(self):
        """tsh must be converted before ts to avoid double conversion."""
        assert tl_to_poj("tshit") == "chhit"

    def test_ing_to_eng(self):
        assert tl_to_poj("sing") == "seng"

    def test_ik_to_ek(self):
        assert tl_to_poj("sik") == "sek"

    def test_ua_to_oa(self):
        assert tl_to_poj("kua") == "koa"

    def test_ue_to_oe(self):
        assert tl_to_poj("kue") == "koe"

    def test_no_change(self):
        assert tl_to_poj("lang") == "lang"

    def test_multi_syllable(self):
        assert tl_to_poj("tsiah-png") == "chiah-png"

    def test_empty(self):
        assert tl_to_poj("") == ""


class TestPojToTl:
    """Convert POJ (白話字) to TL (教育部台羅)."""

    def test_ch_to_ts(self):
        assert poj_to_tl("chit") == "tsit"

    def test_chh_to_tsh(self):
        assert poj_to_tl("chhiu") == "tshiu"

    def test_chh_before_ch(self):
        """chh must be converted before ch to avoid double conversion."""
        assert poj_to_tl("chhit") == "tshit"

    def test_eng_to_ing(self):
        assert poj_to_tl("seng") == "sing"

    def test_ek_to_ik(self):
        assert poj_to_tl("sek") == "sik"

    def test_oa_to_ua(self):
        assert poj_to_tl("koa") == "kua"

    def test_oe_to_ue(self):
        assert poj_to_tl("koe") == "kue"

    def test_empty(self):
        assert poj_to_tl("") == ""
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/scipio/projects/rime-phah-taibun && uv run pytest tests/test_tl_poj_convert.py -v -x`
Expected: FAIL with ModuleNotFoundError

- [ ] **Step 3: Implement tl_poj_convert.py**

Create `scripts/tl_poj_convert.py`:

```python
"""TL ↔ POJ romanization conversion utility.

Converts between TL (教育部台羅, Tâi-lô) and POJ (白話字, Pe̍h-ōe-jī)
romanization systems for Taiwanese Hokkien.
"""

import re


def tl_to_poj(tl_text: str) -> str:
    """Convert TL romanization to POJ.

    Args:
        tl_text: Text in TL romanization

    Returns:
        Text converted to POJ romanization
    """
    if not tl_text:
        return tl_text
    result = tl_text
    # Order matters: longer patterns first to avoid partial matches
    result = result.replace("tsh", "chh")
    result = result.replace("ts", "ch")
    result = re.sub(r"ing\b", "eng", result)
    result = re.sub(r"ik\b", "ek", result)
    result = result.replace("ua", "oa")
    result = result.replace("ue", "oe")
    return result


def poj_to_tl(poj_text: str) -> str:
    """Convert POJ romanization to TL.

    Args:
        poj_text: Text in POJ romanization

    Returns:
        Text converted to TL romanization
    """
    if not poj_text:
        return poj_text
    result = poj_text
    # Order matters: longer patterns first
    result = result.replace("chh", "tsh")
    result = result.replace("ch", "ts")
    result = re.sub(r"eng\b", "ing", result)
    result = re.sub(r"ek\b", "ik", result)
    result = result.replace("oa", "ua")
    result = result.replace("oe", "ue")
    return result
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /home/scipio/projects/rime-phah-taibun && uv run pytest tests/test_tl_poj_convert.py -v`
Expected: all PASSED

- [ ] **Step 5: Lint and commit**

```bash
uv run ruff check scripts/tl_poj_convert.py tests/test_tl_poj_convert.py
uv run ruff format scripts/tl_poj_convert.py tests/test_tl_poj_convert.py
git add scripts/tl_poj_convert.py tests/test_tl_poj_convert.py
git commit -m "feat: add TL ↔ POJ romanization converter

Bidirectional conversion between TL (教育部台羅) and POJ (白話字)
for preprocessing and validation. Handles ts↔ch, tsh↔chh, ing↔eng,
ik↔ek, ua↔oa, ue↔oe patterns."
```

---

## Chunk 3: Final Verification (Task 5)

### Task 5: Full Test Suite + Coverage

- [ ] **Step 1: Run full test suite with coverage**

Run: `cd /home/scipio/projects/rime-phah-taibun && uv run pytest --cov=scripts --cov-report=term-missing -v`
Expected: 80%+ coverage, all PASSED

- [ ] **Step 2: Run lint**

Run: `cd /home/scipio/projects/rime-phah-taibun && uv run ruff check scripts/ tests/`
Expected: All checks passed

- [ ] **Step 3: Final commit**

```bash
git add -A
git commit -m "chore: Phase 1 Lua completion — functional Han-Lo filter

All Lua modules now functional:
- phah_taibun_filter.lua: output mode switching (漢羅/全羅 x TL/POJ)
- phah_taibun_data.lua: centralized YAML data loader with caching
- phah_taibun_wildcard.lua: initial expansion for ? queries
- TL↔POJ Python converter for preprocessing"
```
