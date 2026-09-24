"""Behavior tests for the phah_taibun Lua filter."""

import shutil
import subprocess
import textwrap
from pathlib import Path

ROOT = Path(__file__).parent.parent
LUA_EXECUTABLE = shutil.which("lua") or shutil.which("lua5.4") or "lua"


def run_lua(script: str) -> str:
    result = subprocess.run(
        [LUA_EXECUTABLE, "-"],
        input=script,
        capture_output=True,
        text=True,
        cwd=ROOT,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    return result.stdout


def test_hanlo_rules_can_replace_han_candidate_by_roman_syllable():
    script = textwrap.dedent(
        r"""
        package.path = "lua/?.lua;" .. package.path
        package.loaded["phah_taibun_data"] = {
          get_hanlo_type = function(word)
            if word == "ê" then return "lo" end
            return nil
          end,
          format_romanization = function(roman)
            if roman == "e5" then return "ê" end
            return roman
          end,
        }

        function Candidate(type, start, end_pos, text, comment)
          return {
            type = type,
            start = start,
            _end = end_pos,
            text = text,
            comment = comment,
            quality = 0,
          }
        end
        local yielded = {}
        function yield(cand)
          table.insert(yielded, cand)
        end

        local filter = require("phah_taibun_filter")
        local input = {
          iter = function()
            local done = false
            return function()
              if done then return nil end
              done = true
              return Candidate("table", 0, 1, "的", " [e5]")
            end
          end
        }
        local env = {
          engine = {
            context = {
              get_option = function(_, _) return false end
            }
          }
        }

        filter.func(input, env)
        for _, cand in ipairs(yielded) do
          print(cand.text .. "\t" .. cand.comment)
        end
        """
    )

    assert run_lua(script).strip() == "ê\t [ê]"


def test_toneless_single_token_full_coverage_candidate_ranked_first():
    """單 token 無調輸入 lim: 讀音完全覆蓋輸入的候選 (林) 必須排在
    只覆蓋部分的碎片組合 (你姆 li+m) 前面——abbrev 無調拼式的補償。"""
    script = textwrap.dedent(
        r"""
        package.path = "lua/?.lua;" .. package.path
        function Candidate(type, start, end_pos, text, comment)
          return {
            type = type,
            start = start,
            _end = end_pos,
            text = text,
            comment = comment,
            quality = 0,
          }
        end
        local items = {
          Candidate("table", 0, 3, "你姆", " [li2 m2]"),
          Candidate("table", 0, 3, "林", " [lím]"),
          Candidate("table", 0, 3, "臨", " [lim5]"),
          Candidate("table", 2, 3, "姆", " [m̄]"),
        }
        local yielded = {}
        function yield(cand)
          table.insert(yielded, cand)
        end
        local filter = require("phah_taibun_toneless")
        items[1].preedit = "li m"
        items[2].preedit = "lim"
        items[3].preedit = "lim"
        items[4].preedit = "m"
        local pos = 0
        local input = {
          iter = function()
            return function()
              pos = pos + 1
              return items[pos]
            end
          end,
        }
        local env = { engine = { context = { input = "lim" } } }

        filter.func(input, env)
        for _, cand in ipairs(yielded) do
          print(cand.text)
        end
        """
    )

    out = run_lua(script).split()
    assert out[0] == "林"
    assert out[1] == "臨"
    assert "你姆" in out[2:]

    script = textwrap.dedent(
        r"""
        package.path = "lua/?.lua;" .. package.path
        package.loaded["phah_taibun_data"] = {
          get_hanlo_type = function(word)
            if word == "khok" then return "lo" end
            return nil
          end,
          format_romanization = function(roman)
            if roman == "tsui2 khok4 a2" then return "tsuí-khok-á" end
            if roman == "khok4" then return "khok" end
            return roman
          end,
        }
        function Candidate(type, start, end_pos, text, comment)
          return {
            type = type,
            start = start,
            _end = end_pos,
            text = text,
            comment = comment,
            quality = 0,
          }
        end
        local yielded = {}
        function yield(cand)
          table.insert(yielded, cand)
        end

        local filter = require("phah_taibun_filter")
        local input = {
          iter = function()
            local done = false
            return function()
              if done then return nil end
              done = true
              return Candidate("table", 0, 1, "水觳仔", " [tsui2 khok4 a2]")
            end
          end
        }
        local env = {
          engine = {
            context = {
              get_option = function(_, _) return false end
            }
          }
        }

        filter.func(input, env)
        for _, cand in ipairs(yielded) do
          print(cand.text .. "\t" .. cand.comment)
        end
        """
    )

    assert run_lua(script).strip() == "水觳仔\t [tsuí-khok-á]"


def test_toneless_dual_format_comment_covers_poj_input():
    """雙格式註解 [TL:tshia1 POJ:chhia1] 的 1 聲字, POJ 無調輸入 (chhia)
    同樣要視為完整覆蓋而排前——TL 與 POJ 拼式任一對上即覆蓋."""
    script = textwrap.dedent(
        r"""
        package.path = "lua/?.lua;" .. package.path
        function Candidate(type, start, end_pos, text, comment)
          return {
            type = type, start = start, _end = end_pos,
            text = text, comment = comment, quality = 0,
          }
        end
        local items = {
          Candidate("table", 0, 5, "刺仔", " ◆ [TL:tshì-á POJ:chhì-á]"),
          Candidate("table", 0, 5, "車", " ◆ [TL:tshia1 POJ:chhia1]"),
        }
        local yielded = {}
        function yield(cand)
          table.insert(yielded, cand)
        end
        local filter = require("phah_taibun_toneless")
        items[1].preedit = "chhi a"
        items[2].preedit = "chhia"
        local pos = 0
        local input = {
          iter = function()
            return function()
              pos = pos + 1
              return items[pos]
            end
          end,
        }
        local env = { engine = { context = { input = "chhia" } } }

        filter.func(input, env)
        for _, cand in ipairs(yielded) do
          print(cand.text)
        end
        """
    )

    out = run_lua(script).split()
    assert out[0] == "車", out
    assert out[1] == "刺仔", out


def test_toneless_multi_segment_input_does_not_boost_segment_singles():
    """多段輸入 (tai-uan): 只覆蓋第一段的單字 (帶) 不得升權壓過整詞 (台灣).

    升權只屬於「候選覆蓋整個輸入」的單 token 場景; 段內單字全體升權會
    把 10 格選單塞滿單字, 免調連字號字典詞被擠出候選.
    """
    script = textwrap.dedent(
        r"""
        package.path = "lua/?.lua;" .. package.path
        function Candidate(type, start, end_pos, text, comment)
          return {
            type = type, start = start, _end = end_pos,
            text = text, comment = comment, quality = 0,
          }
        end
        local items = {
          Candidate("table", 0, 7, "台灣", " [tai5 uan5]"),
          Candidate("table", 0, 3, "帶", " [tài]"),
          Candidate("table", 0, 3, "戴", " [tài]"),
        }
        local yielded = {}
        function yield(cand)
          table.insert(yielded, cand)
        end
        local filter = require("phah_taibun_toneless")
        items[1].preedit = "tai-uan"
        items[2].preedit = "tai"
        items[3].preedit = "tai"
        local pos = 0
        local input = {
          iter = function()
            return function()
              pos = pos + 1
              return items[pos]
            end
          end,
        }
        local env = { engine = { context = { input = "tai-uan" } } }

        filter.func(input, env)
        for _, cand in ipairs(yielded) do
          print(cand.text)
        end
        """
    )

    out = run_lua(script).split()
    assert out[0] == "台灣", out


def test_formats_direct_tl_input_with_hyphen_and_light_tone_marker():
    script = textwrap.dedent(
        r"""
        package.path = "lua/?.lua;" .. package.path
        local data = require("phah_taibun_data")

        print(data.format_input_romanization("tsng-kio5", false))
        print(data.format_input_romanization("kio3--i", false))
        """
    )

    assert run_lua(script).splitlines() == ["tsng-kio\u0302", "kio\u0300--i"]


def test_formats_direct_poj_input_without_forcing_tl_spelling():
    script = textwrap.dedent(
        r"""
        package.path = "lua/?.lua;" .. package.path
        local data = require("phah_taibun_data")

        print(data.format_input_romanization("goa2-kio5", true))
        """
    )

    assert run_lua(script).strip() == "go\u0301a-kio\u0302"


def _origin_script(
    *,
    input_text: str,
    poj: bool,
    ascii_mode: bool,
    cap: bool,
    enabled: bool,
    segment_start: int = 0,
    segment_end: int | None = None,
) -> str:
    """Build a harness that runs phah_taibun_origin over one mocked Han candidate.

    format_input_romanization / capitalize_first are stubbed so the test exercises
    the FILTER logic (guards, ordering, label, flag plumbing), not the romanizer
    (which has its own tests above).
    """
    if segment_end is None:
        segment_end = len(input_text)
    return textwrap.dedent(
        rf"""
        package.path = "lua/?.lua;" .. package.path
        package.loaded["phah_taibun_data"] = {{
          format_input_romanization = function(inp, poj)
            return "<" .. inp .. "|poj=" .. tostring(poj) .. ">"
          end,
          get_shared_state = function() return {{ capitalize_next = {str(cap).lower()} }} end,
          capitalize_first = function(s) return "CAP:" .. s end,
        }}

        function Candidate(type, start, end_pos, text, comment)
          return {{ type=type, start=start, _end=end_pos, text=text,
                   comment=comment, quality=0 }}
        end
        local yielded = {{}}
        function yield(c) table.insert(yielded, c) end

        local filter = require("phah_taibun_origin")
        local env = {{
          engine = {{
            context = {{
              input = "{input_text}",
              get_option = function(_, name)
                if name == "poj_mode" then return {str(poj).lower()} end
                if name == "ascii_mode" then return {str(ascii_mode).lower()} end
                return false
              end,
            }},
            schema = {{ config = {{
              get_bool = function(_, _) return {str(enabled).lower()} end,
            }} }},
          }},
          name_space = "*phah_taibun_origin",
        }}
        filter.init(env)

        local input = {{
          iter = function()
            local done = false
            return function()
              if done then return nil end
              done = true
              return Candidate("table", {segment_start}, {segment_end}, "X", " [e5]")
            end
          end
        }}
        filter.func(input, env)
        for _, c in ipairs(yielded) do
          print(c.text .. "\t" .. (c.comment or ""))
        end
        """
    )


def test_origin_appends_romanization_candidate_last_for_tl_input():
    out = run_lua(
        _origin_script(input_text="tsng-kio5", poj=False, ascii_mode=False, cap=False, enabled=True)
    ).splitlines()
    assert out == ["X\t [e5]", "<tsng-kio5|poj=false>\t\u3014\u7f85\u99ac\u5b57\u539f\u6587\u3015"]


def test_origin_defers_capitalization_until_commit():
    out = run_lua(
        _origin_script(input_text="goa2-kio5", poj=True, ascii_mode=False, cap=True, enabled=True)
    ).splitlines()
    assert out == ["X\t [e5]", "<goa2-kio5|poj=true>\t\u3014羅馬字原文\u3015"]


def test_origin_formats_only_the_active_segment():
    out = run_lua(
        _origin_script(
            input_text="gua2-li2",
            poj=False,
            ascii_mode=False,
            cap=False,
            enabled=True,
            segment_start=5,
            segment_end=8,
        )
    ).splitlines()
    assert out == ["X\t [e5]", "<li2|poj=false>\t\u3014羅馬字原文\u3015"]


def test_origin_skips_special_modes_and_non_romanization():
    # reverse (~), wildcard (?), phrase (;), helper (vv*), empty, ascii mode
    for text, ascii_mode in [
        ("~tsiah", False),
        ("si?", False),
        (";tsiah", False),
        ("vvh", False),
        ("", False),
        ("hello", True),
    ]:
        out = run_lua(
            _origin_script(input_text=text, poj=False, ascii_mode=ascii_mode, cap=False, enabled=True)
        ).splitlines()
        assert out == ["X\t [e5]"], f"should not append for {text!r} (ascii={ascii_mode})"


def test_origin_can_be_disabled_via_config():
    out = run_lua(
        _origin_script(input_text="tsng-kio5", poj=False, ascii_mode=False, cap=False, enabled=False)
    ).splitlines()
    assert out == ["X\t [e5]"]


def test_full_romanization_return_commits_typed_romanization_directly():
    script = textwrap.dedent(
        r"""
        package.path = "lua/?.lua;" .. package.path

        local committed = ""
        local cleared = false
        local context = {
          input = "tsng-kio5",
          is_composing = function() return true end,
          has_menu = function() return true end,
          get_option = function(_, name)
            return name == "full_romanization"
          end,
          clear = function()
            cleared = true
          end,
          get_script_text = function() return "tsng-kio5" end,
        }
        local env = {
          engine = {
            context = context,
            schema = {
              config = {
                get_int = function() return 10 end,
                get_string = function() return "asdfghjkl;" end,
              },
            },
            commit_text = function(_, text)
              committed = text
            end,
          },
        }
        local key = {
          keycode = 13,
          release = function() return false end,
          repr = function() return "Return" end,
        }

        local commit = require("phah_taibun_commit")
        commit.init(env)
        local result = commit.func(key, env)

        print(result)
        print(committed)
        print(cleared)
        """
    )

    assert run_lua(script).splitlines() == ["1", "Tsng-kio\u0302", "true"]


def test_origin_selection_capitalizes_once_and_consumes_sentence_state():
    script = textwrap.dedent(
        r"""
        package.path = "lua/?.lua;" .. package.path

        local committed = ""
        local cleared = false
        local selected = {
          type = "origin",
          text = "tsng-kiô",
          comment = "\u{3014}羅馬字原文\u{3015}",
        }
        local context = {
          input = "tsng-kio5",
          is_composing = function() return true end,
          has_menu = function() return true end,
          get_option = function() return false end,
          get_selected_candidate = function() return selected end,
          clear = function() cleared = true end,
        }
        local env = {
          engine = {
            context = context,
            schema = {
              config = {
                get_int = function() return 10 end,
                get_string = function() return "asdfghjkl;" end,
              },
            },
            commit_text = function(_, text) committed = text end,
          },
        }
        local key = {
          keycode = 0x20,
          release = function() return false end,
          repr = function() return "space" end,
        }

        local commit = require("phah_taibun_commit")
        commit.init(env)
        local result = commit.func(key, env)

        print(result)
        print(committed)
        print(cleared)
        print(env.state.capitalize_next)
        """
    )

    assert run_lua(script).splitlines() == ["1", "Tsng-kiô", "true", "false"]


def test_lookup_uses_shared_tl_to_poj_converter():
    script = textwrap.dedent(
        r"""
        package.path = "lua/?.lua;" .. package.path
        package.loaded["phah_taibun_data"] = {
          tl_to_poj = function(text) return "shared:" .. text end,
          poj_fix_diacritics = function(text) return text end,
        }

        function Candidate(type, start, end_pos, text, comment)
          return {
            type = type,
            start = start,
            _end = end_pos,
            text = text,
            comment = comment,
            quality = 0,
          }
        end
        local yielded = {}
        function yield(cand)
          table.insert(yielded, cand)
        end
        local input = {
          iter = function()
            local done = false
            return function()
              if done then return nil end
              done = true
              return Candidate("table", 0, 5, "平", " [ping5]")
            end
          end
        }

        local lookup = require("phah_taibun_lookup")
        lookup.func(input, {})
        print(yielded[1].comment)
        """
    )

    assert run_lua(script).strip() == "[TL:ping5 POJ:shared:ping5]"


def test_help_lists_every_user_facing_shortcut():
    script = textwrap.dedent(
        r"""
        package.path = "lua/?.lua;" .. package.path
        function Candidate(_, _, _, text, comment)
          return { text = text, comment = comment }
        end
        local yielded = {}
        function yield(cand)
          table.insert(yielded, cand)
        end

        require("phah_taibun_help").func("vvh", { start = 0, _end = 3 }, {})
        for _, cand in ipairs(yielded) do
          print(cand.text)
        end
        """
    )

    keys = set(run_lua(script).splitlines())
    assert {
        "F4 / Ctrl+`",
        "Ctrl+Space",
        "Space",
        "Tab / Shift+Tab",
        "PageUp / PageDown",
        "[ / ]",
        "Shift+A-Z",
        "Enter",
        "\\",
        "'",
        "~",
        "`",
        "?",
        ";",
        "vvh",
        "vvjit",
        "vvsp",
    } <= keys


def test_word_identity_distinguishes_same_hanzi_different_reading():
    """Word identity = (hanji, reading) pair (PLAN 9-1D).

    重/tîng and 重/tāng are two different words and must never merge
    into one identity key.
    """
    script = textwrap.dedent(
        r"""
        package.path = "lua/?.lua;" .. package.path
        local data = require("phah_taibun_data")
        local a = data.word_identity("重", "ting5")
        local b = data.word_identity("重", "tang7")
        assert(a ~= b, "same hanji different readings must differ")
        print("OK")
        """
    )
    assert run_lua(script).strip() == "OK"


def test_word_identity_unifies_case_and_separators():
    """Case and hyphen/space are typography, not identity (PLAN 9-1D)."""
    script = textwrap.dedent(
        r"""
        package.path = "lua/?.lua;" .. package.path
        local data = require("phah_taibun_data")
        local a = data.word_identity("Uân-á", "Uan5-A2")
        local b = data.word_identity("uân á", "uan5 a2")
        assert(a == b, "case/hyphen variants must share identity")
        print("OK")
        """
    )
    assert run_lua(script).strip() == "OK"


def test_word_identity_never_collides_across_hanzi():
    """Different hanji with identical readings stay distinct."""
    script = textwrap.dedent(
        r"""
        package.path = "lua/?.lua;" .. package.path
        local data = require("phah_taibun_data")
        local a = data.word_identity("飯", "png7")
        local b = data.word_identity("夢", "png7")
        assert(a ~= b, "identical readings must not merge hanji")
        print("OK")
        """
    )
    assert run_lua(script).strip() == "OK"


def test_phrase_dedup_keeps_multiple_readings_of_same_char():
    """造詞查音 ;si: 同一個字的多個讀音必須全部列出。

    造詞去重的 identity 是 (字, 音) 對——seen 以 entry.text 當鍵會把
    同字第二讀音丟掉, 違反字典型態 (熟 siak8/sik8 兩讀都要出現)。
    """
    script = textwrap.dedent(
        r"""
        package.path = "lua/?.lua;" .. package.path

        function Memory(engine, schema)
          local entries = {
            { text = "熟", custom_code = "siak8" },
            { text = "熟", custom_code = "sik8" },
          }
          local i = 0
          return {
            dict_lookup = function() return true end,
            iter_dict = function()
              return function()
                i = i + 1
                return entries[i]
              end
            end,
          }
        end

        function Candidate(type, start, end_pos, text, comment)
          return { type=type, start=start, _end=end_pos, text=text,
                   comment=comment, quality=0 }
        end
        local yielded = {}
        function yield(c) table.insert(yielded, c) end

        local phrase = require("phah_taibun_phrase")
        local env = { engine = { schema = {} } }
        phrase.init(env)
        phrase.func(";si", { start = 0, _end = 3 }, env)
        for _, c in ipairs(yielded) do
          print(c.text .. "\t" .. (c.comment or ""))
        end
        """
    )
    out = run_lua(script).splitlines()
    assert out == ["熟\t [siak8]", "熟\t [sik8]"]


def _homophone_script(comment: str, rev_code: str) -> str:
    """Harness: commit single char 重 via space, then press '.

    The candidate comment carries the reading the user selected; env.rev
    simulates the reverse dictionary returning its first code first.
    Harness shape mirrors test_full_romanization_return_commits_….
    """
    return textwrap.dedent(
        rf"""
        package.path = "lua/?.lua;" .. package.path

        local composing = true
        local pushed = ""
        local selected = {{
          type = "table", start = 0, _end = 5,
          text = "重", comment = "{comment}", quality = 0,
        }}
        local context = {{
          input = "tang7",
          is_composing = function() return composing end,
          has_menu = function() return composing end,
          get_option = function() return false end,
          get_selected_candidate = function() return selected end,
          clear = function() end,
          push_input = function(_, s) pushed = s end,
        }}
        local env = {{
          engine = {{
            context = context,
            schema = {{ config = {{
              get_int = function() return 10 end,
              get_string = function() return "asdfghjkl;" end,
            }} }},
            commit_text = function() end,
          }},
        }}

        local commit = require("phah_taibun_commit")
        commit.init(env)
        -- init() resets env.rev (no ReverseLookup global here); inject after.
        env.rev = {{ lookup = function(_, text)
          if text == "重" then return "{rev_code}" end
          return nil
        end }}

        local space = {{
          keycode = 0x20,
          release = function() return false end,
          repr = function() return "space" end,
        }}
        commit.func(space, env)

        composing = false
        local apostrophe = {{
          keycode = 0x27,
          release = function() return false end,
          repr = function() return "apostrophe" end,
        }}
        local result = commit.func(apostrophe, env)

        print(result)
        print(pushed)
        """
    )


def test_homophone_uses_reading_of_committed_candidate():
    """V4: 單字確認後按 ', 同音選字必須重進「使用者選的那個音」。

    候選註解裡的編號調代碼 [tang7] 才是使用者實際選的讀音;
    反查詞典只會給第一個代碼 (ting5), 音不對。
    """
    out = run_lua(_homophone_script("[tang7]", "ting5 tang7")).splitlines()
    assert out == ["1", "tang7"]


def test_homophone_falls_back_to_reverse_lookup_without_code():
    """候選註解沒有編號調代碼 (last_code = nil) 時, ' 仍走反查路徑。"""
    out = run_lua(_homophone_script("", "ting5 tang7")).splitlines()
    assert out == ["1", "ting5"]
