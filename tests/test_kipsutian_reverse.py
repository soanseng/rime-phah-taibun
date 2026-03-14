"""Tests for KipSutian reverse dictionary builder."""

import io

from scripts.build_kipsutian_reverse import parse_kipsutian_csv


class TestParseKipsutianCsv:
    """Parse KipSutian kautian.csv into reverse lookup entries."""

    @staticmethod
    def sample_csv():
        return (
            "詞目id,詞目類型,漢字,羅馬字,分類,羅馬字音檔檔名,又唸作,合音唸作,俗唸作,"
            "語音差異,詞彙比較,名,姓,異用字,詞目tuì詞目近義,詞目tuì詞目反義,"
            "解說,詞性,例句,例句-華語,例句-音檔,義項tuì義項近義,義項tuì義項反義,"
            "義項tuì詞目近義,義項tuì詞目反義\n"
            '1,主詞目,一(替),tsi̍t,"性質,數詞",1(1),,,,,,,,一,,,'
            '"1. 數目。\n2. 全部的。","1. 數詞\n2. 形容詞",'
            '"一蕊花","一朵花",,,,\n'
            "2,主詞目,食飯,tsia̍h-pn̄g,動作,2(1),,,,,,,,,,,"
            '"吃飯。","動詞",'
            '"來食飯","來吃飯",,,,\n'
        )

    def test_basic_parse(self):
        entries = parse_kipsutian_csv(io.StringIO(self.sample_csv()))
        assert len(entries) >= 2

    def test_entry_fields(self):
        entries = parse_kipsutian_csv(io.StringIO(self.sample_csv()))
        first = entries[0]
        assert "漢字" in first or "word" in first
        assert first["word"] == "一(替)" or first["word"] == "一"
        assert "tsi" in first["reading"]

    def test_has_definition(self):
        entries = parse_kipsutian_csv(io.StringIO(self.sample_csv()))
        has_def = any(e.get("definition", "") for e in entries)
        assert has_def
