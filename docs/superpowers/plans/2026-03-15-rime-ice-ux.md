# Rime-Ice UX Adoption Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [x]`) syntax for tracking.

**Status:** COMPLETED (2026-03-15)

**Goal:** Port 5 rime-ice UX features into phah-taibun: 以詞定字, 長詞優先, editor key bindings, emoji, inline English.

**Architecture:** Two new Lua modules (`phah_taibun_select_char.lua`, `phah_taibun_long_word.lua`) plus schema YAML config changes. Emoji and English use existing rime-ice data files (OpenCC, melt_eng dictionary) with no new code — config only. All changes are in `lua/`, `schema/`, and `rime.lua`.

**Tech Stack:** Lua 5.x (Rime sandbox), YAML (Rime schema config)

---

## Chunk 1: 以詞定字 (Select Character from Phrase)

### Task 1: Create phah_taibun_select_char.lua

**Files:**
- Create: `lua/phah_taibun_select_char.lua`

- [x] **Step 1: Write the Lua processor module**

```lua
-- phah_taibun_select_char.lua
-- 以詞定字：按 [ 選首字、按 ] 選尾字
-- Ported from rime-ice select_character.lua, adapted for phah-taibun

local M = {}

function M.init(env)
    local config = env.engine.schema.config
    env.name_space = env.name_space:gsub("^*", "")
    env.first_key = config:get_string(env.name_space .. "/first_key")
    env.last_key = config:get_string(env.name_space .. "/last_key")
end

function M.func(key, env)
    local engine = env.engine
    local context = engine.context

    if
        not key:release()
        and (context:is_composing() or context:has_menu())
        and (env.first_key or env.last_key)
    then
        local input = context.input
        local selected_candidate = context:get_selected_candidate()
        selected_candidate = selected_candidate and selected_candidate.text or input

        local selected_char = ""
        if key:repr() == env.first_key then
            selected_char = selected_candidate:sub(1, utf8.offset(selected_candidate, 2) - 1)
        elseif key:repr() == env.last_key then
            selected_char = selected_candidate:sub(utf8.offset(selected_candidate, -1))
        else
            return 2  -- kNoop
        end

        local commit_text = context:get_commit_text()
        local _, end_pos = commit_text:find(selected_candidate, 1, true)
        local caret_pos = context.caret_pos

        local part1 = commit_text:sub(1, end_pos):gsub(
            selected_candidate, selected_char, 1
        )
        local part2 = commit_text:sub(end_pos + 1)

        engine:commit_text(part1)
        context:clear()
        if caret_pos ~= #input then
            part2 = part2 .. input:sub(caret_pos + 1)
        end
        if part2 ~= "" then
            context:push_input(part2)
        end
        return 1  -- kAccepted
    end
    return 2  -- kNoop
end

return M
```

- [x] **Step 2: Verify Lua syntax**

Run: `luac -p lua/phah_taibun_select_char.lua` (or `lua5.3 -e "loadfile('lua/phah_taibun_select_char.lua')"`)
Expected: no output (clean syntax)

- [x] **Step 3: Run existing test suite to confirm no regressions**

Run: `cd /home/scipio/Downloads/rime-phah-taibun && mise exec uv -- uv run pytest tests/test_lua_filter.py -v`
Expected: All Lua syntax tests pass including the new file (parametrized glob picks it up automatically)

- [x] **Step 4: Commit**

```bash
git add lua/phah_taibun_select_char.lua
git commit -m "feat: add 以詞定字 select_char Lua processor"
```

---

## Chunk 2: 長詞優先 (Long Word Priority Filter)

### Task 2: Create phah_taibun_long_word.lua

**Files:**
- Create: `lua/phah_taibun_long_word.lua`

- [x] **Step 1: Write the Lua filter module**

