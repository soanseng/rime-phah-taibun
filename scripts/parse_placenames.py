"""Parse MOE placename ODT lists into a dictionary source TSV.

Source: 教育部「以本土語言標注臺灣地名計畫」成果清單
(https://language.moe.gov.tw/001/Upload/Files/site_content/M0001/mhigeonames/twplacename.html),
released under 創用CC-姓名標示 3.0 臺灣 (CC BY 3.0 TW). Each list zip
carries docx/odt/pdf of the same table; only the ODT is parsed and only
臺灣台語 columns are consumed — 客語 columns and audio zips are dropped.

Layouts (auto-detected per table from header text):
- stage-1 station lists: 號次 / 業者代碼 / 國語 / 臺灣台語 (第一優勢腔 /
  建議漢字 / 第二優勢腔 / 說明) / 臺灣客語 (…). 第一優勢腔 is the primary
  reading (weight 700); 建議漢字 is a recommended hanji variant sharing
  it; 第二優勢腔 becomes an extra reading at a lower weight (650).
- stage-2 placename list: 序號 / 地名 / 客語拼音 / 客語備註 / 台語拼音 /
  台語備註. Only 地名 + 台語拼音 are used. Parenthesized alternates pair
  with parenthesized hanji when counts align: 「中庄(大庄)」 +
  「Tiong-tsng (Tuā-tsng)」 → (中庄, Tiong-tsng) + (大庄, Tuā-tsng).

Cells use ``·`` as the empty placeholder. Readings expand slash variants
and parenthesized alternates; a single-syllable slash tail (partial-
syllable variant like 「tshun/tshuan」) is dropped instead of becoming a
bogus one-syllable word. Codes reuse
build_dictionary_supplement.romanization_to_rime_key. Output lines are
華語地名<TAB>漢字<TAB>rime key<TAB>weight; the 華語 column feeds the
hoabun_map stage from the same file.
"""

from __future__ import annotations

import argparse
import re
import sys
import zipfile
from dataclasses import dataclass
from pathlib import Path
from xml.etree import ElementTree as ET

try:
    from scripts.build_dictionary_supplement import romanization_to_rime_key
    from scripts.convert_chhoetaigi import clean_hanlo_text
except ModuleNotFoundError:
    from build_dictionary_supplement import romanization_to_rime_key
    from convert_chhoetaigi import clean_hanlo_text

TABLE_NS = "urn:oasis:names:tc:opendocument:xmlns:table:1.0"
TEXT_NS = "urn:oasis:names:tc:opendocument:xmlns:text:1.0"
_Q_TABLE = f"{{{TABLE_NS}}}"
_Q_TEXT = f"{{{TEXT_NS}}}"

EMPTY_PLACEHOLDER = "·"
_PAREN_RE = re.compile(r"^[\uff08(](.+)[)\uff09]$")
_MAX_EXPANDED_COLUMNS = 32

# stage-1 absolute column layout (recon-verified against all four lists):
# 號次(0) 業者代碼(1) 國語(2) 第一優勢腔(3) 建議漢字(4) 第二優勢腔(5)
_STATION_HUA, _STATION_PRIMARY, _STATION_HANJI, _STATION_SECONDARY = 2, 3, 4, 5
_MIN_STATION_CELLS = 6

PRIMARY_WEIGHT = 700  # 第一優勢腔 (使用者明示為主要讀音)
SECONDARY_WEIGHT = 650  # 第二優勢腔: 保留可用, 排序讓位


@dataclass(frozen=True)
class PlacenameEntry:
    hua: str
    han: str
    code: str
    weight: int


def _cell_paragraphs(cell: ET.Element) -> list[str]:
    paras = []
    for p in cell.iter(f"{_Q_TEXT}p"):
        text = clean_hanlo_text("".join(p.itertext()))
        if text and text != EMPTY_PLACEHOLDER:
            paras.append(text)
    return paras


def _row_cells(row: ET.Element) -> list[list[str]]:
    cells: list[list[str]] = []
    for cell in row.findall(f"{_Q_TABLE}table-cell"):
        repeat = int(cell.get(f"{_Q_TABLE}number-columns-repeated", "1"))
        paras = _cell_paragraphs(cell)
        for _ in range(min(repeat, _MAX_EXPANDED_COLUMNS - len(cells))):
            cells.append(paras)
    return cells


def _header_names(cells: list[list[str]]) -> list[str]:
    return [paras[0] if paras else "" for paras in cells]


