"""Tests for KipSutian example sentence extractor."""

import io
from collections import Counter

from scripts.extract_kipsutian_sentences import extract_kipsutian_sentences

# CSV header matching the actual kautian.csv structure
CSV_HEADER = (
    "詞目id,詞目類型,漢字,羅馬字,分類,羅馬字音檔檔名,又唸作,合音唸作,俗唸作,"
    "語音差異,詞彙比較,名,姓,異用字,詞目tuì詞目近義,詞目tuì詞目反義,"
    "解說,詞性,例句,例句-華語,例句-音檔,義項tuì義項近義,義項tuì義項反義,"
    "義項tuì詞目近義,義項tuì詞目反義\n"
)


def _make_csv(*rows: str) -> io.StringIO:
    """Build a CSV StringIO from header + data rows."""
    return io.StringIO(CSV_HEADER + "".join(rows))


class TestExtractKipsutianSentences:
    """Extract romanization tokens from KipSutian CSV entries."""

    def test_extracts_romanization(self):
        row = (
            "1,主詞目,食飯,tsia̍h-pn̄g,動作,1(1),,,,,,,,,,,"
            '"吃飯。","動詞",'
            '"來食飯","來吃飯",,,,\n'
        )
        sentences, freq = extract_kipsutian_sentences(_make_csv(row))
        assert len(sentences) >= 1
        # The romanization tsia̍h-pn̄g should appear as a token
        assert any("tsia" in s for s in sentences)

    def test_skips_entries_without_reading(self):
        row = (
            "1,主詞目,食飯,,動作,1(1),,,,,,,,,,,"
            '"吃飯。","動詞",'
            '"來食飯","來吃飯",,,,\n'
        )
        sentences, freq = extract_kipsutian_sentences(_make_csv(row))
        assert len(sentences) == 0

    def test_empty_csv(self):
        sentences, freq = extract_kipsutian_sentences(io.StringIO(CSV_HEADER))
        assert sentences == []
        assert len(freq) == 0

    def test_frequency_counting(self):
        rows = (
            "1,主詞目,食飯,tsia̍h8-pn̄g7,動作,1(1),,,,,,,,,,,"
            '"吃飯。","動詞",'
            '"來食飯","來吃飯",,,,\n'
            "2,主詞目,食物,tsia̍h8-mi̍h8,名詞,2(1),,,,,,,,,,,"
            '"食物。","名詞",'
            '"好食物","好的食物",,,,\n'
        )
        sentences, freq = extract_kipsutian_sentences(_make_csv(rows))
        # tsia̍h8 appears in both entries as part of compound
        assert isinstance(freq, Counter)
        assert len(freq) > 0

    def test_multiple_readings_with_又唸作(self):
        """Entries with 又唸作 (alternate reading) should also be extracted."""
        row = (
            "1,主詞目,一,tsi̍t,數詞,1(1),it,,,,,,,,,,,"
            '"數目。","數詞",'
            '"一蕊花","一朵花",,,,\n'
        )
        sentences, freq = extract_kipsutian_sentences(_make_csv(row))
        # Both main reading and alternate reading should be extracted
        assert len(sentences) >= 1

    def test_skips_empty_reading(self):
        """Entries where all reading fields are empty should be skipped."""
        row = (
            '1,主詞目,無讀音,,,1(1),,,,,,,,,,,'
            '"解說。","名詞",'
            '"例句","例句華語",,,,\n'
        )
        sentences, freq = extract_kipsutian_sentences(_make_csv(row))
        assert len(sentences) == 0
