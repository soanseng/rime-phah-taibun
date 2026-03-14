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

return M
