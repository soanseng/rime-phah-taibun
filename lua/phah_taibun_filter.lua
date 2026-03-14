-- phah_taibun_filter.lua
-- 核心過濾器：候選拼音註解 + 輸出模式切換
-- 參考 rime-liur (ryanwuson/rime-liur) 模組架構

local M = {}

-- 初始化
function M.init(env)
  env.name_space = env.name_space or ""
end

-- 主過濾器：為每個候選附加拼音註解
function M.func(input, env)
  for cand in input:iter() do
    -- 取得候選的拼音（Rime 自動提供）
    local comment = cand.comment or ""
    -- 直接輸出候選，保留 Rime 自動生成的拼音註解
    yield(cand)
  end
end

return M
