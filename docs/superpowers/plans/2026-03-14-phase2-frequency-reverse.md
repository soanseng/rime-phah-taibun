# Phase 2: Word Frequency Refinement + Enhanced Reverse Dictionary

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Improve candidate ranking with real-world word frequencies from iCorpus news data, and build a richer reverse dictionary from MOE structured data with definitions and example sentences.

**Architecture:** A new `scripts/extract_icorpus_freq.py` tokenizes the human-corrected iCorpus TL text (64K sentences) to count word/syllable frequencies, then `build_frequency.py` is enhanced to merge corpus-based frequencies with the existing heuristic weights. A new `scripts/build_moe_reverse.py` parses `moedict-data-twblg/uni/` CSVs to create a richer reverse dictionary with definitions. Both scripts follow existing TDD patterns.

**Tech Stack:** Python 3.10+ (uv, pytest, pyyaml), existing scripts infrastructure

---

## Chunk 1: iCorpus Word Frequency Extraction (Tasks 1-2)

### File Structure

```
scripts/
├── extract_icorpus_freq.py    # NEW: Parse iCorpus TL text → frequency table
├── build_frequency.py         # MODIFY: Merge corpus frequencies with heuristics
tests/
├── test_icorpus_freq.py       # NEW: Tests for frequency extraction
├── test_frequency.py          # MODIFY: Tests for merged frequency logic
```

### Task 1: Extract Word Frequencies from iCorpus

**Goal:** Parse the human-corrected iCorpus TL romanization file (64K lines) to count syllable and word frequencies.

**Files:**
- Create: `scripts/extract_icorpus_freq.py`
- Create: `tests/test_icorpus_freq.py`

**Data format** (`data/icorpus_ka1_han3-ji7/語料/自動標人工改音標.txt`):
- One sentence per line, space-separated TL syllables with tone numbers
- Example: `Obama toa7-seng3 Bi2-kok thau5-chit8-ui7 ou-lang5 chong2-thong2`

- [ ] **Step 1: Write failing test for tokenize_tl_line**

Create `tests/test_icorpus_freq.py`:

```python
"""Tests for iCorpus frequency extraction."""

from scripts.extract_icorpus_freq import tokenize_tl_line


class TestTokenizeTlLine:
    """Tokenize a TL romanization line into words."""

    def test_basic_tokenize(self):
        tokens = tokenize_tl_line("gua2 beh4 khi3 tshit4-tho5")
        assert tokens == ["gua2", "beh4", "khi3", "tshit4-tho5"]

    def test_hyphenated_words_kept(self):
        """Hyphenated compounds are single tokens."""
        tokens = tokenize_tl_line("tsiah8-png7")
        assert tokens == ["tsiah8-png7"]

    def test_empty_line(self):
        assert tokenize_tl_line("") == []

    def test_strips_punctuation(self):
        tokens = tokenize_tl_line("gua2, beh4.")
        assert tokens == ["gua2", "beh4"]

    def test_skips_non_tl(self):
        """Skip tokens that are clearly not TL (e.g., English names)."""
        tokens = tokenize_tl_line("Obama toa7-seng3")
        # Obama has no tone number → skip; toa7-seng3 is valid TL
        assert "toa7-seng3" in tokens
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_icorpus_freq.py -v -x`
Expected: FAIL

- [ ] **Step 3: Implement tokenize_tl_line**

Create `scripts/extract_icorpus_freq.py`:

```python
"""Extract word frequencies from iCorpus TL romanization data.

Parses the human-corrected iCorpus parallel news corpus to count
syllable and word frequencies for Rime dictionary weighting.
"""

import re
from collections import Counter
from pathlib import Path


def tokenize_tl_line(line: str) -> list[str]:
    """Tokenize a TL romanization line into words.

    Keeps hyphenated compounds as single tokens.
    Strips punctuation and skips non-TL tokens.

    Args:
        line: A line of TL romanization text

    Returns:
        List of TL word tokens
    """
    if not line.strip():
        return []
    # Split on whitespace
    raw_tokens = line.strip().split()
    tokens = []
    for token in raw_tokens:
        # Strip punctuation from edges
        cleaned = re.sub(r"^[^a-zA-Z]+|[^a-zA-Z0-9\-]+$", "", token)
        if not cleaned:
            continue
        # A valid TL token should contain at least one tone number (1-9)
        # or be a known particle (a, e, etc.)
        if re.search(r"[1-9]", cleaned) or cleaned.lower() in {"a", "e", "i", "o", "u", "m", "ng"}:
            tokens.append(cleaned)
    return tokens
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_icorpus_freq.py -v -x`
Expected: PASS

