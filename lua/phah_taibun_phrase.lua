-- phah_taibun_phrase.lua
-- 造詞模式 ; — 組合新詞條
-- 移植自 rime-liur (ryanwuson/rime-liur) 造詞模組
--
-- Usage: type ;word to compose a new phrase entry
-- The ; prefix triggers phrase composition mode.
-- Composed phrases can be saved to custom_phrase for future use.

local M = {}

function M.init(env)
  env.name_space = env.name_space or ""
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
      { ";", "造詞模式：輸入拼音組成新詞" },
      { "用法", "; + 拼音 → 選字組詞" },
      { "例", ";tsia-iah → 食飯" },
      { "提示", "組好的詞請加入 custom_phrase 保存" },
    }
    for _, item in ipairs(hints) do
      local cand = Candidate("phrase", seg.start, seg._end, item[1], item[2])
      yield(cand)
    end
    return
  end

  -- Pass the phrase input through as a candidate with annotation
  -- This allows the user to see and select the composed phrase
  local cand = Candidate("phrase", seg.start, seg._end,
    phrase_input, "造詞：" .. phrase_input .. " — 選字後加入 custom_phrase 保存")
  yield(cand)
end

return M
