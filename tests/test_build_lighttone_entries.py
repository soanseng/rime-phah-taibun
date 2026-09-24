"""Tests for light-tone (輕聲) dictionary entry generation."""

import pytest

from scripts.build_lighttone_entries import (
    build_lighttone_entries,
    collect_lighttone_words,
    compute_lighttone_weight,
    insert_lighttone_marker,
    kip_to_rime_key,
    load_dict,
    load_lighttone_rules,
    reverse_lookup_hanzi,
    unicode_tl_to_numeric,
    write_entries,
)


class TestKipToRimeKey:
    """Convert kip_input to rime_key format."""

    @pytest.mark.parametrize(
        "kip, expected",
        [
            ("tng2--lai5", "tng2  lai5"),
            ("khi2--lai5", "khi2  lai5"),
            ("tng2-lai5", "tng2 lai5"),
            ("tsit8", "tsit8"),
            ("to3-tng2--lai5", "to3 tng2  lai5"),
            ("si2--khi3", "si2  khi3"),
            ("loh8--khi3", "loh8  khi3"),
        ],
    )
    def test_conversion(self, kip, expected):
        assert kip_to_rime_key(kip) == expected

    def test_no_hyphens(self):
        assert kip_to_rime_key("tsit8") == "tsit8"

    def test_only_double_hyphen(self):
        assert kip_to_rime_key("a--b") == "a  b"

    def test_multiple_single_hyphens(self):
        assert kip_to_rime_key("a-b-c") == "a b c"


class TestToneBareSuffixes:
    """Bare particle syllables must gain a digit before reaching the dict.

    Source corpus light-tone particles carry no diacritic (`khi3--ah`), so
    kip_to_rime_key emits a bare token. Bare tokens create exact prism
    edges that shadow abbrev edges (typing `ah`/`tsiah` then finds
    nothing), and validate_dict now fails the build on them.
    """

    def test_bare_suffix_gains_attested_digit(self):
        from scripts.build_lighttone_entries import tone_bare_suffixes

        att = {"啊": {"ah": "ah4"}}
        assert tone_bare_suffixes("khi3  ah", "去--啊", att) == "khi3  ah4"

    def test_already_toned_unchanged(self):
        from scripts.build_lighttone_entries import tone_bare_suffixes

        assert tone_bare_suffixes("khi3  ah4", "去--啊", {}) == "khi3  ah4"

    def test_unattested_returns_none(self):
        from scripts.build_lighttone_entries import tone_bare_suffixes

        assert tone_bare_suffixes("khi2  lih", "起--哩", {}) is None

    def test_bare_middle_token_rejected(self):
        from scripts.build_lighttone_entries import tone_bare_suffixes

        # 僅最終粒子可補調; 中段裸碼(語料異常)必須整條拒絕, 不局部修
        assert tone_bare_suffixes("khi3  ah  e", "去--啊--的", {"的": {"e": "e5"}}) is None

    def test_pipeline_reports_rejected_bare_entries(self, tmp_path, capsys):
        """無典據的裸碼條目必須被明確回報, 不得靜默消失."""
        dict_file = tmp_path / "test.dict.yaml"
        dict_file.write_text("---\nname: test\n...\n轉來\ttng2 lai5\t947\n起\tkhi2\t500\n")
        rules_file = tmp_path / "rules.json"
        rules_file.write_text('[{"hanzi": "來", "tl": "--lâi"}, {"hanzi": "哩", "tl": "--lih"}]')
        freq_file = tmp_path / "freq.tsv"
        freq_file.write_text("khi2--lih\t100\n")
        entries = build_lighttone_entries(dict_file, rules_file, [freq_file])
        hanlo_map = {e["hanlo"] for e in entries}
        assert "起--哩" not in hanlo_map
        err = capsys.readouterr().err
        assert "rejected bare-code entry" in err


