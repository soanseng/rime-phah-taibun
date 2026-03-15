"""Tests for phrase builder: reverse index, bigram extraction, and entry generation."""

from scripts.build_phrases import (
    _strip_tones,
    build_phrases_from_files,
    build_reverse_index,
    extract_bigrams,
    generate_phrase_entries,
)


class TestStripTones:
    def test_basic(self):
        assert _strip_tones("gua2") == "gua"

    def test_hyphenated(self):
        assert _strip_tones("tsiah8-png7") == "tsiah-png"

    def test_no_tones(self):
        assert _strip_tones("beh") == "beh"

    def test_multiple_tones(self):
        assert _strip_tones("tua7-lang5") == "tua-lang"

    def test_empty(self):
        assert _strip_tones("") == ""


class TestBuildReverseIndex:
    def test_basic_index(self):
        lines = [
            "我\tgua\t900",
            "袂\tbeh\t800",
            "曉\thiau\t700",
        ]
        idx = build_reverse_index(lines)
        assert "gua" in idx
        assert idx["gua"] == [{"text": "我", "weight": 900}]
        assert idx["beh"] == [{"text": "袂", "weight": 800}]
        assert idx["hiau"] == [{"text": "曉", "weight": 700}]

    def test_ambiguous_keys(self):
        lines = [
            "青\ttshenn\t500",
            "生\ttshenn\t800",
            "星\ttshenn\t300",
        ]
        idx = build_reverse_index(lines)
        assert len(idx["tshenn"]) == 3
        # sorted by weight descending
        assert idx["tshenn"][0]["text"] == "生"
        assert idx["tshenn"][1]["text"] == "青"
        assert idx["tshenn"][2]["text"] == "星"

    def test_skips_yaml_header(self):
        lines = [
            "---",
            "name: phah_taibun",
            "version: \"0.1.0\"",
            "sort: by_weight",
            "...",
            "我\tgua\t900",
        ]
        idx = build_reverse_index(lines)
        assert "gua" in idx
        assert len(idx) == 1


class TestExtractBigrams:
    def test_basic(self):
        sentences = ["gua2 beh4 khi3"]
        bigrams = extract_bigrams(sentences)
        assert bigrams[("gua", "beh")] == 1
        assert bigrams[("beh", "khi")] == 1

    def test_strips_tones(self):
        sentences = ["gua2 beh4"]
        bigrams = extract_bigrams(sentences)
        assert ("gua", "beh") in bigrams
        assert ("gua2", "beh4") not in bigrams

    def test_counts_across_sentences(self):
        sentences = ["gua2 beh4", "gua2 beh4", "gua2 beh4"]
        bigrams = extract_bigrams(sentences)
        assert bigrams[("gua", "beh")] == 3

    def test_single_word(self):
        sentences = ["gua2"]
        bigrams = extract_bigrams(sentences)
        assert len(bigrams) == 0

    def test_empty(self):
        bigrams = extract_bigrams([])
        assert len(bigrams) == 0

    def test_empty_string(self):
        bigrams = extract_bigrams([""])
        assert len(bigrams) == 0


class TestGeneratePhraseEntries:
    def _make_reverse_index(self):
        return {
            "gua": [{"text": "我", "weight": 900}],
            "beh": [{"text": "袂", "weight": 800}],
            "khi": [{"text": "去", "weight": 700}],
        }

    def test_basic_phrase(self):
        from collections import Counter
        from math import log10

        bigrams = Counter({("gua", "beh"): 10})
        idx = self._make_reverse_index()
        entries = generate_phrase_entries(bigrams, idx, set(), min_count=5, base_weight=500)
        assert len(entries) == 1
        assert entries[0]["hanlo"] == "我袂"
        assert entries[0]["rime_key"] == "gua beh"
        expected_weight = int(500 * (1.0 + log10(1 + 10) * 0.3))
        assert entries[0]["weight"] == expected_weight

    def test_skips_existing(self):
        from collections import Counter

        bigrams = Counter({("gua", "beh"): 10})
        idx = self._make_reverse_index()
        existing = {("我袂", "gua beh")}
        entries = generate_phrase_entries(bigrams, idx, existing, min_count=5)
        assert len(entries) == 0

    def test_skips_below_threshold(self):
        from collections import Counter

        bigrams = Counter({("gua", "beh"): 3})
        idx = self._make_reverse_index()
        entries = generate_phrase_entries(bigrams, idx, set(), min_count=5)
        assert len(entries) == 0

    def test_skips_unknown_words(self):
        from collections import Counter

        bigrams = Counter({("gua", "unknown"): 10})
        idx = self._make_reverse_index()
        entries = generate_phrase_entries(bigrams, idx, set(), min_count=5)
        assert len(entries) == 0

    def test_uses_highest_weight(self):
        from collections import Counter

        bigrams = Counter({("tshenn", "hue"): 10})
        idx = {
            "tshenn": [
                {"text": "生", "weight": 800},
                {"text": "青", "weight": 500},
            ],
            "hue": [{"text": "花", "weight": 700}],
        }
        entries = generate_phrase_entries(bigrams, idx, set(), min_count=5)
        assert len(entries) == 1
        assert entries[0]["hanlo"] == "生花"


class TestBuildPhrasesFromFiles:
    def test_full_pipeline(self, tmp_path):
        # Create dict file
        dict_file = tmp_path / "dict.yaml"
        dict_file.write_text(
            "---\nname: test\nversion: \"0.1\"\nsort: by_weight\n...\n"
            "我\tgua\t900\n"
            "袂\tbeh\t800\n"
            "去\tkhi\t700\n"
            "曉\thiau\t600\n",
            encoding="utf-8",
        )

        # Create sentence files
        sent1 = tmp_path / "sent1.txt"
        sent1.write_text("gua2 beh4\ngua2 beh4\ngua2 beh4\ngua2 beh4\ngua2 beh4\n", encoding="utf-8")
        sent2 = tmp_path / "sent2.txt"
        sent2.write_text("gua2 beh4\n", encoding="utf-8")

        output = tmp_path / "phrases.txt"
        count = build_phrases_from_files(
            dict_path=dict_file,
            sentence_paths=[sent1, sent2],
            output_path=output,
            min_count=5,
        )

        assert count >= 1
        content = output.read_text(encoding="utf-8")
        assert "我袂" in content
        assert "gua beh" in content
