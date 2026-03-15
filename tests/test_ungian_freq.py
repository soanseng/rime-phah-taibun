"""Tests for Ungian literary corpus frequency extraction."""

import json
from collections import Counter

from scripts.extract_ungian_freq import (
    count_ungian_frequencies,
    extract_kip_tokens,
    parse_ungian_json,
    write_ungian_sentences,
)

SAMPLE_JSON = {
    "作者": "Test Author",
    "出版年": "2001",
    "文類": "民間故事",
    "書名": "Test Book",
    "書寫系統": "漢羅",
    "資料": [
        {
            "段": [
                ["有一个少年人", "U7 chit8 e5 siau3-lian5-lang5"],
                ["伊去學校讀冊", "I1 khi3 hak8-hau7 thak8-chheh"],
            ],
            "篇名": "Test Story",
        }
    ],
}


class TestParseUngianJson:
    """Parse Ungian JSON structure."""

    def test_extracts_kip_lines(self):
        lines = parse_ungian_json(SAMPLE_JSON)
        assert len(lines) == 2
        assert "chit8" in lines[0]

    def test_empty_data(self):
        data = {"資料": []}
        assert parse_ungian_json(data) == []

    def test_missing_kip(self):
        """Segments with only hanzi (no KIP pair) are skipped."""
        data = {"資料": [{"段": [["只有漢字"]]}]}
        assert parse_ungian_json(data) == []


class TestExtractKipTokens:
    """Tokenize KIP romanization lines."""

    def test_basic_tokens(self):
        tokens = extract_kip_tokens("U7 chit8 e5 siau3-lian5-lang5")
        assert "U7" in tokens or "u7" in [t.lower() for t in tokens]
        assert "chit8" in tokens
        assert "siau3-lian5-lang5" in tokens

    def test_empty(self):
        assert extract_kip_tokens("") == []


class TestCountUngianFrequencies:
    """Count frequencies from a directory of JSON files."""

    def test_counts_from_json_files(self, tmp_path):
        # Create a test JSON file
        json_file = tmp_path / "test.json"
        json_file.write_text(json.dumps(SAMPLE_JSON, ensure_ascii=False), encoding="utf-8")

        freq = count_ungian_frequencies(tmp_path)
        assert isinstance(freq, Counter)
        assert len(freq) > 0
        assert freq["chit8"] >= 1

    def test_empty_dir(self, tmp_path):
        freq = count_ungian_frequencies(tmp_path)
        assert len(freq) == 0


class TestSentenceOutput:
    """Write tokenized sentences from Ungian JSON files."""

    def test_writes_sentences(self, tmp_path):
        json_dir = tmp_path / "json"
        json_dir.mkdir()
        data = {"資料": [{"段": [["漢字text", "kip2 romanization3"]]}]}
        (json_dir / "test.json").write_text(
            json.dumps(data, ensure_ascii=False), encoding="utf-8"
        )
        output = tmp_path / "sentences.txt"
        count = write_ungian_sentences(json_dir, output)
        assert count == 1
        lines = output.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 1
        assert "kip2" in lines[0]
        assert "romanization3" in lines[0]

    def test_skips_empty_lines(self, tmp_path):
        json_dir = tmp_path / "json"
        json_dir.mkdir()
        data = {"資料": [{"段": [["只有漢字", ""]]}]}
        (json_dir / "test.json").write_text(
            json.dumps(data, ensure_ascii=False), encoding="utf-8"
        )
        output = tmp_path / "sentences.txt"
        count = write_ungian_sentences(json_dir, output)
        assert count == 0
        content = output.read_text(encoding="utf-8").strip()
        assert content == ""
