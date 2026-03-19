-- phah_taibun_reverse_format.lua
-- Convert numeric tones to diacritics in reverse lookup annotations
-- Runs after reverse_lookup_filter in the filter chain
--
-- The built-in reverse_lookup_filter generates comments with numeric tones
-- (e.g. "Siau2 Siau3 tsio2"). This filter converts them to diacritics
-- (e.g. "Siáu Siàu tsió") and respects TL/POJ output mode.
--
-- Note: comment_format xform in the schema (wrapping in brackets) is applied
-- at display time, NOT stored on the candidate. The raw comment is just
-- space-separated readings like "Siau2 Siau3 siau2 siau2(文)".

local M = {}

local data_mod = nil
local ok, mod = pcall(require, "phah_taibun_data")
if ok and mod then
  data_mod = mod
end

function M.init(env)
  env.name_space = env.name_space or ""
end

function M.func(input, env)
  local context = env.engine.context
  local poj = context and context:get_option("poj_mode")

  for cand in input:iter() do
    local comment = cand.comment or ""

    -- Only process if there are tone numbers (digits) in the comment.
    -- Normal candidates already have diacritics by this point, so this
    -- naturally targets only reverse lookup results.
    if comment ~= "" and comment:match("[1-9]") and data_mod then
      local tokens = {}
      for token in comment:gmatch("[^%s]+") do
        -- Separate syllable from annotation like (文) or (白)
        local syl, annotation = token:match("^(.-)(%b())$")
        if not syl or syl == "" then
          syl = token
          annotation = ""
        end

        -- Convert TL to POJ if needed (must run before adding diacritics)
        if poj then
          syl = data_mod.tl_to_poj(syl)
        end

        -- Convert tone number to diacritic
        local formatted = data_mod.format_romanization(syl)
        if poj and data_mod.poj_fix_diacritics then
          formatted = data_mod.poj_fix_diacritics(formatted)
        end

        table.insert(tokens, formatted .. annotation)
      end

      local new_comment = table.concat(tokens, " ")
      if new_comment ~= comment then
        local new_cand = Candidate(cand.type, cand.start, cand._end, cand.text, new_comment)
        new_cand.quality = cand.quality
        new_cand.preedit = cand.preedit
        yield(new_cand)
      else
        yield(cand)
      end
    else
      yield(cand)
    end
  end
end

return M