class TestUnicodeTlToNumeric:
    """Convert Unicode TL diacritics to numeric tones."""

    @pytest.mark.parametrize(
        "text, expected",
        [
            ("lâi", "lai5"),
            ("khí", "khi2"),
            ("khì", "khi3"),
            ("sī", "si7"),
            ("tio̍h", "tioh8"),
            ("guá", "gua2"),
            ("bô", "bo5"),
        ],
    )
    def test_single_syllable(self, text, expected):
        assert unicode_tl_to_numeric(text) == expected

    def test_multi_syllable(self):
        assert unicode_tl_to_numeric("khí-lâi") == "khi2-lai5"

    def test_no_diacritics(self):
        assert unicode_tl_to_numeric("ka") == "ka"

    def test_empty_string(self):
        assert unicode_tl_to_numeric("") == ""

    def test_tone_1_no_mark(self):
        # Tone 1 has no diacritic; should remain without tone number
        assert unicode_tl_to_numeric("tsi") == "tsi"

    def test_multi_syllable_complement(self):
        assert unicode_tl_to_numeric("tńg-lâi") == "tng2-lai5"

    def test_macron_tone_7(self):
        assert unicode_tl_to_numeric("tn̄g") == "tng7"

    def test_grave_tone_3(self):
        assert unicode_tl_to_numeric("kè") == "ke3"

    def test_complex_multi_syllable(self):
        assert unicode_tl_to_numeric("tām-po̍h-á") == "tam7-poh8-a2"


class TestInsertLighttoneMarker:
    """Insert -- into hanzi string at correct position."""

    @pytest.mark.parametrize(
        "hanlo, prefix_count, expected",
        [
            ("轉來", 1, "轉--來"),
            ("出來", 1, "出--來"),
            ("起來", 1, "起--來"),
            ("倒轉來", 2, "倒轉--來"),
            ("落去", 1, "落--去"),
        ],
    )
    def test_pure_hanzi(self, hanlo, prefix_count, expected):
        assert insert_lighttone_marker(hanlo, prefix_count) == expected

    def test_single_char_prefix(self):
        assert insert_lighttone_marker("食飽", 1) == "食--飽"

    def test_three_char_word(self):
        assert insert_lighttone_marker("起來去", 1) == "起--來去"


class TestComputeLighttoneWeight:
    """Compute weight for light-tone entries."""

    def test_minimum_bound(self):
        # Very low count should still be at least 300
        assert compute_lighttone_weight(0) >= 300

    def test_maximum_bound(self):
        # Very high count should be capped at 1500
        assert compute_lighttone_weight(10**9) <= 1500

    def test_within_range(self):
        weight = compute_lighttone_weight(100)
        assert 300 <= weight <= 1500

    def test_weight_from_count_only(self):
        """Builder emits the raw formula: Step 9 owns the parent cap.

        A 10000-count word lands at 300 + 150 * log10(10001) ~ 900 with no
        parent knowledge at all; enforce_lighttone_cap (build_frequency,
        Step 9 of build_all) is the single authority for ranking a
        light-tone row below its plain variant.
        """
        assert compute_lighttone_weight(10000) == 900
        assert compute_lighttone_weight(0) == 300

    def test_exact_formula(self):
        weight = compute_lighttone_weight(100)
        expected = int(300 + 150 * 2.004321)  # log10(101) ~ 2.004
        assert abs(weight - expected) <= 2  # Allow rounding

    def test_monotonically_increasing(self):
        w1 = compute_lighttone_weight(10)
        w2 = compute_lighttone_weight(100)
        w3 = compute_lighttone_weight(1000)
        assert w1 <= w2 <= w3


