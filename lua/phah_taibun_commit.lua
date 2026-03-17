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

-- ============================================================
-- Utilities
-- ============================================================

-- Count UTF-8 characters
local function utf8_len(s)
  if not s or s == "" then return 0 end
  local count = 0
  for _ in s:gmatch("[%z\1-\127\194-\244][\128-\191]*") do
    count = count + 1
  end
  return count
end

-- TL → POJ conversion
local function tl_to_poj(tl_text)
  if not tl_text or tl_text == "" then
    return tl_text
  end
  local result = tl_text
  result = result:gsub("tsh", "chh")
  result = result:gsub("ts", "ch")
  result = result:gsub("ing([^a-z])", "eng%1")
  result = result:gsub("ing$", "eng")
  result = result:gsub("ik([^a-z])", "ek%1")
  result = result:gsub("ik$", "ek")
  -- POJ special characters
  result = result:gsub("nn", "\226\129\191")                    -- nn → ⁿ (U+207F)
  result = result:gsub("o(\204[\128-\191])o", "o%1\205\152")    -- ó+o → ó͘ (with tone diacritic)
  result = result:gsub("oo", "o\205\152")                       -- oo → o͘ (U+0358)
  result = result:gsub("ua", "oa")
  result = result:gsub("ue", "oe")
  return result
end

-- Use shared format_romanization from data module
local function format_romanization(roman)
  if data_mod and data_mod.format_romanization then
    return data_mod.format_romanization(roman)
  end
  return roman
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

  -- Track last committed character for homophone
  env.last_text = nil
end

-- Extract romanization from candidate's comment
-- Handles both simple [roman] and lookup-modified [TL:roman POJ:roman] formats
local function extract_roman(cand, env)
  if not cand then return nil end
  local comment = cand.comment or ""
  local content = comment:match("%[(.-)%]")
  if not content or content == "" then return nil end

  local context = env.engine.context
  local poj = context and context:get_option("poj_mode")

  -- Handle dual annotation format from phah_taibun_lookup:
  -- [TL:gua2 ai li POJ:goa2 ai li]
  local tl_part = content:match("TL:(.-)%s+POJ:")
  local poj_part = content:match("POJ:(.+)")
  if tl_part and poj_part then
    local raw = poj and poj_part or tl_part
    return format_romanization(raw)
  end

  -- Simple format: [gua2 ai li]
  local raw = content
  if poj then
    raw = tl_to_poj(raw)
  end
  return format_romanization(raw)
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

function M.func(key, env)
  local context = env.engine.context

  -- ============================================================
  -- NOT COMPOSING: homophone trigger with '
  -- ============================================================
  if not context:is_composing() and not context:has_menu() then
    if key:release() then return 2 end

    if key:repr() == "apostrophe" and env.last_text then
      local tl_code = nil
      -- Try ReverseLookup first
      if env.rev then
        local code = env.rev:lookup(env.last_text)
        if code and code ~= "" then
          tl_code = code:match("^(%S+)")
        end
      end
      -- Fallback: hoabun_map
      if not tl_code and data_mod and data_mod.hoabun_to_tl then
        tl_code = data_mod.hoabun_to_tl(env.last_text)
      end
      if tl_code then
        context:push_input(tl_code)
        env.last_text = nil  -- one-shot
        return 1  -- kAccepted
      end
    end

    -- Clear last_text on non-modifier keys (not ', not Shift/Ctrl/etc.)
    if key:repr() ~= "apostrophe" and not key:repr():match("^[A-Z]") then
      env.last_text = nil
    end
    return 2  -- kNoop
  end

  if key:release() then return 2 end

  local input = context.input or ""
  local kc = key.keycode

  -- ============================================================
  -- WILDCARD FEED-BACK: ?pattern → select romanization → push as input
  -- ============================================================
  if input:match("^%?") and input ~= "?" then
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

    if kc == 0x20 then  -- space
      local cand = context:get_selected_candidate()
      if cand then
        local tl_code = lookup_tl(cand.text)
        if tl_code then
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
        -- 全羅 mode: output the Han-Lo display text (cand.text)
        -- In 全羅 mode, filter sets cand.text to Han-Lo display text
        env.engine:commit_text(cand.text)
        context:clear()
        return 1  -- kAccepted
      else
        -- 漢羅 mode: output full romanization
        local roman = extract_roman(cand, env)
        if roman then
          env.engine:commit_text(roman)
          context:clear()
          return 1  -- kAccepted
        end
      end
    end
    return 2
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
      -- Only track single characters (useful for homophone)
      if cand and utf8_len(cand.text) == 1 then
        env.last_text = cand.text
      else
        env.last_text = nil
      end
    end
  end

  local full_roman = context:get_option("full_romanization")

  -- 以下只在全羅模式下攔截
  if not full_roman then
    return 2  -- kNoop, let normal processing handle 漢羅 modes
  end

  -- Handle space → confirm selected candidate with romanization
  if kc == 0x20 then
    local cand = context:get_selected_candidate()
    local roman = extract_roman(cand, env)
    if roman then
      env.engine:commit_text(roman)
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
        env.engine:commit_text(roman)
        context:clear()
        return 1  -- kAccepted
      end
    end
    return 2
  end

  return 2  -- kNoop for all other keys
end

return M
