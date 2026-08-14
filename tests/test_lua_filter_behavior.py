"""Behavior tests for the phah_taibun Lua filter."""

import subprocess
import textwrap
from pathlib import Path

ROOT = Path(__file__).parent.parent


def run_lua(script: str) -> str:
    result = subprocess.run(
        ["lua", "-"],
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


def test_hanlo_rules_preserve_multi_character_hanzi_candidate_when_syllable_is_lo():
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
    *, input_text: str, poj: bool, ascii_mode: bool, cap: bool, enabled: bool
) -> str:
    """Build a harness that runs phah_taibun_origin over one mocked Han candidate.

    format_input_romanization / capitalize_first are stubbed so the test exercises
    the FILTER logic (guards, ordering, label, flag plumbing), not the romanizer
    (which has its own tests above).
    """
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
              return Candidate("table", 0, 1, "X", " [e5]")
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
        _origin_script(
            input_text="tsng-kio5", poj=False, ascii_mode=False, cap=False, enabled=True
        )
    ).splitlines()
    assert out == ["X\t [e5]", "<tsng-kio5|poj=false>\t\u3014\u7f85\u99ac\u5b57\u539f\u6587\u3015"]


def test_origin_passes_poj_mode_and_capitalize_flag():
    out = run_lua(
        _origin_script(
            input_text="goa2-kio5", poj=True, ascii_mode=False, cap=True, enabled=True
        )
    ).splitlines()
    # poj flag forwarded to the romanizer; capitalize_next True -> capitalize_first applied
    assert out == ["X\t [e5]", "CAP:<goa2-kio5|poj=true>\t\u3014\u7f85\u99ac\u5b57\u539f\u6587\u3015"]


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
            _origin_script(
                input_text=text, poj=False, ascii_mode=ascii_mode, cap=False, enabled=True
            )
        ).splitlines()
        assert out == ["X\t [e5]"], f"should not append for {text!r} (ascii={ascii_mode})"


def test_origin_can_be_disabled_via_config():
    out = run_lua(
        _origin_script(
            input_text="tsng-kio5", poj=False, ascii_mode=False, cap=False, enabled=False
        )
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
