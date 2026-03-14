"""Tests for ChhoeTaigi CSV to Rime dictionary conversion."""

import io

from scripts.convert_chhoetaigi import (
    clean_kip_input,
    convert_chhoetaigi,
    dedup_entries,
    main,
    parse_itaigi_csv,
    parse_taihoa_csv,
    strip_tone_numbers,
    write_rime_dict,
)


class TestStripToneNumbers:
    """Remove trailing tone digits (1-9) from KipInput syllables."""

    def test_basic_tone_removal(self):
        assert strip_tone_numbers("tsit8") == "tsit"

    def test_multi_syllable(self):
        assert strip_tone_numbers("tua7-lang5") == "tua-lang"

    def test_no_tone(self):
        assert strip_tone_numbers("a") == "a"

    def test_hyphen_to_space(self):
        """Rime uses space-separated syllables, not hyphens."""
        assert strip_tone_numbers("tua7-lang5", delimiter=" ") == "tua lang"


class TestCleanKipInput:
    """Clean KipInput: remove (替), split slashes, handle -- sandhi."""

    def test_remove_tai_marker(self):
        assert clean_kip_input("tsit8(替)") == ["tsit8"]

    def test_split_slash_variants(self):
        assert clean_kip_input("tsiah8/sit8") == ["tsiah8", "sit8"]

    def test_preserve_double_dash(self):
        """Double dash -- indicates tone sandhi, keep it."""
        assert clean_kip_input("kong2--e5") == ["kong2--e5"]

    def test_combined_tai_and_slash(self):
        assert clean_kip_input("tsit8(替)/it4") == ["tsit8", "it4"]

    def test_empty_input(self):
        assert clean_kip_input("") == []

    def test_whitespace_input(self):
        assert clean_kip_input("  ") == []


class TestParseItaigiCsv:
    """Parse iTaigi CSV into list of dict entries."""

    def test_basic_parse(self, itaigi_csv_content):
        entries = parse_itaigi_csv(io.StringIO(itaigi_csv_content))
        assert len(entries) == 3

    def test_entry_fields(self, itaigi_csv_content):
        entries = parse_itaigi_csv(io.StringIO(itaigi_csv_content))
        first = entries[0]
        assert first["hanlo"] == "𤺪呢"
        assert first["kip_input"] == "sian7-neh"
        assert first["hoabun"] == "討厭"

    def test_rime_key_generated(self, itaigi_csv_content):
        """Each entry should have a toneless space-separated rime_key."""
        entries = parse_itaigi_csv(io.StringIO(itaigi_csv_content))
        first = entries[0]
        assert first["rime_key"] == "sian neh"

    def test_source_tagged(self, itaigi_csv_content):
        entries = parse_itaigi_csv(io.StringIO(itaigi_csv_content))
        assert all(e["source"] == "itaigi" for e in entries)


class TestParseTaihoaCsv:
    """Parse 台華線頂 CSV (has Others columns for variant pronunciations)."""

    def test_basic_parse(self, taihoa_csv_content):
        entries = parse_taihoa_csv(io.StringIO(taihoa_csv_content))
        assert len(entries) == 3

    def test_entry_fields(self, taihoa_csv_content):
        entries = parse_taihoa_csv(io.StringIO(taihoa_csv_content))
        first = entries[0]
        assert first["hanlo"] == "á無"
        assert first["kip_input"] == "a2-bo5"
        assert first["rime_key"] == "a bo"
        assert first["hoabun"] == "不然"

    def test_source_tagged(self, taihoa_csv_content):
        entries = parse_taihoa_csv(io.StringIO(taihoa_csv_content))
        assert all(e["source"] == "taihoa" for e in entries)

    def test_handles_alternates(self, kip_with_alternates_csv):
        """Slash-separated and (替) variants produce multiple entries."""
        entries = parse_taihoa_csv(io.StringIO(kip_with_alternates_csv))
        kip_values = [e["kip_input"] for e in entries]
        assert "tsit8" in kip_values
        assert "tsiah8" in kip_values
        assert "sit8" in kip_values
        assert "kong2--e5" in kip_values


