# Light Tone (輕聲) Candidate Generation

## Problem

Taiwanese Hokkien has light tone (輕聲) where certain syllables lose their original tone. The light tone marker `--` changes meaning: `āu-ji̍t` (後日, "in the future") vs `āu--ji̍t` (後--日, "day after tomorrow"). The dictionary currently has only 391 manually sourced `--` entries, while corpus data contains ~28,700 light-tone word forms that are not leveraged.

## Solution

Two-phase approach: build-time extraction from corpus data (Phase A), then runtime dynamic generation via Lua filter (Phase B).

---

## Phase A: Build-time Light Tone Entry Generation

### New Script: `scripts/build_lighttone_entries.py`

**Input:**
- Corpus frequency TSVs available at build time: `ungian_freq.tsv` (9,077 `--` forms), `900leku_freq.tsv` (319), `kok4hau7_freq.tsv` (58), `icorpus_freq.tsv`
- Late-stage TSVs (if step is placed after Step 9): `nmtl_freq.tsv` (8,978), `kipsutian_sent_freq.tsv` (243), `pojbh_freq.tsv` (34)
- Existing dictionary: `phah_taibun.dict.yaml`
- Light tone rules: `lighttone_rules.json`

**Output:**
- New entries appended to `phah_taibun.dict.yaml`

### Data Flow

```
Corpus freq.tsv files
    → Collect all kip_input containing "--" with merged frequencies
    → Reverse-lookup hanzi from existing dictionary
    → Filter: keep only entries whose non-light-tone variant exists in dict
    → Deduplicate against existing dict entries (by rime_key, not just hanlo)
    → Append to dict.yaml
```

### Hanzi Reverse Lookup Strategy

Three methods, tried in order:

1. **Whole-word match**: Look up the non-light-tone version (strip `--`) in the existing dictionary. E.g., `tng2--lai5` → strip to `tng2-lai5` → find `轉來` → produce `轉--來`.

2. **Syllable-by-syllable assembly**: Split at `--` boundary into prefix and suffix. Look up each part separately. E.g., `khi2--lai5` → `khi2` = `起`, `lai5` = `來` → `起--來`.

3. **lighttone_rules.json validation**: The 111 rules map light-tone morphemes to hanzi (e.g., `--lâi` → `來`). Note: rules use Unicode diacritics, so a diacritics-to-numeric conversion is needed when cross-referencing with corpus kip_input. Use to verify or supply the suffix hanzi when syllable lookup is ambiguous.

### Deduplication

The dictionary has **two kinds** of existing light-tone entries:
1. **391 entries with `--` in hanlo** (e.g., `一頂--的` with rime_key `it ting2  e5`)
2. **~2,038 entries with double-space rime_key but NO `--` in hanlo** (e.g., `出來` with rime_key `tshut  lai5`)

Deduplication must check **rime_key** (not just hanlo) to avoid producing entries that collide with existing double-space rime_keys. When a collision is found, skip the new entry (the existing one is already functional).

### Duplicate TL Keys in lighttone_rules.json

13 TL keys map to multiple hanzi (e.g., `--eh` → 咧/見/呃/呢). For Phase A, the hanzi is determined by dictionary reverse lookup, not by lighttone_rules.json — the rules are only used for validation. When multiple hanzi are possible from the dictionary (e.g., single-syllable lookup returns multiple characters), prefer the hanzi listed in lighttone_rules.json.

### Entries with Multiple `--` Positions

Some corpus tokens have two or more `--` markers (e.g., reduplicative forms). Phase A will handle these: split at each `--` boundary, assemble hanzi for each segment, preserve all `--` positions.

### Case Normalization

Corpus data may contain capitalized forms (e.g., `Chong2--si7`). Normalize to lowercase for dictionary lookup and rime_key generation.

### Rime Key Format

Consistent with existing entries: `--` position represented as **double space** in rime_key.

| hanlo | rime_key | weight |
|-------|----------|--------|
| 轉--來 | `tng2  lai5` | 800 |
| 後--日 | `au7  jit8` | 800 |

### Weight Calculation

- Base weight from corpus frequency: `base = 300 + log10(1 + merged_count) * 150`
- Capped at the non-light-tone variant's weight minus 100 (light tone candidate should rank lower)
- If no non-light-tone variant found, use the formula as-is
- Minimum weight: 300 (to appear in candidate list)
- Maximum weight: 1500 (prevent dominating over common entries)

### Build Pipeline Integration

Insert as **Step 9b** in `build_all.py`, after Step 9 (POJ texts extraction) and before Step 10 (bigram phrases). This ensures all corpus freq TSVs are available.

```
Step 9:  Extract Khin-hoan POJ texts
Step 9b: Build light-tone entries → append to dict.yaml  ← NEW
Step 10: Build bigram phrases from all corpora
Step 11: Re-validate dictionary (with new phrases + light-tone entries)
```

### Expected Output

- Corpus has ~28,700 `--` word forms across all TSVs
- After deduplication and filtering (must have hanzi match): estimated **1,000-3,000 new entries**
- Existing 391 entries preserved unchanged

