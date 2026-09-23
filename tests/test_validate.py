"""Tests for dictionary validation."""

from pathlib import Path

import pytest

from scripts.validate_dict import main, validate_dict_format, verify_known_keys, verify_poj_integrity


class TestValidateDictFormat:
    """Validate Rime dict.yaml format correctness."""

    def test_valid_dict(self, tmp_path):
        dictfile = tmp_path / "test.dict.yaml"
        dictfile.write_text('---\nname: test\nversion: "0.1.0"\nsort: by_weight\n...\n食飯\ttsiah8 png7\t500\n')
        errors = validate_dict_format(dictfile)
        assert len(errors) == 0

    def test_detects_digitless_syllable_in_code(self, tmp_path):
        """Bare syllables create exact prism edges that shadow abbrev edges.

        Typing `ah`/`tsi`/`tsiah` then finds no candidates (verified against
        a pure librime scratch build); every code syllable must carry a tone
        digit.
        """
        dictfile = tmp_path / "test.dict.yaml"
        dictfile.write_text('---\nname: test\nversion: "0.1.0"\nsort: by_weight\n...\n去--啊\tkhi3 ah\t100\n')
        errors = validate_dict_format(dictfile)
        assert any("digitless" in error for error in errors)

    def test_committed_dictionary_codes_all_toned(self):
        dictfile = Path(__file__).parents[1] / "schema" / "phah_taibun.dict.yaml"
        errors = validate_dict_format(dictfile)
        assert not [error for error in errors if "digitless" in error.lower()]

    def test_missing_header(self, tmp_path):
        dictfile = tmp_path / "test.dict.yaml"
        dictfile.write_text("食飯\ttsiah8 png7\t500\n")
        errors = validate_dict_format(dictfile)
        assert any("header" in e.lower() for e in errors)

    def test_bad_tab_count(self, tmp_path):
        dictfile = tmp_path / "test.dict.yaml"
        dictfile.write_text('---\nname: test\nversion: "0.1.0"\nsort: by_weight\n...\n食飯 tsiah8 png7 500\n')
        errors = validate_dict_format(dictfile)
        assert any("tab" in e.lower() or "format" in e.lower() for e in errors)

    def test_detects_duplicates(self, tmp_path):
        dictfile = tmp_path / "test.dict.yaml"
        dictfile.write_text(
            '---\nname: test\nversion: "0.1.0"\nsort: by_weight\n...\n食飯\ttsiah8 png7\t500\n食飯\ttsiah8 png7\t300\n'
        )
        errors = validate_dict_format(dictfile)
        assert any("duplicate" in e.lower() for e in errors)

    def test_detects_non_canonical_rime_key(self, tmp_path):
        dictfile = tmp_path / "test.dict.yaml"
        dictfile.write_text('---\nname: test\nversion: "0.1.0"\nsort: by_weight\n...\n你好\tlí hó\t500\n')
        errors = validate_dict_format(dictfile)
        assert any("rime key" in e.lower() for e in errors)

        dictfile = tmp_path / "test.dict.yaml"
        dictfile.write_text('---\nname: test\nversion: "0.1.0"\nsort: by_weight\n...\n食(替)\ttsiah8\t500\n')
        errors = validate_dict_format(dictfile)
        assert any("editorial marker" in error.lower() for error in errors)

    def test_committed_dictionary_has_no_editorial_markers(self):
        dictfile = Path(__file__).parents[1] / "schema" / "phah_taibun.dict.yaml"
        errors = validate_dict_format(dictfile)
        assert not [error for error in errors if "editorial marker" in error.lower()]


class TestValidateCli:
    """Test CLI entry point."""

    def test_valid_file_exits_zero(self, tmp_path):
        dictfile = tmp_path / "test.dict.yaml"
        dictfile.write_text('---\nname: test\nversion: "0.1.0"\nsort: by_weight\n...\n食飯\ttsiah8 png7\t500\n')
        with pytest.raises(SystemExit) as exc_info:
            main([str(dictfile)])
        assert exc_info.value.code == 0

    def test_invalid_file_exits_nonzero(self, tmp_path):
        dictfile = tmp_path / "test.dict.yaml"
        dictfile.write_text("食飯\ttsiah8 png7\t500\n")
        with pytest.raises(SystemExit) as exc_info:
            main([str(dictfile)])
        assert exc_info.value.code == 1

    def test_missing_file_skips(self, tmp_path):
        with pytest.raises(SystemExit) as exc_info:
            main([str(tmp_path / "nonexistent.yaml")])
        assert exc_info.value.code == 0


