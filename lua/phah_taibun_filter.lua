-- phah_taibun_filter.lua
-- 核心過濾器：候選拼音註解 + 輸出模式切換 + 漢羅轉換
-- 參考 rime-liur (ryanwuson/rime-liur) 模組架構
--
-- output_mode switch states:
--   0 = 漢羅TL (default): Han-Lo mixed text, TL annotation
--   1 = 漢羅POJ: Han-Lo mixed text, POJ annotation
--   2 = 全羅TL: Full romanization in TL
--   3 = 全羅POJ: Full romanization in POJ

local M = {}

-- Simple TL to POJ conversion for display
-- Handles the most common differences between the two systems
local function tl_to_poj(tl_text)
  if not tl_text or tl_text == "" then
    return tl_text
  end
  local result = tl_text
  -- Order matters: longer patterns first
  result = result:gsub("tsh", "chh")
  result = result:gsub("ts", "ch")
  result = result:gsub("ing([^a-z])", "eng%1")
  result = result:gsub("ing$", "eng")
  result = result:gsub("ik([^a-z])", "ek%1")
  result = result:gsub("ik$", "ek")
  result = result:gsub("ua", "oa")
  result = result:gsub("ue", "oe")
  return result
end

-- Get the current output mode from Rime context
-- Returns 0-3 based on output_mode switch state
local function get_output_mode(env)
  local context = env.engine.context
  if not context then
    return 0
  end
  -- Rime multi-state switches: check option name with index suffix
  -- output_mode is defined with 4 states in schema
  if context:get_option("output_mode") then
    return 1  -- 漢羅POJ
  end
  return 0  -- Default: 漢羅TL
end

-- Reference to data module (loaded in init)
local data_mod = nil

function M.init(env)
  env.name_space = env.name_space or ""

  -- Load hanlo_rules data module
  if not data_mod then
    local ok, mod = pcall(require, "phah_taibun_data")
    if ok and mod then
      data_mod = mod
    end
  end
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

-- Replace Han characters with romanization for words classified as "lo"
-- For single characters/words: check the whole word
-- For phrases: check each character individually
local function apply_hanlo_rules(text, raw_roman)
  if not data_mod or not raw_roman or raw_roman == "" then
    return text
  end

  -- Check the whole word/phrase first
  if is_lo_type(text) then
    return raw_roman
  end

  -- For multi-character text, check each character
  -- Split romanization by hyphens/spaces to match individual characters
  local chars = {}
  for char in text:gmatch("[%z\1-\127\194-\244][\128-\191]*") do
    table.insert(chars, char)
  end

  -- If single character, we already checked above
  if #chars <= 1 then
    return text
  end

  -- Split romanization syllables (hyphen-separated or space-separated)
  local syllables = {}
  for syl in raw_roman:gmatch("[^%s%-]+") do
    table.insert(syllables, syl)
  end

  -- If syllable count doesn't match character count, keep original
  if #syllables ~= #chars then
    return text
  end

  -- Check each character: if "lo" type, replace with romanization
  local result_parts = {}
  local changed = false
  for i, char in ipairs(chars) do
    if is_lo_type(char) then
      table.insert(result_parts, syllables[i])
      changed = true
    else
      table.insert(result_parts, char)
    end
  end

  if changed then
    return table.concat(result_parts, "")
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

    if mode == 2 or mode == 3 then
      -- 全羅模式：replace text with full romanization
      local roman = raw_roman
      if mode == 3 then
        roman = tl_to_poj(roman)
      end
      if roman and roman ~= "" then
        -- Boost quality for multi-syllable phrases
        local syllable_count = 1
        for _ in roman:gmatch(" ") do syllable_count = syllable_count + 1 end
        local boost = 0
        if syllable_count >= 3 then
          boost = 1.0
        elseif syllable_count >= 2 then
          boost = 0.5
        end
        local new_cand = Candidate(cand.type, cand.start, cand._end, roman, comment)
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

      local new_comment = comment
      if display_roman ~= "" and display_roman ~= raw_roman then
        new_comment = " [" .. display_roman .. "]"
      end

      -- Boost quality for longer matches (multi-character phrases)
      local text_len = utf8_len(new_text)
      local boost = 0
      if text_len >= 4 then
        boost = 1.0    -- 4+ chars: strong boost (e.g., 無要緊, tshit-thô)
      elseif text_len >= 2 then
        boost = 0.5    -- 2-3 chars: moderate boost (e.g., 食飯, 我去)
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
