-- phah_taibun_telex.lua
-- Telex input layer for 拍台文(Telex).
-- Immediately normalizes Telex spellings to numeric TL keys so the shared
-- dictionary, user dict, filters, and romanization output stay unchanged.
--
--   v = tone 2 / 8 (checked -p/-t/-k/-h)
--   y = tone 3
--   d = tone 5
--   w = tone 7
--   q = tone 9
--   1/4 stay unmarked (x is not required)
--   z  → ts
--   zh → tsh
--   f  → syllable hyphen after a complete syllable

local M = {}

local TL_FINALS = {
  "iaunnh", "iaunn", "aunnh", "ainnh", "uainnh", "iannh", "iunnh", "uinnh",
  "iauh", "iau", "iam", "ian", "iang", "iap", "iat", "iak", "iah", "ia",
  "ioh", "iok", "iong", "ionn", "io", "iuh", "iu", "iunn",
  "uaih", "uai", "uainn", "uah", "uak", "uan", "uang", "uat", "ua",
  "ueh", "ue", "uih", "ui", "uinn",
  "ainn", "aih", "ai", "aunn", "auh", "au",
  "annh", "ann", "ennh", "enn", "innh", "inn", "onnh", "onn", "unnh", "unn",
  "ooh", "oo", "erh", "ere", "er", "irh", "irn", "ir", "ioo",
  "ang", "eng", "ing", "ong", "am", "im", "om", "an", "in", "un",
  "ak", "ek", "ik", "ok", "ap", "ip", "op", "at", "it", "ut",
  "ah", "eh", "ih", "oh", "uh",
  "ngh", "nng", "ng", "mh", "m",
  "a", "e", "i", "o", "u",
}

local function poj_variant(final)
  local variant = final
  variant = variant:gsub("ua", "oa")
  variant = variant:gsub("ue", "oe")
  variant = variant:gsub("oo", "ou")
  variant = variant:gsub("ing", "eng")
  variant = variant:gsub("ik", "ek")
  return variant
end

local FINALS = {}
do
  local seen = {}
  local function add(final)
    if final ~= "" and not seen[final] then
      seen[final] = true
      FINALS[#FINALS + 1] = final
    end
  end
  for _, final in ipairs(TL_FINALS) do
    add(final)
    add(poj_variant(final))
  end
  table.sort(FINALS, function(a, b)
    if #a == #b then
      return a < b
    end
    return #a > #b
  end)
end

-- Longest raw initial first. canon is the spelling written back.
local INITIALS = {
  { "tsh", "tsh" },
  { "chh", "chh" },
  { "zh", "tsh" },
  { "ts", "ts" },
  { "th", "th" },
  { "ph", "ph" },
  { "kh", "kh" },
  { "ng", "ng" },
  { "ch", "ch" },
  { "z", "ts" },
  { "p", "p" },
  { "b", "b" },
  { "m", "m" },
  { "t", "t" },
  { "n", "n" },
  { "l", "l" },
  { "k", "k" },
  { "g", "g" },
  { "h", "h" },
  { "s", "s" },
  { "j", "j" },
  { "", "" },
}

local TONE_LETTER = {
  v = true,
  y = true,
  d = true,
  w = true,
  q = true,
}

local function is_checked(final)
  return final:find("[ptkh]$") ~= nil
end

local function tone_digit(letter, checked)
  if letter == "v" then
    return checked and "8" or "2"
  elseif letter == "y" then
    return "3"
  elseif letter == "d" then
    return "5"
  elseif letter == "w" then
    return "7"
  elseif letter == "q" then
    return "9"
  end
end

local function match_syllable(s, i)
  local best_end, best_out
  for _, init in ipairs(INITIALS) do
    local raw, canon = init[1], init[2]
    local raw_len = #raw
    if raw_len == 0 or s:sub(i, i + raw_len - 1) == raw then
      local j = i + raw_len
      for _, final in ipairs(FINALS) do
        local fin_len = #final
        if s:sub(j, j + fin_len - 1) == final then
          local k = j + fin_len
          local base = canon .. final
          local out, endpos = base, k
          local mark = s:sub(k, k)
          if mark:match("[1-9]") then
            out = base .. mark
            endpos = k + 1
          elseif TONE_LETTER[mark] then
            out = base .. tone_digit(mark, is_checked(final))
            endpos = k + 1
          end
          if not best_end or endpos > best_end then
            best_end = endpos
            best_out = out
          end
          break
        end
      end
    end
  end
  return best_end, best_out
end

local SKIP_EXACT = {
  vvh = true,
  vvjit = true,
  vvsp = true,
}

function M.normalize(input)
  if not input or input == "" then
    return input
  end
  if SKIP_EXACT[input] or input:sub(1, 1) == "~" or input:sub(1, 1) == ";"
      or input:sub(1, 1) == "`" or input:find("?", 1, true) then
    return input
  end

  local i = 1
  local n = #input
  local out = {}
  local last_kind

  local function emit(piece, kind)
    if last_kind == "syl" and (kind == "syl" or kind == "raw") then
      out[#out + 1] = "-"
    end
    out[#out + 1] = piece
    last_kind = kind
  end

  while i <= n do
    local endpos, canon = match_syllable(input, i)
    if endpos then
      emit(canon, "syl")
      i = endpos
    elseif input:sub(i, i + 1) == "--" then
      emit("--", "delim")
      i = i + 2
    elseif input:sub(i, i) == "-" or input:sub(i, i) == " " or input:sub(i, i) == "'" then
      emit(input:sub(i, i), "delim")
      i = i + 1
    elseif input:sub(i, i) == "f" and last_kind == "syl" then
      emit("-", "delim")
      i = i + 1
    elseif input:sub(i, i + 1) == "zh" then
      emit("tsh", "raw")
      i = i + 2
    elseif input:sub(i, i) == "z" then
      emit("ts", "raw")
      i = i + 1
    else
      emit(input:sub(i, i), "raw")
      i = i + 1
    end
  end

  return table.concat(out)
end

local function should_skip(input)
  return not input or input == "" or SKIP_EXACT[input]
      or input:sub(1, 1) == "~" or input:sub(1, 1) == ";"
      or input:sub(1, 1) == "`" or input:find("?", 1, true)
end

function M.init(env)
  local context = env.engine.context
  env.normalizing = false
  env.notifier = context.update_notifier:connect(function(ctx)
    if env.normalizing then
      return
    end
    local input = ctx.input
    if should_skip(input) then
      return
    end
    local normalized = M.normalize(input)
    if normalized ~= input then
      env.normalizing = true
      ctx.input = normalized
      env.normalizing = false
    end
  end)
end

function M.func(key, env)
  return 2
end

function M.fini(env)
  if env.notifier then
    env.notifier:disconnect()
    env.notifier = nil
  end
end

return M
