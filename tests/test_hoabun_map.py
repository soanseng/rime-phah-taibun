"""Tests for Mandarin→Taiwanese hoabun_map generation."""

from scripts.build_hoabun_map import extract_hoabun_mappings


def test_poj_fallback_is_converted_to_tl(tmp_path):
    data_dir = tmp_path / "ChhoeTaigiDatabase"
    data_dir.mkdir()
    csv_path = data_dir / "ChhoeTaigi_MaryknollTaiengSutian.csv"
    csv_path.write_text(
        "PojInput,KipInput,HanLoTaibunPoj,HanLoTaibunKip,HoaBun\n"
        "chiah8-png7,,食飯,,吃飯\n",
        encoding="utf-8",
    )

    mappings = extract_hoabun_mappings(data_dir)

    assert mappings["吃飯"][0] == "tsiah8 png7"


def test_unicode_tone_kip_input_is_normalized(tmp_path):
    data_dir = tmp_path / "ChhoeTaigiDatabase"
    data_dir.mkdir()
    csv_path = data_dir / "ChhoeTaigi_iTaigiHoataiTuichiautian.csv"
    csv_path.write_text(
        "KipInput,HanLoTaibunKip,HoaBun\n"
        "lí-hó,你好,妳好\n",
        encoding="utf-8",
    )

    mappings = extract_hoabun_mappings(data_dir)

    assert mappings["妳好"][0] == "li2 ho2"
