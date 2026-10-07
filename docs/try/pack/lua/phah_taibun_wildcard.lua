-- phah_taibun_wildcard.lua
-- 萬用查字 ? — 二段式模糊拼音匹配
-- 移植自 rime-liur (ryanwuson/rime-liur) 萬用字元模組
--
-- Two-step flow:
--   Step 1: ?iah  → shows available syllable patterns (tsiah, siah, liah...)
--           si?   → shows available syllable patterns (sia, siah, siam, sian...)
--           s?ah  → shows available syllable patterns (sah, siah, suah...)
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

-- All possible TL finals (韻母), including syllabic nasals
local FINALS = {
  -- Single vowels
  "a", "e", "i", "o", "oo", "u",
  -- Vowel + h (checked tone)
  "ah", "eh", "ih", "oh", "ooh", "uh",
  -- Vowel + stop codas (-k, -p, -t)
  "ak", "ek", "ik", "ok",
  "ap", "ip", "op",
  "at", "it", "ut",
  -- Vowel + nasal codas (-m, -n, -ng)
  "am", "im", "om",
  "an", "in", "un",
  "ang", "eng", "ing", "ong",
  -- a-diphthongs
  "ai", "aih", "au", "auh",
  -- i-diphthongs and triphthongs
  "ia", "iah", "iak", "iam", "ian", "iang", "iap", "iat",
  "iau", "iauh",
  "io", "ioh", "iok", "iong",
  "iu", "iuh",
  -- u-diphthongs and triphthongs
  "ua", "uah", "uai", "uaih", "uak", "uan", "uang", "uat",
  "ue", "ueh",
  "ui", "uih",
  -- Nasalized (-nn)
  "ann", "enn", "inn", "onn",
  "ainn", "aunn",
  "iann", "ionn", "iunn",
  "iaunn",
  "uann", "uainn", "uinn",
  -- Nasalized + h (checked nasalized)
  "ainnh", "annh", "aunnh", "ennh", "innh", "onnh", "unnh",
  "iannh", "iaunnh", "iunnh",
  "uainnh", "uinnh",
  -- Special / dialectal
  "er", "erh", "ere", "ir", "irh", "irn",
  "ioo",
  -- Syllabic nasals
  "m", "mh", "ng", "ngh", "nng",
}

-- Count unique single-syllable characters for a given romanization code.
-- Uses predictive lookup so all tone variants are included.
local function count_chars(mem, code)
  if not mem:dict_lookup(code, true, 100) then
    return 0
  end
  local count = 0
  local seen = {}
  for entry in mem:iter_dict() do
    local c = entry.custom_code or code
    if not c:find(" ") and not seen[entry.text] then
      seen[entry.text] = true
      count = count + 1
    end
  end
  return count
end

function M.init(env)
  env.name_space = env.name_space or ""
  env.mem = Memory(env.engine, env.engine.schema)
end

function M.func(input, seg, env)
  -- Only process inputs containing ?
  if not input:find("?", 1, true) then
    return
  end

  -- Find the ? position, split into before/after
  local qpos = input:find("?", 1, true)
  local before = input:sub(1, qpos - 1)  -- letters before ?
  local after  = input:sub(qpos + 1)     -- letters/digits after ?

  -- Just "?" alone: show usage hint
  if before == "" and after == "" then
    local cand = Candidate("wildcard", seg.start, seg._end,
      "?", "? + 韻母/聲母 = 萬用查字（例：?iah, si?, s?ah）")
    yield(cand)
    return
  end

  -- Separate trailing tone digits from alpha part of 'after'
  local after_alpha = after:match("^(%a*)") or ""
  local after_tone  = after:sub(#after_alpha + 1)  -- e.g., "8" from "ah8"

  if before == "" then
    -- ========================================
    -- ? at start: ?iah → try all initials + after
    -- (original behavior)
    -- ========================================
    for _, initial in ipairs(INITIALS) do
      local expanded = initial .. after
      local count = count_chars(env.mem, expanded)
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
  else
    -- ========================================
    -- ? at middle or end: si?, s?ah, tsh?ing
    -- Try all INITIAL+FINAL combinations matching the pattern
    -- ========================================
    local seen_code = {}
    for _, initial in ipairs(INITIALS) do
      -- Check if 'before' starts with this initial
      if #initial <= #before and before:sub(1, #initial) == initial then
        local partial = before:sub(#initial + 1)  -- remaining part of 'before' after initial
        for _, final in ipairs(FINALS) do
          -- Final must start with partial (the known part after the initial)
          if #partial <= #final and final:sub(1, #partial) == partial then
            -- Final must end with after_alpha (the known part after ?)
            if after_alpha == "" or
               (#after_alpha <= #final and final:sub(-#after_alpha) == after_alpha) then
              local code = initial .. final .. after_tone
              if not seen_code[code] then
                seen_code[code] = true
                local count = count_chars(env.mem, code)
                if count > 0 then
                  local label = count .. " 個字"
                  if initial == "" then
                    label = label .. "（零聲母）"
                  end
                  local cand = Candidate("wildcard", seg.start, seg._end,
                    code, label)
                  yield(cand)
                end
              end
            end
          end
        end
      end
    end
  end
end

return M
