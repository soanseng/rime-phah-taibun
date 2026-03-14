"""Validate Rime dictionary files for format correctness and data quality."""

import argparse
import sys
from pathlib import Path


def validate_dict_format(dict_path: Path) -> list[str]:
    """Validate a Rime dict.yaml file for common issues.

    Checks:
    - YAML header presence (--- ... block)
    - Tab-separated data lines
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
        key = (parts[0], parts[1])
        if key in seen:
            errors.append(f"Line {i}: duplicate entry '{parts[0]}' with key '{parts[1]}'")
        seen.add(key)

    return errors


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
