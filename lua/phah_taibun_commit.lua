-- phah_taibun_commit.lua
-- 全羅模式輸出處理器：候選清單顯示漢羅，確定選字後輸出全羅拼音
--
-- 在全羅模式下，filter 將候選 text 設為漢羅顯示文字，
-- 全羅拼音存在 comment 的 [roman] 中。
-- 本 processor 攔截選字按鍵，改為輸出 comment 中的全羅拼音，
-- 並將聲調數字轉為 Unicode 調符、空格轉為連字符。

local M = {}

-- ============================================================
-- TL ↔ POJ consonant/vowel conversion
-- ============================================================
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
  result = result:gsub("ua", "oa")
  result = result:gsub("ue", "oe")
  return result
end

-- ============================================================
-- Tone number → Unicode combining diacritics
-- ============================================================
-- Combining diacritical marks (UTF-8 encoded)
local TONE_MARKS = {
  ["2"] = "\xCC\x81",  -- U+0301 combining acute accent
  ["3"] = "\xCC\x80",  -- U+0300 combining grave accent
  ["5"] = "\xCC\x82",  -- U+0302 combining circumflex
  ["7"] = "\xCC\x84",  -- U+0304 combining macron
  ["8"] = "\xCC\x8D",  -- U+030D combining vertical line above
  ["9"] = "\xCC\x86",  -- U+0306 combining breve
}

-- Add tone diacritic to a single syllable (e.g. "gua2" → "guá")
-- TL tone mark placement rules:
--   1. 'oo' → mark first 'o'
--   2. 'a'  → mark 'a'
--   3. 'e'  → mark 'e'
--   4. last vowel (i, o, u)
--   5. syllabic nasal (m, n)
local function add_tone_to_syllable(syl)
  local tone = syl:sub(-1)
  local mark = TONE_MARKS[tone]
  if not mark then
    return syl  -- no tone number (tone 1 or 4), return as-is
  end

  local base = syl:sub(1, -2)

  -- Find the vowel position to place the mark after
  local pos = nil

  -- Priority 1: 'oo' → mark first 'o'
  local oo_pos = base:find("oo")
  if oo_pos then
    pos = oo_pos
  end

  -- Priority 2: 'a'
  if not pos then
    pos = base:find("a")
  end

  -- Priority 3: 'e'
  if not pos then
    pos = base:find("e")
  end

  -- Priority 4: last vowel (i, o, u)
  if not pos then
    for i = #base, 1, -1 do
      local c = base:sub(i, i)
      if c == "i" or c == "o" or c == "u" then
        pos = i
        break
      end
    end
  end

  -- Priority 5: syllabic nasal (m, n in 'm7', 'ng7', etc.)
  if not pos then
    pos = base:find("[mn]")
  end

  if pos then
    return base:sub(1, pos) .. mark .. base:sub(pos + 1)
  end

  -- Fallback: just remove the tone number
  return base
end

-- Convert space-separated syllables with tone numbers to
-- hyphen-joined syllables with Unicode diacritics
-- e.g. "gua2 ai li" → "guá-ai-lī"  (wait, "li" has no tone → "li")
local function format_romanization(roman)
  if not roman or roman == "" then
    return roman
  end
  local parts = {}
  for syl in roman:gmatch("[^%s]+") do
    table.insert(parts, add_tone_to_syllable(syl))
  end
  return table.concat(parts, "-")
end

-- ============================================================
-- Processor
-- ============================================================
function M.init(env)
  local config = env.engine.schema.config
  env.page_size = config:get_int("menu/page_size") or 5

  -- Build select key → page-relative index mapping
  local keys = config:get_string("menu/select_keys") or "1234567890"
  env.select_map = {}
  for i = 1, #keys do
    env.select_map[keys:byte(i)] = i - 1  -- 0-based
  end
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

function M.func(key, env)
  local context = env.engine.context

  -- Only active when composing in 全羅 mode
  if not context:is_composing() and not context:has_menu() then
    return 2  -- kNoop
  end
  if key:release() then return 2 end
  if not context:get_option("full_romanization") then
    return 2  -- kNoop, let normal processing handle non-全羅 modes
  end

  local kc = key.keycode

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
