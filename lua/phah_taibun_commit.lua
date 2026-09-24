-- phah_taibun_commit.lua
-- 多功能選字處理器：
--   1. 全羅模式輸出（候選顯示漢羅，確定後輸出全羅拼音）
--   2. 反斜線 \ 強制輸出羅馬字
--   3. 萬用查字 ? 送回（選音節 → 送回主輸入查字）
--   4. 注音反查 ~ 送回（選字 → 查TL → 送回主輸入）
--   5. 同音選字 '（輸入後按 ' → 查同音字）

local M = {}

-- Load shared data module
local data_mod = nil
local ok, mod = pcall(require, "phah_taibun_data")
if ok and mod then
  data_mod = mod
end

-- Learning observer (phah_taibun_learn): records user selections so the
-- learn filter can boost frequent words. Optional: without the module
-- committing works exactly as before.
local learn_mod = nil
local lok, lmod = pcall(require, "phah_taibun_learn")
if lok and lmod then
  learn_mod = lmod
end

local function observe(cand)
  if learn_mod and learn_mod.observe then
    learn_mod.observe(cand)
  end
end

-- ============================================================
-- Half-width punctuation for 全羅 mode
-- ============================================================
local PUNCT_MAP = {
  [0x2c] = ",",   -- comma (instead of ，)
  [0x2e] = ".",   -- period (instead of 。)
  [0x21] = "!",   -- exclamation (instead of ！)
  [0x3f] = "?",   -- question mark (instead of ？)
  [0x3a] = ":",   -- colon (instead of ：)
  [0x3b] = ";",   -- semicolon (instead of ；)
  [0x22] = '"',   -- double quote (instead of 「」)
  [0x27] = "'",   -- apostrophe (instead of 『』)
  [0x28] = "(",   -- left paren (instead of （)
  [0x29] = ")",   -- right paren (instead of ）)
  [0x2f] = "/",   -- slash (instead of 、)
  [0x5f] = "_",   -- underscore (instead of ——)
  [0x5b] = "[",   -- left bracket (instead of 「)
  [0x5d] = "]",   -- right bracket (instead of 」)
  [0x7b] = "{",   -- left brace (instead of 『)
  [0x7d] = "}",   -- right brace (instead of 』)
  [0x3c] = "<",   -- less-than (instead of 《)
  [0x3e] = ">",   -- greater-than (instead of 》)
}

local SENTENCE_ENDERS = { ["."] = true, ["!"] = true, ["?"] = true }

-- Ctrl+標點＝臨時翻寬：全羅模式改出全角（漢羅模式的臨時半角走 PUNCT_MAP）
local FULL_PUNCT_MAP = {
  [0x2c] = "，",
  [0x2e] = "。",
  [0x21] = "！",
  [0x3f] = "？",
  [0x3a] = "：",
  [0x3b] = "；",
  [0x28] = "（",
  [0x29] = "）",
}

-- ============================================================
-- Utilities (forwarding to shared data module)
-- ============================================================

local function capitalize_first(text)
  if data_mod then return data_mod.capitalize_first(text) end
  return text
end

local function utf8_len(s)
  if data_mod then return data_mod.utf8_len(s) end
  return 0
end

local function extract_roman(cand, env)
  if data_mod then return data_mod.extract_roman(cand, env.engine.context, env.engine) end
  return nil
end

local function extract_raw_code(cand)
  if data_mod then return data_mod.extract_raw_code(cand) end
  return nil
end

local function format_input_romanization(input, env)
  if data_mod and data_mod.format_input_romanization then
    return data_mod.format_input_romanization(input, env.engine.context:get_option("poj_mode"))
  end
  return nil
end

-- Get candidate at a specific index (for select keys)
local function get_candidate_at(context, env, rel_idx)
  local comp = context.composition
  if comp:empty() then return nil end
  local seg = comp:back()
  local old_idx = seg.selected_index
  local page = math.floor(old_idx / env.page_size)
  local abs_idx = page * env.page_size + rel_idx
  seg.selected_index = abs_idx
  local cand = context:get_selected_candidate()
  if not cand then
    seg.selected_index = old_idx  -- restore
  end
  return cand
