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
