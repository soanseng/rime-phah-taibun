"""Tests for Khin-hoan POJ text extractor."""

from collections import Counter

from scripts.extract_pojbh import extract_pojbh_sentences


class TestPojToTlConversion:
    """POJ text is converted to TL before tokenization."""

    def test_poj_ch_becomes_tl_ts(self, tmp_path):
        """POJ 'ch' consonants are converted to TL 'ts'."""
        txt = tmp_path / "test.txt"
        txt.write_text("chi2-chit8\n", encoding="utf-8")
        sentences, freq = extract_pojbh_sentences(tmp_path)
        # "ch" → "ts", so chi2 → tsi2, chit8 → tsit8
        assert len(sentences) == 1
        assert "tsi2-tsit8" in sentences[0]

    def test_poj_chh_becomes_tl_tsh(self, tmp_path):
        """POJ 'chh' consonant cluster becomes TL 'tsh'."""
        txt = tmp_path / "test.txt"
        txt.write_text("chhui3\n", encoding="utf-8")
        sentences, freq = extract_pojbh_sentences(tmp_path)
        assert len(sentences) == 1
        assert "tshui3" in sentences[0]

    def test_poj_oa_becomes_tl_ua(self, tmp_path):
        """POJ 'oa' vowel becomes TL 'ua'."""
        txt = tmp_path / "test.txt"
        txt.write_text("hoa1\n", encoding="utf-8")
        sentences, freq = extract_pojbh_sentences(tmp_path)
        assert len(sentences) == 1
        assert "hua1" in sentences[0]


class TestUnicodePoj:
    """Unicode POJ characters (o͘, superscript n) are handled."""

    def test_superscript_n_to_nn(self, tmp_path):
        """Superscript n (U+207F) becomes nn."""
        txt = tmp_path / "test.txt"
        # saⁿ2 → sann2
        txt.write_text("sa\u207f2\n", encoding="utf-8")
        sentences, freq = extract_pojbh_sentences(tmp_path)
        assert len(sentences) == 1
        assert "sann2" in sentences[0]

    def test_o_dot_above_right_to_oo(self, tmp_path):
        """o followed by combining dot above right (U+0358) becomes oo."""
        txt = tmp_path / "test.txt"
        # o͘1 → oo1
        txt.write_text("o\u03581\n", encoding="utf-8")
        sentences, freq = extract_pojbh_sentences(tmp_path)
        assert len(sentences) == 1
        assert "oo1" in sentences[0]


class TestEmptyDirectory:
    """Empty directory returns empty results."""

    def test_empty_dir(self, tmp_path):
        sentences, freq = extract_pojbh_sentences(tmp_path)
        assert sentences == []
        assert len(freq) == 0


class TestMultipleFiles:
    """Multiple .txt files are processed."""

    def test_reads_all_txt_files(self, tmp_path):
        (tmp_path / "a.txt").write_text("lang5\n", encoding="utf-8")
        (tmp_path / "b.txt").write_text("lang5\n", encoding="utf-8")
        sentences, freq = extract_pojbh_sentences(tmp_path)
        assert len(sentences) == 2
        assert freq["lang5"] == 2

    def test_recursive_subdirectories(self, tmp_path):
        sub = tmp_path / "subdir"
        sub.mkdir()
        (sub / "deep.txt").write_text("goa2\n", encoding="utf-8")
        sentences, freq = extract_pojbh_sentences(tmp_path)
        assert len(sentences) == 1
        # goa2 → POJ oa→ua → gua2
        assert "gua2" in sentences[0]

    def test_frequency_counter_aggregates(self, tmp_path):
        (tmp_path / "a.txt").write_text("lang5 si7\n", encoding="utf-8")
        (tmp_path / "b.txt").write_text("lang5 bo5\n", encoding="utf-8")
        sentences, freq = extract_pojbh_sentences(tmp_path)
        assert freq["lang5"] == 2
        assert freq["si7"] == 1
        assert freq["bo5"] == 1

    def test_ignores_non_txt_files(self, tmp_path):
        (tmp_path / "data.csv").write_text("lang5\n", encoding="utf-8")
        sentences, freq = extract_pojbh_sentences(tmp_path)
        assert sentences == []
        assert len(freq) == 0
