-- phah_taibun_filter.lua
-- 核心過濾器：候選拼音註解 + 輸出模式切換 + 漢羅轉換
-- 參考 rime-liur (ryanwuson/rime-liur) 模組架構
--
-- Output mode is determined by two boolean switches:
--   full_romanization: off=漢羅 (Han-Lo mixed), on=全羅 (full romanization)
--   poj_mode:          off=TL,                   on=POJ
--
-- Combinations:
--   漢羅TL (default): full_romanization=off, poj_mode=off
--   漢羅POJ:          full_romanization=off, poj_mode=on
--   全羅TL:           full_romanization=on,  poj_mode=off
--   全羅POJ:          full_romanization=on,  poj_mode=on

local M = {}

-- Load shared data module
local data_mod = nil
local ok, mod = pcall(require, "phah_taibun_data")
if ok and mod then
  data_mod = mod
end

-- Use shared tl_to_poj from data module
local function tl_to_poj(tl_text)
  if data_mod then return data_mod.tl_to_poj(tl_text) end
  return tl_text
end

-- Get the current output mode from Rime context
-- Returns 0-3 based on two boolean switches:
--   0 = 漢羅TL, 1 = 漢羅POJ, 2 = 全羅TL, 3 = 全羅POJ
local function get_output_mode(env)
  local context = env.engine.context
  if not context then
    return 0
  end
  local full_roman = context:get_option("full_romanization")
  local poj = context:get_option("poj_mode")
  if full_roman and poj then
    return 3  -- 全羅POJ
  elseif full_roman then
    return 2  -- 全羅TL
  elseif poj then
    return 1  -- 漢羅POJ
  end
  return 0  -- 漢羅TL (default)
end

function M.init(env)
  env.name_space = env.name_space or ""
end

-- Count UTF-8 characters (not bytes)
local function utf8_len(s)
  if not s or s == "" then return 0 end
  local count = 0
  for _ in s:gmatch("[%z\1-\127\194-\244][\128-\191]*") do
    count = count + 1
  end
  return count
end

-- Check if a word should be displayed as romanization (lo) per hanlo_rules
-- Returns true if the word is classified as "lo" type
local function is_lo_type(word)
  if not data_mod then
    return false
  end
  local htype = data_mod.get_hanlo_type(word)
  return htype == "lo"
end

-- Apply hanlo rules to a single group (no "--" markers)
-- Returns: result_text, changed
local function apply_hanlo_rules_group(text, roman_group)
  local fmt = data_mod.format_romanization

  local chars = {}
  for char in text:gmatch("[%z\1-\127\194-\244][\128-\191]*") do
    table.insert(chars, char)
  end

  -- Split romanization syllables (hyphen-separated or space-separated)
  local syllables = {}
  for syl in roman_group:gmatch("[^%s%-]+") do
    table.insert(syllables, syl)
  end

  -- If syllable count doesn't match character count, keep original
  if #syllables ~= #chars then
    return text, false
  end

  -- Single character: check directly
  if #chars == 1 then
    if is_lo_type(text) then
      local result = fmt and fmt(roman_group) or roman_group
      return result, true
    end
    return text, false
  end

  -- Check each character: if "lo" type, replace with romanization (with diacritics)
  local result_parts = {}
  local changed = false
  for i, char in ipairs(chars) do
    if is_lo_type(char) then
      local syl = syllables[i]
      if fmt then syl = fmt(syl) end
      table.insert(result_parts, syl)
      changed = true
    else
      table.insert(result_parts, char)
    end
  end

  if changed then
    return table.concat(result_parts, ""), true
  end

  return text, false
end

-- Replace Han characters with romanization for words classified as "lo"
-- For single characters/words: check the whole word
-- For phrases: check each character individually
-- Handles "--" light-tone markers: splits text and romanization into groups
local function apply_hanlo_rules(text, raw_roman)
  if not data_mod or not raw_roman or raw_roman == "" then
    return text
  end

  local fmt = data_mod.format_romanization

  -- Check the whole word/phrase first (excluding "--" markers)
  local text_no_marker = text:gsub("%-%-", "")
  if is_lo_type(text_no_marker) then
    return fmt and fmt(raw_roman) or raw_roman
  end

  -- Split text on "--" into groups, and romanization on "--"
  local text_groups = {}
  local tpos = 1
  while true do
    local dp = text:find("--", tpos, true)
    if dp then
      table.insert(text_groups, text:sub(tpos, dp - 1))
      tpos = dp + 2
    else
      table.insert(text_groups, text:sub(tpos))
      break
    end
  end

  local roman_groups = {}
  local rpos = 1
  while true do
    local ds = raw_roman:find("--", rpos, true)
    if ds then
      table.insert(roman_groups, raw_roman:sub(rpos, ds - 1))
      rpos = ds + 2
    else
      table.insert(roman_groups, raw_roman:sub(rpos))
      break
    end
  end

  -- Group counts must match
  if #text_groups ~= #roman_groups then
    return text
  end

  -- Process each group independently
  local result_groups = {}
  local changed = false
  for g = 1, #text_groups do
    local group_result, group_changed = apply_hanlo_rules_group(text_groups[g], roman_groups[g])
    table.insert(result_groups, group_result)
    if group_changed then changed = true end
  end

  if changed then
    return table.concat(result_groups, "--")
  end

  return text
