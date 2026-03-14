"""Tests for MOE reverse dictionary builder."""

import io

from scripts.build_moe_reverse import load_definitions, parse_moe_entries, write_enhanced_reverse_dict


class TestParseMoeEntries:
    """Parse MOE vocabulary CSV."""

    @staticmethod
    def sample_csv():
        return "主編碼,屬性,詞目,音讀,文白屬性,部首\n" '1,1,一,tsi̍t,4,一\n' '2,1,一,it,0,一\n' '3,1,一下,tsi̍t-ē,0,一\n'

    def test_basic_parse(self):
        entries = parse_moe_entries(io.StringIO(self.sample_csv()))
        assert len(entries) >= 2

    def test_entry_fields(self):
        entries = parse_moe_entries(io.StringIO(self.sample_csv()))
        first = entries[0]
        assert first["word"] == "一"
        assert "tsi" in first["reading"]
        assert first["moe_id"] == "1"

    def test_multiple_readings(self):
        """Same word with different readings produces multiple entries."""
        entries = parse_moe_entries(io.StringIO(self.sample_csv()))
        yi_entries = [e for e in entries if e["word"] == "一"]
        assert len(yi_entries) == 2


class TestLoadDefinitions:
    """Load definitions from CSV."""

    @staticmethod
    def sample_definitions_csv():
        return (
            "釋義總序號,主編碼,釋義順序,詞性代號,釋義\n"
            "1,1,1,15,數目。\n"
            "2,1,2,6,全部的、整個的。\n"
            "3,3,1,6,稍微。\n"
        )

    def test_basic_load(self):
        defs = load_definitions(io.StringIO(self.sample_definitions_csv()))
        assert "1" in defs
        assert len(defs["1"]) == 2

    def test_definition_text(self):
        defs = load_definitions(io.StringIO(self.sample_definitions_csv()))
        assert defs["1"][0] == "數目。"


class TestWriteEnhancedReverseDict:
    """Write enhanced reverse dictionary."""

    def test_writes_with_definitions(self, tmp_path):
        entries = [
            {"word": "一", "reading": "tsi̍t", "moe_id": "1", "wen_bai": "4"},
        ]
        defs = {"1": ["數目。", "全部的。"]}
        outfile = tmp_path / "reverse.dict.yaml"
        write_enhanced_reverse_dict(entries, defs, outfile)
        content = outfile.read_text()
        assert "一" in content
        assert "phah_taibun_reverse" in content

    def test_entries_tab_separated(self, tmp_path):
        entries = [
            {"word": "食飯", "reading": "tsia̍h-pn̄g", "moe_id": "100", "wen_bai": "0"},
        ]
        outfile = tmp_path / "reverse.dict.yaml"
        write_enhanced_reverse_dict(entries, {}, outfile)
        content = outfile.read_text()
        lines = [ln for ln in content.splitlines() if "\t" in ln]
        assert len(lines) >= 1
