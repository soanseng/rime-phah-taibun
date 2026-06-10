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
