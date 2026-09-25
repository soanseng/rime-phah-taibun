"""Tests for MOE recommended-word list generation (700字 + 900例句).

moe700.yaml feeds phah_taibun_recommend.lua: any candidate whose text
matches a list entry gets the ◆ badge and the moe nudge tier (1 slot,
vs LKK's 3). The lua picks ONE tier per candidate via if/elseif, so a
word present in several sources never stacks boosts — the yaml side
must mirror that by deduplicating merged entries.
"""

import json

import pytest

from scripts.parse_moe700 import main, parse_leku900_json


def test_parse_leku900_json_extracts_terms(tmp_path):
    p = tmp_path / "minnan900.json"
    p.write_text(
        json.dumps(
            {
                "001": {"詞條漢字": "一身人", "詞條臺羅": "tsi̍t sian lâng"},
                "002": {"詞條漢字": "查某人", "詞條臺羅": "tsa-bóo-lâng"},
                "003": {"詞條漢字": "", "詞條臺羅": ""},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    assert parse_leku900_json(p) == ["一身人", "查某人"]


def test_parse_leku900_json_accepts_list_shape(tmp_path):
    p = tmp_path / "minnan900.json"
    p.write_text(
        json.dumps([{"詞條漢字": "一身人"}], ensure_ascii=False),
        encoding="utf-8",
    )

    assert parse_leku900_json(p) == ["一身人"]


def test_leku900_terms_merge_after_700_deduped(tmp_path, capsys):
    csv = tmp_path / "700.csv"
    csv.write_text("建議用字\n食\n一身人\n", encoding="utf-8")
    j = tmp_path / "minnan900.json"
    j.write_text(
        json.dumps(
            {"001": {"詞條漢字": "一身人"}, "002": {"詞條漢字": "查某人"}},
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    out = tmp_path / "moe700.yaml"

    main(["--input", str(csv), "--leku900", str(j), "--output", str(out)])

    words = [ln for ln in out.read_text(encoding="utf-8").splitlines() if ln.startswith("- ")]
    # 一身人 appears in both sources → single entry, 700 order first.
    assert words == ["- 食", "- 一身人", "- 查某人"]


def test_without_leku900_output_unchanged(tmp_path, capsys):
    csv = tmp_path / "700.csv"
    csv.write_text("建議用字\n食\n", encoding="utf-8")
    out = tmp_path / "moe700.yaml"

    main(["--input", str(csv), "--output", str(out)])

    words = [ln for ln in out.read_text(encoding="utf-8").splitlines() if ln.startswith("- ")]
    assert words == ["- 食"]


@pytest.mark.parametrize("flag", ["--leku900"])
def test_missing_leku900_file_fails_loud(flag, tmp_path, capsys):
    csv = tmp_path / "700.csv"
    csv.write_text("建議用字\n食\n", encoding="utf-8")

    with pytest.raises(SystemExit):
        main(["--input", str(csv), flag, str(tmp_path / "nope.json"), "--output", str(tmp_path / "o.yaml")])
