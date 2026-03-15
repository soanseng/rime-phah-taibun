"""Tests for NMTL literary corpus frequency extraction."""

import json
from collections import Counter

from scripts.extract_nmtl import (
    extract_nmtl_sentences,
    write_nmtl_output,
)


SAMPLE_JSON = [
    {"漢羅": "伊去學校讀冊", "音標": "I1 khi3 hak8-hau7 thak8-chheh"},
    {"漢羅": "有一个少年人", "音標": "U7 chit8 e5 siau3-lian5-lang5"},
]


class TestExtractNmtlSentencesJson:
    """Extract sentences from nmtl.json format."""

    def test_reads_json_format(self, tmp_path):
        json_file = tmp_path / "nmtl.json"
        json_file.write_text(json.dumps(SAMPLE_JSON, ensure_ascii=False), encoding="utf-8")

        sentences, freq = extract_nmtl_sentences(tmp_path)
        assert len(sentences) == 2
        assert isinstance(freq, Counter)
        assert freq["chit8"] >= 1

    def test_json_with_empty_sound(self, tmp_path):
        data = [{"漢羅": "只有漢字", "音標": ""}]
        json_file = tmp_path / "nmtl.json"
        json_file.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

        sentences, freq = extract_nmtl_sentences(tmp_path)
        assert len(sentences) == 0
        assert len(freq) == 0

    def test_json_missing_sound_key(self, tmp_path):
        """Records without 音標 key are skipped."""
        data = [{"漢羅": "只有漢字"}]
        json_file = tmp_path / "nmtl.json"
        json_file.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

        sentences, freq = extract_nmtl_sentences(tmp_path)
        assert len(sentences) == 0


class TestExtractNmtlSentencesTxt:
    """Fallback: extract from .tbk/.txt files."""

    def test_reads_txt_files(self, tmp_path):
        txt_file = tmp_path / "story1.txt"
        txt_file.write_text("I1 khi3 hak8-hau7\nU7 chit8 e5\n", encoding="utf-8")

        sentences, freq = extract_nmtl_sentences(tmp_path)
        assert len(sentences) == 2
        assert freq["chit8"] >= 1

    def test_reads_tbk_files(self, tmp_path):
        tbk_file = tmp_path / "story1.tbk"
        tbk_file.write_text("I1 khi3 hak8-hau7\n", encoding="utf-8")

        sentences, freq = extract_nmtl_sentences(tmp_path)
        assert len(sentences) == 1
        assert freq["hak8-hau7"] >= 1

    def test_reads_recursive(self, tmp_path):
        sub = tmp_path / "subdir"
        sub.mkdir()
        (sub / "deep.txt").write_text("khi3 hak8-hau7\n", encoding="utf-8")

        sentences, freq = extract_nmtl_sentences(tmp_path)
        assert len(sentences) == 1

    def test_json_takes_priority_over_txt(self, tmp_path):
        """When nmtl.json exists, txt files are ignored."""
        json_file = tmp_path / "nmtl.json"
        json_file.write_text(
            json.dumps([{"漢羅": "A", "音標": "khi3"}], ensure_ascii=False),
            encoding="utf-8",
        )
        txt_file = tmp_path / "extra.txt"
        txt_file.write_text("hak8-hau7\n", encoding="utf-8")

        sentences, freq = extract_nmtl_sentences(tmp_path)
        # Should only have the JSON entry
        assert len(sentences) == 1
        assert "khi3" in sentences[0]


class TestExtractNmtlEmpty:
    """Handle empty or missing directories."""

    def test_empty_directory(self, tmp_path):
        sentences, freq = extract_nmtl_sentences(tmp_path)
        assert sentences == []
        assert len(freq) == 0


class TestFrequencyCounting:
    """Verify frequency counting accuracy."""

    def test_counts_repeated_words(self, tmp_path):
        txt_file = tmp_path / "repeat.txt"
        txt_file.write_text("khi3 khi3 khi3\nhak8 khi3\n", encoding="utf-8")

        sentences, freq = extract_nmtl_sentences(tmp_path)
        assert freq["khi3"] == 4
        assert freq["hak8"] == 1


class TestWriteNmtlOutput:
    """Write frequency TSV and sentences file."""

    def test_writes_both_files(self, tmp_path):
        txt_file = tmp_path / "input" / "story.txt"
        txt_file.parent.mkdir()
        txt_file.write_text("khi3 hak8-hau7\nU7 chit8\n", encoding="utf-8")

        freq_path = tmp_path / "output" / "freq.tsv"
        sent_path = tmp_path / "output" / "sentences.txt"

        write_nmtl_output(txt_file.parent, freq_path, sent_path)

        assert freq_path.exists()
        freq_lines = freq_path.read_text(encoding="utf-8").strip().splitlines()
        assert len(freq_lines) > 0
        # TSV format: word\tcount
        assert "\t" in freq_lines[0]

        assert sent_path.exists()
        sent_lines = sent_path.read_text(encoding="utf-8").strip().splitlines()
        assert len(sent_lines) == 2

    def test_writes_freq_only(self, tmp_path):
        txt_file = tmp_path / "input" / "story.txt"
        txt_file.parent.mkdir()
        txt_file.write_text("khi3 hak8\n", encoding="utf-8")

        freq_path = tmp_path / "output" / "freq.tsv"
        write_nmtl_output(txt_file.parent, freq_path, None)

        assert freq_path.exists()
