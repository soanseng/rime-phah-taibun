"""Behavior tests for the phah_taibun_symbols `` ` `` menu."""

import shutil
import subprocess
import textwrap
from pathlib import Path

ROOT = Path(__file__).parent.parent
LUA_EXECUTABLE = shutil.which("lua") or shutil.which("lua5.4") or "lua"

# 方音符號 = extended bopomofo (U+312A-312D) + Phofsit Jiping block (U+31A0-31BF).
FANGYIN_RANGES = ((0x312A, 0x312D), (0x31A0, 0x31BF))


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


def _fangyin_chars(text: str) -> list[str]:
    return [ch for ch in text if any(lo <= ord(ch) <= hi for lo, hi in FANGYIN_RANGES)]


HARNESS = textwrap.dedent(
    """
    package.path = "lua/?.lua;" .. package.path
    local symbols = require("phah_taibun_symbols")
    local seg = { start = 0, _end = 1 }
    local function run(input)
      local yielded = {}
      function Candidate(t, s, e, text, comment)
        return { text = text, comment = comment }
      end
      function yield(cand) table.insert(yielded, cand.text) end
      symbols.func(input, seg, {})
      return table.concat(yielded, "\\t")
    end
    print(run("`"))
    print(run("`11"))
    """
)


def test_backtick_menu_offers_no_fangyin() -> None:
    """` directory and zhuyin category must not offer fangyin symbols."""
    directory, zhuyin = run_lua(HARNESS).splitlines()

    assert not _fangyin_chars(directory), _fangyin_chars(directory)
    assert not _fangyin_chars(zhuyin), _fangyin_chars(zhuyin)


def test_backtick_menu_keeps_tone_marks_and_standard_zhuyin() -> None:
    """Tone marks and standard bopomofo stay selectable after fangyin removal."""
    directory, zhuyin = run_lua(HARNESS).splitlines()

    assert "á" in directory and "a̍" in directory, directory
    assert "ㄅ" in zhuyin and "ㄦ" in zhuyin and "˙" in zhuyin, zhuyin
