-- phah_taibun_speedup.lua
-- Phase 2：簡拼提示 ,,sp
-- 移植自 rime-liur (ryanwuson/rime-liur) 快打模組
-- 打完整拼音時，comment 提示縮寫
--
-- 例如打 tshit-tho 時提示「簡拼：ct」

local M = {}

function M.init(env)
  env.name_space = env.name_space or ""
end

function M.func(input, seg, env)
  if input == ",,sp" then
    local cand = Candidate("speedup", seg.start, seg._end,
      ",,sp", "簡拼提示模式（Phase 2 開發中）")
    yield(cand)
  end
end

return M
