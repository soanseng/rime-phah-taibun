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

  -- ============================================================
  -- TAB: enter selection mode (when menu visible)
  -- When no menu: falls through to key_binder YAML binding
  -- which sends Shift+Right for next syllable
  -- ============================================================
  if key:repr() == "Tab" then
    if context:has_menu() then
      state.selection_mode = true
      return 1  -- kAccepted
    end
    return 2  -- kNoop: let key_binder handle (next syllable or pass through)
  end

  -- ============================================================
  -- SELECTION MODE key handling
  -- ============================================================
  if not state.selection_mode then
    return 2  -- kNoop: not in selection mode, pass through
  end

  local kc = key.keycode

  -- Helper: commit candidate and track homophone
  local function commit_candidate(cand)
    local full_roman = context:get_option("full_romanization")
    if full_roman and data_mod then
      data_mod.commit_with_roman(env.engine, context, cand, state)
      context:clear()
    else
      context:confirm_current_selection()
    end
    -- Track for homophone
    if data_mod and data_mod.utf8_len(cand.text) == 1 then
      state.last_text = cand.text
    else
      state.last_text = nil
    end
    state.selection_mode = false
  end

  -- Space: confirm highlighted candidate
  if kc == 0x20 then
    local cand = context:get_selected_candidate()
    if cand then
      commit_candidate(cand)
    end
    state.selection_mode = false
    return 1  -- kAccepted
  end

  -- Selection keys (asdf... or 0-9): select specific candidate
  local sel_idx = SELECTION_KEYS[kc] or NUMBER_KEYS[kc]
  if sel_idx then
    local comp = context.composition
    if not comp:empty() then
      local seg = comp:back()
      local page = math.floor(seg.selected_index / env.page_size)
      local abs_idx = page * env.page_size + sel_idx
      seg.selected_index = abs_idx
      local cand = context:get_selected_candidate()
      if cand then
        commit_candidate(cand)
      end
    end
    state.selection_mode = false
    return 1  -- kAccepted
  end

  -- Escape: exit selection mode, keep composition
  if key:repr() == "Escape" then
    state.selection_mode = false
    return 1  -- kAccepted
  end

  -- Enter: exit selection mode, pass to fluency_editor for commit_raw_input
  if key:repr() == "Return" then
    state.selection_mode = false
    return 2  -- kNoop
  end

  -- Brackets [ ] and backslash \: exit selection mode, pass to downstream
  if key:repr() == "bracketleft" or key:repr() == "bracketright"
     or key:repr() == "backslash" then
    state.selection_mode = false
    return 2  -- kNoop
  end

  -- Navigation keys: pass through (don't exit selection mode)
  if key:repr() == "Up" or key:repr() == "Down"
     or key:repr() == "Page_Up" or key:repr() == "Page_Down" then
    return 2  -- kNoop: let selector/navigator handle
  end

  -- Any other letter: exit selection mode, let speller handle
  if kc >= 0x61 and kc <= 0x7a then  -- a-z
    state.selection_mode = false
    return 2  -- kNoop
  end

  -- All other keys: exit selection mode, pass through
  state.selection_mode = false
  return 2  -- kNoop
end

return M