class TestLoadDict:
    """Load dictionary into lookup tables."""

    def test_basic_load(self, tmp_path):
        dict_file = tmp_path / "test.dict.yaml"
        dict_file.write_text("---\nname: test\n...\n轉來\ttng2 lai5\t947\n出來\ttshut4 lai5\t1320\n")
        kip_to_hanlo, existing, _kip_to_weight, _hw = load_dict(dict_file)
        assert "tng2-lai5" in kip_to_hanlo
        assert "轉來" in kip_to_hanlo["tng2-lai5"]
        assert ("轉來", "tng2 lai5") in existing

    def test_skips_yaml_header(self, tmp_path):
        dict_file = tmp_path / "test.dict.yaml"
        dict_file.write_text("---\nname: test\nversion: 0.1\nsort: by_weight\n...\n食\ttsiah8\t800\n")
        kip_to_hanlo, _existing, _, _hw = load_dict(dict_file)
        assert "tsiah8" in kip_to_hanlo

    def test_existing_lighttone_entries_tracked(self, tmp_path):
        dict_file = tmp_path / "test.dict.yaml"
        dict_file.write_text("---\n...\n轉--來\ttng2  lai5\t500\n")
        _, existing, _, _hw = load_dict(dict_file)
        assert ("轉--來", "tng2  lai5") in existing

    def test_lighttone_entries_not_in_kip_lookup(self, tmp_path):
        """Light-tone entries (with --) should not be indexed in kip_to_hanlo."""
        dict_file = tmp_path / "test.dict.yaml"
        dict_file.write_text("---\n...\n轉--來\ttng2  lai5\t500\n")
        kip_to_hanlo, _, _, _hw = load_dict(dict_file)
        assert "tng2--lai5" not in kip_to_hanlo

    def test_weight_tracking(self, tmp_path):
        dict_file = tmp_path / "test.dict.yaml"
        dict_file.write_text("---\n...\n轉來\ttng2 lai5\t947\n轉來\ttng2 lai5\t500\n")
        _, _, kip_to_weight, _hw = load_dict(dict_file)
        # Should track max weight
        assert kip_to_weight["tng2-lai5"] == 947

    def test_case_normalization(self, tmp_path):
        dict_file = tmp_path / "test.dict.yaml"
        dict_file.write_text("---\n...\nTest\tTng2 Lai5\t500\n")
        kip_to_hanlo, _, _, _hw = load_dict(dict_file)
        assert "tng2-lai5" in kip_to_hanlo


class TestLoadLighttoneRules:
    """Load lighttone_rules.json into suffix_hanzi mapping."""

    def test_basic_load(self, tmp_path):
        rules_file = tmp_path / "rules.json"
        rules_file.write_text('[{"tl": "--lâi", "hanzi": "來", "rule": "補語"}]')
        suffix_hanzi = load_lighttone_rules(rules_file)
        assert suffix_hanzi["lai5"] == "來"

    def test_multi_syllable(self, tmp_path):
        rules_file = tmp_path / "rules.json"
        rules_file.write_text('[{"tl": "--khí-lâi", "hanzi": "起來", "rule": "補語"}]')
        suffix_hanzi = load_lighttone_rules(rules_file)
        assert suffix_hanzi["khi2-lai5"] == "起來"

    def test_no_diacritic_suffix(self, tmp_path):
        rules_file = tmp_path / "rules.json"
        rules_file.write_text('[{"tl": "--ka", "hanzi": "家", "rule": "分寫"}]')
        suffix_hanzi = load_lighttone_rules(rules_file)
        assert suffix_hanzi["ka"] == "家"

    def test_first_mapping_wins(self, tmp_path):
        rules_file = tmp_path / "rules.json"
        rules_file.write_text(
            '[{"tl": "--ah", "hanzi": "啊", "rule": "分寫"},{"tl": "--ah", "hanzi": "矣", "rule": "分寫"}]'
        )
        suffix_hanzi = load_lighttone_rules(rules_file)
        assert suffix_hanzi["ah"] == "啊"


class TestCollectLighttoneWords:
    """Collect light-tone words from corpus freq TSVs."""

    def test_basic_collection(self, tmp_path):
        freq_file = tmp_path / "freq.tsv"
        freq_file.write_text("tng2--lai5\t678\nkhi3\t1000\n")
        result = collect_lighttone_words([freq_file])
        assert result["tng2--lai5"] == 678
        assert "khi3" not in result

    def test_merge_across_files(self, tmp_path):
        f1 = tmp_path / "freq1.tsv"
        f2 = tmp_path / "freq2.tsv"
        f1.write_text("tng2--lai5\t100\n")
        f2.write_text("tng2--lai5\t200\n")
        result = collect_lighttone_words([f1, f2])
        assert result["tng2--lai5"] == 300

    def test_case_normalization(self, tmp_path):
        freq_file = tmp_path / "freq.tsv"
        freq_file.write_text("Tng2--Lai5\t50\n")
        result = collect_lighttone_words([freq_file])
        assert "tng2--lai5" in result

    def test_skip_trailing_double_hyphen(self, tmp_path):
        freq_file = tmp_path / "freq.tsv"
        freq_file.write_text("tsa-poo1--\t3\n")
        result = collect_lighttone_words([freq_file])
        assert len(result) == 0

    def test_skip_malformed_parentheses(self, tmp_path):
        freq_file = tmp_path / "freq.tsv"
        freq_file.write_text("siá--ê(1\t2\n")
        result = collect_lighttone_words([freq_file])
        assert len(result) == 0

    def test_nonexistent_file(self, tmp_path):
        result = collect_lighttone_words([tmp_path / "missing.tsv"])
        assert len(result) == 0

    def test_empty_file(self, tmp_path):
        freq_file = tmp_path / "freq.tsv"
        freq_file.write_text("")
        result = collect_lighttone_words([freq_file])
        assert len(result) == 0


