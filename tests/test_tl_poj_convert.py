"""Tests for TL <-> POJ romanization conversion."""

from scripts.tl_poj_convert import poj_diacritics_to_tone_numbers, poj_to_tl, tl_to_poj


class TestTlToPoj:
    """Convert TL to POJ."""

    def test_ts_to_ch(self):
        assert tl_to_poj("tsit") == "chit"

    def test_tsh_to_chh(self):
        assert tl_to_poj("tshiu") == "chhiu"

    def test_tsh_before_ts(self):
        """tsh must be converted before ts to avoid double conversion."""
        assert tl_to_poj("tshit") == "chhit"

    def test_ing_to_eng(self):
        assert tl_to_poj("sing") == "seng"

    def test_ik_to_ek(self):
        assert tl_to_poj("sik") == "sek"

    def test_ua_to_oa(self):
        assert tl_to_poj("kua") == "koa"

    def test_ue_to_oe(self):
        assert tl_to_poj("kue") == "koe"

    def test_no_change(self):
        assert tl_to_poj("lang") == "lang"

    def test_multi_syllable(self):
        assert tl_to_poj("tsiah-png") == "chiah-png"

    def test_empty(self):
        assert tl_to_poj("") == ""


class TestTlToPojFormalGlyphs:
    """POJ formal glyphs: nn → ⁿ (U+207F), oo → o͘ (U+0358).

    Mirrors lua/phah_taibun_data.lua tl_to_poj so dictionary POJ output
    candidates (moe_poj) and the Lua commit path emit identical text.
    """

    def test_nasalization_nn_to_superscript(self):
        assert tl_to_poj("khuann3") == "khoaⁿ3"

    def test_nasalization_end_of_string(self):
        assert tl_to_poj("phinn") == "phiⁿ"

    def test_nasalization_with_h_coda(self):
        assert tl_to_poj("sannh4") == "saⁿh4"

    def test_syllabic_nng_keeps_nn(self):
        assert tl_to_poj("nng7") == "nng7"

    def test_toned_syllabic_nasal_keeps_nn(self):
        # the n carries the tone mark (nn̄g) — must not become ⁿ
        assert tl_to_poj("nn̄g") == "nn̄g"

    def test_oo_to_o_with_dot(self):
        assert tl_to_poj("too7") == "to͘7"

    def test_toned_oo_keeps_mark_on_first_o(self):
        assert tl_to_poj("tóo") == "tó͘"

    def test_capitalized_oo_to_o_with_dot(self):
        # 教典 KipSutian 烏 entries capitalize the first letter (Oo/Ôo);
        # formal POJ is O͘/Ô͘ (gate catch 2026-09-29, 4 stale rows)
        assert tl_to_poj("Oo") == "O͘"
        assert tl_to_poj("Ôo") == "Ô͘"

    def test_ing_before_digit_is_syllable_boundary(self):
        # digits carry the tone: ing/ik followed by a digit is a boundary
        # (lua uses [^a-z], not \b, for the same reason)
        assert tl_to_poj("ping2") == "peng2"

    def test_ik_before_digit_is_syllable_boundary(self):
        assert tl_to_poj("sik8") == "sek8"


class TestTlToPojCapitalized:
    """Capitalized syllables must convert too, preserving initial case."""

    def test_capitalized_ts(self):
        # POJ ui carries the mark on u (Tsuí → Chúi, not Chuí)
        assert tl_to_poj("Tsuí") == "Chúi"

    def test_capitalized_tsh(self):
        assert tl_to_poj("Tshiū-nâ") == "Chhiū-nâ"

    def test_capitalized_ing(self):
        assert tl_to_poj("Ing-ko") == "Eng-ko"

    def test_capitalized_ua(self):
        assert tl_to_poj("Uan-á") == "Oan-á"

