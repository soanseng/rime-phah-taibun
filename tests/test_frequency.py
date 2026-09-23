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
        words: list[tuple[str, int]] = []
        for line in copied.read_text(encoding="utf-8").splitlines():
            parts = line.split("\t")
            if len(parts) < 3 or not parts[2].strip().isdigit():
                continue
            tokens = self._split_tokens(parts[1])
            if len(tokens) == 1:
                token = tokens[0]
                singles[token] = max(singles.get(token, 0), int(parts[2]))
            elif len(tokens) >= 2:
                words.append((parts[1], int(parts[2])))

        random.seed(42)
        sample = random.sample(words, min(1000, len(words)))
        for rime_key, weight in sample:
            total = sum(singles.get(token, 0) for token in self._split_tokens(rime_key))
            if total > 0:
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