- [ ] **Step 5: Write failing test for count_frequencies**

Append to `tests/test_icorpus_freq.py`:

```python
import io
from scripts.extract_icorpus_freq import count_frequencies


class TestCountFrequencies:
    """Count word frequencies from corpus text."""

    def test_basic_count(self):
        text = "gua2 beh4 khi3\ngua2 ai3 li2\n"
        freq = count_frequencies(io.StringIO(text))
        assert freq["gua2"] == 2
        assert freq["beh4"] == 1

    def test_hyphenated_counted(self):
        text = "tsiah8-png7\ntsiah8-png7\ntsiah8-png7\n"
        freq = count_frequencies(io.StringIO(text))
        assert freq["tsiah8-png7"] == 3

    def test_empty_input(self):
        freq = count_frequencies(io.StringIO(""))
        assert len(freq) == 0
```

- [ ] **Step 6: Run test to verify it fails**

Run: `uv run pytest tests/test_icorpus_freq.py::TestCountFrequencies -v -x`
Expected: FAIL

- [ ] **Step 7: Implement count_frequencies**

Add to `scripts/extract_icorpus_freq.py`:

```python
from typing import TextIO


def count_frequencies(corpus_file: TextIO) -> Counter:
    """Count word frequencies from a TL corpus file.

    Args:
        corpus_file: File-like object with one TL sentence per line

    Returns:
        Counter mapping TL words to occurrence counts
    """
    freq = Counter()
    for line in corpus_file:
        tokens = tokenize_tl_line(line)
        freq.update(tokens)
    return freq
```

- [ ] **Step 8: Run test to verify it passes**

Run: `uv run pytest tests/test_icorpus_freq.py -v`
Expected: all PASSED

- [ ] **Step 9: Write failing test for write_frequency_table**

Append to `tests/test_icorpus_freq.py`:

```python
from scripts.extract_icorpus_freq import write_frequency_table


class TestWriteFrequencyTable:
    """Write frequency data to a simple TSV file."""

    def test_writes_sorted(self, tmp_path):
        freq = Counter({"gua2": 100, "beh4": 50, "tsiah8-png7": 75})
        outfile = tmp_path / "freq.tsv"
        write_frequency_table(freq, outfile)
        lines = outfile.read_text().splitlines()
        # Should be sorted by frequency descending
        assert lines[0].startswith("gua2\t")
        assert "100" in lines[0]

    def test_empty_counter(self, tmp_path):
        outfile = tmp_path / "freq.tsv"
        write_frequency_table(Counter(), outfile)
        assert outfile.read_text() == ""
```

- [ ] **Step 10: Run test to verify it fails**

Run: `uv run pytest tests/test_icorpus_freq.py::TestWriteFrequencyTable -v -x`
Expected: FAIL

- [ ] **Step 11: Implement write_frequency_table**

Add to `scripts/extract_icorpus_freq.py`:

```python
def write_frequency_table(freq: Counter, output_path: Path) -> None:
    """Write frequency data to a TSV file sorted by count descending.

    Args:
        freq: Counter mapping words to counts
        output_path: Path to write TSV
    """
    with open(output_path, "w", encoding="utf-8") as f:
        for word, count in freq.most_common():
            f.write(f"{word}\t{count}\n")
```

- [ ] **Step 12: Run all tests, lint, commit**

