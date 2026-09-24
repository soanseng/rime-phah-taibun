"""Tests for MOE STTI 學科術語 ODS parser (parse_stti.py).

Source: 教育部「學科術語臺灣台語/臺灣客語對譯」ttg ODS
(https://stti.moe.edu.tw), CC BY 3.0 TW. Only the 臺灣台語 columns are
consumed. Cells hold one paragraph per variant, so 詞彙/臺羅 variant lists
pair positionally only when their lengths agree — mismatches are skipped
rather than mis-paired into fake 詞身份.
"""

import zipfile

from scripts.parse_stti import SttiEntry, parse_stti_ods, write_stti_tsv

TABLE_NS = "urn:oasis:names:tc:opendocument:xmlns:table:1.0"

HEADER = [
    "序號",
    "學科術語",
    "參考解釋",
    "第1階段",
    "第2階段",
    "第3階段",
    "第4階段",
    "第5階段",
    "臺灣台語詞彙",
    "臺羅",
]

CONTENT_TMPL = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    '<office:document-content'
    ' xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0"'
    ' xmlns:table="urn:oasis:names:tc:opendocument:xmlns:table:1.0"'
    ' xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0">'
    "<office:body><office:spreadsheet>"
    '<table:table table:name="學科術語綜整檔">{rows}'
    "</table:table></office:spreadsheet></office:body></office:document-content>"
)


def _cell(paras: list[str]) -> str:
    body = "".join(f"<text:p>{p}</text:p>" for p in paras)
    return f"<table:table-cell>{body}</table:table-cell>"


def _empty(repeated: int = 1) -> str:
    if repeated == 1:
        return "<table:table-cell/>"
    return f'<table:table-cell table:number-columns-repeated="{repeated}"/>'


def _row(cells: list[str]) -> str:
    return f"<table:table-row>{''.join(cells)}</table:table-row>"


def make_ods(path, data_rows) -> None:
    """Write a minimal STTI-shaped ODS.

    data_rows: iterable of (序號, 學科術語, 詞彙 paragraphs, 臺羅 paragraphs).
    The empty span uses number-columns-repeated like the real file, so every
    test exercises repeat expansion.
    """
    rows = [_row([_cell([h]) for h in HEADER] + [_empty()])]
    for seq, hua, han_paras, lo_paras in data_rows:
        cells = [
            _cell([seq]),
            _cell([hua]),
            _empty(repeated=6),  # 參考解釋 + 第1..第5階段
            _cell(han_paras),
            _cell(lo_paras),
        ]
        rows.append(_row(cells))
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("content.xml", CONTENT_TMPL.format(rows="".join(rows)))


class TestVariantPairing:
    """詞彙/臺羅 variant lists must pair without inventing fake 詞身份."""

    def test_equal_counts_pair_by_index(self, tmp_path):
        ods = tmp_path / "stti.ods"
        make_ods(
            ods,
            [("100016", "一年級", ["一年級", "一年仔", "一年的"], ["it-nî-kip", "it-nî-á", "it-nî--ê"])],
        )
        entries, stats = parse_stti_ods(ods)
        assert entries == [
            SttiEntry(hua="一年級", han="一年級", code="it4 ni5 kip4"),
            SttiEntry(hua="一年級", han="一年仔", code="it4 ni5 a2"),
            SttiEntry(hua="一年級", han="一年的", code="it4 ni5 e5"),
        ]
        assert stats["skipped_mismatch"] == 0

    def test_single_han_multiple_readings(self, tmp_path):
        ods = tmp_path / "stti.ods"
        make_ods(ods, [("100047", "人權", ["人權"], ["jîn-khuân", "jîn-kuân"])])
        entries, _ = parse_stti_ods(ods)
        assert [(e.han, e.code) for e in entries] == [
            ("人權", "jin5 khuan5"),
            ("人權", "jin5 kuan5"),
        ]

    def test_mismatched_variant_lists_skipped(self, tmp_path):
        ods = tmp_path / "stti.ods"
        make_ods(
            ods,
            [
                (
                    "100659",
                    "同學",
                    ["同學", "仝班的", "同窗"],
                    ["tông-ha̍k", "tông-o̍h", "tâng-ha̍k", "tâng-o̍h", "kāng-pan--ê", "tông-tshong"],
                )
            ],
        )
        entries, stats = parse_stti_ods(ods)
        assert entries == []
        assert stats["skipped_mismatch"] == 1

    def test_numeric_term_kept(self, tmp_path):
        ods = tmp_path / "stti.ods"
        make_ods(ods, [("100001", "110", ["110"], ["it it khòng"])])
        entries, _ = parse_stti_ods(ods)
        assert entries == [SttiEntry(hua="110", han="110", code="it4 it4 khong3")]


class TestRowFiltering:
    """Rows without a usable anchor are skipped and counted, never dropped silently."""

    def test_row_without_mandarin_term_skipped(self, tmp_path):
        ods = tmp_path / "stti.ods"
        make_ods(ods, [("", "", ["漢字"], ["han3-ji7"])])
        entries, stats = parse_stti_ods(ods)
        assert entries == []
        assert stats["skipped_empty"] == 1

    def test_invalid_romanization_skipped(self, tmp_path):
        ods = tmp_path / "stti.ods"
        make_ods(ods, [("100099", "??", ["漢字"], ["???"])])
        entries, stats = parse_stti_ods(ods)
        assert entries == []
        assert stats["skipped_invalid"] == 1

    def test_duplicate_pairs_collapsed_within_source(self, tmp_path):
        ods = tmp_path / "stti.ods"
        row = ("100001", "110", ["110"], ["it it khòng"])
        make_ods(ods, [row, row])
        entries, stats = parse_stti_ods(ods)
        assert entries == [SttiEntry(hua="110", han="110", code="it4 it4 khong3")]
        assert stats["dupe_collapsed"] == 1

    def test_empty_variant_paragraphs_ignored(self, tmp_path):
        ods = tmp_path / "stti.ods"
        make_ods(ods, [("100047", "人權", ["人權", ""], ["jîn-khuân", ""])])
        entries, _ = parse_stti_ods(ods)
        assert [(e.han, e.code) for e in entries] == [("人權", "jin5 khuan5")]


class TestTsvOutput:
    """TSV carries the Mandarin column so hoabun_map can consume the same file."""

    def test_write_stti_tsv_lines(self, tmp_path):
        out = tmp_path / "stti.tsv"
        count = write_stti_tsv(
            [
                SttiEntry(hua="人權", han="人權", code="jin5 khuan5"),
                SttiEntry(hua="110", han="110", code="it4 it4 khong3"),
            ],
            out,
        )
        assert count == 2
        assert out.read_text(encoding="utf-8") == (
            "人權\t人權\tjin5 khuan5\n110\t110\tit4 it4 khong3\n"
        )


class TestCli:
    def test_main_writes_output(self, tmp_path, capsys):
        from scripts.parse_stti import main

        ods = tmp_path / "stti.ods"
        make_ods(ods, [("100047", "人權", ["人權"], ["jîn-khuân", "jîn-kuân"])])
        out = tmp_path / "stti.tsv"
        main(["--input", str(ods), "--output", str(out)])
        assert out.read_text(encoding="utf-8") == (
            "人權\t人權\tjin5 khuan5\n人權\t人權\tjin5 kuan5\n"
        )
