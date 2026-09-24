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


def test_recommend_badged_candidate_outranks_same_quality_tie():
    """◆ 推薦字必須贏過同品質同音的字典字 (伊=衣 同 1064)。

    徽章只改 comment 是顯示用的——librime filter 不會依 .quality 重排,
    所以推薦字要實際重排到最前 (two-pass reorder)。
    """
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
        local yielded = {}
        function yield(cand)
          table.insert(yielded, cand)
        end

        phah_taibun_data = {
          check_lkk_recommend = function(text)
            if text == "伊" then return true, false end
            return false, false
          end,
          check_moe700 = function() return false end,
        }

        local filter = require("phah_taibun_recommend")
        local env = {
          name_space = "",
          engine = { schema = { config = {
            get_bool = function() return true end,
          } } },
        }
        filter.init(env)

        local items = {
          Candidate("table", 0, 2, "衣", " [i1]"),
          Candidate("table", 0, 2, "伊", " [i1]"),
        }
        items[1].quality = 1064
        items[2].quality = 1064
        local pos = 0
        local input = {
          iter = function()
            return function()
              pos = pos + 1
              return items[pos]
            end
          end,
        }

        filter.func(input, env)

        for _, cand in ipairs(yielded) do
          print(cand.text .. "\t" .. cand.comment)
        end
        """
    )

    assert run_lua(script).splitlines() == ["伊\t ◆ [i1]", "衣\t [i1]"]


def test_recommend_lkk_badge_outranks_moe700_badge_at_equal_quality():
    """加成依來源分級: LKK (B_LKK) > 教育部700 (B_MOE)。

    同品質下 moe700 字先進串流也照樣輸給 LKK 推薦字——兩者都用 ◆,
    但 LKK 是第一目標, 加成較高。
    """
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
        local yielded = {}
        function yield(cand)
          table.insert(yielded, cand)
        end

        phah_taibun_data = {
          check_lkk_recommend = function(text)
            if text == "伊" then return true, false end
            return false, false
          end,
          check_moe700 = function(text) return text == "醫" end,
        }

        local filter = require("phah_taibun_recommend")
        local env = {
          name_space = "",
          engine = { schema = { config = {
            get_bool = function() return true end,
          } } },
        }
        filter.init(env)

        -- Incoming order: moe700 candidate first.
        local items = {
          Candidate("table", 0, 1, "醫", " [i1]"),
          Candidate("table", 0, 1, "伊", " [i1]"),
        }
        items[1].quality = 1064
        items[2].quality = 1064
        local pos = 0
        local input = {
          iter = function()
            return function()
              pos = pos + 1
              return items[pos]
            end
          end,
        }

        filter.func(input, env)

        for _, cand in ipairs(yielded) do
          print(cand.text .. "\t" .. cand.comment)
        end
        """
    )

    assert run_lua(script).splitlines() == ["伊\t ◆ [i1]", "醫\t ◆ [i1]"]


