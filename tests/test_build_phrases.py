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
        assert bigrams[("gua2", "beh4")] == 1
        assert bigrams[("beh4", "khi3")] == 1

    def test_keeps_tones(self):
        """The tone is part of word identity (做 tso3 vs 曹 tso5)."""
        bigrams = extract_bigrams(["tso3 e5", "tso5 e5"])
        assert bigrams[("tso3", "e5")] == 1
        assert bigrams[("tso5", "e5")] == 1

    def test_counts_across_sentences(self):
        sentences = ["gua2 beh4", "gua2 beh4", "gua2 beh4"]
        bigrams = extract_bigrams(sentences)
        assert bigrams[("gua2", "beh4")] == 3

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
        return build_reverse_index(["我\tgua2\t900", "欲\tbeh4\t800", "去\tkhi3\t700"])

    def test_basic_phrase(self):
        from collections import Counter
        from math import log10

        bigrams = Counter({("gua2", "beh4"): 10})
        idx = self._make_reverse_index()
        entries = generate_phrase_entries(bigrams, idx, set(), min_count=5, base_weight=500)
        assert len(entries) == 1
        assert entries[0]["hanlo"] == "我欲"
        assert entries[0]["rime_key"] == "gua2 beh4"
        expected_weight = int(500 * (1.0 + log10(1 + 10) * 0.3))
        assert entries[0]["weight"] == expected_weight

    def test_skips_existing(self):
        from collections import Counter

        bigrams = Counter({("gua2", "beh4"): 10})
        idx = self._make_reverse_index()
        existing = {("我欲", "gua2 beh4")}
        entries = generate_phrase_entries(bigrams, idx, existing, min_count=5)
        assert len(entries) == 0

    def test_skips_below_threshold(self):
        from collections import Counter

        bigrams = Counter({("gua2", "beh4"): 3})
        idx = self._make_reverse_index()
        entries = generate_phrase_entries(bigrams, idx, set(), min_count=5)
        assert len(entries) == 0

    def test_skips_unknown_words(self):
        from collections import Counter

        bigrams = Counter({("gua2", "unknown"): 10})
        idx = self._make_reverse_index()
        entries = generate_phrase_entries(bigrams, idx, set(), min_count=5)
        assert len(entries) == 0

    def test_uses_highest_weight(self):
        """Bare tokens are the implicit tone (tshenn = tshenn1); among its
        rows the clearly heaviest names the word."""
        from collections import Counter

        bigrams = Counter({("tshenn", "hue"): 10})
        idx = build_reverse_index(["生\ttshenn1\t800", "青\ttshenn1\t500", "花\thue1\t700"])
        entries = generate_phrase_entries(bigrams, idx, set(), min_count=5)
        assert [(e["hanlo"], e["rime_key"]) for e in entries] == [("生花", "tshenn1 hue1")]

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
        bigrams = Counter({("gua2", "e5"): 10})
        entries = generate_phrase_entries(bigrams, idx, set(), min_count=5)
        assert entries[0]["hanlo"] == "我的"
        assert entries[0]["rime_key"] == "gua2 e5"

    def test_toned_token_keeps_its_reading_identity(self):
        """Corpus tso3 is 做, not the heavier toneless homophone 曹 (tso5):
        stripping tones fabricated 曹的/tso5 e5 from 做的 evidence."""
        from collections import Counter

        idx = build_reverse_index(["曹\ttso5\t2000", "做\ttso3\t1539", "的\te5\t1900"])
        entries = generate_phrase_entries(Counter({("tso3", "e5"): 10}), idx, set(), min_count=5)
        assert [(e["hanlo"], e["rime_key"]) for e in entries] == [("做的", "tso3 e5")]

    def test_toned_token_without_matching_reading_skipped(self):
        """No dictionary row carries tso2: picking a toneless homophone would
        invent an identity the corpus never attested."""
        from collections import Counter

        idx = build_reverse_index(["曹\ttso5\t2000", "的\te5\t1900"])
        entries = generate_phrase_entries(Counter({("tso2", "e5"): 10}), idx, set(), min_count=5)
        assert entries == []

    def test_bare_and_toned_tokens_resolving_alike_merge_counts(self):
        """'khuann3 i' and 'khuann3 i1' are one identity 看伊/khuann3 i1:
        emitted once, weighted by the summed count."""
        from collections import Counter
        from math import log10

        idx = build_reverse_index(["看\tkhuann3\t900", "伊\ti1\t900"])
        bigrams = Counter({("khuann3", "i"): 10, ("khuann3", "i1"): 10})
        entries = generate_phrase_entries(bigrams, idx, set(), min_count=5, base_weight=500)
        assert [(e["hanlo"], e["rime_key"]) for e in entries] == [("看伊", "khuann3 i1")]
        assert entries[0]["weight"] == int(500 * (1.0 + log10(1 + 20) * 0.3))

    def test_one_phrase_per_toneless_pair_from_dominant_reading(self):
        """Volume stays one phrase per toneless pair (the miner's input also
        feeds the word-boundary roundtrip). The dominant attested identity
        wins, weighted and thresholded by its own count only: 曹 tso5 is a
        different word, its occurrences never credit 做的."""
        from collections import Counter
        from math import log10

        idx = build_reverse_index(["曹\ttso5\t2000", "做\ttso3\t1539", "的\te5\t1900"])
        bigrams = Counter({("tso3", "e5"): 8, ("tso5", "e5"): 3})
        entries = generate_phrase_entries(bigrams, idx, set(), min_count=5, base_weight=500)
        assert [(e["hanlo"], e["rime_key"]) for e in entries] == [("做的", "tso3 e5")]
        assert entries[0]["weight"] == int(500 * (1.0 + log10(1 + 8) * 0.3))

    def test_identity_below_threshold_not_rescued_by_homophones(self):
        from collections import Counter

        idx = build_reverse_index(["曹\ttso5\t2000", "做\ttso3\t1539", "的\te5\t1900"])
        bigrams = Counter({("tso3", "e5"): 4, ("tso5", "e5"): 3})
        assert generate_phrase_entries(bigrams, idx, set(), min_count=5) == []

    def test_no_phrase_when_hanzi_not_identified_by_reading(self):
        """sann1 is 衫 / 三 / 相 at one code: picking the heaviest (衫) for
        corpus 'sann1 ji7' (三字) fabricates 衫字. A toned token must resolve
        to one unambiguous hanzi, or the pair is left to the identity path."""
        from collections import Counter

        idx = build_reverse_index(["衫\tsann1\t2000", "三\tsann1\t1900", "字\tji7\t1500"])
        assert generate_phrase_entries(Counter({("sann1", "ji7"): 11}), idx, set(), min_count=5) == []

    def test_bare_token_is_implicit_tone_not_any_tone(self):
        """Corpus 'kha' (tone 1 unmarked, as in pojbh) means kha1: it must
        not borrow a heavier row of another tone (卡 kha2)."""
        from collections import Counter

        idx = build_reverse_index(["卡\tkha2\t3000", "跤\tkha1\t800", "尻\tkha1\t800", "的\te5\t1900"])
        assert generate_phrase_entries(Counter({("e5", "kha"): 20}), idx, set(), min_count=5) == []

    def test_multi_syllable_tokens_left_to_identity_path(self):
        """Heuristic pairing of multi-syllable words (民國+狗) fabricates
        phrases; attested multi-syllable pairs come from identity bigrams."""
        from collections import Counter

        idx = build_reverse_index(["民國\tbin5 kok4\t900", "狗\tkau2\t900"])
        entries = generate_phrase_entries(Counter({("bin5-kok4", "kau2"): 50}), idx, set(), min_count=5)
        assert entries == []


class TestBuildPhrasesFromFiles:
    def test_full_pipeline(self, tmp_path):
        # Create dict file
        dict_file = tmp_path / "dict.yaml"
        dict_file.write_text(
            '---\nname: test\nversion: "0.1"\nsort: by_weight\n...\n'
            "我\tgua2\t900\n"
            "欲\tbeh4\t800\n"
            "去\tkhi3\t700\n"
            "曉\thiau2\t600\n",
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
        assert "我欲\tgua2 beh4" in content


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
