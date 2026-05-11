"""Tests for building dictionary entries from Taigi supplement CSV files."""

from pathlib import Path

from scripts.build_dictionary_supplement import (
    SupplementEntry,
    build_supplement_from_dir,
    parse_supplement_rows,
    source_weight,
)
from scripts.validate_dict import validate_dict_format


def test_converts_unicode_tl_to_rime_key():
    rows = [{"漢字": "司法院", "臺灣台語羅馬字": "Su-huat-īnn"}]

    entries, report = parse_supplement_rows(rows, source_name="一府五院_20260112.csv")

    assert report == []
    assert entries == [
        SupplementEntry(
            text="司法院",
            rime_key="su1 huat4 inn7",
            weight=760,
            source="一府五院_20260112.csv",
            romanization="Su-huat-īnn",
        )
    ]


def test_converts_space_separated_romanization_to_space_delimited_key():
    rows = [{"漢字": "公共事務室", "臺灣台語羅馬字": "Kong-kiōng sū-bū-sik"}]

    entries, report = parse_supplement_rows(rows, source_name="一府五院_20260112.csv")

    assert report == []
    assert entries[0].rime_key == "kong1 kiong7 su7 bu7 sik4"


def test_keeps_roman_candidate_text_for_lkk_words():
    rows = [{"漢字": "ài", "臺灣台語羅馬字": "ài"}]

    entries, report = parse_supplement_rows(rows, source_name="LKK用字_寫台羅e_詞_20260114.csv")

    assert report == []
    assert entries[0].text == "ài"
    assert entries[0].rime_key == "ai3"
    assert entries[0].weight == 700


def test_preserves_leading_light_tone_marker_in_candidate_text_but_not_key():
    rows = [{"漢字": "--ā", "臺灣台語羅馬字": "--ā"}]

    entries, report = parse_supplement_rows(rows, source_name="LKK用字_寫台羅e_詞_20260114.csv")

    assert report == []
    assert entries[0].text == "--ā"
    assert entries[0].rime_key == "a7"


def test_reports_invalid_romanization_without_emitting_entry():
    rows = [{"漢字": "原住民族委員會", "臺灣台語羅馬字": "原住民族委員會"}]

    entries, report = parse_supplement_rows(rows, source_name="一府五院_20260112.csv")

    assert entries == []
    assert report == [
        {
            "source": "一府五院_20260112.csv",
            "text": "原住民族委員會",
            "romanization": "原住民族委員會",
            "reason": "invalid_romanization",
        }
    ]


def test_reports_missing_fields_without_emitting_entry():
    rows = [{"漢字": "司法院", "臺灣台語羅馬字": ""}]

    entries, report = parse_supplement_rows(rows, source_name="一府五院_20260112.csv")

    assert entries == []
    assert report == [
        {
            "source": "一府五院_20260112.csv",
            "text": "司法院",
            "romanization": "",
            "reason": "missing_field",
        }
    ]


def test_reports_duplicate_exact_entries_without_repeating_output():
    rows = [
        {"漢字": "司法院", "臺灣台語羅馬字": "Su-huat-īnn"},
        {"漢字": "司法院", "臺灣台語羅馬字": "Su-huat-īnn"},
    ]

    entries, report = parse_supplement_rows(rows, source_name="一府五院_20260112.csv")

    assert len(entries) == 1
    assert report == [
        {
            "source": "一府五院_20260112.csv",
            "text": "司法院",
            "romanization": "Su-huat-īnn",
            "reason": "duplicate",
        }
    ]


def test_source_weight_by_file_category():
    assert source_weight("數字_時間_日期_20260108.csv") == 920
    assert source_weight("一府五院_20260112.csv") == 760
    assert source_weight("行政區_20260112.csv") == 740
    assert source_weight("台_臺_20260112.csv") == 650
    assert source_weight("內政部菜市仔名_20260112.csv") == 620


def test_build_supplement_from_dir_writes_entries_and_report(tmp_path: Path):
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    (source_dir / "一府五院_20260112.csv").write_text(
        "漢字,臺灣台語羅馬字\r司法院,Su-huat-īnn\r原住民族委員會,原住民族委員會\r",
        encoding="utf-8",
    )
    output = tmp_path / "entries.tsv"
    report = tmp_path / "report.tsv"

    count = build_supplement_from_dir(source_dir=source_dir, output_path=output, report_path=report)

    assert count == 1
    assert output.read_text(encoding="utf-8") == "司法院\tsu1 huat4 inn7\t760\n"
    assert "invalid_romanization" in report.read_text(encoding="utf-8")


def test_build_supplement_from_dir_is_deterministic(tmp_path: Path):
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    (source_dir / "數字_時間_日期_20260108.csv").write_text(
        "漢字,臺灣台語羅馬字\n十二,tsa̍p-jī\n十一,tsa̍p-it\n",
        encoding="utf-8",
    )
    output = tmp_path / "entries.tsv"
    report = tmp_path / "report.tsv"

    build_supplement_from_dir(source_dir=source_dir, output_path=output, report_path=report)

    assert output.read_text(encoding="utf-8") == "十二\ttsap8 ji7\t920\n十一\ttsap8 it4\t920\n"


def test_build_supplement_from_dir_deduplicates_across_files(tmp_path: Path):
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    (source_dir / "一府五院_20260112.csv").write_text(
        "漢字,臺灣台語羅馬字\n司法院,Su-huat-īnn\n",
        encoding="utf-8",
    )
    (source_dir / "教典僻智識_20260112.csv").write_text(
        "漢字,臺灣台語羅馬字\n司法院,Su-huat-īnn\n",
        encoding="utf-8",
    )
    output = tmp_path / "entries.tsv"
    report = tmp_path / "report.tsv"

    count = build_supplement_from_dir(source_dir=source_dir, output_path=output, report_path=report)

    assert count == 1
    assert output.read_text(encoding="utf-8") == "司法院\tsu1 huat4 inn7\t760\n"
    assert "duplicate" in report.read_text(encoding="utf-8")


def test_build_supplement_from_dir_keeps_highest_weight_duplicate(tmp_path: Path):
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    (source_dir / "台_臺_20260112.csv").write_text(
        "漢字,臺灣台語羅馬字\n臺灣,Tâi-uân\n",
        encoding="utf-8",
    )
    (source_dir / "行政區_20260112.csv").write_text(
        "漢字,臺灣台語羅馬字\n臺灣,Tâi-uân\n",
        encoding="utf-8",
    )
    output = tmp_path / "entries.tsv"
    report = tmp_path / "report.tsv"

    count = build_supplement_from_dir(source_dir=source_dir, output_path=output, report_path=report)

    assert count == 1
    assert output.read_text(encoding="utf-8") == "臺灣\ttai5 uan5\t740\n"
    assert "duplicate" in report.read_text(encoding="utf-8")


def test_generated_entries_validate_inside_rime_dict(tmp_path: Path):
    dict_path = tmp_path / "phah_taibun.dict.yaml"
    dict_path.write_text(
        '---\nname: phah_taibun\nversion: "0.1.0"\nsort: by_weight\n...\n司法院\tsu1 huat4 inn7\t760\n--ā\ta7\t700\n',
        encoding="utf-8",
    )

    assert validate_dict_format(dict_path) == []
