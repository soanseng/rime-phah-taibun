# Continuous Input (連打) Improvement Design

## Problem

Currently phah_taibun requires word-by-word candidate selection. Users type `gua beh khi tshit tho` and must select candidates for each word individually. Standard Rime pinyin IMEs (luna_pinyin) offer sentence-level auto-segmentation via grammar/octagram, producing much smoother input flow.

## Solution

Two-pronged approach:

1. **Enrich dictionary with multi-word phrases** from all available Taiwanese corpora (bigrams/trigrams with frequency-based weights)
2. **Improve frequency weights** using comprehensive corpus data to rank common words/phrases higher

The `fluency_editor` (already enabled) combined with a richer, better-weighted dictionary will produce significantly better continuous input.

### Why not essay.txt?

Investigation revealed that Rime's `essay.txt` is a **global shared resource** (`/usr/share/rime-data/essay.txt`, 442K lines of Chinese), not per-schema. The `grammar:/hant?` patch in luna_pinyin references an optional `hant.grammar.yaml` that **does not exist** on this system (build timestamp shows `grammar: 0`). Creating a schema-specific essay.txt requires further Rime internals research and may not work reliably. Instead, we achieve the same goal by enriching the dictionary directly — which is guaranteed to work.

## Architecture

```
6 corpus sources
  → extraction scripts (Python)
    → sentence-level text + frequency counts
      → romanization-to-text mapping (via dict.yaml reverse index)
        → new phrase entries in phah_taibun.dict.yaml
        → improved weights for existing entries
          → fluency_editor + richer dictionary
            → better continuous input experience
```

### Rime Pipeline

```
Dictionary (enriched with phrases + better weights)
  → script_translator (auto-segments input, finds longer matches)
    → Lua filter (Han-Lo/POJ/TL mode switching)
      → user sees final output
```

Key mechanism: Rime's `script_translator` **prefers longer matches with higher weights**. If the dictionary contains `食飯` (weight 1446) in addition to `食` (weight 800) and `飯` (weight 600), the translator will prefer the 2-character match when the user types `tsiah png`. By adding more multi-word phrases, we give the translator more "long match" options.

## Corpus Sources

### Already have extraction scripts (modify to add bigram + sentence output)

| Source | Format | Scale | Script | Romanization |
|--------|--------|-------|--------|-------------|
| iCorpus news | TL text file | 57K words, 302K tokens | `extract_icorpus_freq.py` | TL |
| Ungian literary | JSON (KIP+漢羅) | 93K words, 1,093 files | `extract_ungian_freq.py` | KIP |
| ChhoeTaigi dict | CSV | 86K entries | `convert_chhoetaigi.py` | KIP |

### Need new extraction scripts

| Source | Format | Scale | New Script | Romanization |
|--------|--------|-------|-----------|-------------|
| nmtl literary works | .tbk / JSON | 2,169 works, 25MB | `extract_nmtl.py` | TL+POJ mixed |
| KipSutian examples | CSV/ODS | 65K entries with examples | `extract_kipsutian_sentences.py` | KIP |
| Khin-hoan POJ texts | POJ plain text | historical documents | `extract_pojbh.py` | POJ (→TL conversion) |

## Core Algorithm: Romanization-to-Text Mapping

The critical challenge: corpus sources produce **romanization tokens** (e.g., `khi3`, `tsiah8-png7`), but dictionary entries have **text fields** (e.g., `去`, `食飯`). To add bigram phrases and improve weights, we need to map between them.

### Step 1: Build reverse index from dict.yaml

```python
# Load existing dict.yaml, build rime_key → text mapping
# dict.yaml format: text\trime_key\tweight
reverse_index = {}  # {"tsiah png": ["食飯"], "gua": ["我", "阮"], ...}
for entry in dict_entries:
    key_normalized = strip_tones(entry.rime_key)
    reverse_index.setdefault(key_normalized, []).append(entry)
```

### Step 2: Map corpus bigrams to dictionary text

```python
# Corpus bigram: ("khi", "tsiah-png") with count=45
# Lookup: "khi" → "去", "tsiah png" → "食飯"
# Result: new dict entry "去食飯\tkhi tsiah png\t<weight>"
```

### Step 3: Handle ambiguity

When one romanization maps to multiple hanzi (e.g., `khi` → `去`/`起`/`棄`):
- Use the **highest-weighted existing entry** as the default
- If the bigram itself exists in corpus as hanzi text (Ungian/nmtl have Han-Lo pairs), use that directly
- Mark ambiguous entries with lower confidence weight

## N-gram Strategy

### Bigram phrases → new dictionary entries

From all sentence-level corpora, extract consecutive word pairs:
- Sentence: `gua2 beh4 khi3 tsiah8-png7`
- Bigrams: `(gua, beh)`, `(beh, khi)`, `(khi, tsiah-png)`

**Filtering criteria:**
- Frequency ≥ 5 occurrences across ALL corpora combined
- Not already in dict.yaml as a single entry
- Both component words exist in dict.yaml (can be mapped to text)

**Weight calculation for new entries:**

```python
weight = base_weight * corpus_boost
base_weight = 500  # Default for corpus-derived entries
corpus_boost = 1.0 + log10(1 + total_count) * 0.3
# Example: count=45 → boost=1.0+log10(46)*0.3 = 1.0+0.50 = 1.50 → weight=750
```

### Unigram weight improvements

For existing dict.yaml entries, update weights using the full corpus data:
- Apply the existing `compute_weights()` formula from `build_frequency.py`
- But now with frequencies from ALL 6 sources (not just iCorpus + Ungian)
- This improves ranking of common words without adding new entries

