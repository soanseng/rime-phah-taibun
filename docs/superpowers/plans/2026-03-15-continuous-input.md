# Continuous Input Improvement Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enrich the Rime dictionary with multi-word phrases extracted from 6 Taiwanese corpora, improving continuous sentence input quality.

**Architecture:** Extract sentence-level text from all available corpora (iCorpus, Ungian, nmtl, KipSutian, Khin-hoan, ChhoeTaigi), build a romanization-to-text reverse index from the existing dictionary, generate bigram phrases with frequency-based weights, and append them to `phah_taibun.dict.yaml`. The `fluency_editor` (already enabled) combined with the enriched dictionary produces better auto-segmentation.

**Tech Stack:** Python 3.10+, pyyaml, pytest, existing Rime infrastructure

**Spec:** `docs/superpowers/specs/2026-03-15-continuous-input-design.md`

---

## Chunk 1: Enhanced POJ→TL Conversion

### Task 1: Enhance `poj_to_tl()` for historical POJ texts

**Files:**
- Modify: `scripts/tl_poj_convert.py`
- Modify: `tests/test_tl_poj_convert.py`

- [ ] **Step 1: Write failing tests for POJ diacritics and edge cases**

Add to `tests/test_tl_poj_convert.py`:

```python
class TestPojToTlEnhanced:
    """Enhanced POJ→TL for historical texts."""

    def test_chh_to_tsh(self):
        assert poj_to_tl("chhit") == "tshit"

    def test_ch_to_ts(self):
        assert poj_to_tl("chit") == "tsit"

    def test_eng_to_ing(self):
        assert poj_to_tl("seng") == "sing"

    def test_ek_to_ik(self):
        assert poj_to_tl("sek") == "sik"

    def test_oa_to_ua(self):
        assert poj_to_tl("koa") == "kua"

    def test_oe_to_ue(self):
        assert poj_to_tl("koe") == "kue"

    def test_ou_to_oo(self):
        """POJ ou → TL oo."""
        assert poj_to_tl("kou") == "koo"

    def test_o_dot_to_oo(self):
        """POJ o͘ (combining dot above) → TL oo."""
        assert poj_to_tl("ko\u0358") == "koo"

    def test_nn_nasal(self):
        """POJ nn (nasal) → TL nn (kept as-is, both systems use nn)."""
        assert poj_to_tl("sann") == "sann"

    def test_superscript_n(self):
        """POJ ⁿ → TL nn."""
        assert poj_to_tl("saⁿ") == "sann"

    def test_capitalize_to_lower(self):
        """Normalize capitals."""
        assert poj_to_tl("Chhit-thô") == "tshit-thô"

    def test_tone_diacritics_stripped(self):
        """á→a2, à→a3, â→a5, ā→a7, a̍→a8."""
        from scripts.tl_poj_convert import poj_diacritics_to_tone_numbers
        assert poj_diacritics_to_tone_numbers("á") == "a2"
        assert poj_diacritics_to_tone_numbers("à") == "a3"
        assert poj_diacritics_to_tone_numbers("â") == "a5"
        assert poj_diacritics_to_tone_numbers("ā") == "a7"
        assert poj_diacritics_to_tone_numbers("a̍") == "a8"

    def test_preserve_hyphens(self):
        assert poj_to_tl("chhit-thô") == "tshit-thô"

    def test_empty(self):
        assert poj_to_tl("") == ""
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `mise exec uv -- uv run pytest tests/test_tl_poj_convert.py::TestPojToTlEnhanced -v`
Expected: FAIL (new test class, some functions not defined)

- [ ] **Step 3: Implement enhanced `poj_to_tl()` and `poj_diacritics_to_tone_numbers()`**

In `scripts/tl_poj_convert.py`, add:

```python
import unicodedata

# POJ diacritics → tone number mapping
_TONE_DIACRITICS = {
    '\u0301': '2',  # acute accent (á) → tone 2
    '\u0300': '3',  # grave accent (à) → tone 3
    '\u0302': '5',  # circumflex (â) → tone 5
    '\u0304': '7',  # macron (ā) → tone 7
    '\u030d': '8',  # vertical line above (a̍) → tone 8
}


