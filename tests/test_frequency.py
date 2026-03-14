"""Tests for heuristic frequency weighting."""

from scripts.build_frequency import (
    assign_source_weight,
    compute_weights,
    load_corpus_frequencies,
    word_length_modifier,
)


class TestAssignSourceWeight:
    """Map data source names to base frequency weights."""

    def test_moe_weight(self):
        assert assign_source_weight("moe") == 1000

    def test_itaigi_weight(self):
        assert assign_source_weight("itaigi") == 800

    def test_taihoa_weight(self):
        assert assign_source_weight("taihoa") == 500

    def test_taijit_weight(self):
        assert assign_source_weight("taijit") == 200

    def test_unknown_source(self):
        assert assign_source_weight("unknown") == 100


class TestWordLengthModifier:
    """Adjust weight based on character count of hanlo text."""

    def test_single_char(self):
        assert word_length_modifier("食") == 0.8

    def test_two_chars(self):
        assert word_length_modifier("食飯") == 1.2

    def test_three_chars(self):
        assert word_length_modifier("食早頓") == 1.2

    def test_four_plus_chars(self):
        assert word_length_modifier("七月半鴨仔") == 0.6

    def test_mixed_hanlo_single_cjk(self):
        """Han-Lo mixed text: count only CJK characters for length."""
        assert word_length_modifier("ā好") == 0.8  # 1 CJK char

    def test_pure_romanization(self):
        assert word_length_modifier("tshit-thô") == 1.0


class TestComputeWeights:
    """Compute final weights combining source, length, and overlap."""

    def test_basic_weight(self):
        entries = [
            {"hanlo": "食飯", "rime_key": "tsiah png", "source": "itaigi"},
        ]
        result = compute_weights(entries)
        # base=800, length_mod=1.2 → 960
        assert result[0]["weight"] == 960

    def test_cross_source_bonus(self):
        entries = [
            {"hanlo": "食飯", "rime_key": "tsiah png", "source": "itaigi"},
            {"hanlo": "食飯", "rime_key": "tsiah png", "source": "taihoa"},
        ]
        result = compute_weights(entries)
        # Higher of (800, 500) = 800, length_mod=1.2 -> 960, overlap bonus x1.1 -> 1056
        assert result[0]["weight"] == 1056

    def test_preserves_all_fields(self):
        entries = [
            {"hanlo": "我", "rime_key": "gua", "source": "itaigi", "hoabun": "我"},
        ]
        result = compute_weights(entries)
        assert result[0]["hoabun"] == "我"


class TestLoadCorpusFrequencies:
    """Load corpus frequency TSV into a lookup dict."""

    def test_basic_load(self, tmp_path):
        freq_file = tmp_path / "freq.tsv"
        freq_file.write_text("gua2\t100\nbeh4\t50\n")
        result = load_corpus_frequencies(freq_file)
        assert result["gua2"] == 100
        assert result["beh4"] == 50

    def test_empty_file(self, tmp_path):
        freq_file = tmp_path / "freq.tsv"
        freq_file.write_text("")
        result = load_corpus_frequencies(freq_file)
        assert len(result) == 0

    def test_nonexistent_file(self, tmp_path):
        result = load_corpus_frequencies(tmp_path / "missing.tsv")
        assert len(result) == 0


class TestComputeWeightsWithCorpus:
    """Corpus frequency boost in compute_weights."""

    def test_corpus_boost(self):
        entries = [
            {"hanlo": "食飯", "rime_key": "tsiah png", "source": "itaigi", "kip_input": "tsiah8-png7"},
        ]
        corpus_freq = {"tsiah8-png7": 50}
        result = compute_weights(entries, corpus_freq=corpus_freq)
        result_no_corpus = compute_weights(entries)
        assert result[0]["weight"] > result_no_corpus[0]["weight"]

    def test_no_corpus_same_as_before(self):
        entries = [
            {"hanlo": "食飯", "rime_key": "tsiah png", "source": "itaigi"},
        ]
        result = compute_weights(entries)
        assert result[0]["weight"] == 960
