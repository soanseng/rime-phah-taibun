-- phah_taibun_synonym.lua
-- 同音字/文白讀切換 '
-- 移植自 rime-liur (ryanwuson/rime-liur) 同音模組
-- 選字後按 ' 顯示文讀/白讀的同音字切換
--
-- Currently a scaffold: passes through all candidates unchanged.
-- Full wen/bai (文白讀) switching requires wen_bai data in the
-- reverse dict, which will be populated in a future data build step.

local M = {}

function M.init(env)
  env.name_space = env.name_space or ""
end

-- Filter: pass through candidates, annotating wen/bai status when data available
function M.func(input, env)
  for cand in input:iter() do
    -- Future: check reverse dict for wen_bai markers
    -- If a character has both 文讀 and 白讀, annotate the comment
    -- e.g., 大 [tuā (白) / tāi (文)]
    yield(cand)
  end
end

return M
