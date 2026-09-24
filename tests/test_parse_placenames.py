"""Tests for MOE placename ODT parser (parse_placenames.py).

Source: 教育部「以本土語言標注臺灣地名計畫」成果清單
(https://language.moe.gov.tw/001/Upload/Files/site_content/M0001/mhigeonames/twplacename.html),
released under 創用CC-姓名標示 3.0 臺灣 (CC BY 3.0 TW). The zips carry
docx/odt/pdf of the same lists plus audio; only the ODT lists are parsed
and only 臺灣台語 columns are consumed — 客語 columns are dropped.

Two layouts:
- stage-1 station lists (鐵路/捷運/高鐵/好行): 號次 / 業者代碼 / 國語 /
  臺灣台語 (第一優勢腔 / 建議漢字 / 第二優勢腔 / 說明) / 臺灣客語 (…)
- stage-2 placename list: 序號 / 地名 / 客語拼音 / 客語備註 / 台語拼音 / 台語備註

Cells use ``·`` as the empty placeholder; merged section rows (single
cell) and the header rows are skipped. 第一優勢腔 is the primary reading
(weight 700, user-confirmed); 第二優勢腔 becomes an extra reading at
weight 650. Slash variants and parenthesized alternates expand into
separate readings; single-syllable slash tails are dropped.
"""

import zipfile

from scripts.parse_placenames import PlacenameEntry, main, parse_placename_dir, write_placename_tsv

CONTENT_TMPL = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    "<office:document-content"
    ' xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0"'
    ' xmlns:table="urn:oasis:names:tc:opendocument:xmlns:table:1.0"'
    ' xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0">'
    "<office:body><office:text>{tables}"
    "</office:text></office:body></office:document-content>"
)


def _cell(paras: list[str]) -> str:
    body = "".join(f"<text:p>{p}</text:p>" for p in paras)
    return f"<table:table-cell>{body}</table:table-cell>"


def _row(cells: list[str]) -> str:
    return f"<table:table-row>{''.join(cells)}</table:table-row>"


def make_odt(path, tables: list[list[list[str]]]) -> None:
    """Write a minimal placename ODT.

    Each table is a list of rows; each row is a list of cells; each cell is
    a list of paragraph strings. A bare string cell is normalized to a
    single paragraph.
    """
    xml_tables = []
    for table in tables:
        rows = "".join(_row([_cell(cell if isinstance(cell, list) else [cell]) for cell in row]) for row in table)
        xml_tables.append(f'<table:table table:name="T">{rows}</table:table>')
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("content.xml", CONTENT_TMPL.format(tables="".join(xml_tables)))


def stage1_table() -> list[list[list[str]]]:
    header1 = ["號次", "業者代碼", "國語", "臺灣台語", "臺灣客語"]
    header2 = ["第一優勢腔", "建議漢字", "第二優勢腔", "說明", "四縣腔", "建議漢字", "說明"]
    section = ["臺灣鐵路管理局"]
    keelung = ["1", "0900", "基隆", "Ke-lâng", "鷄籠", "Kue-lâng", "·", "gi lung", "·", "·"]
    badu = ["2", "0910", "八堵", "Peh-tóo", "·", "Pueh-tóo", "·", "bad du", "·", "·"]
    houtong = [
        "3",
        "7350",
        "猴硐",
        "Kâu-tōng-á",
        "猴洞仔",
        "(Kâu-tōng-á)",
        "又唸作Kâu-tōng。",
        "heu tung",
        "猴洞",
        "·",
    ]
    return [[header1, header2, section, keelung, badu, houtong]]


def stage2_table() -> list[list[list[str]]]:
    title = [["教育部"], ["以本土語言標注臺灣地名計畫 (第2階段)"]]
    date = [[["2023年3月16日"]]]
    main_table = [
        [],
        ["序號", "地名", "臺灣客語拼音", "臺灣客語備註", "臺灣台語拼音", "臺灣台語備註"],
        ["A001", "臺北市", "toi bed sii", "·", "Tâi-pak-tshī", "·"],
        ["A002", "中正區", "zung ziin ki", "·", "Tiong-tsìng-khu", "·"],
        ["A003", "大安區", "tai tung ki", "·", "Tāi-an-khu", "聚落稱大龍峒Tuā-lōng-pōn"],
        ["A004", "中庄（大庄）", "·", "·", "Tiong-tsng (Tuā-tsng)", "·"],  # noqa: RUF001 - 真實資料全形括號
        ["A005", "鯉魚潭村", "·", "·", "Lí-hî-thâm-tshun/tshuan", "·"],
    ]
    return [title, date, main_table]


