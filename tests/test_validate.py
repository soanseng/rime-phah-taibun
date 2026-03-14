"""Tests for dictionary validation."""

import pytest

from scripts.validate_dict import main, validate_dict_format


class TestValidateDictFormat:
    """Validate Rime dict.yaml format correctness."""

    def test_valid_dict(self, tmp_path):
        dictfile = tmp_path / "test.dict.yaml"
        dictfile.write_text('---\nname: test\nversion: "0.1.0"\nsort: by_weight\n...\n食飯\ttsiah png\t500\n')
        errors = validate_dict_format(dictfile)
        assert len(errors) == 0

    def test_missing_header(self, tmp_path):
        dictfile = tmp_path / "test.dict.yaml"
        dictfile.write_text("食飯\ttsiah png\t500\n")
        errors = validate_dict_format(dictfile)
        assert any("header" in e.lower() for e in errors)

    def test_bad_tab_count(self, tmp_path):
        dictfile = tmp_path / "test.dict.yaml"
        dictfile.write_text('---\nname: test\nversion: "0.1.0"\nsort: by_weight\n...\n食飯 tsiah png 500\n')
        errors = validate_dict_format(dictfile)
        assert any("tab" in e.lower() or "format" in e.lower() for e in errors)

    def test_detects_duplicates(self, tmp_path):
        dictfile = tmp_path / "test.dict.yaml"
        dictfile.write_text(
            '---\nname: test\nversion: "0.1.0"\nsort: by_weight\n...\n食飯\ttsiah png\t500\n食飯\ttsiah png\t300\n'
        )
        errors = validate_dict_format(dictfile)
        assert any("duplicate" in e.lower() for e in errors)


class TestValidateCli:
    """Test CLI entry point."""

    def test_valid_file_exits_zero(self, tmp_path):
        dictfile = tmp_path / "test.dict.yaml"
        dictfile.write_text('---\nname: test\nversion: "0.1.0"\nsort: by_weight\n...\n食飯\ttsiah png\t500\n')
        with pytest.raises(SystemExit) as exc_info:
            main([str(dictfile)])
        assert exc_info.value.code == 0

    def test_invalid_file_exits_nonzero(self, tmp_path):
        dictfile = tmp_path / "test.dict.yaml"
        dictfile.write_text("食飯\ttsiah png\t500\n")
        with pytest.raises(SystemExit) as exc_info:
            main([str(dictfile)])
        assert exc_info.value.code == 1

    def test_missing_file_skips(self, tmp_path):
        with pytest.raises(SystemExit) as exc_info:
            main([str(tmp_path / "nonexistent.yaml")])
        assert exc_info.value.code == 0