```lua
-- phah_taibun_long_word.lua
-- 長詞優先：提升較長的候選詞到更前面的位置
-- Ported from rime-ice long_word_filter.lua, adapted for phah-taibun

local M = {}

function M.init(env)
    local config = env.engine.schema.config
    env.name_space = env.name_space:gsub("^*", "")
    env.lw_count = config:get_int(env.name_space .. "/count") or 2
    env.lw_idx = config:get_int(env.name_space .. "/idx") or 4
end

function M.func(input, env)
    local l = {}
    local first_len = 0
    local done = 0
    local i = 1
    local count = env.lw_count or 2
    local idx = env.lw_idx or 4
    for cand in input:iter() do
        local leng = utf8.len(cand.text)
        if first_len < 1 then
            first_len = leng
        end
        -- Don't reorder candidates before position idx
        if i < idx then
            i = i + 1
            yield(cand)
        -- Promote longer candidates, skip ASCII-only (English words)
        elseif leng <= first_len or cand.text:find("^[%a%d%p%s]+$") then
            table.insert(l, cand)
        else
            yield(cand)
            done = done + 1
        end
        -- Stop after promoting count candidates or buffering 50
        if done == count or #l > 50 then
            break
        end
    end
    -- Yield buffered candidates
    for _, cand in ipairs(l) do
        yield(cand)
    end
    -- Yield remaining candidates
    for cand in input:iter() do
        yield(cand)
    end
end

return M
```

- [x] **Step 2: Verify Lua syntax**

Run: `luac -p lua/phah_taibun_long_word.lua`
Expected: no output (clean syntax)

- [x] **Step 3: Run test suite**

Run: `cd /home/scipio/Downloads/rime-phah-taibun && mise exec uv -- uv run pytest tests/test_lua_filter.py -v`
Expected: All Lua syntax tests pass including new file

- [x] **Step 4: Commit**

```bash
git add lua/phah_taibun_long_word.lua
git commit -m "feat: add 長詞優先 long_word Lua filter"
```

---

## Chunk 3: Schema YAML Changes

### Task 3: Update schema with all 5 features

**Files:**
- Modify: `schema/phah_taibun.schema.yaml`

The final schema should look like this. Apply all changes in one edit:

- [x] **Step 1: Add `dependencies` to schema header**

After line 9 (`- "拍台文開發團隊"`), before `description:`, add:

```yaml
  dependencies:
    - melt_eng
```

- [x] **Step 2: Add emoji switch**

After the `output_mode` switch (line 23), add:

```yaml
  - name: emoji
    states: [ 💀, 😄 ]
    reset: 1
```

- [x] **Step 3: Update engine processors**

Replace the current processors block (lines 26-34) with:

```yaml
engine:
  processors:
    - ascii_composer
    - lua_processor@*phah_taibun_select_char
    - recognizer
    - key_binder
    - speller
    - punctuator
    - selector
    - navigator
    - fluency_editor
```

Note: `phah_taibun_select_char` goes AFTER `ascii_composer` so ASCII mode is handled first.

- [x] **Step 4: Update engine translators**

Add `table_translator@melt_eng` after `table_translator@custom_phrase`:

```yaml
    - table_translator@custom_phrase
    - table_translator@melt_eng
```

- [x] **Step 5: Update engine filters**

Replace the current filters block with:

```yaml
  filters:
    - lua_filter@*phah_taibun_filter
    - lua_filter@*phah_taibun_lookup
    - lua_filter@*phah_taibun_synonym
    - lua_filter@*phah_taibun_long_word
    - simplifier@emoji
    - uniquifier
```

- [x] **Step 6: Add new config sections at end of file**

Append after the `recognizer` section (after line 117):

```yaml

phah_taibun_select_char:
  first_key: bracketleft
  last_key: bracketright

phah_taibun_long_word:
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

key_binder:
  import_preset: default
  bindings:
    - { when: composing, accept: Tab, send: Shift+Right }
    - { when: composing, accept: Shift+Tab, send: Shift+Left }
    - { when: paging, accept: bracketleft, send: Page_Up }
    - { when: paging, accept: bracketright, send: Page_Down }
```

Note: this replaces the existing `key_binder: import_preset: default` (line 110-111) with the expanded version.

- [x] **Step 7: Validate YAML syntax**

