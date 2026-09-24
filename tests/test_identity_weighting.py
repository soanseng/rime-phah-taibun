"""Identity-keyed corpus weighting: (hanzi, reading) pairs rank homophones.

Same-code homophones (人/膿 both lang5) previously shared one TL-only corpus
boost, so sentence composition picked rare words over common ones. The
iCorpus parallel files give per-identity counts that must break those ties.
"""

import io

from scripts.build_frequency import (
    compute_weights,
    enforce_long_word_invariant,
    load_identity_frequencies,
)
from scripts.extract_identity_freq import extract_identity_counts


def _entry(hanlo: str, rime_key: str, source: str = "itaigi") -> dict:
    return {
        "hanlo": hanlo,
        "rime_key": rime_key,
        "kip_input": rime_key.replace(" ", "-"),
        "source": source,
    }


class TestExtractIdentityCounts:
    def test_aligned_pairs_counted_per_identity(self):
        han = io.StringIO("人 共 我 講\n𪜶 是 學生\n")
        tl = io.StringIO("lang5 kiong7 gua2 kong2\nin1 si7 ha8k-sing1\n")
        counts = extract_identity_counts(han, tl)
        assert counts[("人", "lang5")] == 1
        assert counts[("學生", "ha8k-sing1")] == 1

    def test_repeated_identity_accumulates(self):
        han = io.StringIO("人 來\n人 來\n人 行\n")
        tl = io.StringIO("lang5 lai5\nlang5 lai5\nlang5 kiann5\n")
        counts = extract_identity_counts(han, tl)
        assert counts[("人", "lang5")] == 3
        assert counts[("來", "lai5")] == 2

    def test_misaligned_line_skipped_entirely(self):
        han = io.StringIO("人 來\n足濟 人\n")
        tl = io.StringIO("lang5 lai5\ntsiok8-tse7 lang5 ui7\n")
        counts = extract_identity_counts(han, tl)
        assert ("人", "lang5") in counts
        assert ("足濟", "tsiok8-tse7") not in counts

    def test_non_cjk_token_pair_skipped(self):
        han = io.StringIO("Obama 當選\n")
        tl = io.StringIO("Obama tang1-soan2\n")
        counts = extract_identity_counts(han, tl)
        assert counts.get(("當選", "tang1-soan2"), 0) == 1
        assert ("Obama", "Obama") not in counts

    def test_tl_token_without_tone_digit_skipped(self):
        han = io.StringIO("我 愛 你\n")
        tl = io.StringIO("gua2 ai3 li\n")
        counts = extract_identity_counts(han, tl)
        assert ("我", "gua2") in counts
        assert ("你", "li") not in counts


class TestComputeWeightsIdentity:
    def test_common_identity_outranks_unseen_homophone(self):
        entries = [_entry("人", "lang5"), _entry("膿", "lang5")]
        identity = {("人", "lang5"): 800}
        corpus = {"lang5": 100000}
        weighted = compute_weights(entries, corpus_freq=corpus, identity_freq=identity)
        by_han = {e["hanlo"]: e["weight"] for e in weighted}
        assert by_han["人"] > by_han["膿"], by_han

    def test_unseen_homophone_gets_no_tl_boost_when_code_has_identity(self):
        # TL count 100000 is conflated across 人/膿; 膿 must not inherit it.
        entries = [_entry("膿", "lang5")]
        identity = {("人", "lang5"): 800}
        corpus = {"lang5": 100000}
        weighted = compute_weights(entries, corpus_freq=corpus, identity_freq=identity)
        alone = compute_weights(entries)
        assert weighted[0]["weight"] == alone[0]["weight"]

    def test_multi_syllable_unseen_homophone_gets_no_tl_boost(self):
        # Identity TSV kips are hyphenated ("tai7-tsi3") while rime keys are
        # space separated; the unseen-guard must canonicalize across both.
        entries = [_entry("事志", "tai7 tsi3")]
        identity = {("代誌", "tai7-tsi3"): 71}
        corpus = {"tai7-tsi3": 627}
        weighted = compute_weights(entries, corpus_freq=corpus, identity_freq=identity)
        alone = compute_weights(entries)
        assert weighted[0]["weight"] == alone[0]["weight"]

    def test_tl_fallback_kept_when_code_has_no_identity_data(self):
        entries = [_entry("代誌", "tai7 tsi3")]
        corpus = {"tai7-tsi3": 500}
        weighted = compute_weights(entries, corpus_freq=corpus, identity_freq={})
        alone = compute_weights(entries)
        assert weighted[0]["weight"] > alone[0]["weight"]


