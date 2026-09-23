#!/usr/bin/env python3
"""Repair digitless (bare) syllables in lighttone dict entries.

Bare syllables (e.g. `khi3 ah`) create exact-tone prism edges that shadow
the abbrev edges single-syllable lookups rely on: typing `ah`, `tsi`, or
`tsiah` then finds no candidates (verified in a pure-engine scratch; one
bad row reproduces it).

Rules:
- Codes keep their exact whitespace: a double space encodes the `--`
  light-tone boundary (kip_to_rime_key in build_lighttone_entries.py);
  only the bare syllable token gains its digit.
- A digit is appended ONLY from character-level evidence in this
  dictionary: (1) the same `*--H` construction with a toned final
  syllable, (2) another word ending in the same character with the toned
  form as final syllable, (3) a single-character entry. No frequency
  guessing across different characters.
- Entries without evidence are dropped (reported), never guessed.

Usage: repair_bare_syllables.py [--apply]
"""

from __future__ import annotations

import re
import sys
from collections import Counter
from pathlib import Path

DICT = Path(__file__).resolve().parents[1] / "schema" / "phah_taibun.dict.yaml"
TONE_RE = re.compile(r"[1-9]$")


def load_entries(dict_path: Path = DICT) -> list[list[str]]:
    entries = []
    in_header = True
    for line in dict_path.read_text(encoding="utf-8").splitlines():
        if in_header:
            if line.strip() == "...":
                in_header = False
            continue
        parts = line.split("\t")
        if len(parts) >= 2:
            entries.append(parts)
    return entries


def build_attestation(entries) -> dict[str, dict[str, str]]:
    """Suffix hanzi -> {toneless spelling -> toned spelling}.

    A character legitimately has several readings (呢: ne1/ni5/nih4), so
    keep every toned spelling keyed by its toneless base and pick the
    majority within a base. Evidence layers, strongest last: single
    character entries, word-final syllables, `*--H` constructions. A
    higher layer replaces lower-layer picks for the same (char, base).
    """
    layers: list[dict[str, dict[str, Counter[str]]]] = [{}, {}, {}]
    for parts in entries:
        word, syls = parts[0], parts[1].split()
        m = re.search(r"--([^-\t]+)$", word)
        if m and len(m.group(1)) == 1 and syls and TONE_RE.search(syls[-1]):
            layer, key, syl = 2, m.group(1), syls[-1]
        elif len(word) >= 2 and syls and TONE_RE.search(syls[-1]):
            layer, key, syl = 1, word[-1], syls[-1]
        elif len(word) == 1 and len(syls) == 1 and TONE_RE.search(syls[0]):
            layer, key, syl = 0, word, syls[0]
        else:
            continue
        base = TONE_RE.sub("", syl)
        layers[layer].setdefault(key, {}).setdefault(base, Counter())[syl] += 1
    att: dict[str, dict[str, str]] = {}
    for layer in layers:
        for hanzi, bases in layer.items():
            per_base = att.setdefault(hanzi, {})
            for base, counter in bases.items():
                per_base[base] = counter.most_common(1)[0][0]
    return att


def repair(entries, attestation):
    """Token-level digit fix preserving all whitespace (`--` boundaries)."""
    out, repaired, drop_log = [], 0, []
    for parts in entries:
        code = parts[1]
        syls = code.split()
        bare = [s for s in syls if not TONE_RE.search(s)]
        if not bare:
            out.append("\t".join(parts))
            continue
        m = re.search(r"--([^-\t]+)$", parts[0])
        key = m.group(1) if m and len(m.group(1)) == 1 else None
        fix = key and len(bare) == 1 and attestation.get(key, {}).get(bare[0])
        if not fix:
            drop_log.append((parts[0], code))
            continue
        parts[1] = re.sub(rf"(?<!\S){re.escape(bare[0])}(?!\S)", fix, code)
        repaired += 1
        out.append("\t".join(parts))
    return out, repaired, drop_log


def main() -> None:
    apply = "--apply" in sys.argv
    entries = load_entries()
    attestation = build_attestation(entries)
    out, repaired, drop_log = repair(entries, attestation)
    print(f"attested chars: {len(attestation)}")
    print(f"entries repaired: {repaired}, dropped: {len(drop_log)}, total out: {len(out)}")
    for w, c in drop_log[:20]:
        print("  DROP", w, c)
    if apply:
        lines = DICT.read_text(encoding="utf-8").splitlines(keepends=True)
        header_end = next(i + 1 for i, line in enumerate(lines) if line.strip() == "...")
        DICT.write_text("".join(lines[:header_end]) + "\n".join(out) + "\n", encoding="utf-8")
        print("APPLIED")


if __name__ == "__main__":
    main()