def test_recommend_badged_candidate_moves_forward_at_most_nudge_slots():
    """有界位移: 徽章把候選往前挪固定格數(LKK 3、moe700 1)。

    舊加法排序(quality + B)在引擎實測會退化成徽章置頂、淹沒候選區
    (kio-tiann: 橋 被擠出可見窗); 位移保證任何徽章最多前進 3 格。
    LKK(3) 在平手時贏過 moe700(1): 同格時依原順序, 但位移差距讓
    伊◆(LKK) 越過 醫◆(moe700)。
    """
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
        local yielded = {}
        function yield(cand)
          table.insert(yielded, cand)
        end

        phah_taibun_data = {
          check_lkk_recommend = function(text)
            if text == "伊" then return true, false end
            return false, false
          end,
          check_moe700 = function(text)
            if text == "醫" then return true end
            return false
          end,
        }

        local filter = require("phah_taibun_recommend")
        local env = {
          name_space = "",
          engine = { schema = { config = {
            get_bool = function() return true end,
          } } },
        }
        filter.init(env)

        -- Incoming: 甲(pos1) 醫◆moe(pos2) 衣(pos3) 乙(pos4) 伊◆LKK(pos5) 丙(pos6)
        -- nudged slots: 甲1 醫1 衣3 乙4 伊2 丙6 -> order: 甲,醫,伊,衣,乙,丙
        local names = { "甲", "醫", "衣", "乙", "伊", "丙" }
        local items = {}
        for i, n in ipairs(names) do
          items[i] = Candidate("table", 0, 1, n, " [" .. n .. "]")
        end
        local pos = 0
        local input = {
          iter = function()
            return function()
              pos = pos + 1
              return items[pos]
            end
          end,
        }

        filter.func(input, env)

        for _, cand in ipairs(yielded) do
          print(cand.text)
        end
        """
    )

    # 伊 rises 5->3 (LKK nudge 3, tie-lost to 衣's earlier order at slot 3?
    # slots: 甲=1, 醫=2-1=1(tie with 甲, order 1<2 -> 甲,醫), 伊=5-3=2,
    # 衣=3, 乙=4, 丙=6 -> final: 甲, 醫, 伊, 衣, 乙, 丙
    assert run_lua(script).splitlines() == ["甲", "醫", "伊", "衣", "乙", "丙"]


def test_recommend_no_badges_is_byte_identical_pass_through():
    """無推薦字時必須逐位元組照原樣通過: 順序、comment、物件都不變。"""
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
        local yielded = {}
        function yield(cand)
          table.insert(yielded, cand)
        end

        phah_taibun_data = {
          check_lkk_recommend = function() return false, false end,
          check_moe700 = function() return false end,
        }

        local filter = require("phah_taibun_recommend")
        local env = {
          name_space = "",
          engine = { schema = { config = {
            get_bool = function() return true end,
          } } },
        }
        filter.init(env)

        local items = {
          Candidate("table", 0, 2, "衣", " [i1] 估詞"),
          Candidate("table", 0, 2, "醫", " [i1]"),
        }
        items[1].quality = 1064
        items[2].quality = 1064
        local pos = 0
        local input = {
          iter = function()
            return function()
              pos = pos + 1
              return items[pos]
            end
          end,
        }

        filter.func(input, env)

        for i, cand in ipairs(yielded) do
          -- Same object identity, not a re-wrapped copy.
          print(i .. "\t" .. tostring(cand == items[i]) .. "\t"
            .. cand.text .. "\t" .. cand.comment)
        end
        """
    )

    assert run_lua(script).splitlines() == [
        "1\ttrue\t衣\t [i1] 估詞",
        "2\ttrue\t醫\t [i1]",
    ]