class TestInvariantKeepsHomophoneOrder:
    def test_long_word_raise_keeps_within_code_ordering_strict(self):
        # Both below the fragmentation threshold would flatten 代誌/大志
        # to one identical weight; original order must survive strictly.
        singles = [_entry("大", "tai7"), _entry("志", "tsi3")]
        for e in singles:
            e["weight"] = 1500
        dai = _entry("代誌", "tai7 tsi3")
        dai["weight"] = 3000
        tua = _entry("大志", "tai7 tsi3")
        tua["weight"] = 2000
        entries, _raised = enforce_long_word_invariant([*singles, dai, tua])
        by_han = {e["hanlo"]: e["weight"] for e in entries}
        assert by_han["代誌"] > by_han["大志"], by_han
        assert by_han["代誌"] >= 1.2 * (1500 + 1500)
        assert by_han["大志"] >= 1.2 * (1500 + 1500)


class TestCodeNormalization:
    def test_spacing_variant_non_lighttone_codes_merge(self):
        # Same word, same reading, both non-light-tone → one row even if
        # one source emitted a stray double space inside the code.
        entries = [_entry("記得", "ki3 tit4"), _entry("記得", "ki3  tit4")]
        entries[1]["kip_input"] = "ki3-tit4"  # non-lighttone like entry 0
        weighted = compute_weights(entries)
        assert len(weighted) == 1

    def test_lighttone_marker_keeps_separate_identity(self):
        # kì--tit (light tone) and kì-tit are two readings of 記得;
        # dedup must not collapse the marker (AGENTS.md 詞身份原則).
        entries = [_entry("記得", "ki3 tit4"), _entry("記得", "ki3  tit4")]
        entries[1]["kip_input"] = "ki3--tit4"
        weighted = compute_weights(entries)
        assert len(weighted) == 2


class TestLoadIdentityFrequencies:
    def test_parses_three_column_tsv_and_skips_malformed(self, tmp_path):
        tsv = tmp_path / "identity.tsv"
        tsv.write_text("人\tlang5\t800\n膿\tlang5\t3\n記得\tki3-tit4\n", encoding="utf-8")
        loaded = load_identity_frequencies(tsv)
        assert loaded == {("人", "lang5"): 800, ("膿", "lang5"): 3}


class TestExtractIdentityBigrams:
    """Adjacent (漢字, 讀音) identity pairs from line-aligned parallel text."""

    def test_attested_adjacent_pair(self):
        import io

        from scripts.extract_identity_freq import extract_identity_bigrams

        han = io.StringIO("一 種 新 的\n一 種 人\n")
        tl = io.StringIO("tsit8 tsiong2 sin1 e5\ntsit8 tsiong2 lang5\n")
        bigrams = extract_identity_bigrams(han, tl)
        assert bigrams[(("一", "tsit8"), ("種", "tsiong2"))] == 2
        assert bigrams[(("種", "tsiong2"), ("新", "sin1"))] == 1

    def test_unaligned_lines_skipped(self):
        import io

        from scripts.extract_identity_freq import extract_identity_bigrams

        han = io.StringIO("一 種 新 的\n一 種\n")
        tl = io.StringIO("tsit8 tsiong2 sin1 e5\ntsit8 tsiong2 lang5\n")
        bigrams = extract_identity_bigrams(han, tl)
        assert bigrams[(("一", "tsit8"), ("種", "tsiong2"))] == 1

    def test_non_cjk_han_token_skipped(self):
        import io

        from scripts.extract_identity_freq import extract_identity_bigrams

        han = io.StringIO("GPS 好用\n")
        tl = io.StringIO("tshuā-lōo hó-iōng\n")
        bigrams = extract_identity_bigrams(han, tl)
        assert sum(bigrams.values()) == 0

    def test_filtered_token_between_breaks_adjacency(self):
        import io

        from scripts.extract_identity_freq import extract_identity_bigrams

        # 靠 GPS 𤆬路: the Latin token is filtered, but 靠/𤆬路 are NOT adjacent words
        han = io.StringIO("靠 GPS 𤆬路\n")
        tl = io.StringIO("khoo3 GPS tshua7-loo7\n")
        bigrams = extract_identity_bigrams(han, tl)
        assert sum(bigrams.values()) == 0

    def test_bigram_tsv_serialization_roundtrip(self, tmp_path):
        import subprocess
        import sys as _sys

        han = tmp_path / "han.txt"
        tl = tmp_path / "tl.txt"
        han.write_text("一 種 新 的\n一 種 人\n", encoding="utf-8")
        tl.write_text("tsit8 tsiong2 sin1 e5\ntsit8 tsiong2 lang5\n", encoding="utf-8")
        out = tmp_path / "id.tsv"
        big = tmp_path / "big.tsv"
        subprocess.run(
            [
                _sys.executable,
                "scripts/extract_identity_freq.py",
                "--han",
                str(han),
                "--tl",
                str(tl),
                "--output",
                str(out),
                "--bigram-output",
                str(big),
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        rows = [line.split("\t") for line in big.read_text(encoding="utf-8").splitlines()]
        assert all(len(cols) == 5 for cols in rows)
        counts = {(c[0], c[1], c[2], c[3]): int(c[4]) for c in rows}
        assert counts[("一", "tsit8", "種", "tsiong2")] == 2
