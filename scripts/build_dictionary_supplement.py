"""Build dictionary entries from 建中的 Taigi input method supplement CSV files."""

from __future__ import annotations

import argparse
import csv
import re
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

try:
    from scripts.convert_chhoetaigi import (
        clean_hanlo_text,
        is_valid_kip_input,
        normalize_implicit_tone,
        unicode_tones_to_numeric,
    )
except ModuleNotFoundError:
    from convert_chhoetaigi import (
        clean_hanlo_text,
        is_valid_kip_input,
        normalize_implicit_tone,
        unicode_tones_to_numeric,
    )


TEXT_COLUMN = "漢字"
ROMAN_COLUMN = "臺灣台語羅馬字"


@dataclass(frozen=True)
class SupplementEntry:
    text: str
    rime_key: str
    weight: int
    source: str
    romanization: str


def source_weight(source_name: str) -> int:
    """Return the default dictionary weight for a supplement CSV file."""
    if source_name.startswith("數字_時間_日期"):
        return 920
    if source_name.startswith("一府五院"):
        return 760
    if source_name.startswith("行政區"):
        return 740
    if source_name.startswith("LKK用字"):
        return 700
    if source_name.startswith("written_supplement"):
        return 700
    if source_name.startswith("台_臺"):
        return 650
    if source_name.startswith("內政部菜市仔名"):
        return 620
    if source_name.startswith("教典僻智識"):
        return 620
    return 600


def romanization_to_rime_key(romanization: str) -> str | None:
    """Convert a Unicode TL romanization string to a space-delimited Rime key."""
    normalized = unicode_tones_to_numeric(romanization)
    normalized = re.sub(r"^-+", "", normalized)
    normalized = re.sub(r"-+$", "", normalized)
    normalized = re.sub(r"-+", "-", normalized)
    if not normalized or not is_valid_kip_input(normalized):
        return None
    return normalize_implicit_tone(normalized).replace("-", " ")


def parse_supplement_rows(
    rows: list[dict[str, str]],
    source_name: str,
) -> tuple[list[SupplementEntry], list[dict[str, str]]]:
    """Parse CSV rows into dictionary entries and skipped-row report records."""
    entries: list[SupplementEntry] = []
    report: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    weight = source_weight(source_name)

    for row in rows:
        text = clean_hanlo_text(row.get(TEXT_COLUMN, ""))
        romanization = row.get(ROMAN_COLUMN, "").strip()
        if not text or not romanization:
            report.append(
                {
                    "source": source_name,
                    "text": text,
                    "romanization": romanization,
                    "reason": "missing_field",
                }
            )
            continue

        rime_key = romanization_to_rime_key(romanization)
        if rime_key is None:
            report.append(
                {
                    "source": source_name,
                    "text": text,
                    "romanization": romanization,
                    "reason": "invalid_romanization",
                }
            )
            continue

        dedupe_key = (text, rime_key)
        if dedupe_key in seen:
            report.append(
                {
                    "source": source_name,
                    "text": text,
                    "romanization": romanization,
                    "reason": "duplicate",
                }
            )
            continue
        seen.add(dedupe_key)
        entries.append(
            SupplementEntry(
                text=text,
                rime_key=rime_key,
                weight=weight,
                source=source_name,
                romanization=romanization,
            )
        )

    return entries, report


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    """Read a supplement CSV file while preserving CSV dialect edge cases."""
    with path.open("r", encoding="utf-8-sig", newline="") as csvfile:
        return list(csv.DictReader(csvfile))


def read_extra_file_rows(path: Path) -> list[dict[str, str]]:
    """Read headerless tab-separated (text, code) rows from an extra file.

    The code column already holds the space-delimited Rime key; it is fed
    through the same romanization pipeline as CSV rows for validation and
    normalization.
    """
    rows: list[dict[str, str]] = []
    with path.open("r", encoding="utf-8") as extra_file:
        for line in extra_file:
            stripped = line.strip()
            if not stripped:
                continue
            parts = stripped.split("\t")
            rows.append(
                {
                    TEXT_COLUMN: parts[0].strip(),
                    ROMAN_COLUMN: parts[1].strip() if len(parts) > 1 else "",
                }
            )
    return rows


def build_supplement_from_dir(
    source_dir: Path,
    output_path: Path,
    report_path: Path,
    extra_files: Sequence[Path] = (),
) -> int:
    """Build supplement TSV output and skipped-row report from a source directory."""
    all_report: list[dict[str, str]] = []
    ordered_keys: list[tuple[str, str]] = []
    entry_by_key: dict[tuple[str, str], SupplementEntry] = {}

    def merge_entries(entries: list[SupplementEntry]) -> None:
        for entry in entries:
            dedupe_key = (entry.text, entry.rime_key)
            existing = entry_by_key.get(dedupe_key)
            if existing is not None:
                all_report.append(
                    {
                        "source": entry.source,
                        "text": entry.text,
                        "romanization": entry.romanization,
                        "reason": "duplicate",
                    }
                )
                if entry.weight > existing.weight:
                    entry_by_key[dedupe_key] = entry
                continue
            ordered_keys.append(dedupe_key)
            entry_by_key[dedupe_key] = entry

    for csv_path in sorted(source_dir.glob("*.csv")):
        rows = read_csv_rows(csv_path)
        entries, report = parse_supplement_rows(rows, source_name=csv_path.name)
        all_report.extend(report)
        merge_entries(entries)

    for extra_path in extra_files:
        rows = read_extra_file_rows(extra_path)
        entries, report = parse_supplement_rows(rows, source_name=extra_path.name)
        all_report.extend(report)
        merge_entries(entries)

    all_entries = [entry_by_key[dedupe_key] for dedupe_key in ordered_keys]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as out:
        for entry in all_entries:
            out.write(f"{entry.text}\t{entry.rime_key}\t{entry.weight}\n")

    report_path.parent.mkdir(parents=True, exist_ok=True)
    with report_path.open("w", encoding="utf-8", newline="") as report_file:
        writer = csv.DictWriter(
            report_file,
            fieldnames=["source", "text", "romanization", "reason"],
            delimiter="\t",
        )
        writer.writeheader()
        writer.writerows(all_report)

    return len(all_entries)


def main(argv: list[str] | None = None) -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Build Rime entries from Taigi input method supplement CSV files")
    parser.add_argument("--input", type=Path, required=True, help="Directory containing supplement CSV files")
    parser.add_argument("--output", type=Path, required=True, help="Output TSV path for dictionary entries")
    parser.add_argument("--report", type=Path, required=True, help="Output TSV path for skipped-row report")
    parser.add_argument(
        "--extra-file",
        type=Path,
        action="append",
        default=[],
        help="Extra headerless TSV (text<TAB>code); repeatable, merged with the same dedup",
    )
    args = parser.parse_args(argv)

    if not args.input.exists():
        print(f"SKIP: supplement source not found at {args.input}", file=sys.stderr)
        return

    extra_files = []
    for extra_path in args.extra_file:
        if extra_path.exists():
            extra_files.append(extra_path)
        else:
            print(f"SKIP: extra file not found at {extra_path}", file=sys.stderr)

    count = build_supplement_from_dir(
        source_dir=args.input,
        output_path=args.output,
        report_path=args.report,
        extra_files=extra_files,
    )
    print(f"Generated {count} supplement entries -> {args.output}", file=sys.stderr)


if __name__ == "__main__":
    main()
