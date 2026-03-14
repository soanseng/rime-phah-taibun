"""End-to-end integration test: full data pipeline."""

from pathlib import Path

import pytest

from scripts.convert_chhoetaigi import convert_chhoetaigi
from scripts.extract_icorpus_freq import count_frequencies
from scripts.parse_lkk_rules import parse_lkk_csv, write_hanlo_rules_yaml
from scripts.validate_dict import validate_dict_format

DATA_DIR = Path(__file__).parent.parent / "data"
CHHOETAIGI_DIR = DATA_DIR / "ChhoeTaigiDatabase" / "ChhoeTaigiDatabase"
LKK_CSV = DATA_DIR / "lkk_yongji.csv"


@pytest.mark.skipif(
    not CHHOETAIGI_DIR.exists(),
    reason="ChhoeTaigi data not downloaded (run scripts/download_resources.sh)",
)
class TestFullPipeline:
    """Test the complete data pipeline against real downloaded data."""

    def test_convert_produces_valid_dict(self, tmp_path):
        output = tmp_path / "phah_taibun.dict.yaml"
        convert_chhoetaigi(
            itaigi_paths=[CHHOETAIGI_DIR / "ChhoeTaigi_iTaigiHoataiTuichiautian.csv"],
            taihoa_paths=[CHHOETAIGI_DIR / "ChhoeTaigi_TaihoaSoanntengTuichiautian.csv"],
            output_path=output,
        )
        assert output.exists()
        content = output.read_text()
        lines = [line for line in content.splitlines() if "\t" in line]
        assert len(lines) > 10000, f"Expected >10K entries, got {len(lines)}"
        errors = validate_dict_format(output)
        assert len(errors) == 0, f"Validation errors: {errors[:5]}"

    @pytest.mark.skipif(not LKK_CSV.exists(), reason="LKK CSV not downloaded")
    def test_lkk_parse_produces_rules(self, tmp_path):
        output = tmp_path / "hanlo_rules.yaml"
        with open(LKK_CSV, encoding="utf-8") as f:
            rules = parse_lkk_csv(f)
        assert len(rules) > 100, f"Expected >100 rules, got {len(rules)}"
        write_hanlo_rules_yaml(rules, output)
        assert output.exists()


ICORPUS_FILE = DATA_DIR / "icorpus_ka1_han3-ji7" / "語料" / "自動標人工改音標.txt"
MOE_UNI_DIR = DATA_DIR / "moedict-data-twblg" / "uni"


@pytest.mark.skipif(
    not ICORPUS_FILE.exists(),
    reason="iCorpus data not downloaded",
)
class TestICorpusIntegration:
    """Test iCorpus frequency extraction against real data."""

    def test_extracts_meaningful_frequencies(self):
        with open(ICORPUS_FILE, encoding="utf-8") as f:
            freq = count_frequencies(f)
        assert len(freq) > 1000, f"Expected >1K unique words, got {len(freq)}"
        total = sum(freq.values())
        assert total > 10000, f"Expected >10K total tokens, got {total}"


@pytest.mark.skipif(
    not (MOE_UNI_DIR / "詞目總檔.csv").exists(),
    reason="MOE data not downloaded",
)
class TestMoeReverseIntegration:
    """Test MOE reverse dictionary against real data."""

    def test_parses_moe_vocabulary(self):
        from scripts.build_moe_reverse import parse_moe_entries

        with open(MOE_UNI_DIR / "詞目總檔.csv", encoding="utf-8") as f:
            entries = parse_moe_entries(f)
        assert len(entries) > 5000, f"Expected >5K entries, got {len(entries)}"