def test_recommend_badge_reorders_only_the_badged_candidate():
    """徽章只把該候選提到最前, 其餘無徽章候選維持原入流順序。"""
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
        local yielded = {}
        function yield(cand)
          table.insert(yielded, cand)
        end

        phah_taibun_data = {
          check_lkk_recommend = function(text)
            if text == "伊" then return true, false end
            return false, false
          end,
          check_moe700 = function() return false end,
        }

        local filter = require("phah_taibun_recommend")
        local env = {
          name_space = "",
          engine = { schema = { config = {
            get_bool = function() return true end,
          } } },
        }
        filter.init(env)

        local items = {
          Candidate("table", 0, 1, "甲", " [ka1]"),
          Candidate("table", 0, 1, "衣", " [i1]"),
          Candidate("table", 0, 1, "伊", " [i1]"),
          Candidate("table", 0, 1, "乙", " [it1]"),
        }
        for _, cand in ipairs(items) do
          cand.quality = 1064
        end
        local pos = 0
        local input = {
          iter = function()
            return function()
              pos = pos + 1
              return items[pos]
            end
          end,
        }

        filter.func(input, env)

        for _, cand in ipairs(yielded) do
          print(cand.text .. "\t" .. cand.comment)
        end
        """
    )

    assert run_lua(script).splitlines() == [
        "伊\t ◆ [i1]",
        "甲\t [ka1]",
        "衣\t [i1]",
        "乙\t [it1]",
    ]


def test_lighttone_generated_variant_comes_immediately_after_parent():
    """輕聲變體 (予--人) 必須緊跟在母詞 (予人) 後面, 絕不搶在前頭。

    逐段選字流程下母詞先出現、變體緊跟其後, 是輕聲候選的基本排序。
    """
    script = textwrap.dedent(
        r"""
        package.path = "lua/?.lua;" .. package.path
        package.loaded["phah_taibun_data"] = {}
        rime_api = {
          get_user_data_dir = function() return "tests/fixtures" end,
          get_shared_data_dir = function() return "tests/fixtures" end,
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

        local filter = require("phah_taibun_lighttone")
        filter.init({})

        local items = {
          Candidate("table", 0, 8, "予人", " [u7 lang5]"),
          Candidate("table", 8, 14, "囡仔", " [gin2 na2]"),
        }
        local pos = 0
        local input = {
          iter = function()
            return function()
              pos = pos + 1
              return items[pos]
            end
          end,
        }

        filter.func(input, {})

        for _, cand in ipairs(yielded) do
          print(cand.text)
        end
        """
    )

    assert run_lua(script).splitlines() == ["予人", "予--人", "囡仔"]


def test_lighttone_stream_variant_matched_to_parent_by_collapsed_text():
    """串流裡既有的 -- 詞條 (詞典輕聲詞) 也要配對到母詞後面。

    詞典自帶的輕聲詞 (予--人) 若照詞典順序排在母詞 (予人) 前面,
    會搶走本該屬於母詞的位置; 收合文字 (去 --) + 位置相同即配對,
    yield 母詞後緊跟其變體, 且與動態產生的變體去重不重複出現。
    """
    script = textwrap.dedent(
        r"""
        package.path = "lua/?.lua;" .. package.path
        package.loaded["phah_taibun_data"] = {}
        rime_api = {
          get_user_data_dir = function() return "tests/fixtures" end,
          get_shared_data_dir = function() return "tests/fixtures" end,
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

        local filter = require("phah_taibun_lighttone")
        filter.init({})

        -- Stream order: dictionary light-tone form first, parent after.
        local items = {
          Candidate("table", 0, 8, "予--人", " [u7--lang5]"),
          Candidate("table", 0, 8, "予人", " [u7 lang5]"),
        }
        local pos = 0
        local input = {
          iter = function()
            return function()
              pos = pos + 1
              return items[pos]
            end
          end,
        }

        filter.func(input, {})

        for _, cand in ipairs(yielded) do
          print(cand.text)
        end
        """
    )

    assert run_lua(script).splitlines() == ["予人", "予--人"]


def test_lighttone_parentless_variant_is_demoted_to_end():
    """配對不到母詞的 -- 詞條必須降到最後, 不得壓過其他候選。

    生產症狀: 俾--人 (無俾人母詞在串流中) 排在予人前面。
    """
    script = textwrap.dedent(
        r"""
        package.path = "lua/?.lua;" .. package.path
        package.loaded["phah_taibun_data"] = {}
        rime_api = {
          get_user_data_dir = function() return "tests/fixtures" end,
          get_shared_data_dir = function() return "tests/fixtures" end,
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

        local filter = require("phah_taibun_lighttone")
        filter.init({})

        local items = {
          Candidate("table", 0, 8, "俾--人", " [pi7--lang5]"),
          Candidate("table", 8, 15, "予人", " [u7 lang5]"),
        }
        local pos = 0
        local input = {
          iter = function()
            return function()
              pos = pos + 1
              return items[pos]
            end
          end,
        }

        filter.func(input, {})

        for _, cand in ipairs(yielded) do
          print(cand.text)
        end
        """
    )

    assert run_lua(script).splitlines() == ["予人", "予--人", "俾--人"]


def test_recommend_badge_cannot_cross_beyond_nudge_window():
    """有界位移的邊界: 徽章候選最多前進 NUDGE 格。

    伊◆LKK 在 pos5(nudge 3 -> slot 2)追不上 slot1 的領先者——加法版
    「徽章全置頂」在此退化(淹沒候選區的機制); 位移版保證領先者守住。
    """
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
        local yielded = {}
        function yield(cand)
          table.insert(yielded, cand)
        end
        phah_taibun_data = {
          check_lkk_recommend = function(text)
            if text == "伊" then return true, false end
            return false, false
          end,
          check_moe700 = function() return false end,
        }
        local filter = require("phah_taibun_recommend")
        local env = {
          name_space = "",
          engine = { schema = { config = { get_bool = function() return true end } } },
        }
        filter.init(env)
        -- 甲(pos1) 乙(pos2) 丙(pos3) 丁(pos4) 伊◆LKK(pos5): slot2 追不上 slot1
        local names = { "甲", "乙", "丙", "丁", "伊" }
        local items = {}
        for i, n in ipairs(names) do
          items[i] = Candidate("table", 0, 1, n, " [" .. n .. "]")
        end
        local pos = 0
        local input = {
          iter = function()
            return function()
              pos = pos + 1
              return items[pos]
            end
          end,
        }
        filter.func(input, env)
        for _, cand in ipairs(yielded) do
          print(cand.text)
        end
        """
    )
    assert run_lua(script).splitlines() == ["甲", "乙", "伊", "丙", "丁"]


def test_lighttone_precomposed_rule_suffix_matches_numeric_comment(tmp_path):
    """Identical lookup key: NFC rule suffix "--lâng" must generate the
    variant for a numeric candidate " [u7 lang5]" exactly like its ASCII
    twin "--lang" does (production rules JSON is precomposed UTF-8;
    hexdump-verified — before the normalizer this suffix never matched).
    """
    (tmp_path / "lighttone_rules.json").write_text(
        '[\n {"tl": "--lâng", "hanzi": "人", "rule": "輕聲"}\n]\n',
        encoding="utf-8",
    )
    script = textwrap.dedent(
        r"""
        package.path = "lua/?.lua;" .. package.path
        package.loaded["phah_taibun_data"] = {}
        rime_api = {
          get_user_data_dir = function() return __TMP__ end,
          get_shared_data_dir = function() return __TMP__ end,
        }
        function Candidate(type, start, end_pos, text, comment)
          return { type = type, start = start, _end = end_pos, text = text, comment = comment, quality = 0 }
        end
        local yielded = {}
        function yield(cand) table.insert(yielded, cand) end
        local filter = require("phah_taibun_lighttone")
        filter.init({})
        local items = { Candidate("table", 0, 8, "予人", " [u7 lang5]") }
        local pos = 0
        local input = {
          iter = function()
            return function()
              pos = pos + 1
              return items[pos]
            end
          end,
        }
        filter.func(input, {})
        for _, cand in ipairs(yielded) do
          print(cand.text .. "|" .. (cand.comment or ""))
        end
        """
    ).replace("__TMP__", '"' + str(tmp_path).replace("\\", "\\\\") + '"')
    result = subprocess.run(["lua", "-"], input=script, capture_output=True, text=True, cwd=".")
    assert result.returncode == 0, result.stderr
    lines = result.stdout.strip().splitlines()
    assert len(lines) == 2, f"precomposed rule must generate the variant: {lines}"
    assert lines[0].startswith("予人|")
    assert "--" in lines[1] and "人" in lines[1], f"variant text: {lines[1]}"


def test_recommend_badges_cannot_flood_candidate_window():
    """kio-tiann 生產事件回歸: 深層 ★ 變體不得淹沒候選窗。

    引擎實測(2026-09-24): 加法排序讓可見窗 10 席全被 ★ 輕聲變體佔據、
    橋 被擠出。位移版: 領先者守住第一, 深層變體至多前進 3 格。
    """
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
        local yielded = {}
        function yield(cand)
          table.insert(yielded, cand)
        end
        phah_taibun_data = {
          check_lkk_recommend = function(text)
            if text:find("^變") then return false, true end
            return false, false
          end,
          check_moe700 = function() return false end,
        }
        local filter = require("phah_taibun_recommend")
        local env = {
          name_space = "",
          engine = { schema = { config = { get_bool = function() return true end } } },
        }
        filter.init(env)
        -- SYNTHETIC geometry: badges sit behind a plain block. Engine
        -- pre-filter stream positions were NOT measured (smoke output is
        -- post-filter); this pins the bounded-displacement contract itself.
        local plain = { "甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸" }
        local items = {}
        for i, n in ipairs(plain) do
          items[i] = Candidate("table", 0, 1, n, " [x" .. i .. "]")
        end
        for i = 1, 12 do
          items[#items + 1] = Candidate("table", 0, 1, "變" .. i, " [v" .. i .. "]")
        end
        local pos = 0
        local input = {
          iter = function()
            return function()
              pos = pos + 1
              return items[pos]
            end
          end,
        }
        filter.func(input, env)
        for _, cand in ipairs(yielded) do
          print(cand.text)
        end
        """
    )
    lines = run_lua(script).splitlines()
    top5 = lines[:5]
    assert lines[0] == "甲", f"leader must hold slot 1: {lines[:3]}"
    assert sum(1 for t in top5 if not t.startswith("變")) >= 4, f"top-5 must stay mostly unbadged: {top5}"
    assert "變12" not in lines[:10], f"deep variant must stay out of the window: {lines[:10]}"


def test_recommend_badge_cannot_displace_sentence_candidate():
    """sentence 錨定: 徽章詞不得越過整句組字候選 (type="sentence")。

    v0.9.2 CI 引擎實測: 整句輸入時 LKK ◆ 短詞(是按怎)被 nudge 3 格推到
    組字候選之上——全羅空白上屏因此只出第一詞、句子語料 top-1 命中率
    0.8→0.3。組字候選是引擎斷詞的結果, 任何徽章位移都不得蓋過它;
    錨定之下徽章仍可在 sentence 之後的區間內前進(半格帶)。
    """
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
        local yielded = {}
        function yield(cand)
          table.insert(yielded, cand)
        end

        phah_taibun_data = {
          check_lkk_recommend = function(text)
            if text == "是按怎" then return true, false end
            return false, false
          end,
          check_moe700 = function(text)
            return false
          end,
        }

        local filter = require("phah_taibun_recommend")
        local env = {
          name_space = "",
          engine = { schema = { config = {
            get_bool = function() return true end,
          } } },
        }
        filter.init(env)

        -- Incoming: 整句(sentence, pos1) 是按怎◆LKK(pos2) 人退(pos3) 詞組(pos4)
        -- 是按怎 nudge 3 -> raw slot -1; sentence anchor clamps it behind the
        -- sentence (slot 1.5) but still ahead of its old neighbors.
        local items = {
          Candidate("sentence", 0, 9, "是按怎人退酒了後", " [si7-an2-tsuann2]"),
          Candidate("phrase", 0, 3, "是按怎", " [si7-an2-tsuann2]"),
          Candidate("table", 3, 5, "人退", " [lang5-the3]"),
          Candidate("table", 5, 9, "酒了後", " [tsiu2-liau2-au7]"),
        }
        local pos = 0
        local input = {
          iter = function()
            return function()
              pos = pos + 1
              return items[pos]
            end
          end,
        }

        filter.func(input, env)
        for _, cand in ipairs(yielded) do
          print(cand.type .. ":" .. cand.text)
        end
        """
    )
    lines = run_lua(script).splitlines()
    assert lines[0] == "sentence:是按怎人退酒了後", f"sentence must hold top: {lines}"
    assert lines[1] == "phrase:是按怎", f"badged word follows sentence: {lines}"
    assert lines[2:] == ["table:人退", "table:酒了後"], f"rest keeps order: {lines}"


def test_recommend_lighttone_variant_is_not_the_sentence_anchor():
    """-- 變體(type=sentence 的輕聲衍生形)不得作為 sentence 錨。

    telex zhiah8 引擎實測: 輕聲變體 飼--啊 複製母詞(組字候選)的
    type 與 preedit, 又被 ◆ nudge 到頂——錨定若以它為準, 帶徽章的詞
    就能越過「真正的組字候選」。錨必須是沒有 -- 的組字句。
    """
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
        local yielded = {}
        function yield(cand)
          table.insert(yielded, cand)
        end

        phah_taibun_data = {
          check_lkk_recommend = function(text)
            if text == "飼--啊" or text == "詞B" then return true, false end
            return false, false
          end,
          check_moe700 = function(text)
            return false
          end,
        }

        local filter = require("phah_taibun_recommend")
        local env = {
          name_space = "",
          engine = { schema = { config = {
            get_bool = function() return true end,
          } } },
        }
        filter.init(env)

        -- Incoming: 變體飼--啊(◆, pos1) 真組字句(pos2) 詞A(pos3) 詞B◆(pos4)
        -- 錨=真組字句(order 2): 詞B nudge 後 clamp 到 2.5, 越過詞A 但
        -- 不越過組字句; 變體本身是 sentence 型不位移, 留在原位。
        local items = {
          Candidate("sentence", 0, 9, "飼--啊", " [tshi7--ah8]"),
          Candidate("sentence", 0, 9, "飼啊", " [tshi7 ah8]"),
          Candidate("table", 0, 3, "詞A", " [a]"),
          Candidate("table", 0, 3, "詞B", " [b]"),
        }
        local pos = 0
        local input = {
          iter = function()
            return function()
              pos = pos + 1
              return items[pos]
            end
          end,
        }

        filter.func(input, env)
        for _, cand in ipairs(yielded) do
          print(cand.text)
        end
        """
    )
    lines = run_lua(script).splitlines()
    assert lines == ["飼--啊", "飼啊", "詞B", "詞A"], lines


def test_recommend_lighttone_variant_gets_no_badge_no_nudge():
    """-- 變體不做徽章位移: 排序由 lighttone 貼母詞, 徽章只屬於詞身份。

    telex zhiah8 的選單母詞(飼鴨)是 table 型, 沒有 sentence 錨可依——
    變體一旦可被 ◆ nudge 就會帶著組字 preedit 搶到頂(zhi ah8 分裂)。
    變體是衍生顯示形, 不得與母詞競爭排序(與 W3 沉底設計同向)。
    """
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
        local yielded = {}
        function yield(cand)
          table.insert(yielded, cand)
        end

        phah_taibun_data = {
          check_lkk_recommend = function(text)
            if text == "飼--啊" then return true, false end
            return false, false
          end,
          check_moe700 = function(text)
            return false
          end,
        }

        local filter = require("phah_taibun_recommend")
        local env = {
          name_space = "",
          engine = { schema = { config = {
            get_bool = function() return true end,
          } } },
        }
        filter.init(env)

        local items = {
          Candidate("table", 0, 3, "詞A", " [a]"),
          Candidate("table", 0, 9, "飼--啊", " [tshi7--ah8]"),
          Candidate("table", 0, 5, "詞B", " [b]"),
          Candidate("table", 0, 5, "詞C", " [c]"),
        }
        local pos = 0
        local input = {
          iter = function()
            return function()
              pos = pos + 1
              return items[pos]
            end
          end,
        }

        filter.func(input, env)
        for _, cand in ipairs(yielded) do
          print((cand.comment or "") .. "|" .. cand.text)
        end
        """
    )
    lines = run_lua(script).splitlines()
    # Order unchanged AND the variant carries no injected badge prefix.
    texts = [row.split("|")[1] for row in lines]
    assert texts == ["詞A", "飼--啊", "詞B", "詞C"], lines
    variant_line = next(row for row in lines if row.endswith("飼--啊"))
    assert "◆" not in variant_line.split("|")[0], variant_line
