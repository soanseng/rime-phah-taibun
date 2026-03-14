-- phah_taibun_date.lua
-- 台語日期 ,,jit
-- 移植自 rime-liur (ryanwuson/rime-liur) 日期模組，改為台語格式

local M = {}

-- 台語星期對照
local WEEKDAYS = {
  [0] = "禮拜日",  -- Sunday
  [1] = "拜一",
  [2] = "拜二",
  [3] = "拜三",
  [4] = "拜四",
  [5] = "拜五",
  [6] = "拜六",
}

local WEEKDAYS_LO = {
  [0] = "Lé-pài-ji̍t",
  [1] = "Pài-it",
  [2] = "Pài-jī",
  [3] = "Pài-sann",
  [4] = "Pài-sì",
  [5] = "Pài-gōo",
  [6] = "Pài-la̍k",
}

function M.init(env)
  env.name_space = env.name_space or ""
end

function M.func(input, seg, env)
  if input == ",,jit" then
    local now = os.date("*t")
    local y, m, d = now.year, now.month, now.day
    local wday = now.wday - 1  -- Lua: 1=Sunday, we want 0=Sunday

    -- 漢字版
    local han = string.format("%d年%d月%d %s", y, m, d, WEEKDAYS[wday])
    yield(Candidate("date", seg.start, seg._end, han, "台語日期"))

    -- 羅馬字版
    local lo = string.format("%d nî %d gue̍h %d %s", y, m, d, WEEKDAYS_LO[wday])
    yield(Candidate("date", seg.start, seg._end, lo, "Tâi-gí ji̍t-kî"))

    -- ISO 格式
    local iso = os.date("%Y-%m-%d")
    yield(Candidate("date", seg.start, seg._end, iso, "ISO 8601"))
  end
end

return M