def _detect_layout(names: list[str]) -> tuple[str, int, int] | None:
    """Return (layout, han_col, code_col) for a header row, else None."""
    if "地名" in names and "臺灣台語拼音" in names:
        return "stage2", names.index("地名"), names.index("臺灣台語拼音")
    if "國語" in names and any("臺灣台語" in name for name in names):
        return "stage1", _STATION_HUA, _STATION_PRIMARY
    return None


def _unwrap_variant(text: str) -> str:
    """Strip 又唸 parentheses: ``(Kâu-tōng-á)`` → ``Kâu-tōng-á``."""
    match = _PAREN_RE.match(text)
    return match.group(1) if match else text


_PAREN_ALT_RE = re.compile(r"[\uff08(]([^\uff08\uff09()]+)[)\uff09]")


def _expand_reading(text: str) -> list[str]:
    """Split one reading cell into candidate readings.

    Handles slash variants and parenthesized alternates. A slash tail
    with a single syllable is a partial-syllable variant of the previous
    reading (「Lí-hî-thâm-tshun/tshuan」), not a standalone word, and is
    dropped rather than fabricated into a one-syllable entry.
    """
    readings: list[str] = []
    for index, part in enumerate(text.split("/")):
        part = part.strip()
        if not part:
            continue
        alts = _PAREN_ALT_RE.findall(part)
        base = _PAREN_ALT_RE.sub("", part).strip()
        if base:
            if index > 0 and len(re.split(r"[-\s]+", base)) < 2 and readings:
                # Single-syllable slash tail (「tshun/tshuan」): a final-
                # syllable replacement of the previous reading, not a
                # standalone word.
                previous = re.split(r"[-\s]+", readings[-1])
                if len(previous) > 1:
                    readings.append(" ".join([*previous[:-1], base]))
            else:
                readings.append(base)
        for alt in alts:
            alt = alt.strip()
            if alt:
                readings.append(alt)
    return readings


def _split_hanji(text: str) -> tuple[str, list[str]]:
    """Split 「中庄(大庄)」 into main hanji plus parenthesized alternates."""
    alts = [a.strip() for a in _PAREN_ALT_RE.findall(text) if a.strip()]
    return _PAREN_ALT_RE.sub("", text).strip(), alts


def _add_reading(
    entries: list[PlacenameEntry],
    stats: dict[str, int],
    seen: set,
    hua: str,
    han: str,
    reading: str,
    weight: int,
) -> None:
    code = romanization_to_rime_key(reading)
    if code is None:
        stats["skipped_invalid"] += 1
        return
    key = (han, code)
    if key in seen:
        stats["dupe_collapsed"] += 1
        return
    seen.add(key)
    entries.append(PlacenameEntry(hua=hua, han=han, code=code, weight=weight))


def _parse_station_table(table: ET.Element, entries: list[PlacenameEntry], stats: dict[str, int], seen: set) -> None:
    rows = table.findall(f"{_Q_TABLE}table-row")
    if len(rows) < 3:
        return
    stats["skipped_rows"] += 2  # group header row + sub-header row
    for row in rows[2:]:
        cells = _row_cells(row)
        stats["rows"] += 1
        if (
            len(cells) <= max(_STATION_HANJI, _STATION_SECONDARY)
            or not cells[_STATION_HUA]
            or not cells[_STATION_PRIMARY]
        ):
            stats["skipped_rows"] += 1
            continue
        hua = cells[_STATION_HUA][0]
        primary = cells[_STATION_PRIMARY][0]
        secondary = cells[_STATION_SECONDARY][0] if cells[_STATION_SECONDARY] else ""
        primary_code = romanization_to_rime_key(primary)
        if primary_code is None:
            stats["skipped_invalid"] += 1
        else:
            _add_entry(entries, stats, seen, hua, hua, primary_code, PRIMARY_WEIGHT)
            for hanji in cells[_STATION_HANJI]:
                _add_entry(entries, stats, seen, hua, hanji, primary_code, PRIMARY_WEIGHT)
        if secondary:
            _add_reading(entries, stats, seen, hua, hua, _unwrap_variant(secondary), SECONDARY_WEIGHT)


def _add_entry(
    entries: list[PlacenameEntry], stats: dict[str, int], seen: set, hua: str, han: str, code: str, weight: int
) -> None:
    key = (han, code)
    if key in seen:
        stats["dupe_collapsed"] += 1
        return
    seen.add(key)
    entries.append(PlacenameEntry(hua=hua, han=han, code=code, weight=weight))


