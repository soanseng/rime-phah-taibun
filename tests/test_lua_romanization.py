"""Romanization behavior tests for the real Lua core (phah_taibun_data).

Covers tone-mark placement — TL per the MOE Tâi-lô handbook, POJ per the
standard Pe̍h-ōe-jī convention ("iu"/"ui" mark the u; open-syllable "oa"/"oe"
mark the o; vowel-less syllables mark the nasal consonant, e.g. mn̂g) — and
the POJ formal glyphs (ⁿ, o͘) in tl_to_poj. Drives the actual Lua modules
via a plain-Lua subprocess like test_lua_learn.py.
"""

import shutil
import subprocess
import textwrap
from pathlib import Path

ROOT = Path(__file__).parent.parent
LUA_EXECUTABLE = shutil.which("lua") or shutil.which("lua5.4") or "lua"

PREAMBLE = textwrap.dedent(
    r"""
    package.path = "lua/?.lua;" .. package.path
    local data = require("phah_taibun_data")
    local function eq(name, got, want)
      assert(got == want,
             name .. ": got " .. got .. " (want " .. want .. ")")
    end
    """
)


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
    return result.stdout.strip()


def test_syllabic_nasals_mark_the_n_of_ng():
    """Vowel-less syllables mark ng's n (mn̂g), never the onset m; bare m → m̄.

    POJ convention: "If the syllable has no vowel, mark the nasal
    consonant: m̄, ǹg, mn̂g" (amoytainan.wordpress.com, POJ tone markings).
    """
    out = run_lua(
        PREAMBLE
        + textwrap.dedent(
            r"""
        eq("mng5 門", data.format_romanization("mng5"), "mn\u{0302}g")
        eq("mng7 問", data.format_romanization("mng7"), "mn\u{0304}g")
        eq("nng7 卵", data.format_romanization("nng7"), "nn\u{0304}g")
        eq("ng5 黃", data.format_romanization("ng5"), "n\u{0302}g")
        eq("m7 毋", data.format_romanization("m7"), "m\u{0304}")
        print("OK")
        """
        )
    )
    assert out == "OK"


def test_tl_to_poj_emits_formal_glyphs():
    """nn → ⁿ (nng guarded), oo → o͘ (tone mark stays on the first o)."""
    out = run_lua(
        PREAMBLE
        + textwrap.dedent(
            r"""
        eq("nasal + h coda", data.tl_to_poj("sannh4"), "sa\u{207F}h4")
        eq("syllabic nng keeps nn", data.tl_to_poj("nng7"), "nng7")
        eq("toned nn̄g keeps nn", data.tl_to_poj("nn\u{0304}g"), "nn\u{0304}g")
        eq("nasalization", data.tl_to_poj("khuann3"), "khoa\u{207F}3")
        eq("toned oo → tó͘", data.tl_to_poj("t\u{0301}oo"), "t\u{0301}o\u{0358}")
        print("OK")
        """
        )
    )
    assert out == "OK"


def test_poj_diphthong_tone_mark_repositioning():
    """POJ placement: oa/oe open (and +ⁿ) mark the o; codas keep a/e;
    ui/iu both mark the u; syllabic nasals mark the nasal (mn̂g)."""
    out = run_lua(
        PREAMBLE
        + textwrap.dedent(
            r"""
        local pj = function(num)
          return data.poj_fix_diacritics(
            data.format_romanization(data.tl_to_poj(num)))
        end
        eq("gōa (open)", pj("gua7"), "go\u{0304}a")
        eq("koán (coda n → a)", pj("kuan2"), "koa\u{0301}n")
        eq("khòaⁿ (nasalization → o)", pj("khuann3"), "kho\u{0300}a\u{207F}")
        eq("hōe (open)", pj("ue7"), "o\u{0304}e")
        eq("goe̍h (coda h → e)", pj("gueh8"), "goe\u{030D}h")
        eq("chúi (ui → u)", pj("tsui2"), "chu\u{0301}i")
        eq("khiû (iu → u, same as TL)", pj("khiu5"), "khiu\u{0302}")
        eq("mn̂g (POJ too)", pj("mng5"), "mn\u{0302}g")
        print("OK")
        """
        )
    )
    assert out == "OK"
