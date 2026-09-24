"""Parse MOE STTI 學科術語臺灣台語對譯 ODS into a dictionary source TSV.

Source: 教育部「學科術語臺灣台語/臺灣客語對譯查詢」綜整檔
(https://stti.moe.edu.tw/.galleries/file-download/ttg_20241219.ods),
released under 創用CC-姓名標示 3.0 臺灣 (CC BY 3.0 TW). Only the
臺灣台語 columns are consumed (the sheet carries no 客語 columns).

Each cell holds one paragraph per variant, so 詞彙/臺羅 columns are
parallel variant lists. Pairing rules — never invent (漢字, 讀音) pairs
the source does not attest (詞身份 invariant):

- len(詞彙) == len(臺羅): pair positionally.
- single 詞彙 variant: attach every 臺羅 variant.
- otherwise: skip the row and count it in ``skipped_mismatch``.

Codes reuse build_dictionary_supplement.romanization_to_rime_key, so
Unicode TL diacritics become numeric tones and 連讀 ``--`` markers
collapse exactly like the supplement track. Output lines are
學科術語<TAB>詞彙<TAB>rime key; the 華語 column feeds the hoabun_map
stage from the same file.
"""

from __future__ import annotations

import argparse
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

TERM_HEADER = "學科術語"
HAN_HEADER = "臺灣台語詞彙"
LO_HEADER = "臺羅"

# Data rows span ≤11 columns; ODS files pad with huge repeated empty
# cells, so cap expansion to keep column indices sane and memory flat.
_MAX_EXPANDED_COLUMNS = 32


@dataclass(frozen=True)
class SttiEntry:
    hua: str
    han: str
    code: str


def _cell_paragraphs(cell: ET.Element) -> list[str]:
    paras = []
    for p in cell.iter(f"{_Q_TEXT}p"):
        text = clean_hanlo_text("".join(p.itertext()))
        if text:
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


def _column_indices(header_cells: list[list[str]]) -> tuple[int, int, int]:
    names = [paras[0] if paras else "" for paras in header_cells]
    try:
        return names.index(TERM_HEADER), names.index(HAN_HEADER), names.index(LO_HEADER)
    except ValueError as exc:
        raise SystemExit(f"STTI ODS missing expected header column: {exc}") from exc


def parse_stti_ods(path: Path) -> tuple[list[SttiEntry], dict[str, int]]:
    """Parse the STTI ODS into entries plus a skipped-row report."""
    with zipfile.ZipFile(path) as archive:
        root = ET.fromstring(archive.read("content.xml"))
    table = next(root.iter(f"{_Q_TABLE}table"))
    rows = table.findall(f"{_Q_TABLE}table-row")

    stats = {
        "rows": 0,
        "entries": 0,
        "skipped_mismatch": 0,
        "skipped_empty": 0,
        "skipped_invalid": 0,
        "dupe_collapsed": 0,
    }
    entries: list[SttiEntry] = []
    seen: set[tuple[str, str]] = set()

    term_i = han_i = lo_i = -1
    for row in rows:
        cells = _row_cells(row)
        if not any(cells):
            continue
        if term_i < 0:
            term_i, han_i, lo_i = _column_indices(cells)
            continue
        stats["rows"] += 1
        if max(term_i, han_i, lo_i) >= len(cells):
            stats["skipped_empty"] += 1
            continue
        hua = cells[term_i][0] if cells[term_i] else ""
        han_variants = cells[han_i]
        lo_variants = cells[lo_i]
        if not hua or not han_variants or not lo_variants:
            stats["skipped_empty"] += 1
            continue

        if len(han_variants) == len(lo_variants):
            pairs = list(zip(han_variants, lo_variants, strict=True))
        elif len(han_variants) == 1:
            pairs = [(han_variants[0], lo) for lo in lo_variants]
        else:
            stats["skipped_mismatch"] += 1
            continue

        for han, lo in pairs:
            code = romanization_to_rime_key(lo)
            if code is None:
                stats["skipped_invalid"] += 1
                continue
            key = (han, code)
            if key in seen:
                stats["dupe_collapsed"] += 1
                continue
            seen.add(key)
            entries.append(SttiEntry(hua=hua, han=han, code=code))

    stats["entries"] = len(entries)
    return entries, stats


def write_stti_tsv(entries: list[SttiEntry], output_path: Path) -> int:
    """Write entries as 學科術語<TAB>詞彙<TAB>rime key lines."""
    with output_path.open("w", encoding="utf-8") as out:
        for entry in entries:
            out.write(f"{entry.hua}\t{entry.han}\t{entry.code}\n")
    return len(entries)


def main(argv: list[str] | None = None) -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Parse MOE STTI 學科術語 ODS to TSV")
    parser.add_argument("--input", type=Path, required=True, help="Path to the ttg ODS file")
    parser.add_argument("--output", type=Path, required=True, help="Output TSV path")
    args = parser.parse_args(argv)

    if not args.input.exists():
        print(f"Error: Input file not found: {args.input}", file=sys.stderr)
        sys.exit(1)
    args.output.parent.mkdir(parents=True, exist_ok=True)

    entries, stats = parse_stti_ods(args.input)
    write_stti_tsv(entries, args.output)
    print(
        f"STTI: {stats['entries']} entries from {stats['rows']} rows "
        f"(mismatch={stats['skipped_mismatch']}, invalid={stats['skipped_invalid']}, "
        f"empty={stats['skipped_empty']}, dupes={stats['dupe_collapsed']}) -> {args.output}"
    )


if __name__ == "__main__":
    main()
