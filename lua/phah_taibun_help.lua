-- phah_taibun_help.lua
-- 按鍵說明 ,,h
-- 移植自 rime-liur (ryanwuson/rime-liur)，改寫為台語版

local M = {}

function M.init(env)
  env.name_space = env.name_space or ""
end

function M.func(input, seg, env)
  if input == ",,h" then
    local help_items = {
      { "Ctrl+Shift+T", "切換輸出模式（漢羅/全羅）" },
      { "~", "華語拼音反查台語" },
      { "`", "符號選單（調號/方音/標點）" },
      { ",,h", "本說明" },
      { ",,jit", "台語日期時間" },
    }
    for _, item in ipairs(help_items) do
      local cand = Candidate("help", seg.start, seg._end, item[1], item[2])
      yield(cand)
    end
  end
end

return M
