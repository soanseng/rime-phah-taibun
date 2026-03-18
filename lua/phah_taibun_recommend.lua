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

function M.func(input, env)
  local data_mod = phah_taibun_data

  for cand in input:iter() do
    if not env.enabled or not data_mod then
      yield(cand)
      goto continue
    end

    local comment = cand.comment or ""
    local bracket_pos = comment:find("[", 1, true)

    -- Skip candidates with no bracket (English, emoji, etc.)
    if not bracket_pos then
      yield(cand)
      goto continue
    end

    local text = cand.text or ""
    if text == "" then
      yield(cand)
      goto continue
    end

    -- Check recommendations
    local has_han, has_lo = data_mod.check_lkk_recommend(text)
    if data_mod.check_moe700(text) then
      has_han = true
    end

    if not has_han and not has_lo then
      yield(cand)
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
    yield(new_cand)

    ::continue::
  end
end

return M
