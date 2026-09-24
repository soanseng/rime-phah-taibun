"""Tests for Mandarin→Taiwanese hoabun_map generation."""

from scripts.build_hoabun_map import extract_hoabun_mappings


def test_poj_fallback_is_converted_to_tl(tmp_path):
    data_dir = tmp_path / "ChhoeTaigiDatabase"
    data_dir.mkdir()
    csv_path = data_dir / "ChhoeTaigi_MaryknollTaiengSutian.csv"
    csv_path.write_text(
        "PojInput,KipInput,HanLoTaibunPoj,HanLoTaibunKip,HoaBun\nchiah8-png7,,食飯,,吃飯\n",
        encoding="utf-8",
    )

    mappings = extract_hoabun_mappings(data_dir)

    assert mappings["吃飯"][0] == "tsiah8 png7"


def test_unicode_tone_kip_input_is_normalized(tmp_path):
    data_dir = tmp_path / "ChhoeTaigiDatabase"
    data_dir.mkdir()
    csv_path = data_dir / "ChhoeTaigi_iTaigiHoataiTuichiautian.csv"
    csv_path.write_text(
        "KipInput,HanLoTaibunKip,HoaBun\nlí-hó,你好,妳好\n",
        encoding="utf-8",
    )

    mappings = extract_hoabun_mappings(data_dir)

    assert mappings["妳好"][0] == "li2 ho2"


def test_extra_tsv_adds_moe_source_mappings(tmp_path):
    """STTI/placename TSVs (華語\t漢字\tcode) feed the reverse-lookup map."""
    data_dir = tmp_path / "ChhoeTaigiDatabase"
    data_dir.mkdir()
    extra = tmp_path / "stti_entries.tsv"
    extra.write_text("員林\t員林\tuan5 lim5\n110\t110\tit4 it4 khong3\n", encoding="utf-8")

    mappings = extract_hoabun_mappings(data_dir, extra_tsvs=[extra])

    assert mappings["員林"][0] == "uan5 lim5"
    assert "110" not in mappings  # non-CJK 華語 is useless for 注音反查


def test_extra_tsv_does_not_override_core_dictionary(tmp_path):
    """Priority 3 extras must not displace the 教典 (priority 4) mapping."""
    data_dir = tmp_path / "ChhoeTaigiDatabase"
    data_dir.mkdir()
    csv_path = data_dir / "ChhoeTaigi_KauiokpooTaigiSutian.csv"
    csv_path.write_text(
        "KipInput,HanLoTaibunKip,HoaBun\ntong5 hak8,同學,同學\n",
        encoding="utf-8",
    )
    extra = tmp_path / "placename_entries.tsv"
    extra.write_text("同學\t同學\ttang5 hak8\n", encoding="utf-8")

    mappings = extract_hoabun_mappings(data_dir, extra_tsvs=[extra])

    assert mappings["同學"][0] == "tong5 hak8"
