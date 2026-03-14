-- phah_taibun_symbols.lua
-- 台語符號選單 `
-- 移植自 rime-liur (ryanwuson/rime-liur) 符號清單，替換為台語專用符號

local M = {}

local SYMBOLS = {
  -- 台羅調號 (TL)
  { "á", "第二聲 (TL)" },
  { "à", "第三聲 (TL)" },
  { "â", "第五聲 (TL)" },
  { "ā", "第七聲 (TL)" },
  { "a̍", "第八聲 (TL)" },
  -- POJ 特殊
  { "o͘", "POJ oo (o͘)" },
  { "ⁿ", "鼻化上標 (ⁿ)" },
  -- 方音符號
  { "ㆠ", "方音 b" },
  { "ㆣ", "方音 g" },
  { "ㄫ", "方音 ng" },
  { "ㆢ", "方音 j" },
  { "ㆦ", "方音 oo" },
  { "ㆤ", "方音 ee" },
  { "ㆰ", "方音 am" },
  { "ㆱ", "方音 om" },
  { "ㆲ", "方音 ong" },
  { "ㆬ", "方音 m (韻母)" },
  { "ㆭ", "方音 ng (韻母)" },
  -- 台文標點
  { "--", "輕聲連字號 (--)" },
  { "、", "頓號" },
  { "。", "句號" },
}

function M.init(env)
  env.name_space = env.name_space or ""
end

function M.func(input, seg, env)
  -- Only respond to backtick trigger
  if input:match("^`") then
    for _, sym in ipairs(SYMBOLS) do
      yield(Candidate("symbol", seg.start, seg._end, sym[1], sym[2]))
    end
  end
end

return M
