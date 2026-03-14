"""Tests for light-tone (輕聲) rules extraction."""

import io

from scripts.parse_lighttone import parse_lighttone_csv


class TestParseLighttone:
    """Parse khin1siann1 light-tone CSV."""

    @staticmethod
    def sample_csv():
        return "臺羅,漢字,分連不處理\n--guá,我,分寫\n--mah,媽,連寫\n--ê,的,不處理\n--khí-lâi,起來,補語\n"

    def test_parse_returns_list(self):
        rules = parse_lighttone_csv(io.StringIO(self.sample_csv()))
        assert len(rules) == 4

    def test_rule_fields(self):
        rules = parse_lighttone_csv(io.StringIO(self.sample_csv()))
        first = rules[0]
        assert first["tl"] == "--guá"
        assert first["hanzi"] == "我"
        assert first["rule"] == "分寫"

    def test_complement_type(self):
        rules = parse_lighttone_csv(io.StringIO(self.sample_csv()))
        complement = next(r for r in rules if r["hanzi"] == "起來")
        assert complement["rule"] == "補語"