class TestReverseLookupHanzi:
    """Reverse-lookup hanzi for light-tone words."""

    def test_whole_word_match(self):
        kip_to_hanlo = {"tng2-lai5": {"轉來"}}
        suffix_hanzi = {"lai5": "來"}
        result = reverse_lookup_hanzi("tng2--lai5", kip_to_hanlo, suffix_hanzi)
        assert "轉--來" in result

    def test_syllable_assembly(self):
        kip_to_hanlo = {"khi3": {"去"}}
        suffix_hanzi = {"lih": "哩"}
        result = reverse_lookup_hanzi("khi3--lih", kip_to_hanlo, suffix_hanzi)
        assert "去--哩" in result

    def test_romanization_prefix_assembly_skipped(self):
        # "chò" is a valid han-lo entry but has no hanzi; assembling it
        # with a suffix produced romanization-first candidates like
        # "chò--的" that hijack sentence composition over 做--的.
        kip_to_hanlo = {"tso3": {"chò", "做"}}
        suffix_hanzi = {"e5": "的"}
        result = reverse_lookup_hanzi("tso3--e5", kip_to_hanlo, suffix_hanzi)
        assert "做--的" in result
        assert "chò--的" not in result

    def test_assembly_keeps_only_top_weight_prefix(self):
        # 佐--的 and 做--的 tie at the K-invariant floor (4184) when both
        # are emitted, and sorted() breaks the tie toward 佐--的, hijacking
        # sentence composition. Emit only the highest base-weight prefix.
        kip_to_hanlo = {"tso3": {"做", "佐"}}
        suffix_hanzi = {"e5": "的"}
        hanlo_weight = {("tso3", "做"): 1539, ("tso3", "佐"): 880}
        result = reverse_lookup_hanzi("tso3--e5", kip_to_hanlo, suffix_hanzi, hanlo_weight)
        assert result == ["做--的"]

    def test_no_match(self):
        result = reverse_lookup_hanzi("xxx--yyy", {}, {})
        assert len(result) == 0

    def test_whole_word_preferred_over_assembly(self):
        kip_to_hanlo = {
            "tng2-lai5": {"轉來"},
            "tng2": {"轉"},
        }
        suffix_hanzi = {"lai5": "來"}
        result = reverse_lookup_hanzi("tng2--lai5", kip_to_hanlo, suffix_hanzi)
        # Whole-word match should produce "轉--來"
        assert "轉--來" in result

    def test_invalid_format_no_double_hyphen(self):
        result = reverse_lookup_hanzi("tng2-lai5", {"tng2-lai5": {"轉來"}}, {})
        assert len(result) == 0

    def test_suffix_from_dict_single_candidate(self):
        """When suffix is not in lighttone_rules but has single dict match."""
        kip_to_hanlo = {"si2": {"死"}, "khi3": {"去"}}
        suffix_hanzi = {}
        result = reverse_lookup_hanzi("si2--khi3", kip_to_hanlo, suffix_hanzi)
        assert "死--去" in result

    def test_suffix_from_dict_multiple_candidates_skipped(self):
        """When suffix has multiple dict matches, skip assembly."""
        kip_to_hanlo = {"si2": {"死"}, "e5": {"的", "兮"}}
        suffix_hanzi = {}
        result = reverse_lookup_hanzi("si2--e5", kip_to_hanlo, suffix_hanzi)
        assert len(result) == 0

    def test_multi_syllable_prefix(self):
        kip_to_hanlo = {"to3-tng2-lai5": {"倒轉來"}}
        suffix_hanzi = {}
        result = reverse_lookup_hanzi("to3-tng2--lai5", kip_to_hanlo, suffix_hanzi)
        assert "倒轉--來" in result

    def test_multiple_lighttone_positions(self):
        """Entries with two -- markers (e.g., reduplicative forms)."""
        kip_to_hanlo = {"tshuah4": {"擦"}}
        suffix_hanzi = {"tsit8-e7": "一下"}
        result = reverse_lookup_hanzi(
            "tshuah4--tsit8-e7--tshuah4--tsit8-e7",
            kip_to_hanlo,
            suffix_hanzi,
        )
        assert len(result) > 0
        assert "--" in result[0]

    def test_two_lighttone_simple(self):
        """Two -- segments, each resolvable."""
        kip_to_hanlo = {"a2": {"仔"}}
        suffix_hanzi = {"a2": "仔", "lai5": "來"}
        result = reverse_lookup_hanzi("a2--lai5--a2", kip_to_hanlo, suffix_hanzi)
        assert "仔--來--仔" in result

    def test_multiple_lighttone_unresolvable(self):
        """If any segment fails, return empty."""
        kip_to_hanlo = {"a2": {"仔"}}
        suffix_hanzi = {}
        result = reverse_lookup_hanzi("a2--xxx--a2", kip_to_hanlo, suffix_hanzi)
        assert len(result) == 0

    def test_rules_disambiguate_multiple_dict_candidates(self):
        """When dict has multiple suffix candidates, lighttone_rules disambiguates."""
        kip_to_hanlo = {"si2": {"死"}, "e5": {"的", "兮"}}
        suffix_hanzi = {"e5": "的"}  # Rules say e5 → 的
        result = reverse_lookup_hanzi("si2--e5", kip_to_hanlo, suffix_hanzi)
        assert "死--的" in result