def _parse_list_table(table: ET.Element, entries: list[PlacenameEntry], stats: dict[str, int], seen: set) -> None:
    layout = None
    han_col = code_col = -1
    for row in table.findall(f"{_Q_TABLE}table-row"):
        cells = _row_cells(row)
        if not any(cells):
            continue
        if layout is None:
            detected = _detect_layout(_header_names(cells))
            if detected is None:
                continue  # title/date preamble tables
            layout, han_col, code_col = detected
            stats["skipped_rows"] += 1
            continue
        stats["rows"] += 1
        if len(cells) <= max(han_col, code_col) or not cells[han_col] or not cells[code_col]:
            stats["skipped_rows"] += 1
            continue
        han_main, han_alts = _split_hanji(cells[han_col][0])
        if not han_main:
            stats["skipped_rows"] += 1
            continue
        readings = _expand_reading(cells[code_col][0])
        codes = [romanization_to_rime_key(reading) for reading in readings]
        valid = [code for code in codes if code is not None]
        stats["skipped_invalid"] += len(codes) - len(valid)
        if not valid:
            continue
        if han_alts and len(valid) == len(han_alts) + 1:
            # 「中庄(大庄)」 + 「Tiong-tsng (Tuā-tsng)」: main hanji takes
            # the base reading, each parenthesized hanji its alternate.
            _add_entry(entries, stats, seen, han_main, han_main, valid[0], PRIMARY_WEIGHT)
            for alt, code in zip(han_alts, valid[1:], strict=True):
                _add_entry(entries, stats, seen, han_main, alt, code, PRIMARY_WEIGHT)
        else:
            for code in valid:
                _add_entry(entries, stats, seen, han_main, han_main, code, PRIMARY_WEIGHT)


def parse_placename_dir(input_dir: Path) -> tuple[list[PlacenameEntry], dict[str, int]]:
    """Parse every *.odt list in the directory into entries plus a report."""
    stats = {
        "rows": 0,
        "entries": 0,
        "skipped_rows": 0,
        "skipped_invalid": 0,
        "dupe_collapsed": 0,
    }
    entries: list[PlacenameEntry] = []
    seen: set[tuple[str, str]] = set()

    for odt_path in sorted(input_dir.glob("*.odt")):
        with zipfile.ZipFile(odt_path) as archive:
            root = ET.fromstring(archive.read("content.xml"))
        for table in root.iter(f"{_Q_TABLE}table"):
            first_cells = next(
                (_row_cells(row) for row in table.findall(f"{_Q_TABLE}table-row") if any(_row_cells(row))),
                None,
            )
            if first_cells is None:
                continue
            layout = _detect_layout(_header_names(first_cells))
            if layout is None:
                continue
            if layout[0] == "stage1":
                _parse_station_table(table, entries, stats, seen)
            else:
                _parse_list_table(table, entries, stats, seen)

    stats["entries"] = len(entries)
    return entries, stats


def write_placename_tsv(entries: list[PlacenameEntry], output_path: Path) -> int:
    """Write entries as 華語地名<TAB>漢字<TAB>rime key<TAB>weight lines."""
    with output_path.open("w", encoding="utf-8") as out:
        for entry in entries:
            out.write(f"{entry.hua}\t{entry.han}\t{entry.code}\t{entry.weight}\n")
    return len(entries)


def main(argv: list[str] | None = None) -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Parse MOE placename ODT lists to TSV")
    parser.add_argument("--input", type=Path, required=True, help="Directory holding the ODT lists")
    parser.add_argument("--output", type=Path, required=True, help="Output TSV path")
    args = parser.parse_args(argv)

    if not args.input.is_dir():
        print(f"Error: Input directory not found: {args.input}", file=sys.stderr)
        sys.exit(1)
    args.output.parent.mkdir(parents=True, exist_ok=True)

    entries, stats = parse_placename_dir(args.input)
    write_placename_tsv(entries, args.output)
    print(
        f"Placenames: {stats['entries']} entries from {stats['rows']} rows "
        f"(skipped={stats['skipped_rows']}, invalid={stats['skipped_invalid']}, "
        f"dupes={stats['dupe_collapsed']}) -> {args.output}"
    )


if __name__ == "__main__":
    main()