class TestStage1StationLists:
    """10-column station rows: 國語 + 第一優勢腔 is the core entry."""

    def test_primary_and_recommended_hanji_share_first_accent(self, tmp_path):
        make_odt(tmp_path / "地名清單_臺灣鐵路.odt", stage1_table())
        entries, stats = parse_placename_dir(tmp_path)
        pairs = [(e.han, e.code) for e in entries]
        assert ("基隆", "ke1 lang5") in pairs
        assert ("鷄籠", "ke1 lang5") in pairs
        assert stats["entries"] == len(entries)

    def test_secondary_accent_becomes_extra_reading(self, tmp_path):
        make_odt(tmp_path / "地名清單_臺灣鐵路.odt", stage1_table())
        entries, _ = parse_placename_dir(tmp_path)
        pairs = [(e.han, e.code) for e in entries]
        assert ("基隆", "kue1 lang5") in pairs
        assert ("八堵", "peh4 too2") in pairs
        assert ("八堵", "pueh4 too2") in pairs

    def test_parenthesized_variant_unwrapped(self, tmp_path):
        make_odt(tmp_path / "地名清單_臺灣鐵路.odt", stage1_table())
        entries, _ = parse_placename_dir(tmp_path)
        pairs = [(e.han, e.code) for e in entries]
        assert ("猴硐", "kau5 tong7 a2") in pairs
        assert ("猴洞仔", "kau5 tong7 a2") in pairs

    def test_secondary_accent_ranks_below_primary(self, tmp_path):
        """第一優勢腔 readings get weight 700; 第二優勢腔 extras get 650."""
        make_odt(tmp_path / "地名清單_臺灣鐵路.odt", stage1_table())
        entries, _ = parse_placename_dir(tmp_path)
        weights = {(e.han, e.code): e.weight for e in entries}
        assert weights[("基隆", "ke1 lang5")] == 700
        assert weights[("基隆", "kue1 lang5")] == 650
        assert weights[("八堵", "peh4 too2")] == 700
        assert weights[("八堵", "pueh4 too2")] == 650

    def test_section_and_header_rows_skipped(self, tmp_path):
        make_odt(tmp_path / "地名清單_臺灣鐵路.odt", stage1_table())
        entries, stats = parse_placename_dir(tmp_path)
        hans = {e.han for e in entries}
        assert "臺灣鐵路管理局" not in hans
        assert "國語" not in hans
        # two header rows + one section row all yield no entry attempt
        assert stats["skipped_rows"] == 3

    def test_hakka_columns_dropped(self, tmp_path):
        make_odt(tmp_path / "地名清單_臺灣鐵路.odt", stage1_table())
        entries, _ = parse_placename_dir(tmp_path)
        assert not any("gi" in e.code or "bad" in e.code or "heu" in e.code for e in entries)


class TestStage2PlacenameList:
    """6-column list: 地名 + 臺灣台語拼音, 客語/備註 dropped."""

    def test_hanji_and_reading_parsed(self, tmp_path):
        make_odt(tmp_path / "地名計畫第2階段_地名清單.odt", stage2_table())
        entries, _ = parse_placename_dir(tmp_path)
        pairs = {(e.han, e.code) for e in entries}
        assert ("臺北市", "tai5 pak4 tshi7") in pairs
        assert ("中正區", "tiong1 tsing3 khu1") in pairs
        assert ("大安區", "tai7 an1 khu1") in pairs

    def test_parenthesized_alternates_pair_with_hanji(self, tmp_path):
        """「中庄(大庄)」+「Tiong-tsng (Tuā-tsng)」→ two aligned pairs."""
        make_odt(tmp_path / "地名計畫第2階段_地名清單.odt", stage2_table())
        entries, _ = parse_placename_dir(tmp_path)
        pairs = {(e.han, e.code) for e in entries}
        assert ("中庄", "tiong1 tsng1") in pairs
        assert ("大庄", "tua7 tsng1") in pairs

    def test_slash_variants_expand_and_partial_tails_dropped(self, tmp_path):
        """Slash variants split; a single-syllable tail never becomes a word."""
        make_odt(tmp_path / "地名計畫第2階段_地名清單.odt", stage2_table())
        entries, _ = parse_placename_dir(tmp_path)
        pairs = {(e.han, e.code) for e in entries}
        assert ("鯉魚潭村", "li2 hi5 tham5 tshun1") in pairs
        assert not any(code.endswith(" tshuan") or code == "tshuan" for _, code in pairs)

    def test_notes_and_hakka_columns_not_in_codes(self, tmp_path):
        make_odt(tmp_path / "地名計畫第2階段_地名清單.odt", stage2_table())
        entries, _ = parse_placename_dir(tmp_path)
        codes = [e.code for e in entries]
        assert not any("long5" in c for c in codes)  # 備註 Tuā-lōng-pōn must not leak
        assert not any("toi" in c for c in codes)  # 客語拼音 must not leak


class TestSharedBehavior:
    def test_duplicate_pairs_collapsed_across_files(self, tmp_path):
        make_odt(tmp_path / "地名清單_臺灣鐵路.odt", stage1_table())
        rows = [
            [],
            ["序號", "地名", "臺灣客語拼音", "臺灣客語備註", "臺灣台語拼音", "臺灣台語備註"],
            ["A001", "基隆", "·", "·", "Ke-lâng", "·"],
        ]
        make_odt(tmp_path / "地名計畫第2階段_地名清單.odt", [[rows[0]], [rows[1], rows[2]]])
        entries, stats = parse_placename_dir(tmp_path)
        assert stats["dupe_collapsed"] >= 1
        pairs = [(e.han, e.code) for e in entries]
        assert pairs.count(("基隆", "ke1 lang5")) == 1

    def test_invalid_romanization_skipped(self, tmp_path):
        make_odt(
            tmp_path / "地名計畫第2階段_地名清單.odt",
            [
                [
                    [],
                    ["序號", "地名", "臺灣客語拼音", "臺灣客語備註", "臺灣台語拼音", "臺灣台語備註"],
                    ["A001", "怪地", "·", "·", "!!!", "·"],
                ]
            ],
        )
        entries, stats = parse_placename_dir(tmp_path)
        assert entries == []
        assert stats["skipped_invalid"] == 1

    def test_write_placename_tsv(self, tmp_path):
        out = tmp_path / "placenames.tsv"
        count = write_placename_tsv(
            [PlacenameEntry(hua="基隆", han="基隆", code="ke1 lang5", weight=700)], out
        )
        assert count == 1
        assert out.read_text(encoding="utf-8") == "基隆\t基隆\tke1 lang5\t700\n"

    def test_cli_writes_output(self, tmp_path):
        make_odt(tmp_path / "地名清單_臺灣鐵路.odt", stage1_table())
        out = tmp_path / "sub" / "placenames.tsv"
        main(["--input", str(tmp_path), "--output", str(out)])
        assert out.exists()
