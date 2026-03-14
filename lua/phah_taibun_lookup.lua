-- phah_taibun_lookup.lua
-- 查台語讀音 Ctrl+'
-- 移植自 rime-liur (ryanwuson/rime-liur) 查碼模組
-- 選字後顯示 TL + POJ 讀音 + 華語對照

local M = {}

function M.init(env)
  env.name_space = env.name_space or ""
end

-- 為候選附加台語讀音資訊
function M.func(input, env)
  for cand in input:iter() do
    -- 取得候選的拼音（Rime 自動提供的 comment 已有拼音）
    local text = cand.text or ""
    local comment = cand.comment or ""

    -- 在 comment 中顯示讀音資訊
    -- Rime 的 script_translator 已自動在 comment 附加拼音
    -- 此模組可做額外增強（如加 POJ 版本），Phase 2 再擴充

    yield(cand)
  end
end

return M
