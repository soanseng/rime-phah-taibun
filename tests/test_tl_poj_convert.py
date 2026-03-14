"""Tests for TL <-> POJ romanization conversion."""

from scripts.tl_poj_convert import poj_to_tl, tl_to_poj


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