def poj_diacritics_to_tone_numbers(text: str) -> str:
    """Convert POJ diacritics to TL tone numbers.

    Handles: á→a2, à→a3, â→a5, ā→a7, a̍→a8.
    Characters without diacritics get no tone number (tone 1).
    """
    # Decompose Unicode to separate base chars from combining marks
    decomposed = unicodedata.normalize("NFD", text)
    result = []
    tone = ""
    for ch in decomposed:
        cat = unicodedata.category(ch)
        if cat.startswith("M"):  # combining mark
            if ch in _TONE_DIACRITICS:
                tone = _TONE_DIACRITICS[ch]
            elif ch == '\u0358':  # combining dot above right (o͘)
                result.append("o")  # double the o → oo
            # skip other combining marks
        else:
            result.append(ch)
    return "".join(result) + tone
```

Update `poj_to_tl()` to:
1. Normalize to lowercase first
2. Convert `ⁿ` → `nn`
3. Convert `o͘` (U+0358 combining dot above right) → `oo`
4. Apply existing substitutions (chh→tsh, ch→ts, etc.)
5. Add `ou` → `oo` mapping

- [ ] **Step 4: Run tests to verify they pass**

Run: `mise exec uv -- uv run pytest tests/test_tl_poj_convert.py -v`
Expected: ALL PASS (existing + new)

- [ ] **Step 5: Run full test suite for regression**

Run: `mise exec uv -- uv run pytest -x --tb=short`
Expected: 123+ passed

- [ ] **Step 6: Commit**

```bash
git add scripts/tl_poj_convert.py tests/test_tl_poj_convert.py
git commit -m "feat: enhance POJ→TL conversion for historical texts (diacritics, nasal, o͘)"
```

---

## Chunk 2: Sentence Extraction from Existing Corpora

### Task 2: Add `--sentences` mode to iCorpus extractor

**Files:**
- Modify: `scripts/extract_icorpus_freq.py`
- Modify: `tests/test_icorpus_freq.py`

- [ ] **Step 1: Write failing test for sentence output**

```python
class TestSentenceOutput:
    """Output raw sentences for bigram extraction."""

    def test_writes_sentences(self, tmp_path):
        text = "gua2 beh4 khi3\ntsiah8-png7 ho2-tsiah8\n"
        outfile = tmp_path / "sentences.txt"
        write_sentences(io.StringIO(text), outfile)
        lines = outfile.read_text().strip().splitlines()
        assert len(lines) == 2
        assert "gua2" in lines[0]

    def test_skips_empty_lines(self, tmp_path):
        text = "gua2 beh4\n\n\ntsiah8\n"
        outfile = tmp_path / "sentences.txt"
        write_sentences(io.StringIO(text), outfile)
        lines = outfile.read_text().strip().splitlines()
        assert len(lines) == 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `mise exec uv -- uv run pytest tests/test_icorpus_freq.py::TestSentenceOutput -v`
Expected: FAIL (write_sentences not defined)

- [ ] **Step 3: Implement `write_sentences()` and `--sentences` CLI flag**

In `scripts/extract_icorpus_freq.py`, add:

```python
def write_sentences(corpus_file: TextIO, output_path: Path) -> None:
    """Write tokenized sentences to a text file, one per line.

    Each line contains space-separated TL tokens (tone numbers preserved).
    Used for bigram extraction downstream.
    """
    count = 0
    with open(output_path, "w", encoding="utf-8") as f:
        for line in corpus_file:
            tokens = tokenize_tl_line(line)
            if tokens:
                f.write(" ".join(tokens) + "\n")
                count += 1
    return count
```

Add `--sentences` flag to `main()`:

```python
parser.add_argument("--sentences", type=Path, default=None, help="Output tokenized sentences file")
```

In main, after frequency extraction:
```python
if args.sentences:
    with open(args.input, encoding="utf-8") as f:
        n = write_sentences(f, args.sentences)
    print(f"Wrote {n} sentences to {args.sentences}")
```

- [ ] **Step 4: Run tests to verify pass**

Run: `mise exec uv -- uv run pytest tests/test_icorpus_freq.py -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/extract_icorpus_freq.py tests/test_icorpus_freq.py
git commit -m "feat: add --sentences mode to iCorpus extractor for bigram pipeline"
```

### Task 3: Add `--sentences` mode to Ungian extractor

**Files:**
- Modify: `scripts/extract_ungian_freq.py`
- Modify: `tests/test_ungian_freq.py`

- [ ] **Step 1: Write failing test for sentence output**