---

## Phase B: Runtime Dynamic Light Tone Generation

### New Module: `lua/phah_taibun_lighttone.lua`

A Rime filter that dynamically generates light-tone candidate variants at typing time.

### Data Loading

On `init`, load `lighttone_rules.json` into a hash table. Since the rules use Unicode diacritics (`--lâi`), key by the diacritical form (stripped of `--` prefix and leading hyphen):

```lua
-- lighttone_rules.json entry: {"tl": "--lâi", "hanzi": "來", "rule": "補語"}
-- Stored as: rules["lâi"] = {hanzi="來", rule="補語"}
-- Multi-syllable: rules["khí-lâi"] = {hanzi="起來", rule="補語"}
```

For duplicate TL keys (e.g., `--eh` → multiple hanzi), store as a list and generate one candidate per hanzi.

### Filter Placement

Place **before** `phah_taibun_filter` in the filter chain, so that `raw_roman` in comments is still in numeric tone format (e.g., `[khi3 lai5]`). The filter will convert numeric tones to diacritics for matching against the rules hash table using `phah_taibun_data.format_romanization`.

### Processing Logic

For each multi-syllable candidate (2+ syllables):

1. Extract `raw_roman` from candidate comment (e.g., `khi3 tshue7 i`)
2. Check if the last 1-3 syllables match a lighttone rule (after converting to diacritical form)
3. If match found and rule is not `不處理`:
   - Generate a new candidate with `--` inserted at the appropriate position
   - Set quality slightly below the original candidate (`cand.quality - 0.3`)
   - Yield both original and light-tone variant

### Trigger Conditions

- Only candidates with **2+ syllables**
- Only when tail 1-3 syllables match `lighttone_rules.json` (up to 3 for multi-syllable suffixes like `--tām-po̍h-á`)
- Skip `不處理` rule entries
- Skip if an identical `--` entry already exists in dictionary (handled by Rime dedup)

### Display Format

- 漢羅 mode: `轉--來`, `後--日` (the `--` appears between hanzi)
- 全羅 TL mode: `tńg--lâi`, `āu--ji̍t`
- 全羅 POJ mode: `tńg--lâi`, `āu--ji̍t`
- Comment annotation: `[tńg--lâi]`

### Rule Categories and Insertion Position

From `lighttone_rules.json`:

| Rule | Meaning | `--` Position | Example |
|------|---------|---------------|---------|
| 分寫 | Separate writing | Before last syllable | `hōo--lí` |
| 補語 | Complement | Before complement | `kiânn--khì` |
| 連寫 | Connected writing | Before suffix | `pâng--á` |
| 不處理 | No action | Skip | — |

### Module Registration

In `rime.lua`:
```lua
phah_taibun_lighttone = require("phah_taibun_lighttone")
```

In schema `engine/filters`, **before** `phah_taibun_filter`:
```yaml
- lua_filter@phah_taibun_lighttone
- lua_filter@phah_taibun_filter
```

### Performance

- Hash table loaded once at init, ~111 entries
- Per-candidate: 1-3 hash lookups on tail syllables, O(1)
- No measurable impact on typing latency

---

## Testing Strategy

### Build-time Tests (pytest)

- Extract `--` words from sample corpus data, verify hanzi reverse lookup correctness
- Verify rime_key format uses double space for `--`
- Verify no duplicate entries with existing dictionary (check by rime_key)
- Verify weight is lower than non-light-tone variant
- Verify `āu--ji̍t` (後--日) is produced from corpus data
- Verify case normalization (capitalized corpus entries)
- Verify entries with multiple `--` positions are handled

### Runtime Tests

- Lua module correctly loads `lighttone_rules.json`
- Dynamic light-tone candidates generated for matching tail syllables (1-3 syllables)
- Quality is lower than original candidate
- No candidates generated for single-syllable input
- `不處理` rule entries are skipped
- Duplicate TL keys generate multiple candidates

---

## Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| Hanzi reverse lookup failure | Skip entries without match; log for manual review |
| False positives (wrong `--` position) | Corpus-attested forms are trustworthy; runtime uses conservative rules |
| Too many candidates cluttering UI | Light-tone candidates ranked lower; only 1-2 variants per candidate |
| Corpus data not available | Graceful skip in build pipeline; runtime works independently |
| Rime_key collision with existing double-space entries | Deduplicate by rime_key, not just hanlo |
| lighttone_rules.json diacritics vs numeric tone mismatch | Use diacritics-to-numeric conversion in build; match diacritical forms in runtime |

---

## File Changes Summary

### New Files
- `scripts/build_lighttone_entries.py` — Build-time light tone entry generator
- `lua/phah_taibun_lighttone.lua` — Runtime light tone filter
- `tests/test_build_lighttone_entries.py` — Build-time tests

### Modified Files
- `scripts/build_all.py` — Add Step 9b
- `rime.lua` — Register new Lua module
- `schema/phah_taibun.schema.yaml` — Add filter to engine chain