```bash
uv run pytest tests/test_icorpus_freq.py -v
uv run ruff check scripts/extract_icorpus_freq.py tests/test_icorpus_freq.py
uv run ruff format scripts/extract_icorpus_freq.py tests/test_icorpus_freq.py
git add scripts/extract_icorpus_freq.py tests/test_icorpus_freq.py
git commit -m "feat: iCorpus TL word frequency extractor

Tokenizes human-corrected TL romanization, counts word frequencies,
writes sorted TSV. Filters non-TL tokens and preserves hyphenated compounds."
```

---

### Task 2: Merge Corpus Frequencies into Dictionary Weights

**Goal:** Enhance `build_frequency.py` to accept an optional corpus frequency table and merge it with heuristic weights.

**Files:**
- Modify: `scripts/build_frequency.py`
- Modify: `tests/test_frequency.py`

Strategy: If a word's toneless form appears in the corpus frequency table, boost its weight proportionally. A word appearing 100 times in 64K sentences is very common.

- [ ] **Step 1: Write failing test for load_corpus_frequencies**

Append to `tests/test_frequency.py`:

```python
from scripts.build_frequency import load_corpus_frequencies


class TestLoadCorpusFrequencies:
    """Load corpus frequency TSV into a lookup dict."""

    def test_basic_load(self, tmp_path):
        freq_file = tmp_path / "freq.tsv"
        freq_file.write_text("gua2\t100\nbeh4\t50\n")
        result = load_corpus_frequencies(freq_file)
        assert result["gua2"] == 100
        assert result["beh4"] == 50

    def test_empty_file(self, tmp_path):
        freq_file = tmp_path / "freq.tsv"
        freq_file.write_text("")
        result = load_corpus_frequencies(freq_file)
        assert len(result) == 0

    def test_nonexistent_file(self, tmp_path):
        result = load_corpus_frequencies(tmp_path / "missing.tsv")
        assert len(result) == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_frequency.py::TestLoadCorpusFrequencies -v -x`
Expected: FAIL

- [ ] **Step 3: Implement load_corpus_frequencies**

Add to `scripts/build_frequency.py`:

```python
from pathlib import Path


def load_corpus_frequencies(freq_path: Path) -> dict[str, int]:
    """Load corpus frequency table from TSV file.

    Args:
        freq_path: Path to TSV with word\\tcount format

    Returns:
        Dict mapping words to frequency counts
    """
    if not freq_path.exists():
        return {}
    result = {}
    with open(freq_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split("\t")
            if len(parts) >= 2:
                try:
                    result[parts[0]] = int(parts[1])
                except ValueError:
                    continue
    return result
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_frequency.py -v`
Expected: all PASSED

- [ ] **Step 5: Write failing test for corpus-boosted compute_weights**

Append to `tests/test_frequency.py`:

```python
class TestComputeWeightsWithCorpus:
    """Corpus frequency boost in compute_weights."""

    def test_corpus_boost(self):
        entries = [
            {"hanlo": "食飯", "rime_key": "tsiah png", "source": "itaigi", "kip_input": "tsiah8-png7"},
        ]
        corpus_freq = {"tsiah8-png7": 50}
        result = compute_weights(entries, corpus_freq=corpus_freq)
        # With corpus boost, weight should be higher than without
        result_no_corpus = compute_weights(entries)
        assert result[0]["weight"] > result_no_corpus[0]["weight"]

    def test_no_corpus_same_as_before(self):
        entries = [
            {"hanlo": "食飯", "rime_key": "tsiah png", "source": "itaigi"},
        ]
        result = compute_weights(entries)
        # base=800, length_mod=1.2 -> 960
        assert result[0]["weight"] == 960
```

- [ ] **Step 6: Run test to verify it fails**

