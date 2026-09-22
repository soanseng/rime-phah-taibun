"""Validate Rime dictionary files for format correctness and data quality."""

import argparse
import re
import sys
from pathlib import Path

try:
    from scripts.tl_poj_convert import tl_to_poj
except ModuleNotFoundError:
    from tl_poj_convert import tl_to_poj

RIME_KEY_RE = re.compile(r"^[a-z0-9]+(?:[ -]+[a-z0-9]+)*$")
EDITORIAL_MARKER_RE = re.compile(r"[\uff08(](?:替|文)[\uff09)]")


def validate_dict_format(dict_path: Path) -> list[str]:
    """Validate a Rime dict.yaml file for common issues.

    Checks:
    - YAML header presence (--- ... block)
    - Tab-separated data lines
    - Canonical Rime keys
    - Source-only editorial markers in candidate text
    - Duplicate entries
    Args:
        dict_path: Path to the dict.yaml file

    Returns:
        List of error/warning messages (empty = valid)
    """
    errors = []
    content = dict_path.read_text(encoding="utf-8")
    lines = content.splitlines()

    # Check header
    if not lines or lines[0] != "---":
        errors.append("Missing YAML header: file must start with '---'")
        return errors

    # Find end of header
    header_end = -1
    for i, line in enumerate(lines[1:], 1):
        if line == "...":
            header_end = i
            break
    if header_end == -1:
        errors.append("Missing header terminator '...'")
        return errors

    # Validate data lines
    seen: set[tuple[str, str]] = set()
    for i, line in enumerate(lines[header_end + 1 :], header_end + 2):
        if not line.strip() or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) < 2:
            errors.append(f"Line {i}: bad format (expected tab-separated, got: {line!r})")
            continue
        if EDITORIAL_MARKER_RE.search(parts[0]):
            errors.append(f"Line {i}: source editorial marker in candidate '{parts[0]}'")
        if not RIME_KEY_RE.fullmatch(parts[1]):
            errors.append(f"Line {i}: non-canonical Rime key '{parts[1]}'")
        key = (parts[0], parts[1])
        if key in seen:
            errors.append(f"Line {i}: duplicate entry '{parts[0]}' with key '{parts[1]}'")
        seen.add(key)

    return errors

def verify_poj_integrity(entries: list[dict]) -> list[str]:
    """Fatal TL-to-POJ conversion integrity gate (PLAN section 9-2F).

    For every moe_poj entry (a full-romanization POJ candidate), a moe_tl
    sibling with the same kip_input must exist, and the POJ text must equal
    tl_to_poj applied to the sibling's TL text. Catches pipeline regressions
    that would ship stale or inconsistent POJ candidates.

    Args:
        entries: Pipeline entries with hanlo, kip_input, source fields.

    Returns:
        List of error descriptions (empty = consistent).
    """
    tl_by_kip: dict[str, dict] = {}
    for entry in entries:
        if entry.get("source") == "moe_tl":
            tl_by_kip.setdefault(entry["kip_input"], entry)

    errors: list[str] = []
    for entry in entries:
        if entry.get("source") != "moe_poj":
            continue
        sibling = tl_by_kip.get(entry["kip_input"])
        if sibling is None:
            errors.append(
                f"moe_poj row without moe_tl sibling: {entry.get('hanlo')} ({entry.get('kip_input')})"
            )
            continue
        expected = _poj_identity(tl_to_poj(sibling["hanlo"]))
        if _poj_identity(entry["hanlo"]) != expected:
            errors.append(
                f"stale POJ for {entry['kip_input']}: {entry['hanlo']!r} != tl_to_poj({sibling['hanlo']!r})"
            )

    poj_kips = {entry["kip_input"] for entry in entries if entry.get("source") == "moe_poj"}
    for entry in entries:
        if entry.get("source") == "moe_tl" and entry["kip_input"] not in poj_kips:
            errors.append(
                f"moe_tl row without moe_poj sibling: {entry.get('hanlo')} ({entry.get('kip_input')})"
            )
    return errors


def _poj_identity(text: str) -> str:
    """Comparison identity for POJ text: case-insensitive, hyphen/space unified.

    The shipped dictionary contains legitimate case and separator drift
    between moe_tl/moe_poj siblings (Hu̍t/hu̍t, hōo-i/hōo i); the gate
    targets spelling regressions (ts/ch, ua/oa, o͘/oo), not typography.
    """
    return text.casefold().replace("-", " ")


def main(argv: list[str] | None = None) -> None:
    """CLI entry point for dictionary validation."""
    parser = argparse.ArgumentParser(description="Validate Rime dict.yaml files")
    parser.add_argument("files", type=Path, nargs="+", help="Dict.yaml files to validate")
    args = parser.parse_args(argv)

    total_errors = 0
    for dict_path in args.files:
        if not dict_path.exists():
            print(f"SKIP: {dict_path} not found")
            continue
        errors = validate_dict_format(dict_path)
        if errors:
            print(f"FAIL: {dict_path} ({len(errors)} issues)")
            for err in errors:
                print(f"  - {err}")
            total_errors += len(errors)
        else:
            print(f"OK: {dict_path}")

    sys.exit(1 if total_errors else 0)


if __name__ == "__main__":
    main()
