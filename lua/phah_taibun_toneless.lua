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

-- "[lim5]" / "[lím]" / "[TL:tshia POJ:chhia]" → "lim" / "tshia"。回傳 nil 的情況：
--   * 非 [純羅馬字] 或 [TL:… POJ:…] 註解格式
--   * 讀音含空白或連字號（多音節；碎片組合 [lí-ḿ] 不算完整覆蓋）
--   * 含漢字等非拉丁內容
local function strip_tone_digits(roman)
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

local function plain_form(comment)
  if not comment then return nil end
  -- 候選註解常帶 ◆/★ 推薦標記前綴（" ◆ [lim5]"），取第一個括號內容
  local roman = comment:match("%[([^%]]+)%]")
  if not roman then return nil end
  if roman:find("[%s%-]") then return nil end
  return strip_tone_digits(roman)
end

-- 雙格式註解 "[TL:tshia1 POJ:chhia1]"（可能有 ◆/★ 前綴）→ 無調形集合
-- {tshia, chhia}；POJ 輸入的 span 對得上 POJ 拼式時同樣視為完整覆蓋。
local function plain_forms(comment)
  if not comment then return {} end
  local tl, poj = comment:match("%[TL:(%S+)%s+POJ:(%S+)%]")
  if not tl then
    local single = plain_form(comment)
    return single and { single } or {}
  end
  local forms = {}
  local tl_plain = strip_tone_digits(tl)
  local poj_plain = strip_tone_digits(poj)
  if tl_plain then forms[#forms + 1] = tl_plain end
  if poj_plain and poj_plain ~= tl_plain then
    forms[#forms + 1] = poj_plain
  end
  return forms
end

function M.func(input, env)
  -- 升權條件：候選 span 是單一 token、純小寫字母（無調輸入意圖）、
  -- 讀音（註解）單音節完全覆蓋該 span，且 span 覆蓋輸入的**尾段**
  -- （cand._end == #context.input）。尾段＝使用者正在打的那個詞：
  -- 逐字選字（kio→橋 確認後打 tiann→鼎）要升權；中段單字（tai-uan
  -- 的 帶）不得升權，否則選單被單字塞滿，免調連字號字典詞（台灣）
  -- 被擠出候選。
  local ctx = env.engine and env.engine.context
  local ctx_input = ctx and ctx.input
  local full, rest = {}, {}
  for cand in input:iter() do
    local span = cand.preedit
    local covered = false
    if type(span) == "string" and span:match("^[a-z]+$") and ctx_input
      and span == ctx_input:sub(cand.start + 1, cand._end) and cand._end == #ctx_input then
      for _, form in ipairs(plain_forms(cand.comment)) do
        if form == span then
          covered = true
          break
        end
      end
    end
    if covered then
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