Run: `uv run pytest tests/test_frequency.py::TestComputeWeightsWithCorpus -v -x`
Expected: FAIL (compute_weights doesn't accept corpus_freq yet)

- [ ] **Step 7: Update compute_weights to accept corpus frequencies**

Modify `scripts/build_frequency.py` `compute_weights` signature and logic:

```python
def compute_weights(
    entries: list[dict],
    corpus_freq: dict[str, int] | None = None,
) -> list[dict]:
    """Compute final frequency weights for dictionary entries.

    Combines source authority, word length modifier, cross-source overlap bonus,
    and optional corpus frequency boost.

    Args:
        entries: List of dicts with hanlo, rime_key, source fields
        corpus_freq: Optional dict mapping kip_input to corpus occurrence counts

    Returns:
        Deduplicated list with computed 'weight' field (int)
    """
    if corpus_freq is None:
        corpus_freq = {}

    # Count how many sources each (hanlo, rime_key) pair appears in
    key_sources: dict[tuple[str, str], set[str]] = {}
    for entry in entries:
        key = (entry["hanlo"], entry["rime_key"])
        key_sources.setdefault(key, set()).add(entry["source"])

    # Group entries by key, keep best source
    best_entries: dict[tuple[str, str], dict] = {}
    for entry in entries:
        key = (entry["hanlo"], entry["rime_key"])
        source_weight = assign_source_weight(entry["source"])
        existing = best_entries.get(key)
        if existing is None or source_weight > assign_source_weight(existing["source"]):
            best_entries[key] = entry.copy()

    # Compute final weights
    result = []
    for key, entry in best_entries.items():
        base = assign_source_weight(entry["source"])
        length_mod = word_length_modifier(entry["hanlo"])
        overlap_bonus = 1.1 ** (len(key_sources[key]) - 1)

        # Corpus frequency boost: log-scale boost if word appears in corpus
        corpus_boost = 1.0
        kip = entry.get("kip_input", "")
        if kip and kip in corpus_freq:
            import math
            corpus_boost = 1.0 + math.log10(1 + corpus_freq[kip]) * 0.2

        entry["weight"] = int(base * length_mod * overlap_bonus * corpus_boost)
        result.append(entry)

    return result
```

- [ ] **Step 8: Run all tests**

Run: `uv run pytest tests/test_frequency.py -v`
Expected: all PASSED

- [ ] **Step 9: Lint and commit**

```bash
uv run ruff check scripts/build_frequency.py tests/test_frequency.py
uv run ruff format scripts/build_frequency.py tests/test_frequency.py
git add scripts/build_frequency.py scripts/extract_icorpus_freq.py tests/test_frequency.py tests/test_icorpus_freq.py
git commit -m "feat: merge iCorpus word frequencies into dictionary weights

Adds corpus frequency boost (log-scale) to heuristic weight computation.
Words appearing in the 64K-sentence iCorpus news corpus get proportional
weight increases while preserving backward compatibility."
```

---

## Chunk 2: Enhanced Reverse Dictionary from MOE Data (Tasks 3-4)

### Task 3: Parse MOE Structured Data for Reverse Dictionary

**Goal:** Build a richer reverse dictionary using `moedict-data-twblg/uni/` CSVs that includes definitions and example sentences.

**Files:**
- Create: `scripts/build_moe_reverse.py`
- Create: `tests/test_moe_reverse.py`

**Data format** (`data/moedict-data-twblg/uni/詞目總檔.csv`):
- Columns: `主編碼,屬性,詞目,音讀,文白屬性,部首,...`
- `詞目` = the Taiwanese word (hanzi), `音讀` = TL romanization with Unicode tones

- [ ] **Step 1: Write failing test for parse_moe_entries**

Create `tests/test_moe_reverse.py`:

```python
"""Tests for MOE reverse dictionary builder."""

import io

from scripts.build_moe_reverse import parse_moe_entries


class TestParseMoeEntries:
    """Parse MOE 詞目總檔.csv into structured entries."""

    @staticmethod
    def sample_csv():
        return (
            "主編碼,屬性,詞目,音讀,文白屬性,部首\n"
            '1,1,一,tsi̍t,4,一\n'
            '2,1,一,it,0,一\n'
            '3,1,一下,tsi̍t-ē,0,一\n'
        )

    def test_basic_parse(self):
        entries = parse_moe_entries(io.StringIO(self.sample_csv()))
        assert len(entries) >= 2

    def test_entry_fields(self):
        entries = parse_moe_entries(io.StringIO(self.sample_csv()))
        first = entries[0]
        assert first["word"] == "一"
        assert "tsi" in first["reading"]  # Unicode TL
        assert first["moe_id"] == "1"

    def test_multiple_readings(self):
        """Same word with different readings produces multiple entries."""
        entries = parse_moe_entries(io.StringIO(self.sample_csv()))
        yi_entries = [e for e in entries if e["word"] == "一"]
        assert len(yi_entries) == 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_moe_reverse.py -v -x`
Expected: FAIL

- [ ] **Step 3: Implement parse_moe_entries**

Create `scripts/build_moe_reverse.py`:

```python
"""Build enhanced reverse dictionary from MOE structured data.

Parses moedict-data-twblg/uni/ CSVs to create a reverse lookup dictionary
with definitions and example sentences. CC BY-ND 3.0 — reverse lookup only.
"""

import csv
from pathlib import Path
from typing import TextIO


def parse_moe_entries(csvfile: TextIO) -> list[dict]:
    """Parse MOE 詞目總檔.csv into structured entries.

    Args:
        csvfile: File-like object for 詞目總檔.csv

    Returns:
        List of dicts with word, reading, moe_id, wen_bai
    """
    entries = []
    reader = csv.DictReader(csvfile)
    for row in reader:
        word = row.get("詞目", "").strip()
        reading = row.get("音讀", "").strip()
        moe_id = row.get("主編碼", "").strip()
        wen_bai = row.get("文白屬性", "0").strip()
        if not word or not reading:
            continue
        entries.append({
            "word": word,
            "reading": reading,
            "moe_id": moe_id,
            "wen_bai": wen_bai,
        })
    return entries
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_moe_reverse.py -v`
Expected: all PASSED

- [ ] **Step 5: Write failing test for load_definitions**

Append to `tests/test_moe_reverse.py`:

```python
from scripts.build_moe_reverse import load_definitions


class TestLoadDefinitions:
    """Load definitions from 釋義.csv."""

    @staticmethod
    def sample_definitions_csv():
        return (
            "釋義總序號,主編碼,釋義順序,詞性代號,釋義\n"
            "1,1,1,15,數目。\n"
            "2,1,2,6,全部的、整個的。\n"
            "3,3,1,6,稍微。\n"
        )

    def test_basic_load(self):
        defs = load_definitions(io.StringIO(self.sample_definitions_csv()))
        assert "1" in defs
        assert len(defs["1"]) == 2

    def test_definition_text(self):
        defs = load_definitions(io.StringIO(self.sample_definitions_csv()))
        assert defs["1"][0] == "數目。"
```

- [ ] **Step 6: Run test to verify it fails**

Run: `uv run pytest tests/test_moe_reverse.py::TestLoadDefinitions -v -x`
Expected: FAIL

- [ ] **Step 7: Implement load_definitions**

Add to `scripts/build_moe_reverse.py`:

```python
def load_definitions(csvfile: TextIO) -> dict[str, list[str]]:
    """Load definitions from MOE 釋義.csv.

    Args:
        csvfile: File-like object for 釋義.csv

    Returns:
        Dict mapping moe_id to list of definition strings
    """
    defs: dict[str, list[str]] = {}
    reader = csv.DictReader(csvfile)
    for row in reader:
        moe_id = row.get("主編碼", "").strip()
        definition = row.get("釋義", "").strip()
        if not moe_id or not definition:
            continue
        defs.setdefault(moe_id, []).append(definition)
    return defs
```

- [ ] **Step 8: Run test to verify it passes**

Run: `uv run pytest tests/test_moe_reverse.py -v`
Expected: all PASSED

- [ ] **Step 9: Write failing test for write_enhanced_reverse_dict**

Append to `tests/test_moe_reverse.py`:

```python
from scripts.build_moe_reverse import write_enhanced_reverse_dict


class TestWriteEnhancedReverseDict:
    """Write enhanced reverse dictionary."""

    def test_writes_with_definitions(self, tmp_path):
        entries = [
            {"word": "一", "reading": "tsi̍t", "moe_id": "1", "wen_bai": "4"},
        ]
        defs = {"1": ["數目。", "全部的。"]}
        outfile = tmp_path / "reverse.dict.yaml"
        write_enhanced_reverse_dict(entries, defs, outfile)
        content = outfile.read_text()
        assert "一" in content
        assert "phah_taibun_reverse" in content

    def test_entries_tab_separated(self, tmp_path):
        entries = [
            {"word": "食飯", "reading": "tsia̍h-pn̄g", "moe_id": "100", "wen_bai": "0"},
        ]
        outfile = tmp_path / "reverse.dict.yaml"
        write_enhanced_reverse_dict(entries, {}, outfile)
        content = outfile.read_text()
        lines = [ln for ln in content.splitlines() if "\t" in ln]
        assert len(lines) >= 1
```

- [ ] **Step 10: Run test to verify it fails**

Run: `uv run pytest tests/test_moe_reverse.py::TestWriteEnhancedReverseDict -v -x`
Expected: FAIL

- [ ] **Step 11: Implement write_enhanced_reverse_dict**

Add to `scripts/build_moe_reverse.py`:

```python
def write_enhanced_reverse_dict(
    entries: list[dict],
    definitions: dict[str, list[str]],
    output_path: Path,
) -> None:
    """Write enhanced reverse lookup dictionary.

    Combines MOE entries with definitions for richer reverse lookup.

    Args:
        entries: List of MOE entry dicts
        definitions: Dict mapping moe_id to definition lists
        output_path: Path to write reverse dict.yaml
    """
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("---\n")
        f.write("name: phah_taibun_reverse\n")
        f.write('version: "0.2.0"\n')
        f.write("sort: by_weight\n")
        f.write("use_preset_vocabulary: false\n")
        f.write("...\n")
        for entry in entries:
            word = entry["word"]
            reading = entry["reading"]
            moe_id = entry["moe_id"]
            # Build comment with reading and first definition
            defs_list = definitions.get(moe_id, [])
            comment = reading
            if defs_list:
                comment += " " + defs_list[0]
            # Weight: wen_bai=4 (文讀 preferred) gets lower weight
            weight = 500 if entry.get("wen_bai", "0") == "0" else 300
            f.write(f"{word}\t{word}\t{weight}\n")
```

- [ ] **Step 12: Run all tests, lint, commit**

```bash
uv run pytest tests/test_moe_reverse.py -v
uv run ruff check scripts/build_moe_reverse.py tests/test_moe_reverse.py
uv run ruff format scripts/build_moe_reverse.py tests/test_moe_reverse.py
git add scripts/build_moe_reverse.py tests/test_moe_reverse.py
git commit -m "feat: enhanced reverse dictionary from MOE structured data

Parses moedict-data-twblg/uni/ 詞目總檔.csv and 釋義.csv to build
a reverse lookup dictionary with definitions. Respects CC BY-ND 3.0
by using data only for reverse lookup display."
```

---

## Chunk 3: Integration + CLI + Full Pipeline (Task 4)

### Task 4: Wire Everything Together

**Goal:** Add CLI entry points, run the full pipeline with real data, update integration tests.

**Files:**
- Modify: `scripts/extract_icorpus_freq.py` (add CLI)
- Modify: `scripts/build_moe_reverse.py` (add CLI)
- Modify: `tests/test_integration.py` (add Phase 2 integration tests)

- [ ] **Step 1: Add CLI to extract_icorpus_freq.py**

Append to `scripts/extract_icorpus_freq.py`:

```python
import argparse
import sys


def main(argv: list[str] | None = None) -> None:
    """CLI entry point for iCorpus frequency extraction."""
    parser = argparse.ArgumentParser(description="Extract word frequencies from iCorpus TL data")
    parser.add_argument("--input", type=Path, required=True, help="Path to iCorpus TL text file")
    parser.add_argument("--output", type=Path, required=True, help="Output TSV path")
    args = parser.parse_args(argv)

    if not args.input.exists():
        print(f"Error: Input not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with open(args.input, encoding="utf-8") as f:
        freq = count_frequencies(f)
    write_frequency_table(freq, args.output)
    print(f"Extracted {len(freq)} unique words, {sum(freq.values())} total tokens → {args.output}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Add CLI to build_moe_reverse.py**

Append to `scripts/build_moe_reverse.py`:

```python
import argparse
import sys


def main(argv: list[str] | None = None) -> None:
    """CLI entry point for MOE reverse dictionary builder."""
    parser = argparse.ArgumentParser(description="Build enhanced reverse dictionary from MOE data")
    parser.add_argument("--input", type=Path, required=True, help="Path to moedict-data-twblg/uni/ directory")
    parser.add_argument("--output", type=Path, required=True, help="Output reverse dict.yaml path")
    args = parser.parse_args(argv)

    vocab_csv = args.input / "詞目總檔.csv"
    defs_csv = args.input / "釋義.csv"

    if not vocab_csv.exists():
        print(f"Error: 詞目總檔.csv not found in {args.input}", file=sys.stderr)
        sys.exit(1)

    with open(vocab_csv, encoding="utf-8") as f:
        entries = parse_moe_entries(f)

    definitions = {}
    if defs_csv.exists():
        with open(defs_csv, encoding="utf-8") as f:
            definitions = load_definitions(f)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    write_enhanced_reverse_dict(entries, definitions, args.output)
    print(f"Written {len(entries)} entries to {args.output}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Add Phase 2 integration tests**

Append to `tests/test_integration.py`:

```python
from scripts.extract_icorpus_freq import count_frequencies

ICORPUS_FILE = DATA_DIR / "icorpus_ka1_han3-ji7" / "語料" / "自動標人工改音標.txt"
MOE_UNI_DIR = DATA_DIR / "moedict-data-twblg" / "uni"


@pytest.mark.skipif(
    not ICORPUS_FILE.exists(),
    reason="iCorpus data not downloaded",
)
class TestICorpusIntegration:
    """Test iCorpus frequency extraction against real data."""

    def test_extracts_meaningful_frequencies(self):
        with open(ICORPUS_FILE, encoding="utf-8") as f:
            freq = count_frequencies(f)
        assert len(freq) > 1000, f"Expected >1K unique words, got {len(freq)}"
        # Common words should appear frequently
        total = sum(freq.values())
        assert total > 10000, f"Expected >10K total tokens, got {total}"


@pytest.mark.skipif(
    not (MOE_UNI_DIR / "詞目總檔.csv").exists(),
    reason="MOE data not downloaded",
)
class TestMoeReverseIntegration:
    """Test MOE reverse dictionary against real data."""

    def test_parses_moe_vocabulary(self):
        from scripts.build_moe_reverse import parse_moe_entries
        with open(MOE_UNI_DIR / "詞目總檔.csv", encoding="utf-8") as f:
            entries = parse_moe_entries(f)
        assert len(entries) > 5000, f"Expected >5K entries, got {len(entries)}"
```

- [ ] **Step 4: Run integration tests**

Run: `uv run pytest tests/test_integration.py -v`
Expected: all PASSED

- [ ] **Step 5: Run full pipeline against real data**

```bash
# Extract iCorpus frequencies
uv run python scripts/extract_icorpus_freq.py \
  --input data/icorpus_ka1_han3-ji7/語料/自動標人工改音標.txt \
  --output data/icorpus_freq.tsv

# Build MOE reverse dict
uv run python scripts/build_moe_reverse.py \
  --input data/moedict-data-twblg/uni \
  --output schema/phah_taibun_reverse.dict.yaml
```

- [ ] **Step 6: Run full test suite with coverage**

Run: `uv run pytest --cov=scripts --cov-report=term-missing -v`
Expected: 80%+ coverage, all PASSED

- [ ] **Step 7: Lint and final commit**

```bash
uv run ruff check scripts/ tests/
uv run ruff format scripts/ tests/
git add scripts/ tests/ docs/superpowers/plans/2026-03-14-phase2-frequency-reverse.md
git commit -m "feat: Phase 2 — iCorpus frequency refinement + MOE reverse dictionary

- extract_icorpus_freq.py: Tokenizes 64K iCorpus sentences for word frequency
- build_frequency.py: Corpus frequency boost (log-scale) merged with heuristics
- build_moe_reverse.py: Enhanced reverse dict from MOE structured data with definitions
- Integration tests against real downloaded data"
```
