-- phah_taibun_synonym.lua
-- Phase 2：同音字/文白讀切換 '
-- 移植自 rime-liur (ryanwuson/rime-liur) 同音模組
-- 選字後按 ' 顯示文讀/白讀的同音字切換
--
-- 需要額外的文白讀標記資料（ChhoeTaigi 部分有 Others 欄位可利用）

local M = {}

function M.init(env)
  env.name_space = env.name_space or ""
end

function M.func(input, env)
  for cand in input:iter() do
    -- Phase 2: 文白讀切換尚未實作
    -- 需要文白讀標記資料
    yield(cand)
  end
end

return M
