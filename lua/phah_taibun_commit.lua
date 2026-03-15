-- phah_taibun_commit.lua
-- 全羅模式輸出處理器：候選清單顯示漢羅，確定選字後輸出全羅拼音
--
-- 在全羅模式下，filter 將候選 text 設為漢羅顯示文字，
-- 全羅拼音存在 comment 的 [roman] 中。
-- 本 processor 攔截選字按鍵，改為輸出 comment 中的全羅拼音，
-- 並將聲調數字轉為 Unicode 調符、空格轉為連字符。

local M = {}

-- Load shared data module
local data_mod = nil
local ok, mod = pcall(require, "phah_taibun_data")
if ok and mod then
  data_mod = mod
end

-- ============================================================
-- TL ↔ POJ consonant/vowel conversion
-- ============================================================
local function tl_to_poj(tl_text)
  if not tl_text or tl_text == "" then
    return tl_text
  end
  local result = tl_text
  result = result:gsub("tsh", "chh")
  result = result:gsub("ts", "ch")
  result = result:gsub("ing([^a-z])", "eng%1")
  result = result:gsub("ing$", "eng")
  result = result:gsub("ik([^a-z])", "ek%1")
  result = result:gsub("ik$", "ek")
  result = result:gsub("ua", "oa")
  result = result:gsub("ue", "oe")
  return result
end

-- Use shared format_romanization from data module
local function format_romanization(roman)
  if data_mod and data_mod.format_romanization then
    return data_mod.format_romanization(roman)
  end
  return roman
end

-- ============================================================
-- Processor
-- ============================================================
function M.init(env)
  local config = env.engine.schema.config
  env.page_size = config:get_int("menu/page_size") or 5

  -- Build select key → page-relative index mapping
  local keys = config:get_string("menu/select_keys") or "1234567890"
  env.select_map = {}
  for i = 1, #keys do
    env.select_map[keys:byte(i)] = i - 1  -- 0-based
  end
end

-- Extract romanization from candidate's comment
-- Handles both simple [roman] and lookup-modified [TL:roman POJ:roman] formats
local function extract_roman(cand, env)
  if not cand then return nil end
  local comment = cand.comment or ""
  local content = comment:match("%[(.-)%]")
  if not content or content == "" then return nil end

  local context = env.engine.context
  local poj = context and context:get_option("poj_mode")

  -- Handle dual annotation format from phah_taibun_lookup:
  -- [TL:gua2 ai li POJ:goa2 ai li]
  local tl_part = content:match("TL:(.-)%s+POJ:")
  local poj_part = content:match("POJ:(.+)")
  if tl_part and poj_part then
    local raw = poj and poj_part or tl_part
    return format_romanization(raw)
  end

  -- Simple format: [gua2 ai li]
  local raw = content
  if poj then
    raw = tl_to_poj(raw)
  end
  return format_romanization(raw)
end

function M.func(key, env)
  local context = env.engine.context

  if not context:is_composing() and not context:has_menu() then
    return 2  -- kNoop
  end
  if key:release() then return 2 end

  local full_roman = context:get_option("full_romanization")

  -- ============================================================
  -- Shift+Space：漢羅模式下強制輸出羅馬字（任何模式皆可）
  -- ============================================================
  if key:repr() == "Shift+space" then
    local cand = context:get_selected_candidate()
    local roman = extract_roman(cand, env)
    if roman then
      env.engine:commit_text(roman)
      context:clear()
      return 1  -- kAccepted
    end
    return 2
  end

  -- 以下只在全羅模式下攔截
  if not full_roman then
    return 2  -- kNoop, let normal processing handle 漢羅 modes
  end

  local kc = key.keycode

  -- Handle space → confirm selected candidate with romanization
  if kc == 0x20 then
    local cand = context:get_selected_candidate()
    local roman = extract_roman(cand, env)
    if roman then
      env.engine:commit_text(roman)
      context:clear()
      return 1  -- kAccepted
    end
    return 2
  end

  -- Handle select keys → select specific candidate with romanization
  local rel_idx = env.select_map[kc]
  if rel_idx then
    local comp = context.composition
    if not comp:empty() then
      local seg = comp:back()
      local page = math.floor(seg.selected_index / env.page_size)
      local abs_idx = page * env.page_size + rel_idx

      -- Set selected index, then get the candidate
      seg.selected_index = abs_idx
      local cand = context:get_selected_candidate()
      local roman = extract_roman(cand, env)
      if roman then
        env.engine:commit_text(roman)
        context:clear()
        return 1  -- kAccepted
      end
    end
    return 2
  end

  return 2  -- kNoop for all other keys
end

return M