## New Files

| File | Purpose |
|------|---------|
| `scripts/extract_nmtl.py` | Extract sentence-level text from nmtl 2,169 literary works |
| `scripts/extract_kipsutian_sentences.py` | Extract example sentences from KipSutian 65K entries |
| `scripts/extract_pojbh.py` | Extract + convert POJ historical texts to TL |
| `scripts/build_phrases.py` | Extract bigrams from all corpora → new dict entries |
| `tests/test_extract_nmtl.py` | Tests for nmtl extraction |
| `tests/test_extract_kipsutian_sentences.py` | Tests for KipSutian sentence extraction |
| `tests/test_extract_pojbh.py` | Tests for POJ extraction |
| `tests/test_build_phrases.py` | Tests for phrase extraction and mapping |

## Modified Files

| File | Change |
|------|--------|
| `scripts/extract_icorpus_freq.py` | Add `--sentences` mode to output raw sentences |
| `scripts/extract_ungian_freq.py` | Add `--sentences` mode to output raw sentences |
| `scripts/convert_chhoetaigi.py` | Accept additional corpus freq files (`--corpus-freq` extended) |
| `scripts/build_all.py` | Add Steps 7-11 for corpus extraction + phrase building |
| `scripts/build_frequency.py` | Accept frequencies from all 6 sources |
| `scripts/tl_poj_convert.py` | Enhance `poj_to_tl()` for historical POJ (diacritics, nn, o͘) |
| `scripts/install_linux.sh` | No change needed (dict.yaml already deployed) |
| `scripts/install_macos.sh` | No change needed (dict.yaml already deployed) |

## build_all.py Pipeline Update

```
Existing Steps 1-6 (modified):
  Step 1: Extract iCorpus frequencies + sentences
  Step 2: Extract Ungian frequencies + sentences
  Step 3: Convert ChhoeTaigi → dict.yaml (with ALL corpus freqs)
  Step 4: Parse LKK rules → hanlo_rules.yaml
  Step 4b: Parse light-tone rules
  Step 5: Build reverse dictionary
  Step 6: Validate dictionary

New Steps:
  Step 7: Extract nmtl literary corpus sentences + frequencies
  Step 8: Extract KipSutian example sentences + frequencies
  Step 9: Extract Khin-hoan POJ texts + convert to TL + frequencies
  Step 10: Build bigram phrases → append to dict.yaml
  Step 11: Re-validate dictionary (including new entries)
```

Note: Steps 1-2 now also output sentence files (`data/*_sentences.txt`) used by Step 10.
Step 3 is enhanced to accept all 6 frequency sources (not just 2).

## POJ→TL Conversion Enhancement

The existing `tl_poj_convert.py` handles basic substitutions (ts↔ch, ing↔eng, etc.). For historical POJ texts (Khin-hoan), it needs additional handling:

- Nasal markers: `nn` → handle as nasalization, not double-n
- Unicode diacritics: `o͘` (combining dot above) → `oo`
- Tone marks: diacritics to tone numbers (á→a2, à→a3, â→a5, ā→a7, a̍→a8)
- Capital letters: normalize to lowercase
- Multi-syllable word boundaries: preserve hyphens

This enhancement is needed for `extract_pojbh.py` and benefits the overall project.

## Testing Strategy

- Unit tests for each new extraction script (nmtl, KipSutian sentences, POJ)
- Unit tests for `build_phrases.py` (bigram extraction, romanization-to-text mapping, weight calculation)
- Unit tests for enhanced `tl_poj_convert.py` (diacritics, nasal, capitals)
- Integration test: full pipeline produces valid dict.yaml with new entries
- Regression: all existing 127 tests still pass
- Manual test: install and verify continuous input improvement with fcitx5-rime

## Success Criteria

1. ≥5K new phrase entries added to dict.yaml from corpus bigrams
2. All existing 127 tests still pass
3. New extraction scripts have ≥80% test coverage
4. Rime deployment succeeds with enriched dictionary
5. Typing `gua beh khi tshit tho` produces better auto-ranked candidates
6. No regression in word-by-word input quality
7. dict.yaml size stays under 5MB (currently 2MB, ~86K entries)

## Dependencies

- Corpus data downloaded via `scripts/download_resources.sh`
- Python 3.10+ with pyyaml
- Existing dict.yaml as reverse index source

## Risks

1. **nmtl format unknown** — .tbk files may need format discovery; fallback to nmtl.json (25MB aligned version)
2. **POJ→TL conversion accuracy** — existing `tl_poj_convert.py` is limited (6 substitutions); needs significant enhancement for historical texts. Fallback: skip Khin-hoan if conversion quality is too low
3. **Romanization ambiguity** — one rime_key mapping to multiple text entries; mitigated by using highest-weight entry and Han-Lo pair data from Ungian
4. **Dictionary size growth** — bigram entries could double dict.yaml; capped at 5MB with frequency threshold adjustable
5. **Bigram quality** — some bigrams may be noise (sentence boundaries, punctuation artifacts); mitigated by frequency threshold ≥5 and validation

## Future: Octagram/Grammar Integration (Phase 3)

Once the dictionary is enriched, a follow-up phase could explore:
- Creating a `phah_taibun.gram` binary language model (if `rime_deployer` supports it)
- Testing schema-specific essay.txt (may need `grammar:` section in translator config)
- Training an n-gram model from the accumulated corpus sentences
- This would provide true sentence-level auto-segmentation beyond dictionary lookup
