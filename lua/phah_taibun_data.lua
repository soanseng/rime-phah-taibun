-- phah_taibun_data.lua
-- Centralized data loader for hanlo_rules
-- Caches loaded data globally to avoid repeated I/O

local M = {}

-- Global cache
local _hanlo_rules = nil
local _moe700_single = nil   -- set of single-char MOE 700 words
local _moe700_multi = nil    -- list of multi-char MOE 700 words
local _lkk_multi_keys = nil  -- list of multi-char hanlo_rules keys

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

-- ============================================================
-- MOE 700字推薦用字
-- ============================================================

-- Find the moe700.yaml file path
local function find_moe700_path()
  local dirs = {}
  if rime_api then
    local user_dir = rime_api.get_user_data_dir()
    if user_dir then table.insert(dirs, user_dir) end
    local shared_dir = rime_api.get_shared_data_dir()
    if shared_dir then table.insert(dirs, shared_dir) end
  end
  for _, dir in ipairs(dirs) do
    local path = dir .. "/moe700.yaml"
    local f = io.open(path, "r")
    if f then
      f:close()
      return path
    end
  end
  return nil
end

-- Parse moe700.yaml (simple YAML list: "- word" per line)
local function parse_moe700_yaml(content)
  local single = {}
  local multi = {}
  for line in content:gmatch("[^\r\n]+") do
    if line:match("^%s*#") or line:match("^%s*$") then
      goto continue
    end
    local word = line:match("^%-%s*(.+)$")
    if word then
      word = word:gsub("^'(.*)'$", "%1")
      local char_count = 0
      for _ in word:gmatch("[%z\1-\127\194-\244][\128-\191]*") do
        char_count = char_count + 1
      end
      if char_count == 1 then
        single[word] = true
      else
        table.insert(multi, word)
      end
    end
    ::continue::
  end
  return single, multi
end

-- Load and cache MOE 700 data
function M.get_moe700()
  if _moe700_single then
    return _moe700_single, _moe700_multi
  end

  local path = find_moe700_path()
  if not path then
    _moe700_single = {}
    _moe700_multi = {}
    return _moe700_single, _moe700_multi
  end

  local f = io.open(path, "r")
  if not f then
    _moe700_single = {}
    _moe700_multi = {}
    return _moe700_single, _moe700_multi
  end

  local content = f:read("*all")
  f:close()
  _moe700_single, _moe700_multi = parse_moe700_yaml(content)
  return _moe700_single, _moe700_multi
end

-- Check if any part of text matches MOE 700
function M.check_moe700(text)
  if not text or text == "" then return false end
  local single, multi = M.get_moe700()

  -- Check individual characters
  for char in text:gmatch("[%z\1-\127\194-\244][\128-\191]*") do
    if single[char] then return true end
  end

  -- Check multi-char words
  for _, word in ipairs(multi) do
    if text:find(word, 1, true) then return true end
  end

  return false
end

-- ============================================================
-- LKK推薦用字查詢
-- ============================================================

-- Build multi-char key list from hanlo_rules (cached)
local function get_lkk_multi_keys()
  if _lkk_multi_keys then return _lkk_multi_keys end
  local rules = M.get_hanlo_rules()
  _lkk_multi_keys = {}
  for key, _ in pairs(rules) do
    local char_count = 0
    for _ in key:gmatch("[%z\1-\127\194-\244][\128-\191]*") do
      char_count = char_count + 1
    end
    if char_count > 1 then
      table.insert(_lkk_multi_keys, key)
    end
  end
  return _lkk_multi_keys
end

-- Check if text has LKK recommended han or lo characters
-- Returns: has_han, has_lo
function M.check_lkk_recommend(text)
  if not text or text == "" then return false, false end
  local rules = M.get_hanlo_rules()
  local has_han = false
  local has_lo = false

  -- Check individual characters
  for char in text:gmatch("[%z\1-\127\194-\244][\128-\191]*") do
    local entry = rules[char]
    if entry then
      if entry.type == "han" then has_han = true end
      if entry.type == "lo" then has_lo = true end
    end
  end

  -- Check multi-char keys
  local multi_keys = get_lkk_multi_keys()
  for _, key in ipairs(multi_keys) do
    if text:find(key, 1, true) then
      local entry = rules[key]
      if entry then
        if entry.type == "han" then has_han = true end
        if entry.type == "lo" then has_lo = true end
      end
    end
  end

  return has_han, has_lo
end

