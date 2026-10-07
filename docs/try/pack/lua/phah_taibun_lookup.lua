-- phah_taibun_lookup.lua
-- 被動 filter：候選註解若已含 TL 讀音，補上 POJ 對照（[TL:… POJ:…]）
-- 移植自 rime-liur (ryanwuson/rime-liur) 查碼模組的呈現方式；不綁任何鍵。
--
-- 與讀音相關的兩條流程（都不是本模組）：
--   `~` 華語注音反查：輸入注音查 terra_pinyin 的華語讀音 → 漢字候選（候選再由本 filter 附台語讀音）
--   `'` 同音選字：上屏後按一次，取回該字詞的台語讀音重新組音（一次性，實作在 phah_taibun_commit.lua）

local M = {}


-- Load shared romanization conversion utilities
local data_mod = nil
local ok, mod = pcall(require, "phah_taibun_data")
if ok and mod then
  data_mod = mod
end

function M.init(env)
  env.name_space = env.name_space or ""
end

-- Enhance candidates with dual TL+POJ annotation
function M.func(input, env)
  for cand in input:iter() do
    local comment = cand.comment or ""

    -- Extract TL romanization from existing comment [...]
    local tl_roman = comment:match("%[(.-)%]")

    if tl_roman and tl_roman ~= "" then
      local poj_roman = data_mod and data_mod.tl_to_poj and data_mod.tl_to_poj(tl_roman) or tl_roman
      if data_mod and data_mod.poj_fix_diacritics then
        poj_roman = data_mod.poj_fix_diacritics(poj_roman)
      end

      -- Only add dual annotation if POJ differs from TL
      if poj_roman ~= tl_roman then
        local new_comment = " [TL:" .. tl_roman .. " POJ:" .. poj_roman .. "]"
        local new_cand = Candidate(cand.type, cand.start, cand._end, cand.text, new_comment)
        new_cand.quality = cand.quality
        new_cand.preedit = cand.preedit
        yield(new_cand)
      else
        -- TL and POJ are the same, keep original comment
        yield(cand)
      end
    else
      yield(cand)
    end
  end
end

return M
