-- phah_taibun_recommend.lua
-- 推薦用字標記：在候選區 comment 加上 ◆（推薦漢字）和 ★（推薦羅馬字）
-- ◆ = LKK type:"han" 或教育部700字
-- ★ = LKK type:"lo"

local M = {}
local data_mod = nil
local ok, mod = pcall(require, "phah_taibun_data")
if ok and mod then
  data_mod = mod
end


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
  -- 待放出的候選, 依 (slot, order) 排序。徽章最多前進 NUDGE_LKK 格,
  -- 故後續候選 (order >= 現序+1) 的 slot 恆 >= 現序+1-NUDGE_LKK
  -- (錨定只會把 slot 往後推)。slot <= 該下界的候選位置已定, 立即 yield:
  -- librime 只取第一頁時不必把上游數千補全候選全部拉完 (wasm 網頁版
  -- 短前綴從每鍵 1.4 秒降到毫秒級), 輸出順序與全收集排序逐項相同。
  local pending = {}
  local order = 0
  -- Sentence anchor: script_translator 的整句組字候選 (type="sentence")
  -- 是引擎斷詞結論, 徽章不得越過 (v0.9.2 CI: ◆短詞蓋過整句讓全羅
  -- 上屏只剩第一詞、句子 top-1 0.8→0.3)。錨定後徽章仍在 sentence
  -- 之後的半格帶 (S+0.5) 內前進, 不失「推薦強化」效果。
  local anchor_floor = nil

  local function before(a, b)
    if a.slot ~= b.slot then
      return a.slot < b.slot
    end
    return a.order < b.order
  end

  local function release(bound)
    while pending[1] and pending[1].slot <= bound do
      yield(table.remove(pending, 1).cand)
    end
  end

  local function collect(cand, new_cand, nudge)
    order = order + 1
    local slot
    if cand.type == "sentence" then
      -- 錨必須是「真組字句」: 輕聲變體（文字含 --）複製母詞的 type 與
      -- preedit, 本身不是引擎斷詞結論, 不得作為位移邊界。
      if not anchor_floor and not cand.text:find("--", 1, true) then
        anchor_floor = order
      end
      slot = order
    else
      slot = order - (nudge or 0)
      if anchor_floor and order > anchor_floor and slot <= anchor_floor then
        slot = anchor_floor + 0.5
      end
    end
    local entry = { cand = new_cand or cand, slot = slot, order = order }
    local i = #pending
    while i > 0 and before(entry, pending[i]) do
      i = i - 1
    end
    table.insert(pending, i + 1, entry)
    release(order + 1 - NUDGE_LKK)
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

    -- -- 變體（輕聲衍生形）不做徽章、不位移: 排序由 lighttone 貼母詞,
    -- 徽章屬於詞身份; 變體若可 nudge 會帶著母詞 preedit 搶位
    -- (telex zhiah8: 飼--啊 蓋頂讓 preedit 分裂成 zhi ah8)。
    if text:find("--", 1, true) then
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

  release(math.huge)
end

return M