class TestDedupEntries:
    """Deduplicate entries: same hanlo + same rime_key → keep one."""

    def test_removes_exact_duplicates(self):
        entries = [
            {
                "hanlo": "食飯",
                "kip_input": "tsiah8-png7",
                "rime_key": "tsiah png",
                "hoabun": "吃飯",
                "source": "itaigi",
            },
            {
                "hanlo": "食飯",
                "kip_input": "tsiah8-png7",
                "rime_key": "tsiah png",
                "hoabun": "吃飯",
                "source": "taihoa",
            },
        ]
        result = dedup_entries(entries)
        assert len(result) == 1

    def test_keeps_different_pronunciations(self):
        entries = [
            {"hanlo": "食", "kip_input": "tsiah8", "rime_key": "tsiah", "hoabun": "吃", "source": "itaigi"},
            {"hanlo": "食", "kip_input": "sit8", "rime_key": "sit", "hoabun": "吃", "source": "itaigi"},
        ]
        result = dedup_entries(entries)
        assert len(result) == 2

    def test_keeps_different_hanlo(self):
        entries = [
            {
                "hanlo": "食飯",
                "kip_input": "tsiah8-png7",
                "rime_key": "tsiah png",
                "hoabun": "吃飯",
                "source": "itaigi",
            },
            {
                "hanlo": "食餐",
                "kip_input": "tsiah8-png7",
                "rime_key": "tsiah png",
                "hoabun": "吃飯",
                "source": "itaigi",
            },
        ]
        result = dedup_entries(entries)
        assert len(result) == 2


class TestWriteRimeDict:
    """Write entries to Rime dict.yaml format."""

    def test_yaml_header(self, tmp_path):
        outfile = tmp_path / "test.dict.yaml"
        write_rime_dict([], outfile)
        content = outfile.read_text()
        assert "name: phah_taibun" in content
        assert "sort: by_weight" in content
        assert content.startswith("---")
        assert "\n...\n" in content

    def test_entries_written(self, tmp_path):
        entries = [
            {"hanlo": "食飯", "rime_key": "tsiah png", "weight": 500},
        ]
        outfile = tmp_path / "test.dict.yaml"
        write_rime_dict(entries, outfile)
        content = outfile.read_text()
        assert "食飯\ttsiah png\t500" in content

    def test_tab_separated(self, tmp_path):
        entries = [
            {"hanlo": "我", "rime_key": "gua", "weight": 1000},
        ]
        outfile = tmp_path / "test.dict.yaml"
        write_rime_dict(entries, outfile)
        lines = outfile.read_text().splitlines()
        data_lines = [line for line in lines if "\t" in line]
        assert len(data_lines) == 1
        parts = data_lines[0].split("\t")
        assert parts == ["我", "gua", "1000"]


class TestConvertPipeline:
    """End-to-end conversion: CSV files → dict.yaml."""

    def test_converts_itaigi_file(self, tmp_path, itaigi_csv_content):
        csv_file = tmp_path / "itaigi.csv"
        csv_file.write_text(itaigi_csv_content, encoding="utf-8")
        output = tmp_path / "output.dict.yaml"
        convert_chhoetaigi(itaigi_paths=[csv_file], taihoa_paths=[], output_path=output)
        content = output.read_text()
        assert "name: phah_taibun" in content
        assert "𤺪呢\tsian neh" in content

    def test_merges_multiple_sources(self, tmp_path, itaigi_csv_content, taihoa_csv_content):
        itaigi_file = tmp_path / "itaigi.csv"
        itaigi_file.write_text(itaigi_csv_content, encoding="utf-8")
        taihoa_file = tmp_path / "taihoa.csv"
        taihoa_file.write_text(taihoa_csv_content, encoding="utf-8")
        output = tmp_path / "output.dict.yaml"
        convert_chhoetaigi(itaigi_paths=[itaigi_file], taihoa_paths=[taihoa_file], output_path=output)
        content = output.read_text()
        assert "𤺪呢" in content
        assert "á無" in content


class TestConvertCli:
    """Test CLI entry point."""

    def test_cli_with_csv_files(self, tmp_path, itaigi_csv_content):
        # Create a mock ChhoeTaigiDatabase structure
        db_dir = tmp_path / "ChhoeTaigiDatabase"
        db_dir.mkdir()
        itaigi = db_dir / "ChhoeTaigi_iTaigiHoataiTuichiautian.csv"
        itaigi.write_text(itaigi_csv_content, encoding="utf-8")
        out_dir = tmp_path / "output"
        main(["--input", str(tmp_path), "--output", str(out_dir)])
        assert (out_dir / "phah_taibun.dict.yaml").exists()
