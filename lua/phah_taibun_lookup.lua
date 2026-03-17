-- phah_taibun_lookup.lua
-- 查台語讀音 Ctrl+'
-- 移植自 rime-liur (ryanwuson/rime-liur) 查碼模組
-- 選字後顯示 TL + POJ 讀音對照

local M = {}

-- Simple TL to POJ conversion (same logic as filter)
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
  -- POJ special characters
  result = result:gsub("nn", "\226\129\191")                    -- nn → ⁿ (U+207F)
  result = result:gsub("o(\204[\128-\191])o", "o%1\205\152")    -- ó+o → ó͘ (with tone diacritic)
  result = result:gsub("oo", "o\205\152")                       -- oo → o͘ (U+0358)
  result = result:gsub("ua", "oa")
  result = result:gsub("ue", "oe")
  return result
end

-- Load shared data module for poj_fix_diacritics
local data_mod = nil
local ok, mod = pcall(require, "phah_taibun_data")
if ok and mod then
  data_mod = mod
end

function M.init(env)
  env.name_space = env.name_space or ""
end

-- Enhance candidates with dual TL+POJ annotation
function M.func(input, env)
  for cand in input:iter() do
    local comment = cand.comment or ""

    -- Extract TL romanization from existing comment [...]
    local tl_roman = comment:match("%[(.-)%]")

    if tl_roman and tl_roman ~= "" then
      local poj_roman = tl_to_poj(tl_roman)

      -- POJ: fix diphthong tone mark position (oa→óa, oe→óe)
      if data_mod and data_mod.poj_fix_diacritics then
        poj_roman = data_mod.poj_fix_diacritics(poj_roman)
      end

      -- Only add dual annotation if POJ differs from TL
      if poj_roman ~= tl_roman then
        local new_comment = " [TL:" .. tl_roman .. " POJ:" .. poj_roman .. "]"
        local new_cand = Candidate(cand.type, cand.start, cand._end, cand.text, new_comment)
        new_cand.quality = cand.quality
        new_cand.preedit = cand.preedit
        yield(new_cand)
      else
        -- TL and POJ are the same, keep original comment
        yield(cand)
      end
    else
      yield(cand)
    end
  end
end

return M
