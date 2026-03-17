-- phah_taibun_input.lua
-- Pre-processor for:
--   1. Uppercase letter interception (Shift+letter → lowercase + capitalize flag)
--   2. Tab selection mode (freeze speller, enable asdf/number candidate selection)
--
-- Must be first in the processor chain (before ascii_composer)

local M = {}

-- Load shared data module
local data_mod = nil
local ok, mod = pcall(require, "phah_taibun_data")
if ok and mod then
  data_mod = mod
end

-- Selection key set: asdfghjkl; (mapped to candidate indices 0-9)
local SELECTION_KEYS = {}
for i, byte in ipairs({
  0x61, 0x73, 0x64, 0x66, 0x67, 0x68, 0x6a, 0x6b, 0x6c, 0x3b, -- a s d f g h j k l ;
}) do
  SELECTION_KEYS[byte] = i - 1  -- 0-based index
end

-- Number keys 0-9 (mapped to candidate indices 0-9)
-- Standard IME numbering: 1→0, 2→1, ..., 9→8, 0→9
local NUMBER_KEYS = {}
for i = 0, 9 do
  NUMBER_KEYS[0x30 + i] = (i == 0) and 9 or (i - 1)
end

function M.init(env)
  local config = env.engine.schema.config
  env.page_size = config:get_int("menu/page_size") or 10
  env.state = data_mod and data_mod.get_shared_state() or {
    selection_mode = false,
    capitalize_next = true,
    last_text = nil,
  }
end

function M.func(key, env)
  local context = env.engine.context
  local state = env.state

  -- Reset selection mode if composition was cleared externally
  if state.selection_mode and not context:is_composing() then
    state.selection_mode = false
  end

  -- Ignore key releases
  if key:release() then return 2 end

  -- ============================================================
  -- UPPERCASE INTERCEPTION: Shift+letter → lowercase + capitalize
  -- Only when in 台文 mode (not ascii_mode) and not in selection mode
  -- ============================================================
  if not state.selection_mode
     and not context:get_option("ascii_mode")
     and key:repr():match("^[A-Z]$")
  then
    -- Use key:repr() to get the letter reliably (keycode may be lowercase on some platforms)
    local lower = key:repr():lower()
    context:push_input(lower)
    -- Set capitalize flag for sentence-start capitalization
    if not context:is_composing() or context.input == lower then
      state.capitalize_next = true
    end
    return 1  -- kAccepted: prevent ascii_composer from seeing Shift+letter
  end

  return 2  -- kNoop
end

return M