```python
class TestSentenceOutput:
    def test_writes_sentences(self, tmp_path):
        from scripts.extract_ungian_freq import write_ungian_sentences
        json_dir = tmp_path / "json"
        json_dir.mkdir()
        data = {"資料": [{"段": [["漢字", "gua2 beh4 khi3"]]}]}
        (json_dir / "test.json").write_text(json.dumps(data, ensure_ascii=False))
        outfile = tmp_path / "sentences.txt"
        write_ungian_sentences(json_dir, outfile)
        lines = outfile.read_text().strip().splitlines()
        assert len(lines) >= 1
        assert "gua2" in lines[0]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `mise exec uv -- uv run pytest tests/test_ungian_freq.py::TestSentenceOutput -v`

- [ ] **Step 3: Implement `write_ungian_sentences()` and `--sentences` CLI flag**

Similar pattern to iCorpus: iterate JSON files, extract KIP lines, tokenize, write one sentence per line.

- [ ] **Step 4: Run tests, verify pass**

Run: `mise exec uv -- uv run pytest tests/test_ungian_freq.py -v`

- [ ] **Step 5: Commit**

```bash
git add scripts/extract_ungian_freq.py tests/test_ungian_freq.py
git commit -m "feat: add --sentences mode to Ungian extractor for bigram pipeline"
```

---

## Chunk 3: New Corpus Extractors

### Task 4: Create nmtl literary corpus extractor

**Files:**
- Create: `scripts/extract_nmtl.py`
- Create: `tests/test_extract_nmtl.py`

This script needs to handle nmtl_2006_dadwt format. The data may be in `.tbk` (plain text) or `nmtl.json` (25MB aligned). Strategy: first try to discover the format by reading sample files, then implement.

- [ ] **Step 1: Write failing tests**

```python
"""Tests for nmtl literary corpus extraction."""
import json
from pathlib import Path
from scripts.extract_nmtl import extract_nmtl_sentences, count_nmtl_frequencies

class TestExtractNmtlSentences:
    def test_json_format(self, tmp_path):
        """Handle nmtl.json with aligned Han-Lo and TL pairs."""
        data = [
            {"漢羅": "我 beh 去食飯", "音標": "gua2 beh4 khi3 tsiah8-png7"},
            {"漢羅": "你好", "音標": "li2 ho2"}
        ]
        (tmp_path / "nmtl.json").write_text(json.dumps(data, ensure_ascii=False))
        sentences, freq = extract_nmtl_sentences(tmp_path)
        assert len(sentences) >= 2
        assert freq["gua2"] >= 1

    def test_tbk_format(self, tmp_path):
        """Handle .tbk plain text files (one sentence per line, TL romanization)."""
        tbk_dir = tmp_path / "texts"
        tbk_dir.mkdir()
        (tbk_dir / "sample.tbk").write_text("gua2 beh4 khi3\ntsiah8-png7\n")
        sentences, freq = extract_nmtl_sentences(tmp_path)
        assert len(sentences) >= 1

    def test_empty_dir(self, tmp_path):
        sentences, freq = extract_nmtl_sentences(tmp_path)
        assert len(sentences) == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `mise exec uv -- uv run pytest tests/test_extract_nmtl.py -v`

- [ ] **Step 3: Implement `extract_nmtl.py`**

Pattern: follows `extract_icorpus_freq.py` structure — argparse CLI, reads files, tokenizes, outputs TSV + sentences.

```python
"""Extract sentences and frequencies from nmtl_2006_dadwt literary corpus."""
import argparse, json, re, sys
from collections import Counter
from pathlib import Path

# Reuse tokenizer from icorpus
from scripts.extract_icorpus_freq import tokenize_tl_line


def extract_nmtl_sentences(data_dir: Path) -> tuple[list[str], Counter]:
    """Extract sentences and word frequencies from nmtl data.

    Tries nmtl.json first, falls back to .tbk files.
    Returns (list of tokenized sentence strings, word frequency Counter).
    """
    sentences = []
    freq = Counter()

    # Try nmtl.json (aligned format)
    json_file = data_dir / "nmtl.json"
    if json_file.exists():
        with open(json_file, encoding="utf-8") as f:
            data = json.load(f)
        for entry in data if isinstance(data, list) else []:
            tl_line = entry.get("音標", "")
            tokens = tokenize_tl_line(tl_line)
            if tokens:
                sentences.append(" ".join(tokens))
                freq.update(tokens)
        return sentences, freq

    # Fallback: .tbk plain text files
    for tbk in sorted(data_dir.rglob("*.tbk")):
        with open(tbk, encoding="utf-8", errors="replace") as f:
            for line in f:
                tokens = tokenize_tl_line(line)
                if tokens:
                    sentences.append(" ".join(tokens))
                    freq.update(tokens)

    return sentences, freq
```

