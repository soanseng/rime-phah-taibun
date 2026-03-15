-- phah_taibun_wildcard.lua
-- 萬用查字 ? — 模糊拼音匹配
-- 移植自 rime-liur (ryanwuson/rime-liur) 萬用字元模組
--
-- Usage: type ?iah to match tsiah, siah, liah, etc.
-- The ? replaces an unknown initial consonant.
-- Each possible expansion is shown as a candidate for further lookup.

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

  -- Generate all possible expansions with each initial
  for _, initial in ipairs(INITIALS) do
    local expanded = initial .. remainder
    local label = expanded
    if initial == "" then
      label = "零聲母 " .. remainder
    end
    local cand = Candidate("wildcard", seg.start, seg._end,
      expanded, "拍入 " .. expanded .. " 來查字")
    yield(cand)
  end
end

return M
