-- phah_taibun_lighttone.lua
-- 輕聲候選產生器：動態為候選詞加上輕聲 (--) 變體
-- Dynamically generates light-tone candidate variants using lighttone_rules.json
--
-- This filter runs BEFORE phah_taibun_filter, so candidate comments still
-- contain raw romanization with numeric tones in format [kip1 input2].

local M = {}

-- Reference to data module (for format_romanization)
local data_mod = nil

-- Global cache for parsed rules
local _rules = nil           -- keyed by diacritical suffix (e.g., "lâi")
local _rules_list = nil      -- keyed by diacritical suffix → list of {hanzi, rule}
local _toneless_rules = nil  -- keyed by toneless suffix for matching

-- ============================================================
-- JSON parsing (Rime Lua has no json module)
-- ============================================================

local function parse_lighttone_json(content)
  local rules = {}  -- suffix → list of {hanzi, rule}
  -- Match each {"tl": "...", "hanzi": "...", "rule": "..."}
  for tl, hanzi, rule in content:gmatch('"tl"%s*:%s*"(.-)".-"hanzi"%s*:%s*"(.-)".-"rule"%s*:%s*"(.-)"') do
    if rule ~= "不處理" then
      -- Strip leading "--" from tl
      local suffix = tl:match("^%-%-(.+)") or tl
      if not rules[suffix] then
        rules[suffix] = {}
      end
      -- Avoid duplicate hanzi for same suffix
      local dominated = false
      for _, entry in ipairs(rules[suffix]) do
        if entry.hanzi == hanzi then
          dominated = true
          break
        end
      end
      if not dominated then
        table.insert(rules[suffix], {hanzi = hanzi, rule = rule})
      end
    end
  end
  return rules
end

-- ============================================================
-- File finding (same pattern as phah_taibun_data.lua)
-- ============================================================

local function find_lighttone_path()
  local dirs = {}
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
    local path = dir .. "/lighttone_rules.json"
    local f = io.open(path, "r")
    if f then
      f:close()
      return path
    end
  end
  return nil
end

-- ============================================================
-- Tone/diacritics utilities
-- ============================================================

-- Strip combining diacritical marks (U+0300-U+036F range)
-- These are 2-byte sequences: \xCC\x80-\xCC\xBF and \xCD\x80-\xCD\x9F
local function strip_diacritics(text)
  if not text then return text end
  -- Remove combining marks: U+0300-U+036F
  -- \xCC[\x80-\xBF] covers U+0300-U+033F
  -- \xCD[\x80-\x9F] covers U+0340-U+035F
  -- \xCD[\xA0-\xAF] covers U+0360-U+036F (less common, but include)
  local result = text:gsub("\204[\128-\191]", "")
  result = result:gsub("\205[\128-\159]", "")
  -- Also handle the dotless-i (ı, U+0131) → i
  result = result:gsub("\196\177", "i")
  return result
end

-- Strip tone numbers from the end of syllables
-- e.g., "khi3" → "khi", "lai5" → "lai"
local function strip_tone_numbers(text)
  if not text then return text end
  -- Remove trailing tone number from each syllable
  local result = text:gsub("([a-z])([1-9])$", "%1")
  result = result:gsub("([a-z])([1-9])([%s%-])", "%1%3")
  return result
end

-- ============================================================
-- Text manipulation utilities
-- ============================================================

-- Split a string into UTF-8 characters
local function utf8_chars(s)
  local chars = {}
  if not s or s == "" then return chars end
  for char in s:gmatch("[%z\1-\127\194-\244][\128-\191]*") do
    table.insert(chars, char)
  end
  return chars
end

-- Split space-separated syllables
local function split_syllables(raw_roman)
  local syllables = {}
  for syl in raw_roman:gmatch("[^%s]+") do
    table.insert(syllables, syl)
  end
  return syllables
end

-- Insert "--" into hanzi text at the given position
-- prefix_syllable_count = number of syllables before "--"
local function insert_lighttone_marker_text(text, prefix_syllable_count)
  local chars = utf8_chars(text)
  if prefix_syllable_count <= 0 or prefix_syllable_count >= #chars then
    return nil
  end
  local prefix = table.concat(chars, "", 1, prefix_syllable_count)
  local suffix = table.concat(chars, "", prefix_syllable_count + 1)
  return prefix .. "--" .. suffix
end