- [ ] **Step 4: Run tests, verify pass**

- [ ] **Step 5: Add CLI main() with --input/--output/--sentences flags**

- [ ] **Step 6: Run full test suite**

Run: `mise exec uv -- uv run pytest -x --tb=short`

- [ ] **Step 7: Commit**

```bash
git add scripts/extract_nmtl.py tests/test_extract_nmtl.py
git commit -m "feat: add nmtl literary corpus extractor (sentences + frequencies)"
```

### Task 5: Create KipSutian example sentence extractor

**Files:**
- Create: `scripts/extract_kipsutian_sentences.py`
- Create: `tests/test_extract_kipsutian_sentences.py`

- [ ] **Step 1: Write failing tests**

Examine the existing `scripts/build_kipsutian_reverse.py` to understand the CSV format (columns: 漢字, 羅馬字, 詞目類型, 解說). Tests should verify extraction of example sentences from the 解說/例句 columns.

```python
"""Tests for KipSutian example sentence extraction."""
import csv, io
from scripts.extract_kipsutian_sentences import extract_kipsutian_sentences

class TestExtractSentences:
    def test_extracts_example_sentence(self, tmp_path):
        csv_content = "漢字,羅馬字,解說,例句音標\n食飯,tsia̍h-pn̄g,吃飯,gua2 beh4 tsiah8-png7\n"
        csv_path = tmp_path / "kautian.csv"
        csv_path.write_text(csv_content)
        sentences, freq = extract_kipsutian_sentences(csv_path)
        assert len(sentences) >= 1

    def test_skips_empty_examples(self, tmp_path):
        csv_content = "漢字,羅馬字,解說,例句音標\n食飯,tsia̍h-pn̄g,吃飯,\n"
        csv_path = tmp_path / "kautian.csv"
        csv_path.write_text(csv_content)
        sentences, freq = extract_kipsutian_sentences(csv_path)
        assert len(sentences) == 0
```

- [ ] **Step 2: Run test, verify fail**
- [ ] **Step 3: Implement extractor**

Read the actual KipSutian CSV to discover exact column names. Extract romanization from example sentence columns. Tokenize using `tokenize_tl_line()`.

- [ ] **Step 4: Run tests, verify pass**
- [ ] **Step 5: Add CLI main()**
- [ ] **Step 6: Commit**

```bash
git add scripts/extract_kipsutian_sentences.py tests/test_extract_kipsutian_sentences.py
git commit -m "feat: add KipSutian example sentence extractor"
```

### Task 6: Create Khin-hoan POJ text extractor

**Files:**
- Create: `scripts/extract_pojbh.py`
- Create: `tests/test_extract_pojbh.py`

- [ ] **Step 1: Write failing tests**

```python
"""Tests for Khin-hoan POJ text extraction."""
from scripts.extract_pojbh import extract_pojbh_sentences

class TestExtractPojbh:
    def test_converts_poj_to_tl(self, tmp_path):
        """POJ text is converted to TL before tokenization."""
        poj_dir = tmp_path / "texts"
        poj_dir.mkdir()
        (poj_dir / "sample.txt").write_text("Chhit-thô chin hó.\n")
        sentences, freq = extract_pojbh_sentences(tmp_path)
        assert len(sentences) >= 1
        # Should contain TL form, not POJ
        assert "tshit" in sentences[0] or "chhit" not in sentences[0]

    def test_handles_unicode_poj(self, tmp_path):
        poj_dir = tmp_path / "texts"
        poj_dir.mkdir()
        (poj_dir / "sample.txt").write_text("Ko͘-niû chin súi.\n")
        sentences, freq = extract_pojbh_sentences(tmp_path)
        assert len(sentences) >= 1

    def test_empty_dir(self, tmp_path):
        sentences, freq = extract_pojbh_sentences(tmp_path)
        assert len(sentences) == 0
```

