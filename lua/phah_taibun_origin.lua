-- phah_taibun_origin.lua
-- 羅馬字原文：在候選清單最後附加一個「照你打的音」候選。
-- 用途：字典沒有的台羅／POJ 詞（人名、地名、新詞），可直接送出自己輸入的音，
-- 支援 `-` 音節連字符與 `--` 輕聲標記，並轉成 Unicode 調符。任何模式都會出現。

local M = {}

local function load_data()
  local ok, mod = pcall(require, "phah_taibun_data")
  if ok and mod then return mod end
  return phah_taibun_data
end

-- 只在「像羅馬字」的輸入才附加：字母開頭，後接字母／數字／空白／連字符。
local ROMAN_PATTERN = "^[A-Za-z][A-Za-z0-9%s%-]*$"

-- 特殊模式不附加：注音反查 ~、萬用查字 ?、造詞 ;、說明 vv*，以及非羅馬字輸入。
local function should_skip(input)
  if not input or input == "" then return true end
  if input:sub(1, 1) == "~" then return true end
  if input:find("?", 1, true) then return true end
  if input:sub(1, 1) == ";" then return true end
  if input:match("^vv") then return true end
  if not input:match(ROMAN_PATTERN) then return true end
  return false
end

function M.init(env)
  local config = env.engine.schema.config
  env.name_space = env.name_space:gsub("^*", "")
  local setting = config:get_bool(env.name_space .. "/enabled")
  -- 預設開啟：nil（未設定）→ true，false → false
  env.enabled = (setting ~= false)
end

function M.func(input, env)
  local data = load_data()

  -- 先原樣放行所有候選，並記下 segment 範圍。
  local seg_start, seg_end
  local seen = false
  for cand in input:iter() do
    if not seen then
      seg_start = cand.start
      seg_end = cand._end
      seen = true
    end
    yield(cand)
  end

  if not env.enabled or not data or not seen then return end

  local context = env.engine.context
  if context:get_option("ascii_mode") then return end

  local text = context.input or ""
  if should_skip(text) then return end

  local poj = context:get_option("poj_mode")
  local roman = data.format_input_romanization(text, poj)
  if not roman or roman == "" then return end

  -- 與 Enter 直接送出的路徑一致：句首／Shift 起首時首字母大寫。
  local state = data.get_shared_state and data.get_shared_state()
  if state and state.capitalize_next and data.capitalize_first then
    roman = data.capitalize_first(roman)
  end

  local cand = Candidate("origin", seg_start, seg_end, roman, "〔羅馬字原文〕")
  cand.quality = -1
  yield(cand)
end

return M
