-- phah_taibun_recommend.lua
-- 推薦用字標記：在候選區 comment 加上 ◆（推薦漢字）和 ★（推薦羅馬字）
-- ◆ = LKK type:"han" 或教育部700字
-- ★ = LKK type:"lo"

local M = {}

function M.init(env)
  local config = env.engine.schema.config
  env.name_space = env.name_space:gsub("^*", "")
  local setting = config:get_bool(env.name_space .. "/enabled")
  -- Default true: nil (not set) → true, false → false
  env.enabled = (setting ~= false)
end

-- 推薦升權：librime filter 不會依 .quality 重排候選，且詞典候選的
-- quality 實務上全是 nil——任何「加法排序」都會退化成徽章置頂、
-- 讓大量 ★ 輕聲變體淹沒候選區（kio-tiann 實測：橋 被擠出可見窗）。
-- 因此改用「有界位移」：維持字典順序為主，徽章只把候選往前挪固定
-- 格數——LKK 推薦（◆ 漢字 / ★ 羅馬字）挪 3 格、教育部700字（◆）挪
-- 1 格。同碼平手時 LKK 因此贏過 moe700（伊◆ vs 醫◆），但任何徽章
-- 都不能越過 3 格以上的差距。
local NUDGE_LKK = 3
local NUDGE_MOE = 1

function M.func(input, env)
  local data_mod = phah_taibun_data

  local all = {}
  local order = 0

  local function collect(cand, new_cand, nudge)
    order = order + 1
    all[#all + 1] = {
      cand = new_cand or cand,
      slot = order - (nudge or 0),
      order = order,
    }
  end

  for cand in input:iter() do
    if not env.enabled or not data_mod then
      collect(cand, nil)
      goto continue
    end

    local comment = cand.comment or ""
    local bracket_pos = comment:find("[", 1, true)

    -- Skip candidates with no bracket (English, emoji, etc.)
    if not bracket_pos then
      collect(cand, nil)
      goto continue
    end

    local text = cand.text or ""
    if text == "" then
      collect(cand, nil)
      goto continue
    end

    -- Check recommendations
    local lkk_han, lkk_lo = data_mod.check_lkk_recommend(text)
    local moe = data_mod.check_moe700(text)
    local has_han = lkk_han or moe
    local has_lo = lkk_lo

    -- Nudge tier by recommendation source (bounded displacement)
    local nudge
    if lkk_han or lkk_lo then
      nudge = NUDGE_LKK
    elseif moe then
      nudge = NUDGE_MOE
    end
    if not nudge then
      collect(cand, nil)
      goto continue
    end

    -- Build prefix
    local prefix = ""
    if has_han then prefix = prefix .. "◆" end
    if has_lo then prefix = prefix .. "★" end

    -- Insert prefix before the [ bracket
    local new_comment = comment:sub(1, bracket_pos - 1) .. prefix .. " " .. comment:sub(bracket_pos)

    local new_cand = Candidate(cand.type, cand.start, cand._end, cand.text, new_comment)
    new_cand.quality = cand.quality
    new_cand.preedit = cand.preedit
    collect(cand, new_cand, nudge)

    ::continue::
  end

  -- Bounded displacement: slot = original position - nudge, stable by
  -- (slot, original order). A badge moves a candidate forward at most
  -- NUDGE_LKK slots — it can never flood the window.
  table.sort(all, function(a, b)
    if a.slot ~= b.slot then
      return a.slot < b.slot
    end
    return a.order < b.order
  end)

  for _, entry in ipairs(all) do
    yield(entry.cand)
  end
end

return M
