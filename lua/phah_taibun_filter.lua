-- phah_taibun_filter.lua
-- 核心過濾器：候選拼音註解 + 輸出模式切換
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

function M.init(env)
  env.name_space = env.name_space or ""
end

function M.func(input, env)
  local mode = get_output_mode(env)

  for cand in input:iter() do
    local text = cand.text or ""
    local comment = cand.comment or ""

    -- Extract the raw romanization from Rime's auto-comment
    -- Rime formats it as " [romanization]" via comment_format xform
    local raw_roman = comment:match("%[(.-)%]") or comment

    if mode == 2 or mode == 3 then
      -- 全羅模式：replace text with full romanization
      local roman = raw_roman
      if mode == 3 then
        roman = tl_to_poj(roman)
      end
      if roman and roman ~= "" then
        local new_cand = Candidate(cand.type, cand.start, cand._end, roman, comment)
        new_cand.quality = cand.quality
        new_cand.preedit = cand.preedit
        yield(new_cand)
      else
        yield(cand)
      end
    else
      -- 漢羅模式：keep text, enhance comment
      if mode == 1 and raw_roman then
        -- POJ mode: convert TL annotation to POJ
        local poj_roman = tl_to_poj(raw_roman)
        local new_comment = " [" .. poj_roman .. "]"
        local new_cand = Candidate(cand.type, cand.start, cand._end, text, new_comment)
        new_cand.quality = cand.quality
        new_cand.preedit = cand.preedit
        yield(new_cand)
      else
        -- TL mode (default): pass through with Rime's auto-comment
        yield(cand)
      end
    end
  end
end

return M
