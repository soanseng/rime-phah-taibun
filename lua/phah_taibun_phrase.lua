-- phah_taibun_phrase.lua
-- Phase 2：造詞模式 ;
-- 移植自 rime-liur (ryanwuson/rime-liur) 造詞模組
-- 逐字打拼音選字，組合成新詞條存入使用者字典
--
-- Phase 1 使用 Rime 內建的 custom_phrase 手動加詞
-- Phase 2 再移植 rime-liur 的 Lua 造詞模組

local M = {}

function M.init(env)
  env.name_space = env.name_space or ""
end

function M.func(input, seg, env)
  -- Phase 2: 造詞模式尚未實作
  -- 目前使用 custom_phrase 手動加詞
  if input:match("^;") then
    local cand = Candidate("phrase", seg.start, seg._end,
      input, "造詞模式（Phase 2 開發中）— 目前請用 custom_phrase 手動加詞")
    yield(cand)
  end
end

return M
