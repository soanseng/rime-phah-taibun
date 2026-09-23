-- phah_taibun_toneless.lua
-- 無調整詞優先
-- schema speller algebra 以 abbrev 邊提供無調拼式（連打時精確音節路徑
-- 壓過弱拼碎片）。副作用：單 token 無調輸入（lim）時，一個 abbrev 邊的
-- 完整音節（林）會被兩個 abbrev 邊的碎片組合（你姆 li+m）壓過。本 filter
-- 把「單音節讀音完全覆蓋輸入」的候選排到最前，維持「聲調可省略」的
-- 短輸入體驗。註解可能是數字調（[lim5]）或變調符（[lím]）形式。

local M = {}

-- 變調符預組字元 → 基本字母（TL/POJ 用的母音與鼻音附標）
local DIACRITIC_BASE = {
  [0xE1] = "a", [0xE0] = "a", [0xE2] = "a", [0x101] = "a", [0x1CE] = "a",
  [0xE9] = "e", [0xE8] = "e", [0xEA] = "e", [0x113] = "e", [0x11B] = "e",
  [0xED] = "i", [0xEC] = "i", [0xEE] = "i", [0x12B] = "i", [0x1D0] = "i",
  [0xF3] = "o", [0xF2] = "o", [0xF4] = "o", [0x14D] = "o", [0x1D2] = "o",
  [0xFA] = "u", [0xF9] = "u", [0xFB] = "u", [0x16B] = "u", [0x1D4] = "u",
  [0x1E3F] = "m",
}

-- "[lim5]" / "[lím]" → "lim"。回傳 nil 的情況：
--   * 非 [純羅馬字] 註解格式
--   * 讀音含空白或連字號（多音節；碎片組合 [lí-ḿ] 不算完整覆蓋）
--   * 含漢字等非拉丁內容
local function plain_form(comment)
  if not comment then return nil end
  local roman = comment:match("^%s*%[([^%]]+)%]%s*$")
  if not roman then return nil end
  if roman:find("[%s%-]") then return nil end
  local out = {}
  for _, code in utf8.codes(roman) do
    if code < 128 then
      -- 去掉聲調數字；保留其餘 ASCII 字母
      if not (code >= 49 and code <= 57) then
        out[#out + 1] = string.char(code)
      end
    else
      local base = DIACRITIC_BASE[code]
      if base then
        out[#out + 1] = base
      elseif code >= 0x300 and code <= 0x36F then
        -- combining mark（含 o͘ 的 U+0358）：略過
      else
        return nil
      end
    end
  end
  return table.concat(out)
end

function M.func(input, env)
  -- 每個候選用自身 preedit（覆蓋的原始輸入片段）判斷：單一 token、
  -- 純小寫字母＝無調輸入意圖；讀音（註解）單音節完全覆蓋該片段者
  -- 排到最前。整句組合（preedit 含空白）與帶調輸入不受影響。
  local full, rest = {}, {}
  for cand in input:iter() do
    local span = cand.preedit
    if type(span) == "string" and span:match("^[a-z]+$")
       and plain_form(cand.comment) == span then
      table.insert(full, cand)
    else
      table.insert(rest, cand)
    end
  end
  for _, cand in ipairs(full) do
    yield(cand)
  end
  for _, cand in ipairs(rest) do
    yield(cand)
  end
end

return M