class TestDeduplication:
    """Deduplication of entries already in dictionary."""

    def test_skip_existing_entries(self, tmp_path):
        dict_file = tmp_path / "test.dict.yaml"
        dict_file.write_text("---\n...\n轉來\ttng2 lai5\t947\n轉--來\ttng2  lai5\t500\n")
        rules_file = tmp_path / "rules.json"
        rules_file.write_text('[{"tl": "--lâi", "hanzi": "來", "rule": "補語"}]')
        freq_file = tmp_path / "freq.tsv"
        freq_file.write_text("tng2--lai5\t678\n")

        entries = build_lighttone_entries(dict_file, rules_file, [freq_file])
        # 轉--來 already exists, should not be duplicated
        hanlo_set = {e["hanlo"] for e in entries}
        assert "轉--來" not in hanlo_set


class TestEndToEnd:
    """End-to-end test with sample data."""

    def test_full_pipeline(self, tmp_path):
        # Create sample dict
        dict_file = tmp_path / "test.dict.yaml"
        dict_file.write_text(
            "---\nname: test\n...\n"
            "轉來\ttng2 lai5\t947\n"
            "出來\ttshut4 lai5\t1320\n"
            "起來\tkhi2 lai5\t2146\n"
            "去\tkhi3\t800\n"
            "死\tsi2\t700\n"
        )

        # Create rules
        rules_file = tmp_path / "rules.json"
        rules_file.write_text(
            '[{"tl": "--lâi", "hanzi": "來", "rule": "補語"},{"tl": "--khì", "hanzi": "去", "rule": "補語"}]'
        )

        # Create freq TSV
        freq_file = tmp_path / "freq.tsv"
        freq_file.write_text("tng2--lai5\t678\ntshut4--lai5\t371\nkhi2--lai5\t319\nsi2--khi3\t142\n")

        entries = build_lighttone_entries(dict_file, rules_file, [freq_file])

        hanlo_map = {e["hanlo"]: e for e in entries}
        assert "轉--來" in hanlo_map
        assert "出--來" in hanlo_map
        assert "起--來" in hanlo_map
        assert "死--去" in hanlo_map

        # Check rime_key format
        assert hanlo_map["轉--來"]["rime_key"] == "tng2  lai5"
        assert hanlo_map["出--來"]["rime_key"] == "tshut4  lai5"
        assert hanlo_map["死--去"]["rime_key"] == "si2  khi3"

        # Check weights are within bounds
        for entry in entries:
            assert 300 <= entry["weight"] <= 1500

    def test_write_entries(self, tmp_path):
        output_file = tmp_path / "output.tsv"
        entries = [
            {"hanlo": "轉--來", "rime_key": "tng2  lai5", "weight": 500},
            {"hanlo": "出--來", "rime_key": "tshut4  lai5", "weight": 400},
        ]
        write_entries(entries, output_file)
        lines = output_file.read_text().strip().split("\n")
        assert len(lines) == 2
        assert lines[0] == "轉--來\ttng2  lai5\t500"
        assert lines[1] == "出--來\ttshut4  lai5\t400"

    def test_weight_uncapped_at_builder_step9_caps(self, tmp_path):
        """Builder emits the formula weight even with a plain parent present.

        The 轉來 tng2 lai5=500 parent must NOT cap 轉--來 here: the builder
        emits uncapped corpus weights and Step 9
        (build_frequency.enforce_lighttone_cap) applies the parent-100 cap
        to the assembled dictionary as the single authority.
        """
        dict_file = tmp_path / "test.dict.yaml"
        dict_file.write_text("---\n...\n轉來\ttng2 lai5\t500\n")
        rules_file = tmp_path / "rules.json"
        rules_file.write_text('[{"tl": "--lâi", "hanzi": "來", "rule": "補語"}]')
        freq_file = tmp_path / "freq.tsv"
        freq_file.write_text("tng2--lai5\t10000\n")

        entries = build_lighttone_entries(dict_file, rules_file, [freq_file])
        weights = [e["weight"] for e in entries if e["hanlo"] == "轉--來"]
        assert weights == [900]  # 300 + 150 * log10(10001), clamp, no parent cap

    def test_cli_main(self, tmp_path):
        dict_file = tmp_path / "test.dict.yaml"
        dict_file.write_text("---\n...\n轉來\ttng2 lai5\t947\n")
        rules_file = tmp_path / "rules.json"
        rules_file.write_text('[{"tl": "--lâi", "hanzi": "來", "rule": "補語"}]')
        freq_file = tmp_path / "freq.tsv"
        freq_file.write_text("tng2--lai5\t100\n")
        output_file = tmp_path / "output.tsv"

        from scripts.build_lighttone_entries import main

        main(
            [
                "--dict",
                str(dict_file),
                "--rules",
                str(rules_file),
                "--corpus-freq",
                str(freq_file),
                "--output",
                str(output_file),
            ]
        )

        assert output_file.exists()
        content = output_file.read_text()
        assert "轉--來" in content


