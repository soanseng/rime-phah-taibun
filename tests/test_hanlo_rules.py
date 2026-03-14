"""Tests for LKK rules parsing."""

import io

import pytest
import yaml

from scripts.parse_lkk_rules import classify_hanlo_type, parse_lkk_csv, write_hanlo_rules_yaml


class TestClassifyHanloType:
    """Determine if a word should output as han (漢字) or lo (羅馬字)."""

    def test_pure_cjk_is_han(self):
        assert classify_hanlo_type("食飯") == "han"

    def test_pure_romanization_is_lo(self):
        assert classify_hanlo_type("ê") == "lo"

    def test_mixed_hanlo_is_han(self):
        """Mixed text defaults to han (has CJK content)."""
        assert classify_hanlo_type("ā好") == "han"

    def test_common_function_words_are_lo(self):
        """Known function words that should always be romanized."""
        assert classify_hanlo_type("beh") == "lo"
        assert classify_hanlo_type("kap") == "lo"

    def test_single_cjk_char(self):
        assert classify_hanlo_type("阿") == "han"


class TestParseLkkCsv:
    """Parse LKK CSV into structured rules."""

    @pytest.fixture
    def lkk_csv_content(self):
        """Sample LKK CSV (tab-separated with header)."""
        return (
            "→\t建議用字\t音讀\t數字版音讀\t又音\t教育部推薦漢字\t對應華語\t用例\t異用字\n"
            "001\t阿\ta\ta1\t\t\t阿\t阿母、阿爸\t\n"
            "\tê\tê\te5\t\t\t的\tgún ê 厝\t\n"
            "002\t食飯\ttsia̍h-pn̄g\ttsiah8-png7\t\t\t吃飯\t來食飯\t\n"
            "\tbeh\tbeh\tbeh4\t\t\t要\t我 beh 去\t\n"
            "\tkap\tkap\tkap4\t\t\t和\t我 kap 你\t\n"
        )

    def test_parse_returns_list(self, lkk_csv_content):
        rules = parse_lkk_csv(io.StringIO(lkk_csv_content))
        assert isinstance(rules, list)
        assert len(rules) == 5

    def test_han_word_classified(self, lkk_csv_content):
        rules = parse_lkk_csv(io.StringIO(lkk_csv_content))
        ah_rule = next(r for r in rules if r["word"] == "阿")
        assert ah_rule["type"] == "han"

    def test_lo_word_classified(self, lkk_csv_content):
        rules = parse_lkk_csv(io.StringIO(lkk_csv_content))
        e_rule = next(r for r in rules if r["word"] == "ê")
        assert e_rule["type"] == "lo"

    def test_rule_has_kip(self, lkk_csv_content):
        rules = parse_lkk_csv(io.StringIO(lkk_csv_content))
        tsiah_rule = next(r for r in rules if r["word"] == "食飯")
        assert tsiah_rule["kip"] == "tsiah8-png7"


class TestWriteHanloRulesYaml:
    """Write parsed rules to YAML format."""

    def test_writes_valid_yaml(self, tmp_path):
        rules = [
            {"word": "ê", "type": "lo", "kip": "e5", "hoabun": "的"},
            {"word": "食飯", "type": "han", "kip": "tsiah8-png7", "hoabun": "吃飯"},
        ]
        outfile = tmp_path / "hanlo_rules.yaml"
        write_hanlo_rules_yaml(rules, outfile)
        data = yaml.safe_load(outfile.read_text())
        assert "ê" in data
        assert data["ê"]["type"] == "lo"
        assert "食飯" in data
        assert data["食飯"]["type"] == "han"

    def test_kip_preserved(self, tmp_path):
        rules = [{"word": "beh", "type": "lo", "kip": "beh4", "hoabun": "要"}]
        outfile = tmp_path / "hanlo_rules.yaml"
        write_hanlo_rules_yaml(rules, outfile)
        data = yaml.safe_load(outfile.read_text())
        assert data["beh"]["kip"] == "beh4"