end

-- ============================================================
-- Processor
-- ============================================================
function M.init(env)
  local config = env.engine.schema.config
  env.page_size = config:get_int("menu/page_size") or 5

  -- Build select key → page-relative index mapping
  local keys = config:get_string("menu/alternative_select_keys") or "1234567890"
  env.select_map = {}
  for i = 1, #keys do
    env.select_map[keys:byte(i)] = i - 1  -- 0-based
  end

  -- ReverseLookup for homophone and reverse lookup feed-back
  env.rev = nil
  local rok, rev
  rok, rev = pcall(function() return ReverseLookup("phah_taibun") end)
  if rok and rev then
    env.rev = rev
  end

  -- Shared state for cross-processor communication
  env.state = data_mod.get_shared_state()
  env.state.last_text = nil
  env.state.last_code = nil
  env.state.capitalize_next = true
end

function M.func(key, env)
  local context = env.engine.context
  local state = env.state

  -- ============================================================
  -- NOT COMPOSING: homophone trigger with '
  -- ============================================================
  if not context:is_composing() and not context:has_menu() then
    if key:release() then return 2 end

    if key:repr() == "apostrophe" and state.last_text then
      -- Prefer the reading the user actually selected (stored at commit
      -- time); re-deriving via reverse lookup may return another sound.
      local tl_code = state.last_code
      -- ReverseLookup only when the commit carried no numbered code
      if not tl_code and env.rev then
        local code = env.rev:lookup(state.last_text)
        if code and code ~= "" then
          tl_code = code:match("^(%S+)")
        end
      end
      -- Fallback: hoabun_map
      if not tl_code and data_mod and data_mod.hoabun_to_tl then
        tl_code = data_mod.hoabun_to_tl(state.last_text)
      end
      if tl_code then
        context:push_input(tl_code)
        state.last_text = nil  -- one-shot
        state.last_code = nil
        return 1  -- kAccepted
      end
    end

    -- 標點寬度：全羅→半角；Ctrl+標點＝臨時翻寬（漢羅→半角、全羅→全角）
    local full_roman = context:get_option("full_romanization")
    local repr = key:repr()
    if repr:find("Control+", 1, true) then
      local out
      if full_roman then
        out = FULL_PUNCT_MAP[key.keycode]
      else
        out = PUNCT_MAP[key.keycode]
      end
      if out then
        env.engine:commit_text(out)
        if SENTENCE_ENDERS[out] then
          state.capitalize_next = true
        end
        return 1  -- kAccepted
      end
      return 2  -- kNoop: let the punctuator see the bare key
    end
    if full_roman then
      local punct = PUNCT_MAP[key.keycode]
      if punct then
        env.engine:commit_text(punct)
        if SENTENCE_ENDERS[punct] then
          state.capitalize_next = true
        end
        return 1  -- kAccepted
      end
    end

    -- 漢羅 mode: double-quote alternates “ / ” (one commit per
    -- press). Pair punctuation cannot auto-commit via the punctuator,
    -- so the alternating state lives here (single source: the punctuator
    -- pair is unreachable because this processor runs first); 全羅
    -- keeps the straight ASCII quote through PUNCT_MAP above.
    if not full_roman and key.keycode == 0x22 then
      local quote = state.quote_open and "”" or "“"
      state.quote_open = not state.quote_open
      env.engine:commit_text(quote)
      state.last_text = nil
      return 1  -- kAccepted
    end

    -- Clear last_text on non-modifier keys (not ', not Shift/Ctrl/etc.)
    if key:repr() ~= "apostrophe" and not key:repr():match("^[A-Z]") then
      state.last_text = nil
      state.last_code = nil
    end
    return 2  -- kNoop
  end

  if key:release() then return 2 end

  local input = context.input or ""
  local kc = key.keycode

  -- ============================================================
  -- WILDCARD FEED-BACK: ?pattern → select romanization → push as input
  -- Supports ? at any position: ?iah, si?, s?ah
  -- ============================================================
  if input:find("?", 1, true) and input ~= "?" then
    if kc == 0x20 then  -- space
      local cand = context:get_selected_candidate()
      if cand and cand.type == "wildcard" and cand.text:match("^[a-z]") then
        context:clear()
        context:push_input(cand.text)
        return 1  -- kAccepted
      end
    end
    local rel_idx = env.select_map[kc]
    if rel_idx then
      local cand = get_candidate_at(context, env, rel_idx)
      if cand and cand.type == "wildcard" and cand.text:match("^[a-z]") then
        context:clear()
        context:push_input(cand.text)
        return 1
      end
    end
    -- Fall through for other keys
  end

  -- ============================================================
  -- REVERSE LOOKUP FEED-BACK: ~zhuyin → select → look up TL → push as input
  -- Uses ReverseLookup first, then hoabun_map (華→台) as fallback
  -- ============================================================
  if input:match("^~") then
    local full_roman = context:get_option("full_romanization")
    local poj = context:get_option("poj_mode")

    local function lookup_tl(text)
      -- Try ReverseLookup (for chars in our dictionary like 食, 人, 大)
      if env.rev then
        local code = env.rev:lookup(text)
        if code and code ~= "" then
          return code:match("^(%S+)")
        end
      end
      -- Fallback: hoabun_map (for Mandarin chars like 吃→tsiah8, 好→ho2)
      if data_mod and data_mod.hoabun_to_tl then
        local tl = data_mod.hoabun_to_tl(text)
        if tl then return tl end
      end
      return nil
    end

    -- 全羅 mode: directly commit formatted romanization (no feed-back needed,
    -- since all candidates for the same TL code produce the same romanization)
    local function commit_reverse_roman(tl_code)
      local roman = tl_code
      if poj and data_mod then
        roman = data_mod.tl_to_poj(roman)
      end
      if data_mod then
        roman = data_mod.format_romanization(roman)
      end
      if poj and data_mod and data_mod.poj_fix_diacritics then
        roman = data_mod.poj_fix_diacritics(roman)
      end
      if state.capitalize_next then
        roman = capitalize_first(roman)
      end
      env.engine:commit_text(roman)
      state.capitalize_next = false
      context:clear()
      return 1  -- kAccepted
    end

    if kc == 0x20 then  -- space
      local cand = context:get_selected_candidate()
      if cand then
        local tl_code = lookup_tl(cand.text)
        if tl_code then
          if full_roman then
            return commit_reverse_roman(tl_code)
          end
          context:clear()
          context:push_input(tl_code)
          return 1  -- kAccepted
        end
      end
      -- No TL code found: fall through to normal commit
    end
    local rel_idx = env.select_map[kc]
    if rel_idx then
      local cand = get_candidate_at(context, env, rel_idx)
      if cand then
        local tl_code = lookup_tl(cand.text)
        if tl_code then
          if full_roman then
            return commit_reverse_roman(tl_code)
          end
          context:clear()
          context:push_input(tl_code)
          return 1
        end
      end
    end
    -- Fall through for other keys or if no TL code
  end

  -- ============================================================
  -- BACKSLASH \：toggle output mode for current candidate
  --   漢羅 mode + \ → output full romanization (全羅)
  --   全羅 mode + \ → output Han-Lo mixed text (漢羅)
  -- ============================================================
  if key:repr() == "backslash" then
    local full_roman = context:get_option("full_romanization")
    local cand = context:get_selected_candidate()
    if cand then
      if full_roman then
        -- 全羅 mode: output the Han-Lo display text (cand.text), keeping
        -- any mid-sentence Tab selections buffered as romanization.
        local text = cand.text
        if state.roman_buffer and state.roman_buffer ~= "" then
          text = state.roman_buffer .. " " .. text
          state.roman_buffer = nil
        end
        env.engine:commit_text(text)
        observe(cand) -- 學習此次確認的候選
        context:clear()
        return 1  -- kAccepted
      else
        -- 漢羅 mode: output full romanization; in 手動漢羅 keep the marked
        -- segments in front and clear the mix state with the composition.
        local roman = extract_roman(cand, env)
        if roman then
          if state.mix_output and data_mod then
            data_mod.mix_append(state, #cand.text, roman, true)
            roman = state.mix_output
            state.mix_output, state.mix_bytes, state.mix_last_han = nil, 0, nil
          end
          env.engine:commit_text(roman)
          context:clear()
          return 1  -- kAccepted
        end
      end
    end
    return 2
  end

  -- 原文候選由 Lua 直接確認，確保句首大寫狀態只消耗一次。
  local origin_cand
  if kc == 0x20 then
    origin_cand = context:get_selected_candidate()
  else
    local origin_idx = env.select_map[kc]
    if origin_idx then
      origin_cand = get_candidate_at(context, env, origin_idx)
    end
  end
  if origin_cand and origin_cand.type == "origin" then
    local roman = origin_cand.text
    if state.capitalize_next then
      roman = capitalize_first(roman)
    end
    env.engine:commit_text(roman)
    state.capitalize_next = false
    context:clear()
    return 1  -- kAccepted
  end

  -- ============================================================
  -- 手動漢羅: segments marked with Tab+backslash assemble as romanization,
  -- everything else commits as hanzi. Applies to Space, select keys, and
  -- punctuation endings once any marking happened this composition.
  -- ============================================================
  if state.mix_output
     and context:get_option("hanlo_manual")
     and not context:get_option("full_romanization")
     and (kc == 0x20 or env.select_map[kc] or PUNCT_MAP[kc]) then
    local full_text = context:get_commit_text() or ""
    local remainder = full_text:sub((state.mix_bytes or 0) + 1)
    if remainder ~= "" then
      data_mod.mix_append(state, #remainder, remainder, false)
    end
    local text = state.mix_output
    state.mix_output, state.mix_bytes, state.mix_last_han = nil, 0, nil
    if state.capitalize_next then
      text = capitalize_first(text)
    end
    env.engine:commit_text(text)
    state.capitalize_next = false
    local punct = PUNCT_MAP[kc]
    if punct then
      env.engine:commit_text(punct)
      if SENTENCE_ENDERS[punct] then
        state.capitalize_next = true
      end
    end
    context:clear()
    return 1  -- kAccepted
  end

  -- ============================================================
  -- TRACK last committed character for homophone (all modes)
  -- Store before full_roman check so it works in 漢羅 mode too
  -- ============================================================
  if (kc == 0x20 or env.select_map[kc]) and context:has_menu() then
    local cand = context:get_selected_candidate()
    if cand then
      -- For select keys, get the candidate at the right index
      if env.select_map[kc] then
        cand = get_candidate_at(context, env, env.select_map[kc])
      end
      -- Learn the selection (both modes; origin/readingless candidates
      -- are skipped inside the observer).
      observe(cand)
      -- Only track single characters (useful for homophone)
      if cand and utf8_len(cand.text) == 1 then
        state.last_text = cand.text
        state.last_code = extract_raw_code(cand)
      else
        state.last_text = nil
        state.last_code = nil
      end
    end
  end

  local full_roman = context:get_option("full_romanization")

  -- In romanization modes, Return commits the sound the user typed instead of
  -- forcing a dictionary candidate. This keeps hyphen and light-tone input usable.
  -- The composition preedit keeps syllable spacing (context.input can arrive
  -- concatenated without separators), and the result is segmented into words.
  if full_roman and key:repr() == "Return"
     and input ~= "" and not input:match("^~") and not input:find("?", 1, true)
     and not input:match("^;") then
    local preedit = context:get_script_text()
    if preedit == "" then
      preedit = input
    end
    local roman = format_input_romanization(preedit, env)
    if roman then
      if state.capitalize_next then
        roman = capitalize_first(roman)
      end
      env.engine:commit_text(roman)
      state.capitalize_next = false
      context:clear()
      return 1  -- kAccepted
    end
  end

  -- 漢羅 mode: double-quote while composing commits the composition
  -- plus the alternating “ / ” quote.
  if not full_roman and kc == 0x22
     and not input:match("^~") and not input:find("?", 1, true)
     and not input:match("^`") and not input:match("^;") then
    local text = context:get_commit_text() or ""
    if text ~= "" then
      local quote = state.quote_open and "”" or "“"
      state.quote_open = not state.quote_open
      env.engine:commit_text(text)
      env.engine:commit_text(quote)
      state.last_text = nil
      context:clear()
      return 1  -- kAccepted
    end
  end

  -- 以下只在全羅模式下攔截
  if not full_roman then
    return 2  -- kNoop, let normal processing handle 漢羅 modes
  end

  -- Helper: commit romanization with auto-capitalization
  local function commit_roman(roman)
    if state.capitalize_next then
      roman = capitalize_first(roman)
    end
    env.engine:commit_text(roman)
    state.capitalize_next = false
  end

  -- Handle space → confirm selected candidate with romanization
  if kc == 0x20 then
    local cand = context:get_selected_candidate()
    local roman = extract_roman(cand, env)
    if not roman and cand then
      -- Sentence-composed candidates carry no comment romanization; the
      -- reading is the segmented preedit, and word boundaries come from
      -- reverse lookup on the candidate's Hanzi text.
      local preedit = context:get_script_text()
      if preedit ~= "" and data_mod
         and data_mod.format_sentence_romanization then
        local poj = context:get_option("poj_mode")
        roman = data_mod.format_sentence_romanization(cand.text, preedit, poj)
      end
    end
    -- 連打 (全羅): earlier mid-sentence Tab selections were confirmed into
    -- the composition with their romanization buffered. Prepend the buffer
    -- and re-segment the remainder so word boundaries survive: strip the
    -- confirmed hanzi prefix from the script text (which keeps syllable
    -- spacing; context.input arrives with delimiters consumed).
    if state.roman_buffer and state.roman_buffer ~= "" then
      local tail_roman = roman
      if cand and cand.text ~= "" and data_mod
         and data_mod.format_sentence_romanization then
        local full_text = context:get_commit_text() or ""
        if #full_text > #cand.text
           and full_text:sub(-#cand.text) == cand.text then
          local prefix_text = full_text:sub(1, #full_text - #cand.text)
          local script = context:get_script_text() or ""
          if script:sub(1, #prefix_text) == prefix_text then
            local tail = script:sub(#prefix_text + 1)
            if tail ~= "" then
              tail_roman = data_mod.format_sentence_romanization(
                cand.text, tail, context:get_option("poj_mode")) or tail_roman
            end
          end
        end
      end
      roman = tail_roman
        and (state.roman_buffer .. " " .. tail_roman) or state.roman_buffer
      state.roman_buffer = nil
    end
    if roman then
      commit_roman(roman)
      context:clear()
      return 1  -- kAccepted
    end
    return 2
  end

  -- Handle select keys → select specific candidate with romanization
  local rel_idx = env.select_map[kc]
  if rel_idx then
    local comp = context.composition
    if not comp:empty() then
      local seg = comp:back()
      local page = math.floor(seg.selected_index / env.page_size)
      local abs_idx = page * env.page_size + rel_idx

      -- Set selected index, then get the candidate
      seg.selected_index = abs_idx
      local cand = context:get_selected_candidate()
      local roman = extract_roman(cand, env)
      if roman then
        commit_roman(roman)
        context:clear()
        return 1  -- kAccepted
      end
    end
    return 2
  end

  -- Handle punctuation while composing: commit romanization + half-width punctuation
  local punct = PUNCT_MAP[kc]
  if punct and not input:match("^~") and not input:find("?", 1, true) then
    local cand = context:get_selected_candidate()
    local roman = extract_roman(cand, env)
    if roman then
      observe(cand) -- 學習此次確認的候選
      commit_roman(roman)
      env.engine:commit_text(punct)
      context:clear()
      if SENTENCE_ENDERS[punct] then
        state.capitalize_next = true
      end
      return 1  -- kAccepted
    end
  end

  return 2  -- kNoop for all other keys
end

return M
