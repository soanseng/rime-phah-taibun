-- phah_taibun_wildcard.lua
-- 萬用查字 ? — 二段式模糊拼音匹配
-- 移植自 rime-liur (ryanwuson/rime-liur) 萬用字元模組
--
-- Two-step flow:
--   Step 1: ?iah → shows available syllable patterns (tsiah, siah, liah...)
--   Step 2: select a pattern → feeds romanization into main translator
--           → shows all Han characters for that pronunciation
--
-- The feed-back from Step 1→2 is handled by phah_taibun_commit processor.

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
  env.mem = Memory(env.engine, env.engine.schema)
end

function M.func(input, seg, env)
  -- Only process inputs starting with ?
  if not input:match("^%?") then
    return
  end

  local remainder = input:sub(2)  -- Everything after ?

  if remainder == "" then
    -- Just "?" typed: show usage hint
    local cand = Candidate("wildcard", seg.start, seg._end,
      "?", "? + 韻母 = 萬用查字（例：?iah → tsiah, siah, liah...）")
    yield(cand)
    return
  end

  -- Step 1: Show available romanization patterns for each initial
  for _, initial in ipairs(INITIALS) do
    local expanded = initial .. remainder
    if env.mem:dict_lookup(expanded, true, 100) then
      -- Count unique characters for this pattern
      local count = 0
      local seen = {}
      for entry in env.mem:iter_dict() do
        local code = entry.custom_code or expanded
        -- Only count single-syllable entries (no spaces in code)
        if not code:find(" ") and not seen[entry.text] then
          seen[entry.text] = true
          count = count + 1
        end
      end
      if count > 0 then
        local label = count .. " 個字"
        if initial == "" then
          label = label .. "（零聲母）"
        end
        local cand = Candidate("wildcard", seg.start, seg._end,
          expanded, label)
        yield(cand)
      end
    end
  end
end

return M