-- ============================================================
-- Tone number → Unicode diacritics (shared utility)
-- ============================================================
local TONE_MARKS = {
  ["2"] = "\xCC\x81",  -- U+0301 combining acute accent
  ["3"] = "\xCC\x80",  -- U+0300 combining grave accent
  ["5"] = "\xCC\x82",  -- U+0302 combining circumflex
  ["7"] = "\xCC\x84",  -- U+0304 combining macron
  ["8"] = "\xCC\x8D",  -- U+030D combining vertical line above
  ["9"] = "\xCC\x86",  -- U+0306 combining breve
}

-- Add tone diacritic to a single syllable (e.g. "gua2" → "guá")
-- 教育部台羅拼音方案 tone mark placement rules:
--   Priority: a > oo > e > o
--   When i,u both present: mark the SECOND one (main vowel, not glide)
--     iu → iú (mark u), ui → uí (mark i)
--   Special: ere → mark second e (erê)
--   Syllabic nasals: m, ng, nng (mark second n for nng: nn̄g)
local function add_tone_to_syllable(syl)
  local tone = syl:sub(-1)
  if not tone:match("[1-9]") then return syl end  -- no tone number
  local base = syl:sub(1, -2)
  local mark = TONE_MARKS[tone]
  if not mark then return base end  -- tone 1, 4: strip number, no diacritic
  local pos = base:find("oo")
  if not pos then pos = base:find("a") end
  if not pos then
    local ere = base:find("ere")
    if ere then
      pos = ere + 2  -- mark the second e in ere
    else
      pos = base:find("e")
    end
  end
  if not pos then pos = base:find("o") end
  if not pos then
    local pi = base:find("i")
    local pu = base:find("u")
    if pi and pu then
      pos = math.max(pi, pu)  -- mark the second vowel (main vowel)
    else
      pos = pi or pu
    end
  end
  if not pos then
    -- Syllabic nasals: for nng, mark the second n (nn̄g not n̄ng)
    if base:sub(1, 2) == "nn" then
      pos = 2
    else
      pos = base:find("[mn]")
    end
  end
  if pos then return base:sub(1, pos) .. mark .. base:sub(pos + 1) end
  return base
end

-- Convert space-separated syllables with tone numbers to
-- hyphen-joined syllables with Unicode diacritics
-- e.g. "gua2 ai3 li2" → "guá-ài-lí"
-- Light-tone marker "--" in input is preserved in output:
-- e.g. "tng2--lai5" → "tǹg--lâi"
function M.format_romanization(roman)
  if not roman or roman == "" then return roman end
  -- Split on "--" first to preserve light-tone boundaries
  local groups = {}
  local start = 1
  while true do
    local ds = roman:find("--", start, true)
    if ds then
      table.insert(groups, roman:sub(start, ds - 1))
      start = ds + 2
    else
      table.insert(groups, roman:sub(start))
      break
    end
  end
  -- Process each group: single-space-separated syllables joined with "-"
  local formatted = {}
  for _, group in ipairs(groups) do
    local parts = {}
    for syl in group:gmatch("[^%s]+") do
      table.insert(parts, add_tone_to_syllable(syl))
    end
    table.insert(formatted, table.concat(parts, "-"))
  end
  return table.concat(formatted, "--")
end

-- Fix POJ diphthong tone mark position after format_romanization
-- POJ rules differ from TL for certain diphthongs:
--   oa at end of syllable: mark o (goā → gōa), but oan keeps mark on a (koán)
--   oe at end of syllable: mark o (hoé → hōe)
--   ui: mark first vowel u (uī → ūi)
--   iu: no change (both TL and POJ mark u: iū → iū)
function M.poj_fix_diacritics(text)
  if not text then return text end
  -- oa + diacritic at end of syllable: before -, ⁿ (U+207F), or end of string
  -- NOT when followed by consonant coda (n, t, k, h)
  -- ⁿ is nasalization (not a coda), so oa+ⁿ is still open syllable
  text = text:gsub("oa(\204[\128-\191])%-", "o%1a-")
  text = text:gsub("oa(\204[\128-\191])(\226\129\191)", "o%1a%2")  -- before ⁿ
  text = text:gsub("oa(\204[\128-\191])$", "o%1a")
  -- oe + diacritic at end of syllable
  text = text:gsub("oe(\204[\128-\191])%-", "o%1e-")
  text = text:gsub("oe(\204[\128-\191])(\226\129\191)", "o%1e%2")  -- before ⁿ
  text = text:gsub("oe(\204[\128-\191])$", "o%1e")
  -- ui: move diacritic from i (second) to u (first)
  text = text:gsub("ui(\204[\128-\191])", "u%1i")
  -- iu: both TL and POJ mark u (second vowel), no conversion needed
  return text
