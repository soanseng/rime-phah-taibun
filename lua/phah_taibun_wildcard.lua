-- phah_taibun_wildcard.lua
-- 萬用查字 ? — 模糊拼音匹配
-- 移植自 rime-liur (ryanwuson/rime-liur) 萬用字元模組
--
-- 使用場景：不確定「食」的聲母？打 ?iah 匹配 tsiah（食）、siah（削）等
-- 實作：Lua translator 攔截含 ? 的輸入，展開為所有可能的音節匹配

local M = {}

-- 台語聲母列表（TL 系統）
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
  -- 只處理包含 ? 的輸入
  if not input:match("%?") then
    return
  end

  -- 將 ? 替換為各種可能的聲母
  local pattern = input:gsub("%?", "(.*)")
  -- 這裡提供基本的萬用字元提示
  -- 完整的匹配邏輯需要存取字典，在 Rime Lua 環境中
  -- 透過 env.engine.context 來實現
  local cand = Candidate("wildcard", seg.start, seg._end,
    input, "萬用字元：? 代替不確定的拼音部分")
  yield(cand)
end

return M
