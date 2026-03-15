-- phah_taibun_wildcard.lua
-- 萬用查字 ? — 模糊拼音匹配
-- 移植自 rime-liur (ryanwuson/rime-liur) 萬用字元模組
--
-- Usage: type ?iah to match tsiah, siah, liah, etc.
-- The ? replaces an unknown initial consonant.
-- Directly looks up the dictionary and yields Han character candidates.

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

  -- Look up dictionary for each possible initial + remainder
  for _, initial in ipairs(INITIALS) do
    local expanded = initial .. remainder
    if env.mem:dict_lookup(expanded, true, 50) then
      for entry in env.mem:iter_dict() do
        local code = entry.custom_code or expanded
        -- Use first syllable only (skip multi-syllable phrases)
        if not code:find(" ") then
          local cand = Candidate("wildcard", seg.start, seg._end,
            entry.text, " [" .. code .. "]")
          yield(cand)
        end
      end
    end
  end
end

return M
