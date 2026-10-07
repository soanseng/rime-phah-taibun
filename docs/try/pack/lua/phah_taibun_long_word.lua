-- phah_taibun_long_word.lua
-- 長詞優先：提升較長的候選詞到更前面的位置
-- Ported from rime-ice long_word_filter.lua, adapted for phah-taibun

local M = {}

function M.init(env)
    local config = env.engine.schema.config
    env.name_space = env.name_space:gsub("^*", "")
    env.lw_count = config:get_int(env.name_space .. "/count") or 2
    env.lw_idx = config:get_int(env.name_space .. "/idx") or 4
end

function M.func(input, env)
    local l = {}
    local first_len = 0
    local done = 0
    local i = 1
    local count = env.lw_count or 2
    local idx = env.lw_idx or 4
    for cand in input:iter() do
        local leng = utf8.len(cand.text)
        if first_len < 1 then
            first_len = leng
        end
        -- Don't reorder candidates before position idx
        if i < idx then
            i = i + 1
            yield(cand)
        -- Promote longer candidates, skip ASCII-only (English words)
        elseif leng <= first_len or cand.text:find("^[%a%d%p%s]+$") then
            table.insert(l, cand)
        else
            yield(cand)
            done = done + 1
        end
        -- Stop after promoting count candidates or buffering 50
        if done == count or #l > 50 then
            break
        end
    end
    -- Yield buffered candidates
    for _, cand in ipairs(l) do
        yield(cand)
    end
    -- Yield remaining candidates
    for cand in input:iter() do
        yield(cand)
    end
end

return M