-- Insert "--" into romanization comment
-- syllables is an array, match_count is number of tail syllables that matched
local function insert_lighttone_marker_roman(syllables, match_count)
  if match_count <= 0 or match_count >= #syllables then
    return nil
  end
  local prefix_count = #syllables - match_count
  local prefix = table.concat(syllables, " ", 1, prefix_count)
  local suffix = table.concat(syllables, " ", prefix_count + 1)
  return prefix .. "--" .. suffix
end

-- ============================================================
-- Rule loading and indexing
-- ============================================================

local function load_rules()
  if _rules_list then return end

  local path = find_lighttone_path()
  if not path then
    _rules_list = {}
    _toneless_rules = {}
    return
  end

  local f = io.open(path, "r")
  if not f then
    _rules_list = {}
    _toneless_rules = {}
    return
  end

  local content = f:read("*all")
  f:close()

  _rules_list = parse_lighttone_json(content)

  -- Build toneless lookup for matching against numeric-tone input
  _toneless_rules = {}
  for suffix, entries in pairs(_rules_list) do
    local toneless = strip_diacritics(suffix):lower()
    if not _toneless_rules[toneless] then
      _toneless_rules[toneless] = {}
    end
    for _, entry in ipairs(entries) do
      table.insert(_toneless_rules[toneless], entry)
    end
  end
end

-- ============================================================
-- Matching logic
-- ============================================================

-- Try to match the tail N syllables (1 to max_tail) against rules
-- Returns: match_count, entries (list of {hanzi, rule}) or nil
local function find_tail_match(syllables, max_tail)
  if not _toneless_rules or not syllables or #syllables < 2 then
    return nil, nil
  end

  -- Try longest match first (3-syllable, then 2, then 1)
  local limit = math.min(max_tail, #syllables - 1)  -- must leave at least 1 prefix syllable
  for n = limit, 1, -1 do
    local tail_parts = {}
    for i = #syllables - n + 1, #syllables do
      -- Strip tone number for matching
      local syl = strip_tone_numbers(syllables[i]):lower()
      table.insert(tail_parts, syl)
    end
    local tail_key = table.concat(tail_parts, "-")
    local entries = _toneless_rules[tail_key]
    if entries and #entries > 0 then
      return n, entries
    end
  end

  return nil, nil
end

-- ============================================================
-- Filter interface
-- ============================================================

function M.init(env)
  env.name_space = env.name_space or ""

  -- Load data module for format_romanization
  if not data_mod then
    local ok, mod = pcall(require, "phah_taibun_data")
    if ok and mod then
      data_mod = mod
    end
  end

  -- Load lighttone rules
  load_rules()
end

function M.func(input, env)
  for cand in input:iter() do
    local comment = cand.comment or ""

    -- Extract raw romanization from comment: " [khi3 lai5]"
    local raw_roman = comment:match("%[(.-)%]")

    -- If no romanization, pass through
    if not raw_roman or raw_roman == "" then
      yield(cand)
      goto continue
    end

    -- Split into syllables
    local syllables = split_syllables(raw_roman)

    -- Only process multi-syllable candidates
    if #syllables < 2 then
      yield(cand)
      goto continue
    end

    -- Always yield the original candidate first
    yield(cand)

    -- Try to match tail syllables against lighttone rules (up to 3)
    local match_count, entries = find_tail_match(syllables, 3)

    if match_count and entries then
      local text = cand.text or ""

      -- Insert "--" into the romanization
      local new_roman = insert_lighttone_marker_roman(syllables, match_count)

      if new_roman then
        -- Insert "--" into the hanzi text
        local prefix_count = #syllables - match_count
        local new_text = insert_lighttone_marker_text(text, prefix_count)

        if new_text then
          -- Build new comment with "--" marker in romanization
          local new_comment = " [" .. new_roman .. "]"

          -- Generate one candidate per hanzi variant from the rules
          -- (most rules have just one entry)
          local yielded_texts = {}
          for _, entry in ipairs(entries) do
            -- Build hanzi-specific text: prefix hanzi + "--" + rule hanzi
            local chars = utf8_chars(text)
            if prefix_count <= #chars and prefix_count > 0 then
              local prefix_text = table.concat(chars, "", 1, prefix_count)
              local variant_text = prefix_text .. "--" .. entry.hanzi
              -- Avoid yielding duplicate texts
              if not yielded_texts[variant_text] then
                yielded_texts[variant_text] = true
                local new_cand = Candidate(cand.type, cand.start, cand._end,
                                           variant_text, new_comment)
                new_cand.quality = cand.quality - 0.3
                new_cand.preedit = cand.preedit
                yield(new_cand)
              end
            end
          end
        end
      end
    end

    ::continue::
  end
end

return M
