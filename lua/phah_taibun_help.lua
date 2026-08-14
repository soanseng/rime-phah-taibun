-- phah_taibun_help.lua
-- 按鍵說明 vvh
-- 移植自 rime-liur (ryanwuson/rime-liur)，改寫為台語版

local M = {}

function M.init(env)
  env.name_space = env.name_space or ""
end

function M.func(input, seg, env)
  if input == "vvh" then
    local help_items = {
      { "F4 / Ctrl+`", "開 Rime 方案選單，切換漢羅/全羅與 TL/POJ" },
      { "Ctrl+Space", "切換台文/英文輸入" },
      { "Space", "確認目前候選" },
      { "Tab / Shift+Tab", "移動音節選取範圍" },
      { "PageUp / PageDown", "切換候選頁" },
      { "[ / ]", "以詞定字：選首字 / 尾字" },
      { "Shift+A-Z", "句首或專有名詞首字母大寫" },
      { "Enter", "全羅模式直接送出目前羅馬字" },
      { "\\", "切換目前候選的漢羅/全羅輸出" },
      { "'", "同音選字：輸入後按 ' 查同音字" },
      { "~", "注音反查→台語（選字後送回台語輸入）" },
      { "`", "符號選單（調號/方音/標點）" },
      { "?", "萬用查字（?iah → 選音節 → 選字）" },
      { ";", "造詞模式（;拼音 → 查字典選字）" },
      { "vvh", "本說明" },
      { "vvjit", "台語日期時間" },
      { "vvsp", "簡拼提示表" },
    }
    for _, item in ipairs(help_items) do
      local cand = Candidate("help", seg.start, seg._end, item[1], item[2])
      yield(cand)
    end
  end
end

return M