Run: `cd /home/scipio/Downloads/rime-phah-taibun && mise exec uv -- uv run python -c "import yaml; yaml.safe_load(open('schema/phah_taibun.schema.yaml'))"`
Expected: No output (valid YAML)

- [x] **Step 8: Run full test suite**

Run: `cd /home/scipio/Downloads/rime-phah-taibun && mise exec uv -- uv run pytest tests/ -q`
Expected: All tests pass (including schema validation tests in test_validate.py)

- [x] **Step 9: Commit**

```bash
git add schema/phah_taibun.schema.yaml
git commit -m "feat: add rime-ice UX features to schema

- 以詞定字 processor (select_char)
- 長詞優先 filter (long_word)
- Editor key bindings (Tab syllable nav, Ctrl+Backspace)
- Emoji via OpenCC simplifier
- English melt_eng translator"
```

---

## Chunk 4: rime.lua Registration + Deploy

### Task 4: Register new modules in rime.lua and deploy

**Files:**
- Modify: `rime.lua` (project root — the install script merges this into the user's Rime directory)

- [x] **Step 1: Add module registrations to repo's rime.lua**

In `/home/scipio/Downloads/rime-phah-taibun/rime.lua`, append after `phah_taibun_speedup  = require("phah_taibun_speedup")`:

```lua
phah_taibun_select_char = require("phah_taibun_select_char")
phah_taibun_long_word = require("phah_taibun_long_word")
```

- [x] **Step 2: Also update the deployed rime.lua**

In `~/.local/share/fcitx5/rime/rime.lua`, append the same two lines after the existing `phah_taibun_speedup` line.

- [x] **Step 3: Copy new files to Rime directory**

```bash
cp lua/phah_taibun_select_char.lua ~/.local/share/fcitx5/rime/lua/
cp lua/phah_taibun_long_word.lua ~/.local/share/fcitx5/rime/lua/
cp schema/phah_taibun.schema.yaml ~/.local/share/fcitx5/rime/
```

- [x] **Step 4: Deploy and verify**

```bash
rime_deployer --build ~/.local/share/fcitx5/rime/ /usr/share/rime-data
```

Expected: Builds without errors. Check that `~/.local/share/fcitx5/rime/build/phah_taibun.prism.bin` is updated.

- [x] **Step 5: Run full test suite one final time**

Run: `cd /home/scipio/Downloads/rime-phah-taibun && mise exec uv -- uv run pytest tests/ -q`
Expected: All tests pass

- [x] **Step 6: Commit**

```bash
git add rime.lua
git commit -m "feat: register select_char and long_word modules in rime.lua"
```

---

## Chunk 5: Verify Dependencies

### Task 5: Verify emoji and melt_eng files are present

**Files:** None (verification only)

- [x] **Step 1: Check emoji OpenCC files**

```bash
ls ~/.local/share/fcitx5/rime/opencc/emoji.json ~/.local/share/fcitx5/rime/opencc/emoji.txt
```

Expected: Both files exist (copied from rime-ice during earlier installation).

- [x] **Step 2: Check melt_eng dictionary**

```bash
ls ~/.local/share/fcitx5/rime/melt_eng.dict.yaml ~/.local/share/fcitx5/rime/melt_eng.schema.yaml
```

Expected: Both files exist.

- [x] **Step 3: Check melt_eng is built**

```bash
ls ~/.local/share/fcitx5/rime/build/melt_eng.*.bin 2>/dev/null || echo "melt_eng not built — will be built on first use"
```

Expected: Either bin files exist, or they'll be built when Rime deploys. If not built yet, the deploy in Task 4 Step 3 should have built them.

- [x] **Step 4: Manual smoke test**

Switch to phah-taibun input method and verify:
1. Type `tsiah-png` → see `食飯` candidate → press `[` → should commit `食`
2. Type `gua beh khi tshit tho` → longer phrases should appear in top positions
3. Press Tab while composing → cursor should jump to next syllable
4. Type a word like `sim` (心) → should see ❤️ emoji candidate
5. Type `hello` → should see English `hello` candidate (below台語 results)
