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
-- Placement: oo > a > e > last vowel (i,o,u) > syllabic nasal (m,n)
local function add_tone_to_syllable(syl)
  local tone = syl:sub(-1)
  local mark = TONE_MARKS[tone]
  if not mark then return syl end
  local base = syl:sub(1, -2)
  local pos = base:find("oo")
  if not pos then pos = base:find("a") end
  if not pos then pos = base:find("e") end
  if not pos then
    for i = #base, 1, -1 do
      local c = base:sub(i, i)
      if c == "i" or c == "o" or c == "u" then pos = i; break end
    end
  end
  if not pos then pos = base:find("[mn]") end
  if pos then return base:sub(1, pos) .. mark .. base:sub(pos + 1) end
  return base
end

-- Convert space-separated syllables with tone numbers to
-- hyphen-joined syllables with Unicode diacritics
-- e.g. "gua2 ai3 li2" → "guá-ài-lí"
function M.format_romanization(roman)
  if not roman or roman == "" then return roman end
  local parts = {}
  for syl in roman:gmatch("[^%s]+") do
    table.insert(parts, add_tone_to_syllable(syl))
  end
  return table.concat(parts, "-")
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

return M
