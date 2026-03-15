-- phah_taibun_speedup.lua
-- 簡拼提示 vvsp
-- 移植自 rime-liur (ryanwuson/rime-liur) 快打模組
-- 顯示常用簡拼縮寫表，幫助使用者學習打字加速
--
-- Usage: type vvsp to show the abbreviation reference table

local M = {}

function M.init(env)
  env.name_space = env.name_space or ""
end

-- Common abbreviation patterns for TL initials
local SPEEDUP_TABLE = {
  { "p-",   "p   → 波 (p)" },
  { "ph-",  "ph  → 頗 (ph)" },
  { "b-",   "b   → 門 (b)" },
  { "m-",   "m   → 毛 (m)" },
  { "t-",   "t   → 地 (t)" },
  { "th-",  "th  → 他 (th)" },
  { "n-",   "n   → 耐 (n)" },
  { "l-",   "l   → 柳 (l)" },
  { "k-",   "k   → 求 (k)" },
  { "kh-",  "kh  → 去 (kh)" },
  { "g-",   "g   → 語 (g)" },
  { "ng-",  "ng  → 雅 (ng)" },
  { "ts-",  "ts  → 曾 (ts/ch)" },
  { "tsh-", "tsh → 出 (tsh/chh)" },
  { "s-",   "s   → 時 (s)" },
  { "j-",   "j   → 入 (j/l)" },
  { "h-",   "h   → 喜 (h)" },
  { "---",  "──────────────" },
  { "用法", "聲母 + Enter = 快速選字" },
  { "例",   "ts → 曾/做/走/... (所有 ts- 開頭字)" },
  { "提示", "schema algebra 已設定 abbrev 規則" },
}

function M.func(input, seg, env)
  if input ~= "vvsp" then
    return
  end

  for _, item in ipairs(SPEEDUP_TABLE) do
    local cand = Candidate("speedup", seg.start, seg._end, item[1], item[2])
    yield(cand)
  end
end

return M
