"""Convert MOE KipSutian ODS data into the flat kautian.csv shape.

The upstream ODS is a normalized workbook. This script keeps the same flat CSV
columns already consumed by build_kipsutian_reverse.py and
extract_kipsutian_sentences.py, without requiring pandas/odfpy at runtime.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import zipfile
from collections import defaultdict
from collections.abc import Iterable
from pathlib import Path
from xml.etree import ElementTree as ET

NS = {
    "office": "urn:oasis:names:tc:opendocument:xmlns:office:1.0",
    "table": "urn:oasis:names:tc:opendocument:xmlns:table:1.0",
    "text": "urn:oasis:names:tc:opendocument:xmlns:text:1.0",
}

CSV_FIELDS = [
    "詞目id",
    "詞目類型",
    "漢字",
    "羅馬字",
    "分類",
    "羅馬字音檔檔名",
    "又唸作",
    "合音唸作",
    "俗唸作",
    "語音差異",
    "詞彙比較",
    "名",
    "姓",
    "異用字",
    "詞目tuì詞目近義",
    "詞目tuì詞目反義",
    "解說",
    "詞性",
    "例句",
    "例句-華語",
    "例句-音檔",
    "義項tuì義項近義",
    "義項tuì義項反義",
    "義項tuì詞目近義",
    "義項tuì詞目反義",
]

ENTRY_RELATIONS = [
    "又唸作",
    "合音唸作",
    "俗唸作",
    "語音差異",
    "詞彙比較",
    "名",
    "姓",
    "異用字",
    "詞目tuì詞目近義",
    "詞目tuì詞目反義",
]

DEF_RELATIONS = [
    "義項tuì義項近義",
    "義項tuì義項反義",
    "義項tuì詞目近義",
    "義項tuì詞目反義",
]


def _q(namespace: str, name: str) -> str:
    return f"{{{NS[namespace]}}}{name}"


def _normalize_id(value: str) -> str:
    value = value.strip()
    if value.endswith(".0"):
        return value[:-2]
    return value


def _cell_value(cell: ET.Element) -> str:
    value_type = cell.attrib.get(_q("office", "value-type"))
    if value_type in {"float", "percentage", "currency"}:
        return _normalize_id(cell.attrib.get(_q("office", "value"), ""))

    paragraphs = ["".join(paragraph.itertext()) for paragraph in cell.findall("text:p", NS)]
    if paragraphs:
        return "\n".join(paragraphs)
    return "".join(cell.itertext())


def _iter_row_values(row: ET.Element, max_columns: int | None = None) -> Iterable[str]:
    values: list[str] = []
    for cell in row.findall("table:table-cell", NS):
        repeat = int(cell.attrib.get(_q("table", "number-columns-repeated"), "1"))
        value = _cell_value(cell)
        if max_columns is not None:
            repeat = min(repeat, max_columns - len(values))
        if repeat <= 0:
            break
        values.extend([value] * repeat)
        if max_columns is not None and len(values) >= max_columns:
            break
    return values


def _read_sheet(sheet: ET.Element) -> list[dict[str, str]]:
    rows = sheet.findall("table:table-row", NS)
    if not rows:
        return []

    header: list[str] | None = None
    records: list[dict[str, str]] = []
    for row in rows:
        if header is None:
            values = list(_iter_row_values(row))
            if any(values):
                header = values
            continue

        values = list(_iter_row_values(row, max_columns=len(header)))
        values.extend([""] * (len(header) - len(values)))
        if not any(values):
            continue
        records.append({name: values[index] for index, name in enumerate(header) if name})
    return records


def _read_ods_tables(path: Path) -> dict[str, list[dict[str, str]]]:
    with zipfile.ZipFile(path) as archive:
        content = archive.read("content.xml")

    root = ET.fromstring(content)
    spreadsheet = root.find("office:body/office:spreadsheet", NS)
    if spreadsheet is None:
        return {}

    tables: dict[str, list[dict[str, str]]] = {}
    for sheet in spreadsheet.findall("table:table", NS):
        name = sheet.attrib.get(_q("table", "name"), "")
        if name:
            tables[name] = _read_sheet(sheet)
    return tables


def _format_hanji(text: str) -> str:
    return text.replace("【", "(").replace("】", ")") if text else text


def _format_lomaji(text: str) -> str:
    if not text:
        return text
    match = re.match(r"^【(.*?)】(.*)$", text)
    if not match:
        return text

    tag = match.group(1)
    return "/".join(f"{part.strip()}({tag})" for part in match.group(2).split("/"))


def _group_by(rows: Iterable[dict[str, str]], keys: tuple[str, ...]) -> dict[tuple[str, ...], list[dict[str, str]]]:
    grouped: dict[tuple[str, ...], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        key = tuple(row.get(part, "") for part in keys)
        if not all(key):
            continue
        grouped[key].append(row)
    return grouped


def _entry_relation_value(name: str, rows: list[dict[str, str]]) -> str:
    if name == "異用字":
        return "/".join(row["異用字"] for row in rows if row.get("異用字"))
    if name == "語音差異":
        lines = []
        for row in rows:
            for key, value in row.items():
                if key not in {"詞目id", "漢字"} and value:
                    lines.append(f"{key}：{value}")  # noqa: RUF001
        return "\n".join(lines)
    if name in {"詞目tuì詞目近義", "詞目tuì詞目反義"}:
        return "/".join(row["對應詞目漢字"] for row in rows if row.get("對應詞目漢字"))
    return json.dumps(rows, ensure_ascii=False) if rows else ""


def _definition_relation_value(index: int, rows: list[dict[str, str]]) -> str:
    targets = [row["對應詞目漢字"] for row in rows if row.get("對應詞目漢字")]
    return f"{index}. {'/'.join(targets)}" if targets else ""


def _flatten_entry(
    entry: dict[str, str],
    definitions: list[dict[str, str]],
    sentence_groups: dict[tuple[str, str], list[dict[str, str]]],
    entry_relation_groups: dict[str, dict[tuple[str], list[dict[str, str]]]],
    definition_relation_groups: dict[str, dict[tuple[str, str], list[dict[str, str]]]],
) -> dict[str, str]:
    entry_id = entry.get("詞目id", "")
    row = {field: entry.get(field, "") for field in CSV_FIELDS}
    row["漢字"] = _format_hanji(row["漢字"])
    row["羅馬字"] = _format_lomaji(row["羅馬字"])

    for name, groups in entry_relation_groups.items():
        row[name] = _entry_relation_value(name, groups.get((entry_id,), []))

    explanations: list[str] = []
    parts_of_speech: list[str] = []
    sentence_lines: list[str] = []
    sentence_hoabun_lines: list[str] = []
    sentence_audio_lines: list[str] = []
    definition_relation_lines: dict[str, list[str]] = {name: [] for name in DEF_RELATIONS}
    multiple_definitions = len(definitions) > 1

    for index, definition in enumerate(definitions, 1):
        definition_id = definition.get("義項id", "")
        part_of_speech = definition.get("詞性", "")
        explanation = definition.get("解說", "")
        prefix = f"({part_of_speech})" if part_of_speech else ""
        explanations.append(f"{index}. {prefix} {explanation}".strip())
        if part_of_speech:
            parts_of_speech.append(f"{index}. {part_of_speech}")

        sentences = sentence_groups.get((entry_id, definition_id), [])
        for sentence_index, sentence in enumerate(sentences, 1):
            if multiple_definitions:
                sentence_prefix = f"{index}-{sentence_index}." if len(sentences) > 1 else f"{index}."
            else:
                sentence_prefix = f"{sentence_index}."

            hanji = _format_hanji(sentence.get("漢字", ""))
            lomaji = _format_lomaji(sentence.get("羅馬字", ""))
            main = f"{sentence_prefix} {hanji}"
            if lomaji:
                main += f" ({lomaji})"
            sentence_lines.append(main)
            sentence_hoabun_lines.append(f"{sentence_prefix} {sentence.get('華語', '')}")
            sentence_audio_lines.append(f"{sentence_prefix} {sentence.get('音檔檔名', '')}")

        for name, groups in definition_relation_groups.items():
            value = _definition_relation_value(index, groups.get((entry_id, definition_id), []))
            if value:
                definition_relation_lines[name].append(value)

    row["解說"] = "\n".join(explanations)
    row["詞性"] = "\n".join(parts_of_speech)
    row["例句"] = "\n".join(sentence_lines)
    row["例句-華語"] = "\n".join(sentence_hoabun_lines)
    row["例句-音檔"] = "\n".join(sentence_audio_lines)
    for name, lines in definition_relation_lines.items():
        row[name] = "\n".join(lines)
    return row


def convert_kautian_ods(input_path: Path, output_path: Path) -> int:
    """Convert a KipSutian ODS workbook to flat CSV.

    Returns the number of rows written.
    """
    tables = _read_ods_tables(input_path)
    entries = tables.get("詞目", [])
    definitions = tables.get("義項", [])
    sentences = tables.get("例句", [])

    def_to_entry = {row.get("義項id", ""): row.get("詞目id", "") for row in definitions if row.get("義項id")}
    for name in DEF_RELATIONS:
        for row in tables.get(name, []):
            if not row.get("詞目id") and row.get("義項id") in def_to_entry:
                row["詞目id"] = def_to_entry[row["義項id"]]

    definition_groups = _group_by(definitions, ("詞目id",))
    sentence_groups = _group_by(sentences, ("詞目id", "義項id"))
    entry_relation_groups = {name: _group_by(tables.get(name, []), ("詞目id",)) for name in ENTRY_RELATIONS}
    definition_relation_groups = {name: _group_by(tables.get(name, []), ("詞目id", "義項id")) for name in DEF_RELATIONS}

    rows = [
        _flatten_entry(
            entry,
            definition_groups.get((entry.get("詞目id", ""),), []),
            sentence_groups,
            entry_relation_groups,
            definition_relation_groups,
        )
        for entry in entries
    ]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Convert MOE KipSutian kautian.ods to flat kautian.csv")
    parser.add_argument("--input", type=Path, required=True, help="Path to kautian.ods")
    parser.add_argument("--output", type=Path, required=True, help="Output kautian.csv path")
    args = parser.parse_args(argv)

    if not args.input.exists():
        print(f"Error: not found: {args.input}", file=sys.stderr)
        return 1

    count = convert_kautian_ods(args.input, args.output)
    print(f"Written {count} rows to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
