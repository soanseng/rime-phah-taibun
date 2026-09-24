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
        assert idx["gua"] == [{"text": "我", "weight": 900, "rime_key": "gua"}]
        assert idx["beh"] == [{"text": "袂", "weight": 800, "rime_key": "beh"}]
        assert idx["hiau"] == [{"text": "曉", "weight": 700, "rime_key": "hiau"}]

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
            'version: "0.1.0"',
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

    def test_toned_dict_keys_match_stripped_bigrams(self):
        """Real dict codes carry tone numbers and sentence tokens keep
        hyphens; the index must normalize both or every lookup misses and
        zero phrases are generated (2026-09-23: new_phrases.txt was empty)."""
        from collections import Counter

        lines = [
            "我\tgua2\t900",
            "袂記得\tbe7-ki3-tsit8\t800",
            "的\te5\t700",
        ]
        idx = build_reverse_index(lines)
        assert "gua" in idx and "be ki tsit" in idx and "e" in idx
        bigrams = Counter({("gua", "e"): 10})
        entries = generate_phrase_entries(bigrams, idx, set(), min_count=5)
        assert entries[0]["hanlo"] == "我的"
        assert entries[0]["rime_key"] == "gua2 e5"


class TestBuildPhrasesFromFiles:
    def test_full_pipeline(self, tmp_path):
        # Create dict file
        dict_file = tmp_path / "dict.yaml"
        dict_file.write_text(
            '---\nname: test\nversion: "0.1"\nsort: by_weight\n...\n'
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


class TestGenerateIdentityPhraseEntries:
    """Identity-attested phrase mining: (漢字, 讀音) pairs from parallel corpora.

    The toneless reverse-index path guesses hanzi by top weight and has
    fabricated wrong identities in production (corpus evidence for 一種
    emitted as 這種 instead). The identity path only emits pairs whose
    adjacent (hanzi, code) tokens were both observed in aligned text.
    """

    def test_attested_identity_bigram_emits_entry(self):
        from collections import Counter
        from math import log10

        from scripts.build_phrases import generate_identity_phrase_entries

        bigrams = Counter({(("一", "tsit8"), ("種", "tsiong2")): 7})
        entries = generate_identity_phrase_entries(bigrams, existing_keys=set(), min_count=5)
        assert entries == [
            {
                "hanlo": "一種",
                "rime_key": "tsit8 tsiong2",
                "weight": int(500 * (1.0 + 0.3 * log10(8))),
            }
        ]

    def test_hyphenated_token_normalized_to_spaces(self):
        from collections import Counter

        from scripts.build_phrases import generate_identity_phrase_entries

        bigrams = Counter({(("一", "tsit8-e7"), ("好", "ho2")): 5})
        entries = generate_identity_phrase_entries(bigrams, existing_keys=set(), min_count=5)
        assert entries and entries[0]["rime_key"] == "tsit8 e7 ho2"

    def test_existing_identity_skipped(self):
        from collections import Counter

        from scripts.build_phrases import generate_identity_phrase_entries

        bigrams = Counter({(("一", "tsit8"), ("種", "tsiong2")): 7})
        entries = generate_identity_phrase_entries(bigrams, existing_keys={("一種", "tsit8 tsiong2")}, min_count=5)
        assert entries == []

    def test_below_min_count_skipped(self):
        from collections import Counter

        from scripts.build_phrases import generate_identity_phrase_entries

        bigrams = Counter({(("一", "tsit8"), ("種", "tsiong2")): 4})
        entries = generate_identity_phrase_entries(bigrams, existing_keys=set(), min_count=5)
        assert entries == []


class TestHeuristicIdentityCoexistence:
    """The toneless heuristic and identity-attested paths must not collide.

    Same (hanlo, rime_key) from both paths would emit duplicate dict rows
    (a fatal validate_dict gate); the identity-attested entry wins.
    Ambiguous toneless codes are skipped by the heuristic — it cannot know
    which identity the corpus observed (the 一種/這種 production bug).
    """

    def _write_dict(self, tmp_path, rows):
        d = tmp_path / "dict.yaml"
        d.write_text(
            '---\nname: t\nversion: "1"\nsort: by_weight\n...\n' + "".join(f"{t}\t{k}\t{w}\n" for t, k, w in rows),
            encoding="utf-8",
        )
        return d

    def test_identity_entry_beats_heuristic_duplicate(self, tmp_path):
        from scripts.build_phrases import build_phrases_from_files

        d = self._write_dict(tmp_path, [("一", "tsit8", 900), ("種", "tsiong2", 800)])
        sent = tmp_path / "s.txt"
        sent.write_text("tsit8 tsiong2\n" * 7, encoding="utf-8")
        big = tmp_path / "big.tsv"
        big.write_text("一\ttsit8\t種\ttsiong2\t7\n", encoding="utf-8")
        out = tmp_path / "p.txt"
        n = build_phrases_from_files(
            dict_path=d,
            sentence_paths=[sent],
            output_path=out,
            min_count=5,
            identity_bigrams_path=big,
        )
        lines = out.read_text(encoding="utf-8").splitlines()
        keys = [tuple(row.split("\t")[:2]) for row in lines]
        assert n >= 1
        assert keys.count(("一種", "tsit8 tsiong2")) == 1, f"duplicate emitted: {lines}"

    def test_unambiguous_heuristic_still_emits(self, tmp_path):
        from scripts.build_phrases import build_phrases_from_files

        d = self._write_dict(tmp_path, [("我", "gua2", 900), ("曉", "hiau2", 800)])
        sent = tmp_path / "s.txt"
        sent.write_text("gua2 hiau2\n" * 6, encoding="utf-8")
        out = tmp_path / "p.txt"
        build_phrases_from_files(dict_path=d, sentence_paths=[sent], output_path=out, min_count=5)
        assert "我曉" in out.read_text(encoding="utf-8")

    def test_junk_toneless_token_rejected(self):
        """iCorpus carries torn tokens (bare 'c'); an identity entry whose
        code has a digitless syllable is a fatal validate_dict gate."""
        from collections import Counter

        from scripts.build_phrases import generate_identity_phrase_entries

        bigrams = Counter({(("三", "sam1 c"), ("新品", "san2 phin2")): 9})
        assert generate_identity_phrase_entries(bigrams, set(), min_count=5) == []

    def test_tone_nine_identity_accepted(self):
        """The project's tone inventory is 1-9; tone-9 attestations
        (e.g. tsiûⁿ-tiāu-style double-acute readings) must survive."""
        from collections import Counter

        from scripts.build_phrases import _identity_code_ok, generate_identity_phrase_entries

        assert _identity_code_ok("sam1-c") is False
        assert _identity_code_ok("phinn9") is True
        bigrams = Counter({(("哼", "hnn9"), ("咧", "leh4")): 6})
        entries = generate_identity_phrase_entries(bigrams, set(), min_count=5)
        assert [e["rime_key"] for e in entries] == ["hnn9 leh4"]