- [ ] **Step 2: Run test, verify fail**
- [ ] **Step 3: Implement extractor**

Uses enhanced `poj_to_tl()` from Task 1. Reads `.txt` files, converts POJ→TL, tokenizes.

- [ ] **Step 4: Run tests, verify pass**
- [ ] **Step 5: Add CLI main()**
- [ ] **Step 6: Run full test suite for regression**
- [ ] **Step 7: Commit**

```bash
git add scripts/extract_pojbh.py tests/test_extract_pojbh.py
git commit -m "feat: add Khin-hoan POJ text extractor with POJ→TL conversion"
```

---

## Chunk 4: Phrase Builder (Core Algorithm)

### Task 7: Build romanization-to-text reverse index

**Files:**
- Create: `scripts/build_phrases.py`
- Create: `tests/test_build_phrases.py`

- [ ] **Step 1: Write failing tests for reverse index**

```python
"""Tests for phrase building from corpus bigrams."""
from scripts.build_phrases import build_reverse_index, extract_bigrams, generate_phrase_entries

class TestBuildReverseIndex:
    def test_basic_index(self):
        """Build rime_key → text mapping from dict entries."""
        dict_lines = [
            "食飯\ttsiah png\t1446",
            "我\tgua\t1200",
            "去\tkhi\t900",
        ]
        index = build_reverse_index(dict_lines)
        assert index["tsiah png"][0]["text"] == "食飯"
        assert index["gua"][0]["text"] == "我"

    def test_ambiguous_keys(self):
        """Multiple hanzi for same rime_key, sorted by weight."""
        dict_lines = [
            "去\tkhi\t900",
            "起\tkhi\t500",
            "棄\tkhi\t200",
        ]
        index = build_reverse_index(dict_lines)
        assert len(index["khi"]) == 3
        assert index["khi"][0]["text"] == "去"  # highest weight first

    def test_strips_tones_from_key(self):
        """Corpus tokens have tone numbers; dict keys don't. Normalize."""
        dict_lines = ["食飯\ttsiah png\t1446"]
        index = build_reverse_index(dict_lines)
        # The index key should be toneless
        assert "tsiah png" in index
```

- [ ] **Step 2: Run test, verify fail**

Run: `mise exec uv -- uv run pytest tests/test_build_phrases.py::TestBuildReverseIndex -v`

- [ ] **Step 3: Implement `build_reverse_index()`**

```python
"""Build multi-word phrases from corpus bigrams and dictionary reverse index."""
import math, re
from collections import Counter
from pathlib import Path


def _strip_tones(text: str) -> str:
    """Strip tone numbers from romanization: 'gua2' → 'gua', 'tsiah8-png7' → 'tsiah-png'."""
    return re.sub(r"[1-9]", "", text)


def build_reverse_index(dict_lines: list[str]) -> dict[str, list[dict]]:
    """Build rime_key → [{text, weight}] mapping from dict.yaml data lines.

    Args:
        dict_lines: Lines from dict.yaml (text\\trime_key\\tweight format)

    Returns:
        Dict mapping rime_key to list of {text, weight} sorted by weight desc
    """
    index: dict[str, list[dict]] = {}
    for line in dict_lines:
        parts = line.strip().split("\t")
        if len(parts) < 3:
            continue
        text, rime_key, weight_str = parts[0], parts[1], parts[2]
        try:
            weight = int(weight_str)
        except ValueError:
            continue
        index.setdefault(rime_key, []).append({"text": text, "weight": weight})
    # Sort each list by weight descending
    for key in index:
        index[key].sort(key=lambda e: e["weight"], reverse=True)
    return index
```

- [ ] **Step 4: Run test, verify pass**
- [ ] **Step 5: Commit**

```bash
git add scripts/build_phrases.py tests/test_build_phrases.py
git commit -m "feat: add build_reverse_index for romanization-to-text mapping"
```

### Task 8: Bigram extraction from sentences

**Files:**
- Modify: `scripts/build_phrases.py`
- Modify: `tests/test_build_phrases.py`

- [ ] **Step 1: Write failing tests for bigram extraction**