end

function M.func(input, env)
  local mode = get_output_mode(env)

  for cand in input:iter() do
    local text = cand.text or ""
    local comment = cand.comment or ""

    -- Extract the raw romanization from Rime's auto-comment
    -- Rime formats it as " [romanization]" via comment_format xform
    local raw_roman = comment:match("%[(.-)%]") or ""

    -- Synchronize light-tone "--" from text to romanization.
    -- User dictionary may cache text with "--" but romanization without it.
    if raw_roman ~= "" and text:find("--", 1, true) and not raw_roman:find("--", 1, true) then
      local before = text:match("^(.-)%-%-")
      if before then
        local char_count = 0
        for _ in before:gmatch("[%z\1-\127\194-\244][\128-\191]*") do
          char_count = char_count + 1
        end
        local syls = {}
        for syl in raw_roman:gmatch("[^%s]+") do
          table.insert(syls, syl)
        end
        if char_count > 0 and char_count < #syls then
          local pre = table.concat(syls, " ", 1, char_count)
          local suf = table.concat(syls, " ", char_count + 1)
          raw_roman = pre .. "--" .. suf
        end
      end
    end

    -- Convert tone numbers to diacritics for display (e.g. "gua2" → "guá")
    local fmt = data_mod and data_mod.format_romanization or nil

    if mode == 2 or mode == 3 then
      -- 全羅模式：候選清單顯示漢羅（跟漢羅模式一樣），確定後由 processor 輸出全羅拼音
      local roman = raw_roman
      if mode == 3 then
        roman = tl_to_poj(roman)
      end
      if roman and roman ~= "" then
        -- 候選清單顯示漢羅文字（套用 hanlo rules，跟漢羅模式相同）
        local display_text = text
        if raw_roman ~= "" then
          display_text = apply_hanlo_rules(text, raw_roman)
        end
        -- POJ 模式下，漢羅文字中的羅馬字也要轉 POJ
        if mode == 3 and display_text ~= text then
          display_text = tl_to_poj(display_text)
        end

        -- Boost quality for multi-syllable phrases
        -- Count actual syllables (not individual spaces — double-space is one boundary)
        local syllable_count = 0
        for _ in roman:gmatch("[^%s%-]+") do syllable_count = syllable_count + 1 end
        local boost = 0
        if syllable_count >= 3 then
          boost = 1.0
        elseif syllable_count >= 2 then
          boost = 0.5
        end

        -- text = 漢羅 (顯示在候選清單)
        -- comment = [roman] (全羅拼音，調符版，由 phah_taibun_commit processor 用來輸出)
        local display_roman = fmt and fmt(roman) or roman
        if mode == 3 and data_mod and data_mod.poj_fix_diacritics then
          display_roman = data_mod.poj_fix_diacritics(display_roman)
          if display_text ~= text then
            display_text = data_mod.poj_fix_diacritics(display_text)
          end
        end
        local display_comment = " [" .. display_roman .. "]"
        local new_cand = Candidate(cand.type, cand.start, cand._end, display_text, display_comment)
        new_cand.quality = cand.quality + boost
        new_cand.preedit = cand.preedit
        yield(new_cand)
      else
        yield(cand)
      end
    else
      -- 漢羅模式：apply hanlo_rules to determine Han vs Lo output
      local new_text = text
      if raw_roman ~= "" then
        new_text = apply_hanlo_rules(text, raw_roman)
      end

      local display_roman = raw_roman
      if mode == 1 and raw_roman ~= "" then
        -- POJ mode: convert TL annotation to POJ
        display_roman = tl_to_poj(raw_roman)
      end

      -- If mode 1 (POJ) and text changed to romanization, convert that too
      if mode == 1 and new_text ~= text then
        new_text = tl_to_poj(new_text)
      end

      -- Convert comment to diacritics
      local new_comment = comment
      if display_roman ~= "" then
        local formatted = fmt and fmt(display_roman) or display_roman
        if mode == 1 and data_mod and data_mod.poj_fix_diacritics then
          formatted = data_mod.poj_fix_diacritics(formatted)
          if new_text ~= text then
            new_text = data_mod.poj_fix_diacritics(new_text)
          end
        end
        new_comment = " [" .. formatted .. "]"
      end

      -- LKK lo-type 候選排前面（如 ê、kah 等應為羅馬字的詞）
      local lo_boost = 0
      if new_text ~= text then
        lo_boost = 5.0
      end

      -- Boost quality for longer matches (multi-character phrases)
      -- Exclude "--" light-tone markers from length count
      local text_for_len = new_text:gsub("%-%-", "")
      local text_len = utf8_len(text_for_len)
      local boost = lo_boost
      if text_len >= 4 then
        boost = boost + 1.0
      elseif text_len >= 2 then
        boost = boost + 0.5
      end

      if new_text ~= text or new_comment ~= comment or boost > 0 then
        local new_cand = Candidate(cand.type, cand.start, cand._end, new_text, new_comment)
        new_cand.quality = cand.quality + boost
        new_cand.preedit = cand.preedit
        yield(new_cand)
      else
        yield(cand)
      end
    end
  end
end

return M