class TestVerifyPojIntegrity:
    """Fatal TL-POJ conversion integrity gate (PLAN section 9-2F)."""

    @staticmethod
    def _triple(poj_text="chia̍h-pn̄g"):
        return [
            {"hanlo": "食飯", "kip_input": "tsiah8-png7", "rime_key": "tsiah8 png7", "source": "moe"},
            {"hanlo": "tsia̍h-pn̄g", "kip_input": "tsiah8-png7", "rime_key": "tsiah8 png7", "source": "moe_tl"},
            {"hanlo": poj_text, "kip_input": "tsiah8-png7", "rime_key": "tsiah8 png7", "source": "moe_poj"},
        ]

    def test_consistent_triple_passes(self):
        assert verify_poj_integrity(self._triple()) == []

    def test_stale_poj_text_fails(self):
        errors = verify_poj_integrity(self._triple(poj_text="chhia̍h-pn̄g"))
        assert errors and "tsiah8-png7" in errors[0]

    def test_missing_poj_sibling_fails(self):
        entries = self._triple()[:2]
        errors = verify_poj_integrity(entries)
        assert errors and "moe_poj" in errors[0]

    def test_non_moe_sources_ignored(self):
        entries = [
            {"hanlo": "Doraemon", "kip_input": "lo1-la2-e2-bong7", "rime_key": "lo1 la2 e2 bong7", "source": "taihoa"},
        ]
        assert verify_poj_integrity(entries) == []


class TestVerifyKnownKeys:
    """Post-build smoke: fixed queries must hit at least N rows (PLAN 9-2G)."""

    def _write(self, path, rows):
        body = "".join(f"{t}\t{k}\t{w}\n" for t, k, w in rows)
        path.write_text(f'---\nname: t\nversion: "1"\n...\n{body}', encoding="utf-8")

    def _fixture(self, tmp_path, spec):
        fx = tmp_path / "known_keys.yaml"
        fx.write_text(spec, encoding="utf-8")
        return fx

    def test_counts_exact_and_first_syllable_prefix(self, tmp_path):
        d = tmp_path / "d.dict.yaml"
        self._write(
            d,
            [
                ("食", "tsiah8", 500),
                ("食飯", "tsiah8 png7", 900),
                ("飯", "png7", 300),
            ],
        )
        fx = self._fixture(tmp_path, "tsiah8: 2\npng7: 1\n")
        assert verify_known_keys(d, fx) == []

    def test_below_threshold_fails(self, tmp_path):
        d = tmp_path / "d.dict.yaml"
        self._write(d, [("食", "tsiah8", 500)])
        fx = self._fixture(tmp_path, "tsiah8: 5\n")
        errors = verify_known_keys(d, fx)
        assert errors and "tsiah8" in errors[0]

    def test_missing_fixture_fails(self, tmp_path):
        d = tmp_path / "d.dict.yaml"
        self._write(d, [("食", "tsiah8", 500)])
        errors = verify_known_keys(d, tmp_path / "nope.yaml")
        assert errors and "fixture" in errors[0].lower()

    def test_committed_dictionary_meets_fixture(self):
        root = Path(__file__).parents[1]
        errors = verify_known_keys(
            root / "schema" / "phah_taibun.dict.yaml",
            root / "tests" / "fixtures" / "known_keys.yaml",
        )
        assert errors == []

    def test_cli_known_keys_flag_fails_below_threshold(self, tmp_path):
        d = tmp_path / "d.dict.yaml"
        self._write(d, [("食", "tsiah8", 500)])
        fx = self._fixture(tmp_path, "tsiah8: 5\n")
        with pytest.raises(SystemExit) as exc_info:
            main([str(d), "--known-keys", str(fx)])
        assert exc_info.value.code == 1
