"""Tests for heuristic frequency weighting."""

import math
import random
import re
from pathlib import Path

from scripts.build_frequency import (
    assign_source_weight,
    compute_weights,
    enforce_dict_file_invariant,
    enforce_long_word_invariant,
    load_corpus_frequencies,
    word_length_modifier,
    write_word_keys,
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
        assert word_length_modifier("七月半鴨仔") == 0.9

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

    def test_whitespace_key_variants_dedup_to_one_entry(self):
        """Whitespace variants of one code are one identity: grouping in
        compute_weights must normalize rime_key so downstream dict rows
        (which write normalized keys) can never carry both variants."""
        entries = [
            {"hanlo": "閃著", "rime_key": "siam2  tioh8", "source": "moe"},
            {"hanlo": "閃著", "rime_key": "siam2 tioh8", "source": "itaigi"},
        ]
        result = compute_weights(entries)
        assert len(result) == 1
        assert result[0]["rime_key"] == "siam2 tioh8"


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


class TestEnforceLongWordInvariant:
    """Long-word-first invariant (PLAN section 9-1A).

    weight(W) >= k * sum(weights of strongest single-syllable entries
    with the same readings), so sentence composition never prefers
    fragmenting a dictionary word into single characters.
    """

    def test_long_word_raised_to_threshold(self):
        entries = [
            {"hanlo": "食", "rime_key": "tsiah", "source": "itaigi", "weight": 640},
            {"hanlo": "飯", "rime_key": "png", "source": "itaigi", "weight": 640},
            {"hanlo": "食飯", "rime_key": "tsiah png", "source": "itaigi", "weight": 960},
        ]
        result, raised = enforce_long_word_invariant(entries)
        word = next(e for e in result if e["hanlo"] == "食飯")
        # ceil(1.2 * (640 + 640)) = 1536
        assert word["weight"] == 1536
        assert raised == 1

    def test_no_change_when_already_above(self):
        entries = [
            {"hanlo": "食", "rime_key": "tsiah", "source": "taijit", "weight": 160},
            {"hanlo": "飯", "rime_key": "png", "source": "taijit", "weight": 160},
            {"hanlo": "食飯", "rime_key": "tsiah png", "source": "itaigi", "weight": 960},
        ]
        result, raised = enforce_long_word_invariant(entries)
        word = next(e for e in result if e["hanlo"] == "食飯")
        assert word["weight"] == 960
        assert raised == 0

    def test_single_syllable_entries_untouched(self):
        entries = [
            {"hanlo": "食", "rime_key": "tsiah", "source": "itaigi", "weight": 640},
            {"hanlo": "飯", "rime_key": "png", "source": "itaigi", "weight": 640},
        ]
        result, raised = enforce_long_word_invariant(entries)
        assert all(e["weight"] == 640 for e in result)
        assert raised == 0

    def test_missing_standalone_syllable_noop(self):
        """No single-syllable competitors means nothing to enforce."""
        entries = [
            {"hanlo": "食", "rime_key": "tsiah", "source": "itaigi", "weight": 640},
            {"hanlo": "食飯", "rime_key": "tsiah png", "source": "itaigi", "weight": 960},
        ]
        # "png" has no standalone entry -> fragmented sum = 640, threshold 768 < 960
        result, raised = enforce_long_word_invariant(entries)
        word = next(e for e in result if e["hanlo"] == "食飯")
        assert word["weight"] == 960
        assert raised == 0

    def test_idempotent(self):
        entries = [
            {"hanlo": "食", "rime_key": "tsiah", "source": "itaigi", "weight": 640},
            {"hanlo": "飯", "rime_key": "png", "source": "itaigi", "weight": 640},
            {"hanlo": "食飯", "rime_key": "tsiah png", "source": "itaigi", "weight": 960},
        ]
        first, raised1 = enforce_long_word_invariant(entries)
        _, raised2 = enforce_long_word_invariant(first)
        assert raised1 == 1
        assert raised2 == 0

    def test_long_word_beats_two_word_split(self):
        """A 4-syllable word must also beat its best 2+2 dict-word split.

        The per-syllable floor alone is not enough: composition can bypass
        the word with two shorter dictionary words (長期 + 時間), so the
        floor is max(syllable floor, ceil(k * best two-code split sum)).
        """
        entries = [
            {"hanlo": "長", "rime_key": "tng5", "source": "itaigi", "weight": 400},
            {"hanlo": "期", "rime_key": "ki5", "source": "itaigi", "weight": 400},
            {"hanlo": "時", "rime_key": "si5", "source": "itaigi", "weight": 400},
            {"hanlo": "間", "rime_key": "kan5", "source": "itaigi", "weight": 400},
            {"hanlo": "長期", "rime_key": "tng5-ki5", "source": "itaigi", "weight": 3000},
            {"hanlo": "時間", "rime_key": "si5-kan5", "source": "itaigi", "weight": 3000},
            # 3000 > ceil(1.2 * (400*4)) = 1920 syllable floor, but below
            # ceil(1.2 * (3000 + 3000)) = 7200 two-word-split floor.
            {"hanlo": "長期時間", "rime_key": "tng5-ki5 si5-kan5", "source": "itaigi", "weight": 3000},
        ]
        result, raised = enforce_long_word_invariant(entries)
        by_han = {e["hanlo"]: e["weight"] for e in result}
        assert by_han["長期時間"] == 7200
        assert by_han["長期"] == 3000
        assert by_han["時間"] == 3000
        assert raised == 1

    def test_split_with_missing_half_ignored(self):
        """A split counts only when BOTH halves are existing dict codes."""
        entries = [
            {"hanlo": "長", "rime_key": "tng5", "source": "itaigi", "weight": 400},
            {"hanlo": "期", "rime_key": "ki5", "source": "itaigi", "weight": 400},
            {"hanlo": "時", "rime_key": "si5", "source": "itaigi", "weight": 400},
            {"hanlo": "間", "rime_key": "kan5", "source": "itaigi", "weight": 400},
            # Only the left half of the natural 2+2 split exists as a dict
            # word; 時間 is absent, so no two-code split applies.
            {"hanlo": "長期", "rime_key": "tng5-ki5", "source": "itaigi", "weight": 3000},
            # 3000 > ceil(1.2 * 1600) = 1920 syllable floor.
            {"hanlo": "長期時間", "rime_key": "tng5-ki5 si5-kan5", "source": "itaigi", "weight": 3000},
        ]
        result, raised = enforce_long_word_invariant(entries)
        by_han = {e["hanlo"]: e["weight"] for e in result}
        assert by_han["長期時間"] == 3000
        assert raised == 0

    def test_split_floor_uses_final_component_weights(self):
        """Raised component words feed later split floors until stable.

        看民眾 must beat 看+民眾; once 看民眾 is raised, 看民眾世 must beat
        the RAISED 看民眾+世. Split components are strictly shorter codes,
        so sweeping to a fixpoint terminates and the assembled dictionary
        satisfies the invariant against its own final weights.
        """
        entries = [
            {"hanlo": "看", "rime_key": "khuann3", "source": "itaigi", "weight": 100},
            {"hanlo": "民", "rime_key": "bin5", "source": "itaigi", "weight": 100},
            {"hanlo": "眾", "rime_key": "tsiong3", "source": "itaigi", "weight": 100},
            {"hanlo": "世", "rime_key": "si7", "source": "itaigi", "weight": 100},
            {"hanlo": "民眾", "rime_key": "bin5 tsiong3", "source": "itaigi", "weight": 5000},
            # 1000 < ceil(1.2 * (100 + 5000)) = 6120 one+two split floor.
            {"hanlo": "看民眾", "rime_key": "khuann3 bin5 tsiong3", "source": "itaigi", "weight": 1000},
            # Split floor [看民眾][世] = ceil(1.2 * (6120 + 100)) = 7464,
            # computable only after 看民眾 has been raised.
            {"hanlo": "看民眾世", "rime_key": "khuann3 bin5 tsiong3 si7", "source": "itaigi", "weight": 2000},
        ]
        first, raised1 = enforce_long_word_invariant(entries)
        by_han = {e["hanlo"]: e["weight"] for e in first}
        assert by_han["看民眾"] == 6120
        assert by_han["看民眾世"] == 7464
        assert by_han["民眾"] == 5000
        assert raised1 == 2
        _, raised2 = enforce_long_word_invariant(first)
        assert raised2 == 0


class TestEnforceDictFileInvariant:
    """File-level long-word invariant pass over an assembled dict.yaml."""

    def _write_dict(self, path):
        path.write_text(
            "---\n"
            "name: test\n"
            'version: "0.1"\n'
            "...\n"
            "食\ttsiah8\t640\n"
            "飯\tpng7\t640\n"
            "食飯\ttsiah8 png7\t960\n"
            "菜\ttshai3\t100\n",
            encoding="utf-8",
        )

    def test_violating_word_weight_rewritten(self, tmp_path):
        dict_path = tmp_path / "test.dict.yaml"
        self._write_dict(dict_path)
        raised = enforce_dict_file_invariant(dict_path)
        lines = dict_path.read_text(encoding="utf-8").splitlines()
        assert lines[6] == "食飯\ttsiah8 png7\t1536"
        assert lines[4] == "食\ttsiah8\t640"  # singles untouched
        assert raised == 1

    def test_already_compliant_file_unchanged(self, tmp_path):
        dict_path = tmp_path / "test.dict.yaml"
        path_lines = [
            "---",
            "name: test",
            "...",
            "食\ttsiah8\t160",
            "飯\tpng7\t160",
            "食飯\ttsiah8 png7\t960",
        ]
        dict_path.write_text("\n".join(path_lines) + "\n", encoding="utf-8")
        raised = enforce_dict_file_invariant(dict_path)
        assert raised == 0
        assert dict_path.read_text(encoding="utf-8").splitlines()[5] == "食飯\ttsiah8 png7\t960"

    def test_lighttone_row_capped_below_raised_parent(self, tmp_path):
        """A light-tone row (double-space key) must end at most parent-100.

        Core-dict '--' rows reach the assembled dict with no cap at all
        (the builder-side cap only covers corpus light-tone entries), and
        the raise pass can lift a LT row above its parent — the shipped
        inversion 轉來 tng2 lai5=3386 vs tng2␣␣lai5=7108. The cap runs
        after the raise pass so the raise cannot re-invert the pair.
        """
        dict_path = tmp_path / "test.dict.yaml"
        dict_path.write_text(
            "---\n"
            "name: test\n"
            "...\n"
            "轉\ttng2\t500\n"
            "來\tlai5\t600\n"
            "轉來\ttng2 lai5\t1200\n"
            "轉來\ttng2  lai5\t7108\n"
            "死\tsi2\t100\n"
            "去\tkhi3\t100\n"
            "死去\tsi2  khi3\t800\n",  # no plain parent row in this dict
            encoding="utf-8",
        )
        raised = enforce_dict_file_invariant(dict_path)
        lines = dict_path.read_text(encoding="utf-8").splitlines()
        assert lines[5] == "轉來\ttng2 lai5\t1320"  # ceil(1.2 * (500 + 600))
        assert lines[6] == "轉來\ttng2  lai5\t1220"  # min(7108, 1320 - 100)
        assert lines[9] == "死去\tsi2  khi3\t800"  # parentless LT row: unchanged
        assert raised == 1

    def test_lighttone_cap_is_per_identity(self, tmp_path):
        """Two texts sharing one collapsed code are capped independently.

        Each light-tone row is capped by its own text's parent weight,
        never by a code-max across texts.
        """
        dict_path = tmp_path / "test.dict.yaml"
        dict_path.write_text(
            "---\n"
            "name: test\n"
            "...\n"
            "轉\ttng2\t500\n"
            "來\tlai5\t600\n"
            "轉來\ttng2 lai5\t2000\n"
            "傳來\ttng2 lai5\t1400\n"
            "轉來\ttng2  lai5\t5000\n"
            "傳來\ttng2  lai5\t5000\n",
            encoding="utf-8",
        )
        raised = enforce_dict_file_invariant(dict_path)
        lines = dict_path.read_text(encoding="utf-8").splitlines()
        assert lines[7] == "轉來\ttng2  lai5\t1900"  # own-text parent 2000 - 100
        assert lines[8] == "傳來\ttng2  lai5\t1300"  # own-text parent 1400 - 100
        assert raised == 0

    def test_lighttone_only_change_rewrites_file(self, tmp_path):
        """A cap-only pass (nothing raised) must still rewrite the dict."""
        dict_path = tmp_path / "test.dict.yaml"
        dict_path.write_text(
            "---\nname: test\n...\n食\ttsiah8\t160\n飯\tpng7\t160\n食飯\ttsiah8 png7\t960\n食飯\ttsiah8  png7\t9999\n",
            encoding="utf-8",
        )
        raised = enforce_dict_file_invariant(dict_path)
        lines = dict_path.read_text(encoding="utf-8").splitlines()
        assert raised == 0
        assert lines[6] == "食飯\ttsiah8  png7\t860"  # 960 - 100

    def test_compliant_file_not_rewritten(self, tmp_path, monkeypatch):
        """A no-op pass must not rewrite the artifact.

        The invariant pass runs over the ~5MB assembled dictionary as the
        final build step; rewriting it even when nothing changed destroys
        mtime stability that incremental tooling relies on.
        """
        dict_path = tmp_path / "test.dict.yaml"
        path_lines = [
            "---",
            "name: test",
            "...",
            "食\ttsiah8\t160",
            "飯\tpng7\t160",
            "食飯\ttsiah8 png7\t960",
        ]
        dict_path.write_text("\n".join(path_lines) + "\n", encoding="utf-8")

        writes: list[Path] = []
        real_write_text = Path.write_text

        def spy_write_text(self, data, encoding=None, errors=None, newline=None):
            writes.append(self)
            return real_write_text(self, data, encoding=encoding, errors=errors, newline=newline)

        monkeypatch.setattr(Path, "write_text", spy_write_text)
        raised = enforce_dict_file_invariant(dict_path)
        monkeypatch.undo()

        assert raised == 0
        assert writes == [], "compliant dictionary must not be rewritten"


class TestCommittedDictInvariant:
    """The long-word invariant must be restorable on the shipped dictionary."""

    DICT_PATH = Path(__file__).parents[1] / "schema" / "phah_taibun.dict.yaml"

    @staticmethod
    def _split_tokens(rime_key: str) -> list[str]:
        return [t for t in re.split(r"[ \-]+", rime_key) if t]

    def test_enforcement_restores_invariant_on_committed_dict(self, tmp_path):
        copied = tmp_path / "phah_taibun.dict.yaml"
        copied.write_bytes(self.DICT_PATH.read_bytes())
        enforce_dict_file_invariant(copied)

        singles: dict[str, int] = {}
        parents: dict[tuple[str, str], int] = {}
        words: list[tuple[str, str, int]] = []
        for line in copied.read_text(encoding="utf-8").splitlines():
            parts = line.split("\t")
            if len(parts) < 3 or not parts[2].strip().isdigit():
                continue
            weight = int(parts[2])
            tokens = self._split_tokens(parts[1])
            if len(tokens) == 1:
                singles[tokens[0]] = max(singles.get(tokens[0], 0), weight)
            elif len(tokens) >= 2:
                words.append((parts[0], parts[1], weight))
                if "  " not in parts[1]:
                    identity = (parts[0], " ".join(parts[1].split()))
                    parents[identity] = max(parents.get(identity, 0), weight)

        random.seed(42)
        sample = random.sample(words, min(1000, len(words)))
        for hanlo, rime_key, weight in sample:
            total = sum(singles.get(token, 0) for token in self._split_tokens(rime_key))
            if "  " in rime_key:
                # Light-tone rows are governed by the parent cap, not the
                # fragment threshold: the raise pass may have parked the
                # parent exactly at threshold, and parent-100 then dips
                # below it by design (parent outranks its LT variant).
                parent = parents.get((hanlo, " ".join(rime_key.split())))
                if parent is not None:
                    assert weight <= parent - 100, f"light-tone cap violated: {rime_key}"
            elif total > 0:
                assert weight >= math.ceil(1.2 * total), f"invariant violated: {rime_key}"


class TestWriteWordKeys:
    """Key-set snapshot for release diffing (PLAN 9-2H)."""

    def test_writes_versioned_sorted_unique_pairs(self, tmp_path):
        dict_path = tmp_path / "d.dict.yaml"
        dict_path.write_text(
            "---\n"
            "name: test\n"
            'version: "0.6.2"\n'
            "...\n"
            "飯\tpng7\t100\n"
            "食\ttsiah8\t200\n"
            "食飯\ttsiah8 png7\t300\n"
            "食\ttsiah8\t999\n",
            encoding="utf-8",
        )
        out = write_word_keys(dict_path, tmp_path / "dist")
        assert out.name == "word-keys-v0.6.2.tsv"
        lines = out.read_text(encoding="utf-8").splitlines()
        assert lines[0] == "# word-keys v0.6.2"
        assert lines[1:] == [
            "食\ttsiah8",
            "食飯\ttsiah8 png7",
            "飯\tpng7",
        ]
