"""Tests for ChhoeTaigi CSV to Rime dictionary conversion."""

import io

from scripts.convert_chhoetaigi import (
    clean_kip_input,
    convert_chhoetaigi,
    dedup_entries,
    main,
    parse_generic_csv,
    parse_itaigi_csv,
    parse_taihoa_csv,
    source_name_from_filename,
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


class TestConvertWithCorpusFreq:
    """Corpus frequency data should boost weights for matching entries."""

    def test_corpus_freq_boosts_weight(self, tmp_path):
        from scripts.build_frequency import load_corpus_frequencies

        csv_content = (
            "KipInput,HanLoTaibunKip,HoaBun\n"
            "tsiah8-png7,食飯,吃飯\n"
            "khi3,去,去\n"
        )
        csv_path = tmp_path / "itaigi.csv"
        csv_path.write_text(csv_content, encoding="utf-8-sig")
        freq_path = tmp_path / "corpus_freq.tsv"
        freq_path.write_text("tsiah8-png7\t50\n", encoding="utf-8")
        corpus_freq = load_corpus_frequencies(freq_path)

        out_no_freq = tmp_path / "no_freq.yaml"
        convert_chhoetaigi([csv_path], [], out_no_freq)

        out_with_freq = tmp_path / "with_freq.yaml"
        convert_chhoetaigi([csv_path], [], out_with_freq, corpus_freq=corpus_freq)

        def get_weights(path):
            weights = {}
            for line in path.read_text().splitlines():
                if "\t" in line and not line.startswith(
                    ("#", "-", "name", "version", "sort", "use_preset", "...")
                ):
                    parts = line.split("\t")
                    if len(parts) >= 3:
                        weights[parts[0]] = int(parts[2])
            return weights

        w_no = get_weights(out_no_freq)
        w_yes = get_weights(out_with_freq)
        assert w_yes["食飯"] > w_no["食飯"]
        assert w_yes["去"] == w_no["去"]


class TestParseGenericCsv:
    """Parse generic ChhoeTaigi CSVs with column name fallbacks."""

    def test_basic_parse_with_kip_columns(self):
        csv_data = (
            "KipInput,HanLoTaibunKip,HoaBun\n"
            "tsiah8-png7,食飯,吃飯\n"
            "khi3,去,去\n"
        )
        entries = parse_generic_csv(io.StringIO(csv_data), "maryknoll")
        assert len(entries) == 2
        assert entries[0]["hanlo"] == "食飯"
        assert entries[0]["kip_input"] == "tsiah8-png7"
        assert entries[0]["rime_key"] == "tsiah png"
        assert entries[0]["hoabun"] == "吃飯"
        assert entries[0]["source"] == "maryknoll"

    def test_fallback_to_poj_columns(self):
        """When KipInput/HanLoTaibunKip are missing, use Poj columns."""
        csv_data = (
            "PojInput,HanLoTaibunPoj,HoaBun\n"
            "chiah8-png7,食飯,吃飯\n"
        )
        entries = parse_generic_csv(io.StringIO(csv_data), "kamjitian")
        assert len(entries) == 1
        assert entries[0]["hanlo"] == "食飯"
        assert entries[0]["kip_input"] == "chiah8-png7"
        assert entries[0]["source"] == "kamjitian"

    def test_prefers_kip_over_poj(self):
        """When both KipInput and PojInput exist, use KipInput."""
        csv_data = (
            "KipInput,PojInput,HanLoTaibunKip,HanLoTaibunPoj,HoaBun\n"
            "tsiah8-png7,chiah8-png7,食飯kip,食飯poj,吃飯\n"
        )
        entries = parse_generic_csv(io.StringIO(csv_data), "embree")
        assert len(entries) == 1
        assert entries[0]["kip_input"] == "tsiah8-png7"
        assert entries[0]["hanlo"] == "食飯kip"

    def test_skips_rows_without_pronunciation(self):
        csv_data = (
            "KipInput,HanLoTaibunKip,HoaBun\n"
            ",食飯,吃飯\n"
            "khi3,去,去\n"
        )
        entries = parse_generic_csv(io.StringIO(csv_data), "taijit")
        assert len(entries) == 1

    def test_skips_rows_without_hanlo(self):
        csv_data = (
            "KipInput,HanLoTaibunKip,HoaBun\n"
            "tsiah8-png7,,吃飯\n"
            "khi3,去,去\n"
        )
        entries = parse_generic_csv(io.StringIO(csv_data), "taijit")
        assert len(entries) == 1

    def test_handles_slash_variants(self):
        csv_data = (
            "KipInput,HanLoTaibunKip,HoaBun\n"
            "tsiah8/sit8,食,吃\n"
        )
        entries = parse_generic_csv(io.StringIO(csv_data), "pehoe")
        assert len(entries) == 2
        kips = [e["kip_input"] for e in entries]
        assert "tsiah8" in kips
        assert "sit8" in kips

    def test_source_name_preserved(self):
        csv_data = "KipInput,HanLoTaibunKip,HoaBun\nkhi3,去,去\n"
        entries = parse_generic_csv(io.StringIO(csv_data), "sitbut")
        assert entries[0]["source"] == "sitbut"

    def test_empty_hoabun_is_ok(self):
        csv_data = "KipInput,HanLoTaibunKip,HoaBun\nkhi3,去,\n"
        entries = parse_generic_csv(io.StringIO(csv_data), "embree")
        assert len(entries) == 1
        assert entries[0]["hoabun"] == ""


class TestSourceNameFromFilename:
    """Map ChhoeTaigi CSV filenames to source identifiers."""

    def test_known_filenames(self):
        assert source_name_from_filename("ChhoeTaigi_KamJitian.csv") == "kamjitian"
        assert source_name_from_filename("ChhoeTaigi_MaryknollTaiengSutian.csv") == "maryknoll"
        assert source_name_from_filename("ChhoeTaigi_EmbreeTaiengSutian.csv") == "embree"
        assert source_name_from_filename("ChhoeTaigi_TaijitToaSutian.csv") == "taijit"
        assert source_name_from_filename("ChhoeTaigi_KauiokpooTaigiSutian.csv") == "moe"
        assert source_name_from_filename("ChhoeTaigi_TaioanPehoeKichhooGiku.csv") == "pehoe"
        assert source_name_from_filename("ChhoeTaigi_TaioanSitbutMialui.csv") == "sitbut"

    def test_unknown_filename(self):
        assert source_name_from_filename("ChhoeTaigi_SomethingElse.csv") is None

    def test_itaigi_and_taihoa(self):
        assert source_name_from_filename("ChhoeTaigi_iTaigiHoataiTuichiautian.csv") == "itaigi"
        assert source_name_from_filename("ChhoeTaigi_TaihoaSoanntengTuichiautian.csv") == "taihoa"


class TestConvertWithGenericPaths:
    """End-to-end conversion with generic CSV paths."""

    def test_generic_paths_included(self, tmp_path):
        csv_data = "KipInput,HanLoTaibunKip,HoaBun\nkhi3,去,去\n"
        csv_path = tmp_path / "generic.csv"
        csv_path.write_text(csv_data, encoding="utf-8")
        output = tmp_path / "output.dict.yaml"
        convert_chhoetaigi(
            itaigi_paths=[], taihoa_paths=[], output_path=output,
            generic_paths=[(csv_path, "maryknoll")],
        )
        content = output.read_text()
        assert "去\tkhi" in content


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

    def test_cli_auto_discovers_generic_csvs(self, tmp_path):
        """CLI should auto-discover additional ChhoeTaigi CSVs."""
        db_dir = tmp_path / "ChhoeTaigiDatabase"
        db_dir.mkdir()
        # Create an iTaigi CSV (known special)
        itaigi_data = "KipInput,HanLoTaibunKip,HoaBun\nkhi3,去,去\n"
        itaigi = db_dir / "ChhoeTaigi_iTaigiHoataiTuichiautian.csv"
        itaigi.write_text(itaigi_data, encoding="utf-8")
        # Create a generic CSV (should be auto-discovered)
        generic_data = "KipInput,HanLoTaibunKip,HoaBun\ntsiah8-png7,食飯,吃飯\n"
        generic = db_dir / "ChhoeTaigi_KamJitian.csv"
        generic.write_text(generic_data, encoding="utf-8")
        out_dir = tmp_path / "output"
        main(["--input", str(tmp_path), "--output", str(out_dir)])
        content = (out_dir / "phah_taibun.dict.yaml").read_text()
        assert "去" in content
        assert "食飯" in content