class TestBuildDeterminism:
    """Output order must not depend on the process hash seed (PLAN 9-2H spirit)."""

    def test_output_is_hash_seed_independent(self, tmp_path):
        import subprocess
        import sys

        dict_file = tmp_path / "test.dict.yaml"
        dict_file.write_text(
            "---\n...\n轉\ttng2\t947\n傳\ttng2\t800\n團\ttng2\t700\n屯\ttng2\t600\n",
            encoding="utf-8",
        )
        rules_file = tmp_path / "rules.json"
        rules_file.write_text('[{"tl": "--lâi", "hanzi": "來", "rule": "補語"}]', encoding="utf-8")
        freq_file = tmp_path / "freq.tsv"
        freq_file.write_text("tng2--lai5\t678\n", encoding="utf-8")

        outputs = []
        for seed in ("1", "2"):
            out = tmp_path / f"out-{seed}.tsv"
            env = {"PYTHONHASHSEED": seed, "PATH": "/usr/bin:/bin"}
            subprocess.run(
                [
                    sys.executable,
                    "scripts/build_lighttone_entries.py",
                    "--dict",
                    str(dict_file),
                    "--rules",
                    str(rules_file),
                    "--corpus-freq",
                    str(freq_file),
                    "--output",
                    str(out),
                ],
                check=True,
                env=env,
            )
            outputs.append(out.read_text(encoding="utf-8"))

        assert outputs[0] == outputs[1], "light-tone output order varies with hash seed"