```python
class TestExtractBigrams:
    def test_basic_bigrams(self):
        sentences = ["gua2 beh4 khi3", "gua2 beh4 tsiah8-png7"]
        bigrams = extract_bigrams(sentences)
        assert bigrams[("gua", "beh")] == 2  # appears in both sentences
        assert bigrams[("beh", "khi")] == 1
        assert bigrams[("beh", "tsiah-png")] == 1

    def test_strips_tones(self):
        sentences = ["gua2 beh4"]
        bigrams = extract_bigrams(sentences)
        assert ("gua", "beh") in bigrams  # tones stripped

    def test_single_word_sentence(self):
        sentences = ["gua2"]
        bigrams = extract_bigrams(sentences)
        assert len(bigrams) == 0

    def test_empty(self):
        bigrams = extract_bigrams([])
        assert len(bigrams) == 0
```

- [ ] **Step 2: Run test, verify fail**
- [ ] **Step 3: Implement `extract_bigrams()`**

```python
def extract_bigrams(sentences: list[str], min_count: int = 1) -> Counter:
    """Extract bigram frequencies from tokenized sentences.

    Args:
        sentences: List of space-separated token strings (with tone numbers)
        min_count: Minimum occurrence count to include

    Returns:
        Counter mapping (word1, word2) tuples to counts.
        Words have tones stripped for matching against dict rime_keys.
    """
    bigrams: Counter[tuple[str, str]] = Counter()
    for sentence in sentences:
        tokens = sentence.strip().split()
        stripped = [_strip_tones(t) for t in tokens]
        for i in range(len(stripped) - 1):
            bigrams[(stripped[i], stripped[i + 1])] += 1
    if min_count > 1:
        bigrams = Counter({k: v for k, v in bigrams.items() if v >= min_count})
    return bigrams
```

- [ ] **Step 4: Run test, verify pass**
- [ ] **Step 5: Commit**

```bash
git add scripts/build_phrases.py tests/test_build_phrases.py
git commit -m "feat: add bigram extraction from tokenized sentences"
```

### Task 9: Generate phrase dictionary entries from bigrams

**Files:**
- Modify: `scripts/build_phrases.py`
- Modify: `tests/test_build_phrases.py`

- [ ] **Step 1: Write failing tests for phrase generation**

```python
class TestGeneratePhraseEntries:
    def test_basic_phrase(self):
        index = {
            "gua": [{"text": "我", "weight": 1200}],
            "khi": [{"text": "去", "weight": 900}],
        }
        bigrams = Counter({("gua", "khi"): 10})
        existing_keys = set()
        entries = generate_phrase_entries(bigrams, index, existing_keys, min_count=5)
        assert len(entries) == 1
        assert entries[0]["hanlo"] == "我去"
        assert entries[0]["rime_key"] == "gua khi"
        assert entries[0]["weight"] > 0

    def test_skips_existing(self):
        index = {
            "tsiah": [{"text": "食", "weight": 800}],
            "png": [{"text": "飯", "weight": 600}],
        }
        bigrams = Counter({("tsiah", "png"): 20})
        existing_keys = {("食飯", "tsiah png")}  # already in dict
        entries = generate_phrase_entries(bigrams, index, existing_keys, min_count=5)
        assert len(entries) == 0

    def test_skips_below_threshold(self):
        index = {"gua": [{"text": "我", "weight": 1200}], "khi": [{"text": "去", "weight": 900}]}
        bigrams = Counter({("gua", "khi"): 3})
        entries = generate_phrase_entries(bigrams, index, set(), min_count=5)
        assert len(entries) == 0

    def test_skips_unknown_words(self):
        index = {"gua": [{"text": "我", "weight": 1200}]}
        bigrams = Counter({("gua", "xyz"): 10})
        entries = generate_phrase_entries(bigrams, index, set(), min_count=5)
        assert len(entries) == 0  # "xyz" not in index

    def test_uses_highest_weight_for_ambiguous(self):
        index = {
            "khi": [{"text": "去", "weight": 900}, {"text": "起", "weight": 500}],
            "gua": [{"text": "我", "weight": 1200}],
        }
        bigrams = Counter({("gua", "khi"): 10})
        entries = generate_phrase_entries(bigrams, index, set(), min_count=5)
        assert entries[0]["hanlo"] == "我去"  # "去" has higher weight than "起"
```

- [ ] **Step 2: Run test, verify fail**
- [ ] **Step 3: Implement `generate_phrase_entries()`**

