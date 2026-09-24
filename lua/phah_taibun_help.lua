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
      { "Ctrl+標點", "標點寬度臨時翻轉（漢羅→半形、全羅→全形）" },
      { "Space", "確認目前候選（整句連打：打完整句再按）" },
      { "Tab / Shift+Tab", "移動音節選取範圍；Tab 進入逐詞選字" },
      { "PageUp / PageDown", "切換候選頁" },
      { "[ / ]", "以詞定字：選首字 / 尾字" },
      { "Shift+A-Z", "句首或專有名詞首字母大寫" },
      { "Enter", "整句上屏；全羅模式＝直接送出目前羅馬字" },
      { "Ctrl+Enter", "送出原始輸入（不組字）" },
      { "\\", "切換目前候選的漢羅/全羅輸出；選字模式＋手動漢羅＝標記該詞為羅馬字" },
      { "'", "同音選字：輸入後按 ' 查同音字" },
      { "~", "注音反查→台語（選字後送回台語輸入）" },
      { "`", "符號選單：` 開目錄，`NN 直達 50 類（如 `25 性別）" },
      { ", . ( ) / _ < >", "標點直出：， 。 （ ） 、 —— 《 》（全羅輸出半形）" },
      { "\"", "引號交替：“ 開、” 關（全羅輸出 \"）" },
      { "?", "萬用查字（?iah → 選音節 → 選字）" },
      { ";", "造詞模式（;拼音 → 查字典選字）" },
      { "Telex", "拍台文(Telex)方案：v=2/8 x=1/4 y=3 d=5 w=7 q=9 z=ts zh=tsh f=連字號" },
      { "Emoji", "打詞附加候選（F4 可關）；`e 分類瀏覽（`e1 笑臉…）" },
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