class TestTlToPojDiacriticPlacement:
    """Diacritic input must land on the modern-POJ mark position, matching
    lua/phah_taibun_data.lua poj_fix_diacritics (狗公會曉學台語 §21 /
    張裕宏《白話字基本論》): syllable-final oa/oe mark the o; ui marks the u.
    The build pipeline emits moe_poj candidates through this path, so
    dictionary POJ text and the Lua commit path must render the same
    visible text and mark placement (Python emits NFC, Lua NFD —
    canonical-equivalent, not byte-identical)."""

    def test_open_oa_moves_mark_to_o(self):
        assert tl_to_poj("guā") == "gōa"

    def test_open_oe_moves_mark_to_o(self):
        assert tl_to_poj("huē") == "hōe"

    def test_open_oa_before_nasal_n_moves_mark_to_o(self):
        assert tl_to_poj("khuànn") == "khòaⁿ"

    def test_coda_oa_keeps_mark_on_a(self):
        assert tl_to_poj("kuán") == "koán"

    def test_triple_vowel_oai_keeps_mark_on_a(self):
        assert tl_to_poj("kuài") == "koài"

    def test_coda_oe_keeps_mark_on_e(self):
        assert tl_to_poj("gue̍h") == "goe̍h"

    def test_ui_moves_mark_to_u(self):
        assert tl_to_poj("uī") == "ūi"

    def test_iu_unchanged_marks_u(self):
        assert tl_to_poj("iû") == "iû"

    def test_numeric_input_unchanged(self):
        assert tl_to_poj("gua7 hue7 ui7") == "goa7 hoe7 ui7"

    def test_capitalized_open_oa(self):
        assert tl_to_poj("Guā") == "Gōa"

    def test_space_separated_syllables_fixed_too(self):
        """Lua format_romanization hyphen-joins before poj_fix_diacritics,
        so space-separated input must fix each syllable identically."""
        assert tl_to_poj("guā huē") == "gōa hōe"


class TestPojToTl:
    """Convert POJ to TL."""

    def test_ch_to_ts(self):
        assert poj_to_tl("chit") == "tsit"

    def test_chh_to_tsh(self):
        assert poj_to_tl("chhiu") == "tshiu"

    def test_chh_before_ch(self):
        """chh must be converted before ch to avoid double conversion."""
        assert poj_to_tl("chhit") == "tshit"

    def test_eng_to_ing(self):
        assert poj_to_tl("seng") == "sing"

    def test_ek_to_ik(self):
        assert poj_to_tl("sek") == "sik"

    def test_oa_to_ua(self):
        assert poj_to_tl("koa") == "kua"

    def test_oe_to_ue(self):
        assert poj_to_tl("koe") == "kue"

    def test_empty(self):
        assert poj_to_tl("") == ""


class TestPojToTlEnhanced:
    """Enhanced POJ to TL conversion for historical texts."""

    def test_existing_ch_to_ts(self):
        assert poj_to_tl("chit") == "tsit"

    def test_existing_chh_to_tsh(self):
        assert poj_to_tl("chhiu") == "tshiu"

    def test_existing_eng_to_ing(self):
        assert poj_to_tl("seng") == "sing"

    def test_existing_ek_to_ik(self):
        assert poj_to_tl("sek") == "sik"

    def test_existing_oa_to_ua(self):
        assert poj_to_tl("koa") == "kua"

    def test_existing_oe_to_ue(self):
        assert poj_to_tl("koe") == "kue"

    def test_superscript_n_to_nn(self):
        assert poj_to_tl("siⁿ") == "sinn"

    def test_o_dot_above_right_to_oo(self):
        assert poj_to_tl("o\u0358") == "oo"

    def test_ou_to_oo(self):
        assert poj_to_tl("kou") == "koo"

    def test_uppercase_to_lowercase(self):
        assert poj_to_tl("Chit") == "tsit"

    def test_preserve_hyphens(self):
        assert poj_to_tl("chiah-png") == "tsiah-png"

    def test_empty_string(self):
        assert poj_to_tl("") == ""


class TestPojDiacriticsToToneNumbers:
    """Convert POJ Unicode diacritics to TL tone numbers."""

    def test_acute_tone2(self):
        assert poj_diacritics_to_tone_numbers("á") == "a2"

    def test_grave_tone3(self):
        assert poj_diacritics_to_tone_numbers("à") == "a3"

    def test_circumflex_tone5(self):
        assert poj_diacritics_to_tone_numbers("â") == "a5"

    def test_macron_tone7(self):
        assert poj_diacritics_to_tone_numbers("ā") == "a7"

    def test_vertical_line_above_tone8(self):
        assert poj_diacritics_to_tone_numbers("a\u030d") == "a8"

    def test_word_with_diacritic(self):
        assert poj_diacritics_to_tone_numbers("lâng") == "lang5"

    def test_empty_string(self):
        assert poj_diacritics_to_tone_numbers("") == ""

    def test_no_diacritics(self):
        assert poj_diacritics_to_tone_numbers("lang") == "lang"
