-- phah_taibun_phrase.lua
-- 造詞模式 ; — 字典查字
-- 移植自 rime-liur (ryanwuson/rime-liur) 造詞模組
--
-- Usage: type ;tsiah to look up characters with that pronunciation.
-- Uses Memory API for actual dictionary lookup.

local M = {}

function M.init(env)
  env.name_space = env.name_space or ""
  env.mem = Memory(env.engine, env.engine.schema)
end

function M.func(input, seg, env)
  -- Only process inputs starting with ;
  if not input:match("^;") then
    return
  end

  local phrase_input = input:sub(2)  -- Everything after ;

  if phrase_input == "" then
    -- Show guidance when only ; is typed
    local hints = {
      { ";", "造詞模式：輸入拼音查字典" },
      { "用法", "; + 拼音 → 查字（例：;tsiah → 食）" },
      { "提示", "選字後直接輸出，可連續查多個字" },
    }
    for _, item in ipairs(hints) do
      local cand = Candidate("phrase", seg.start, seg._end, item[1], item[2])
      yield(cand)
    end
    return
  end

  -- Look up characters in dictionary
  local found = false
  if env.mem:dict_lookup(phrase_input, true, 100) then
    local seen = {}
    for entry in env.mem:iter_dict() do
      local code = entry.custom_code or phrase_input
      -- Only show single-syllable entries for character-by-character composition
      if not code:find(" ") and not seen[entry.text] then
        seen[entry.text] = true
        local cand = Candidate("phrase", seg.start, seg._end,
          entry.text, " [" .. code .. "]")
        yield(cand)
        found = true
      end
    end
  end

  if not found then
    local cand = Candidate("phrase", seg.start, seg._end,
      phrase_input, "查無此音，請確認拼音")
    yield(cand)
  end
end

return M