end

-- ============================================================
-- Mandarin→Taiwanese mapping (hoabun_map.txt)
-- ============================================================
local _hoabun_map = nil

local function find_hoabun_map_path()
  local dirs = {}
  if rime_api then
    local user_dir = rime_api.get_user_data_dir()
    if user_dir then table.insert(dirs, user_dir) end
    local shared_dir = rime_api.get_shared_data_dir()
    if shared_dir then table.insert(dirs, shared_dir) end
  end
  for _, dir in ipairs(dirs) do
    local path = dir .. "/hoabun_map.txt"
    local f = io.open(path, "r")
    if f then
      f:close()
      return path
    end
  end
  return nil
end

-- Load and cache hoabun_map (華→台 mapping)
function M.get_hoabun_map()
  if _hoabun_map then
    return _hoabun_map
  end

  local path = find_hoabun_map_path()
  if not path then
    _hoabun_map = {}
    return _hoabun_map
  end

  local f = io.open(path, "r")
  if not f then
    _hoabun_map = {}
    return _hoabun_map
  end

  _hoabun_map = {}
  for line in f:lines() do
    local mandarin, kip = line:match("^(.+)\t(.+)$")
    if mandarin and kip then
      _hoabun_map[mandarin] = kip
    end
  end
  f:close()
  return _hoabun_map
end

-- Look up a Mandarin word → Taiwanese TL code
function M.hoabun_to_tl(word)
  local map = M.get_hoabun_map()
  return map[word]
end

-- ============================================================
-- Shared commit utilities
-- ============================================================

-- TL → POJ conversion
function M.tl_to_poj(tl_text)
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
  -- nn → ⁿ only when NOT followed by g (nng is syllabic nasal, not nasalization)
  result = result:gsub("nn([^g])", "\226\129\191%1")             -- nn → ⁿ (U+207F) before non-g
  result = result:gsub("nn$", "\226\129\191")                    -- nn → ⁿ at end of string
  result = result:gsub("o(\204[\128-\191])o", "o%1\205\152")    -- ó+o → ó͘ (with tone diacritic)
  result = result:gsub("oo", "o\205\152")                       -- oo → o͘ (U+0358)
  result = result:gsub("ua", "oa")
  result = result:gsub("ue", "oe")
  return result
end

-- Capitalize the first letter of romanization text
function M.capitalize_first(text)
  if not text or text == "" then return text end
  local first = text:sub(1, 1)
  if first:match("[a-z]") then
    return first:upper() .. text:sub(2)
  end
  return text
end

-- Count UTF-8 characters (not bytes)
function M.utf8_len(s)
  if not s or s == "" then return 0 end
  local count = 0
  for _ in s:gmatch("[%z\1-\127\194-\244][\128-\191]*") do
    count = count + 1
  end
  return count
end

-- Extract romanization from candidate's comment
-- Handles both simple [roman] and lookup-modified [TL:roman POJ:roman] formats
-- context: Rime context object (for reading poj_mode option)
function M.extract_roman(cand, context)
  if not cand then return nil end
  local comment = cand.comment or ""
  local content = comment:match("%[(.-)%]")
  if not content or content == "" then return nil end

  local poj = context and context:get_option("poj_mode")

  -- Handle dual annotation format from phah_taibun_lookup:
  -- [TL:gua2 ai li POJ:goa2 ai li]
  local tl_part = content:match("TL:(.-)%s+POJ:")
  local poj_part = content:match("POJ:(.+)")
  if tl_part and poj_part then
    local raw = poj and poj_part or tl_part
    return M.format_romanization(raw)
  end

  -- Simple format: [gua2 ai li]
  local raw = content
  if poj then
    raw = M.tl_to_poj(raw)
  end
  local result = M.format_romanization(raw)
  if poj then
    result = M.poj_fix_diacritics(result)
  end
  return result
end

-- Commit candidate as romanization with auto-capitalization
-- engine: Rime engine object
-- context: Rime context object
-- cand: candidate object
-- state: shared state table (from get_shared_state())
-- Returns: committed text (for homophone tracking)
function M.commit_with_roman(engine, context, cand, state)
  local roman = M.extract_roman(cand, context)
  if not roman then return nil end
  if state.capitalize_next then
    roman = M.capitalize_first(roman)
  end
  engine:commit_text(roman)
  state.capitalize_next = false
  return roman
end

-- ============================================================
-- Shared state for cross-processor communication
-- ============================================================
local _shared_state = {
  selection_mode = false,
  capitalize_next = true,
  last_text = nil,
}

function M.get_shared_state()
  return _shared_state
end

return M
