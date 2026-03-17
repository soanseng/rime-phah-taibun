# Light Tone (輕聲) Candidate Generation

## Problem

Taiwanese Hokkien has light tone (輕聲) where certain syllables lose their original tone. The light tone marker `--` changes meaning: `āu-ji̍t` (後日, "in the future") vs `āu--ji̍t` (後--日, "day after tomorrow"). The dictionary currently has only 391 manually sourced `--` entries, while corpus data contains ~28,700 light-tone word forms that are not leveraged.

## Solution

Two-phase approach: build-time extraction from corpus data (Phase A), then runtime dynamic generation via Lua filter (Phase B).

---

## Phase A: Build-time Light Tone Entry Generation

### New Script: `scripts/build_lighttone_entries.py`

**Input:**
- All corpus frequency TSVs: `ungian_freq.tsv` (9,077 `--` forms), `nmtl_freq.tsv` (8,978), `900leku_freq.tsv` (319), `kipsutian_sent_freq.tsv` (243), `pojbh_freq.tsv` (34), `kok4hau7_freq.tsv` (58)
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
    → Deduplicate against existing dict entries
    → Append to dict.yaml
```

### Hanzi Reverse Lookup Strategy

Three methods, tried in order:

1. **Whole-word match**: Look up the non-light-tone version (strip `--`) in the existing dictionary. E.g., `tng2--lai5` → strip to `tng2-lai5` → find `轉來` → produce `轉--來`.

2. **Syllable-by-syllable assembly**: Split at `--` boundary into prefix and suffix. Look up each part separately. E.g., `khi2--lai5` → `khi2` = `起`, `lai5` = `來` → `起--來`.

3. **lighttone_rules.json validation**: The 111 rules map light-tone morphemes to hanzi (e.g., `--lai5` → `來`). Use to verify or supply the suffix hanzi when syllable lookup is ambiguous.

### Rime Key Format

Consistent with existing entries: `--` position represented as **double space** in rime_key.

| hanlo | rime_key | weight |
|-------|----------|--------|
| 轉--來 | `tng2  lai5` | 800 |
| 後--日 | `au7  jit8` | 800 |
| 出--來 | `tshut  lai5` | 750 |

### Weight Calculation

- Base weight from corpus frequency: `base = 300 + log10(1 + merged_count) * 150`
- Capped below the non-light-tone variant's weight (light tone candidate should rank lower)
- Minimum weight: 300 (to appear in candidate list)
- Maximum weight: 1500 (prevent dominating over common entries)

### Build Pipeline Integration

Insert as **Step 3b** in `build_all.py`, after Step 3 (ChhoeTaigi conversion) and before Step 4 (LKK rules):

```
Step 3:  Convert ChhoeTaigi → dict.yaml
Step 3b: Build light-tone entries → append to dict.yaml  ← NEW
Step 4:  Parse LKK rules → hanlo_rules.yaml
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

On `init`, load `lighttone_rules.json` into a hash table keyed by TL syllable (without `--` prefix):

```lua
-- lighttone_rules.json entry: {"tl": "--lâi", "hanzi": "來", "rule": "補語"}
-- Stored as: rules["lai5"] = {hanzi="來", rule="補語"}
```

### Processing Logic

For each multi-syllable candidate (2+ syllables):

1. Extract `raw_roman` from candidate comment (e.g., `khi3 tshue7 i`)
2. Check if the last 1-2 syllables match a lighttone rule
3. If match found:
   - Generate a new candidate with `--` inserted at the appropriate position
   - Set quality slightly below the original candidate (`cand.quality - 0.3`)
   - Yield both original and light-tone variant

### Trigger Conditions

- Only candidates with **2+ syllables**
- Only when tail syllable(s) match `lighttone_rules.json`
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

In schema `engine/filters`, after `phah_taibun_filter`:
```yaml
- lua_filter@phah_taibun_lighttone
```

### Performance

- Hash table loaded once at init, ~111 entries
- Per-candidate: 1-2 hash lookups on tail syllables, O(1)
- No measurable impact on typing latency

---

## Testing Strategy

### Build-time Tests (pytest)

- Extract `--` words from sample corpus data, verify hanzi reverse lookup correctness
- Verify rime_key format uses double space for `--`
- Verify no duplicate entries with existing dictionary
- Verify weight is lower than non-light-tone variant
- Verify `āu--ji̍t` (後--日) is produced from corpus data

### Runtime Tests

- Lua module correctly loads `lighttone_rules.json`
- Dynamic light-tone candidates generated for matching tail syllables
- Quality is lower than original candidate
- No candidates generated for single-syllable input
- `不處理` rule entries are skipped

---

## Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| Hanzi reverse lookup failure | Skip entries without match; log for manual review |
| False positives (wrong `--` position) | Corpus-attested forms are trustworthy; runtime uses conservative rules |
| Too many candidates cluttering UI | Light-tone candidates ranked lower; only 1-2 variants per candidate |
| Corpus data not available | Graceful skip in build pipeline; runtime works independently |

---

## File Changes Summary

### New Files
- `scripts/build_lighttone_entries.py` — Build-time light tone entry generator
- `lua/phah_taibun_lighttone.lua` — Runtime light tone filter
- `tests/test_build_lighttone_entries.py` — Build-time tests

### Modified Files
- `scripts/build_all.py` — Add Step 3b
- `rime.lua` — Register new Lua module
- `schema/phah_taibun.schema.yaml` — Add filter to engine chain
