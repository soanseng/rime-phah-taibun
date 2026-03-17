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
--   Syllabic nasals: m, ng
local function add_tone_to_syllable(syl)
  local tone = syl:sub(-1)
  local mark = TONE_MARKS[tone]
  if not mark then return syl end
  local base = syl:sub(1, -2)
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
  if not pos then pos = base:find("[mn]") end
  if pos then return base:sub(1, pos) .. mark .. base:sub(pos + 1) end
  return base
end

-- Convert space-separated syllables with tone numbers to
-- hyphen-joined syllables with Unicode diacritics
-- e.g. "gua2 ai3 li2" → "guá-ài-lí"
-- Double space (light-tone marker) becomes "--":
-- e.g. "tng2  lai5" → "tǹg--lâi"
function M.format_romanization(roman)
  if not roman or roman == "" then return roman end
  -- Split on double-space first to preserve light-tone "--" boundaries
  local groups = {}
  local start = 1
  while true do
    local ds = roman:find("  ", start, true)
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
-- In POJ, 'oa' and 'oe' (from TL 'ua'/'ue') mark tone on 'o':
--   goá → góa, toà → tòa, hoê → hôe
-- Moves combining diacritical mark from after a/e to after o
function M.poj_fix_diacritics(text)
  if not text then return text end
  text = text:gsub("oa(\204[\128-\191])", "o%1a")
  text = text:gsub("oe(\204[\128-\191])", "o%1e")
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
  result = result:gsub("nn", "\226\129\191")                    -- nn → ⁿ (U+207F)
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
