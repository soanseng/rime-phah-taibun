-- phah_taibun_select_char.lua
-- 以詞定字：按 [ 選首字、按 ] 選尾字
-- Ported from rime-ice select_character.lua, adapted for phah-taibun

local M = {}

function M.init(env)
    local config = env.engine.schema.config
    env.name_space = env.name_space:gsub("^*", "")
    env.first_key = config:get_string(env.name_space .. "/first_key")
    env.last_key = config:get_string(env.name_space .. "/last_key")
    env.page_size = config:get_int("menu/page_size") or 5
end

function M.func(key, env)
    local engine = env.engine
    local context = engine.context

    if
        not key:release()
        and (context:is_composing() or context:has_menu())
        and (env.first_key or env.last_key)
    then
        -- Check if we're on page 2+ — pass through for paging
        if key:repr() == env.first_key or key:repr() == env.last_key then
            local comp = context.composition
            if not comp:empty() then
                local seg = comp:back()
                if seg.selected_index >= env.page_size then
                    return 2  -- kNoop, let key_binder handle paging
                end
            end
        end

        local input = context.input
        local selected_candidate = context:get_selected_candidate()
        selected_candidate = selected_candidate and selected_candidate.text or input

        local selected_char = ""
        if key:repr() == env.first_key then
            selected_char = selected_candidate:sub(1, utf8.offset(selected_candidate, 2) - 1)
        elseif key:repr() == env.last_key then
            selected_char = selected_candidate:sub(utf8.offset(selected_candidate, -1))
        else
            return 2  -- kNoop
        end

        local commit_text = context:get_commit_text()
        local _, end_pos = commit_text:find(selected_candidate, 1, true)
        local caret_pos = context.caret_pos

        local part1 = commit_text:sub(1, end_pos):gsub(
            selected_candidate, selected_char, 1
        )
        local part2 = commit_text:sub(end_pos + 1)

        engine:commit_text(part1)
        context:clear()
        if caret_pos ~= #input then
            part2 = part2 .. input:sub(caret_pos + 1)
        end
        if part2 ~= "" then
            context:push_input(part2)
        end
        return 1  -- kAccepted
    end
    return 2  -- kNoop
end

return M
