-- phah_taibun_wildcard.lua
-- 萬用查字 ? — 模糊拼音匹配
-- 移植自 rime-liur (ryanwuson/rime-liur) 萬用字元模組
--
-- Usage: type ?iah to match tsiah, siah, liah, etc.
-- The ? replaces an unknown initial consonant.

local M = {}

-- All possible TL initials (聲母)
local INITIALS = {
  "", "p", "ph", "b", "m",
  "t", "th", "n", "l",
  "k", "kh", "g", "ng",
  "ts", "tsh", "s", "j", "h",
}

function M.init(env)
  env.name_space = env.name_space or ""
end

function M.func(input, seg, env)
  -- Only process inputs containing ?
  if not input:match("%?") then
    return
  end

  -- Simple case: single syllable with ? at start
  if input:match("^%?") then
    local remainder = input:sub(2)  -- Everything after ?

    -- Try each initial + remainder
    local found = false
    for _, initial in ipairs(INITIALS) do
      local expanded = initial .. remainder

      -- Use Rime's reverse lookup or script translator to find matches
      -- Note: Translation() may not be available in all Rime versions
      local ok, mem = pcall(function()
        return Translation(env.engine, env.name_space, expanded, seg)
      end)

      if ok and mem then
        for cand_item in mem:iter() do
          local new_comment = cand_item.comment .. " (" .. expanded .. ")"
          local new_cand = Candidate(
            "wildcard", seg.start, seg._end,
            cand_item.text, new_comment
          )
          new_cand.quality = cand_item.quality
          yield(new_cand)
          found = true
        end
      end
    end

    -- If no matches found (or Translation not available), show hint
    if not found then
      local hint_parts = {}
      for _, initial in ipairs(INITIALS) do
        if initial ~= "" then
          table.insert(hint_parts, initial .. remainder)
        end
      end
      local hint = table.concat(hint_parts, ", ")
      local cand = Candidate("wildcard", seg.start, seg._end,
        input, "可能的拼音: " .. hint)
      yield(cand)
    end
  else
    -- Fallback: show hint for complex patterns
    local cand = Candidate("wildcard", seg.start, seg._end,
      input, "? = 萬用字元，代替不確定的聲母")
    yield(cand)
  end
end

return M
