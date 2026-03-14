"""Tests for iCorpus frequency extraction."""

import io
from collections import Counter

from scripts.extract_icorpus_freq import count_frequencies, tokenize_tl_line, write_frequency_table


class TestTokenizeTlLine:
    """Tokenize a TL romanization line into words."""

    def test_basic_tokenize(self):
        tokens = tokenize_tl_line("gua2 beh4 khi3 tshit4-tho5")
        assert tokens == ["gua2", "beh4", "khi3", "tshit4-tho5"]

    def test_hyphenated_words_kept(self):
        """Hyphenated compounds are single tokens."""
        tokens = tokenize_tl_line("tsiah8-png7")
        assert tokens == ["tsiah8-png7"]

    def test_empty_line(self):
        assert tokenize_tl_line("") == []

    def test_strips_punctuation(self):
        tokens = tokenize_tl_line("gua2, beh4.")
        assert tokens == ["gua2", "beh4"]

    def test_skips_non_tl(self):
        """Skip tokens that are clearly not TL (e.g., English names)."""
        tokens = tokenize_tl_line("Obama toa7-seng3")
        assert "toa7-seng3" in tokens


class TestCountFrequencies:
    """Count word frequencies from corpus text."""

    def test_basic_count(self):
        text = "gua2 beh4 khi3\ngua2 ai3 li2\n"
        freq = count_frequencies(io.StringIO(text))
        assert freq["gua2"] == 2
        assert freq["beh4"] == 1

    def test_hyphenated_counted(self):
        text = "tsiah8-png7\ntsiah8-png7\ntsiah8-png7\n"
        freq = count_frequencies(io.StringIO(text))
        assert freq["tsiah8-png7"] == 3

    def test_empty_input(self):
        freq = count_frequencies(io.StringIO(""))
        assert len(freq) == 0


class TestWriteFrequencyTable:
    """Write frequency data to a simple TSV file."""

    def test_writes_sorted(self, tmp_path):
        freq = Counter({"gua2": 100, "beh4": 50, "tsiah8-png7": 75})
        outfile = tmp_path / "freq.tsv"
        write_frequency_table(freq, outfile)
        lines = outfile.read_text().splitlines()
        assert lines[0].startswith("gua2\t")
        assert "100" in lines[0]

    def test_empty_counter(self, tmp_path):
        outfile = tmp_path / "freq.tsv"
        write_frequency_table(Counter(), outfile)
        assert outfile.read_text() == ""