```python
def generate_phrase_entries(
    bigrams: Counter,
    reverse_index: dict[str, list[dict]],
    existing_keys: set[tuple[str, str]],
    min_count: int = 5,
    base_weight: int = 500,
) -> list[dict]:
    """Generate new dictionary entries from high-frequency bigrams.

    Args:
        bigrams: Counter of (word1, word2) → count
        reverse_index: rime_key → [{text, weight}] from dict.yaml
        existing_keys: Set of (hanlo, rime_key) already in dict
        min_count: Minimum bigram frequency to include
        base_weight: Base weight for generated entries

    Returns:
        List of new entries with hanlo, rime_key, weight fields
    """
    entries = []
    for (w1, w2), count in bigrams.most_common():
        if count < min_count:
            break
        if w1 not in reverse_index or w2 not in reverse_index:
            continue
        text1 = reverse_index[w1][0]["text"]  # highest weight
        text2 = reverse_index[w2][0]["text"]
        hanlo = text1 + text2
        rime_key = f"{w1} {w2}"
        if (hanlo, rime_key) in existing_keys:
            continue
        corpus_boost = 1.0 + math.log10(1 + count) * 0.3
        weight = int(base_weight * corpus_boost)
        entries.append({"hanlo": hanlo, "rime_key": rime_key, "weight": weight})
    return entries
```

- [ ] **Step 4: Run tests, verify pass**
- [ ] **Step 5: Commit**

```bash
git add scripts/build_phrases.py tests/test_build_phrases.py
git commit -m "feat: generate phrase dictionary entries from corpus bigrams"
```

### Task 10: Add CLI and file I/O to build_phrases.py

**Files:**
- Modify: `scripts/build_phrases.py`
- Modify: `tests/test_build_phrases.py`

- [ ] **Step 1: Write failing test for end-to-end phrase building**

```python
class TestBuildPhrasesEndToEnd:
    def test_full_pipeline(self, tmp_path):
        from scripts.build_phrases import build_phrases_from_files
        # Create minimal dict.yaml
        dict_file = tmp_path / "dict.yaml"
        dict_file.write_text("---\nname: test\n...\n我\tgua\t1200\n去\tkhi\t900\nbeh\tbeh\t800\n")
        # Create sentence files
        sent_file = tmp_path / "sentences.txt"
        sent_file.write_text("gua2 beh4 khi3\n" * 10)  # 10 occurrences
        output = tmp_path / "phrases.txt"
        n = build_phrases_from_files(dict_file, [sent_file], output, min_count=5)
        assert n > 0
        content = output.read_text()
        assert "gua beh" in content or "beh khi" in content
```

- [ ] **Step 2: Run test, verify fail**
- [ ] **Step 3: Implement `build_phrases_from_files()` and `main()`**

CLI pattern: `--dict`, `--sentences` (multiple), `--output`, `--min-count`

- [ ] **Step 4: Run tests, verify pass**
- [ ] **Step 5: Run full test suite**

Run: `mise exec uv -- uv run pytest -x --tb=short`

- [ ] **Step 6: Commit**

```bash
git add scripts/build_phrases.py tests/test_build_phrases.py
git commit -m "feat: add CLI for build_phrases with dict reverse index + sentence input"
```

---

## Chunk 5: Pipeline Integration

### Task 11: Update build_all.py with new pipeline steps

**Files:**
- Modify: `scripts/build_all.py`

- [ ] **Step 1: Add Steps 7-11 to build_all.py**

After existing Step 6, add:

```python
# Step 7: Extract nmtl sentences + frequencies
nmtl_dir = data / "nmtl_2006_dadwt"
nmtl_freq = data / "nmtl_freq.tsv"
nmtl_sentences = data / "nmtl_sentences.txt"
if nmtl_dir.exists():
    steps_ok &= run_step(
        "Extract nmtl literary corpus",
        [python, "scripts/extract_nmtl.py", "--input", str(nmtl_dir),
         "--output", str(nmtl_freq), "--sentences", str(nmtl_sentences)],
    )

# Step 8: Extract KipSutian example sentences
# (find CSV path using same logic as Step 5)
kipsutian_sentences = data / "kipsutian_sentences.txt"
kipsutian_sent_freq = data / "kipsutian_sent_freq.tsv"
if kipsutian_csv and kipsutian_csv.exists():
    steps_ok &= run_step(
        "Extract KipSutian example sentences",
        [python, "scripts/extract_kipsutian_sentences.py", "--input", str(kipsutian_csv),
         "--output", str(kipsutian_sent_freq), "--sentences", str(kipsutian_sentences)],
    )

# Step 9: Extract Khin-hoan POJ texts
pojbh_dir = data / "Khin-hoan_2010_pojbh"
pojbh_freq = data / "pojbh_freq.tsv"
pojbh_sentences = data / "pojbh_sentences.txt"
if pojbh_dir.exists():
    steps_ok &= run_step(
        "Extract Khin-hoan POJ texts (with POJ→TL conversion)",
        [python, "scripts/extract_pojbh.py", "--input", str(pojbh_dir),
         "--output", str(pojbh_freq), "--sentences", str(pojbh_sentences)],
    )

# Step 10: Build bigram phrases → append to dict.yaml
sentence_files = [f for f in [
    data / "icorpus_sentences.txt",
    data / "ungian_sentences.txt",
    nmtl_sentences,
    kipsutian_sentences,
    pojbh_sentences,
] if f.exists()]
if sentence_files and dict_yaml.exists():
    phrase_output = data / "new_phrases.txt"
    steps_ok &= run_step(
        "Build bigram phrases from all corpora",
        [python, "scripts/build_phrases.py",
         "--dict", str(dict_yaml),
         "--sentences"] + [str(f) for f in sentence_files] +
        ["--output", str(phrase_output), "--min-count", "5"],
    )
    # Append new phrases to dict.yaml
    if phrase_output.exists():
        with open(dict_yaml, "a", encoding="utf-8") as out:
            out.write(open(phrase_output, encoding="utf-8").read())

# Step 11: Re-validate dictionary
if dict_yaml.exists():
    steps_ok &= run_step(
        "Re-validate dictionary (with new phrases)",
        [python, "scripts/validate_dict.py", str(dict_yaml)],
    )
```

Also update Steps 1-2 to pass `--sentences` flag:

```python
# Step 1 update: add --sentences
icorpus_sentences = data / "icorpus_sentences.txt"
cmd = [python, "scripts/extract_icorpus_freq.py",
       "--input", str(icorpus_file),
       "--output", str(icorpus_freq),
       "--sentences", str(icorpus_sentences)]

# Step 2 update: add --sentences
ungian_sentences = data / "ungian_sentences.txt"
cmd = [python, "scripts/extract_ungian_freq.py",
       "--input", str(ungian_dir),
       "--output", str(ungian_freq),
       "--sentences", str(ungian_sentences)]
```

- [ ] **Step 2: Run full test suite for regression**

Run: `mise exec uv -- uv run pytest -x --tb=short`
Expected: All existing tests pass (pipeline changes don't affect unit tests)

- [ ] **Step 3: Commit**

```bash
git add scripts/build_all.py
git commit -m "feat: integrate corpus extraction + phrase building into build pipeline"
```

### Task 12: Test full pipeline with real data

- [ ] **Step 1: Download corpus data (if not already present)**

```bash
./scripts/download_resources.sh
```

- [ ] **Step 2: Run full build pipeline**

```bash
mise exec uv -- uv run python scripts/build_all.py
```

Verify:
- No step failures
- New sentence files created in `data/`
- New phrase entries appended to `schema/phah_taibun.dict.yaml`
- dict.yaml size < 5MB

- [ ] **Step 3: Check phrase quality**

```bash
# Count new entries
wc -l schema/phah_taibun.dict.yaml
# Sample some phrases
tail -20 schema/phah_taibun.dict.yaml
```

Verify: phrases look reasonable (e.g., `我去`, `食飯好`, not garbage)

- [ ] **Step 4: Install and deploy**

```bash
./install.sh
```

- [ ] **Step 5: Manual testing**

Open fcitx5-rime, select 拍台文, type:
1. `gua beh khi tshit tho` — verify candidates are better ranked
2. `tsiah png` — verify 食飯 still appears as top candidate
3. `gua ai li` — verify no regression

- [ ] **Step 6: Commit updated dictionary**

```bash
git add schema/phah_taibun.dict.yaml
git commit -m "feat: enrich dictionary with corpus-derived bigram phrases"
```

- [ ] **Step 7: Run validation loop**

```bash
mise exec uv -- uv run pytest -x --tb=short
```

Expected: All tests pass (existing 127 + new tests)
