# Input UX Improvements: Selection Mode & Uppercase Support

## Problem

Two UX issues in the current IME:

1. **Uppercase triggers English mode:** In 漢羅 mode, pressing Shift+letter to type a capital letter (sentence start, proper nouns) causes `ascii_composer` to switch to English/ABC mode instead of starting Taiwanese input.

2. **asdf selection keys don't work:** `alternative_select_keys: "asdfghjkl;"` is configured, but the `speller` processor (alphabet includes a-z) consumes asdf before the `selector` processor ever sees them. Candidates are visible but cannot be selected with asdf.

## Root Causes

- `ascii_composer` runs first in the processor chain and interprets Shift+letter as a mode switch signal.
- `speller` (position 5) runs before `selector` (position 8) in the processor chain. Since the speller's alphabet includes a-z, it always consumes letter keys as romanization input.

## Design

### 1. Mode Switching: Ctrl+Space

**Change:** Replace Shift-based mode toggle with Ctrl+Space.

- `ascii_composer.switch_key`: Set `Shift_L` and `Shift_R` to `noop`
- `key_binder.bindings`: Add `Ctrl+Space` → toggle `ascii_mode`
- Caps Lock: Retains default system behavior (continuous uppercase)

**Result:**
- Shift+letter → types uppercase letter (no mode switch)
- Ctrl+Space → toggles 台文/ABC mode
- Caps Lock → locks uppercase as normal

**Note on Ctrl+Space system conflict:** On some Linux desktop environments (GNOME, KDE), `Ctrl+Space` is the system-level IME switcher. If the system intercepts it before Rime, the toggle will not work. For those users, an alternative like `Control+Shift+space` can be configured. This design assumes Rime is the active IME and receives the key event.

### 2. Tab Selection Mode

**Flow:**
1. User types romanization (e.g., `tsiah8png7`) → candidates appear
2. Press **Tab** → enter selection mode (speller frozen)
3. In selection mode:
   - **asdfghjkl;** or **1234567890** → select corresponding candidate
   - **Space** → confirm highlighted candidate (usually #1)
   - **↑↓ / PgUp / PgDn** → navigate/page candidates
   - **Escape** → exit selection mode, return to editing composition
   - **Any non-selection letter** (bceimnopqrtuvwxyz) → auto-exit selection mode, key returned as kNoop so speller takes over
   - **`[` or `]`** → exit selection mode, key returned as kNoop so `phah_taibun_select_char` handles 以詞定字
   - **Backslash `\`** → exit selection mode, key returned as kNoop so `phah_taibun_commit` handles output mode toggle
4. After selection → auto-exit selection mode

**Tab dual behavior:**
- When `has_menu()` is true (candidates visible): enter selection mode
- When `has_menu()` is false but composing: retain "next syllable" function (send `Shift+Right`)
- When not composing: kNoop (pass through)

This preserves Tab's existing "next syllable" function when no candidates are shown.

### 3. New Lua Module: `phah_taibun_input.lua`

Single module handling both uppercase interception and selection mode. Placed **before** `ascii_composer` in the processor chain (position 1).

**Processor chain:**
```
lua_processor@*phah_taibun_input    ← NEW (position 1)
ascii_composer
lua_processor@*phah_taibun_select_char
recognizer
key_binder
speller
lua_processor@*phah_taibun_commit
punctuator
selector
navigator
fluency_editor
```

**Key handling logic:**

| Key Event | Condition | Action |
|-----------|-----------|--------|
| Shift+letter | 台文 mode, not in selection_mode | `kAccepted`; push lowercase via `context:push_input()`, set capitalize flag |
| Tab | `has_menu()` = true | Set `selection_mode = true`, return `kAccepted` |
| Tab | composing, no menu | Send `Shift+Right` (next syllable), return `kAccepted` |
| asdf.../0-9 | `selection_mode = true` | Set `seg.selected_index`, commit via shared function (see §6), clear flag, return `kAccepted` |
| Space | `selection_mode = true` | Commit highlighted candidate via shared function (see §6), clear flag, return `kAccepted` |
| Escape | `selection_mode = true` | Clear flag, return `kAccepted` (keep composition) |
| Non-selection letter | `selection_mode = true` | Clear flag, return `kNoop` (speller takes over) |
| `[`, `]`, `\` | `selection_mode = true` | Clear flag, return `kNoop` (pass to downstream processors) |
| Other keys | — | return `kNoop` (pass through) |

**Selection keys vs non-selection letters:**
- Selection keys: `a s d f g h j k l ;` and `0 1 2 3 4 5 6 7 8 9` (mapped to candidate indices)
- Non-selection letters: all other alphabetic keys (`b c e i m n o p q r t u v w x y z`) — these exit selection mode and resume composition

### 4. Uppercase: Shift+Letter Implementation

When the user presses Shift+letter (e.g., Shift+G):

1. `phah_taibun_input` intercepts the key event (has Shift modifier + letter keycode)
2. Returns `kAccepted` to prevent `ascii_composer` from seeing it
3. Calls `context:push_input("g")` to inject the lowercase letter into the composition

**Note on speller algebra:** `push_input()` adds characters to the raw input string. The speller re-processes the full input on subsequent key events, so algebra rules (POJ→TL derive, abbreviations) still apply.

**Capitalize flag:**
- Stored in shared state module (see §5) as `shared_state.capitalize_next = true`
- Only applies to the **first letter of the entire composition** (for sentence-start capitalization)
- `phah_taibun_commit` reads this flag when committing in 全羅 mode and applies `capitalize_first()`
- Flag resets after any commit
- For proper nouns mid-sentence, the user can use `\` (backslash) to get the romanization output with manual capitalization via the composition

### 5. Shared State and Commit Utilities

A shared Lua table and shared commit functions in `phah_taibun_data` for cross-processor use:

```lua
-- In phah_taibun_data.lua
local shared_state = {
  selection_mode = false,
  capitalize_next = false,
}

function M.get_shared_state()
  return shared_state
end
```

Both `phah_taibun_input` and `phah_taibun_commit` access state via:
```lua
local state = data_mod.get_shared_state()
```

This avoids the problem of separate `env` tables between processors. Lua's `require()` caches modules, so both processors get the same table reference.

**Shared commit utilities** (moved from `phah_taibun_commit` to `phah_taibun_data`):

```lua
function M.extract_roman(cand, context)
  -- Extract romanization from candidate comment
  -- Handles [TL:... POJ:...] and simple [...] formats
  -- Reads poj_mode via context:get_option("poj_mode")
  -- Applies tl_to_poj conversion if poj_mode is true
  -- Returns formatted romanization string with diacritics
end

function M.tl_to_poj(tl_text)
  -- Convert TL romanization to POJ
end

function M.capitalize_first(text)
  -- Capitalize first letter of text
end
```

These are pure functions (no `env` dependency) that both processors can call.

**Migration note — `capitalize_next`:** `phah_taibun_commit`'s existing `env.capitalize_next` must be replaced with `state.capitalize_next` from shared state. All 5 references must be updated:
- Line 113: `env.capitalize_next = true` (init)
- Line 201: `env.capitalize_next = true` (non-composing half-width punctuation sentence ender)
- Line 348: `if env.capitalize_next then` (commit_roman check)
- Line 352: `env.capitalize_next = false` (commit_roman reset)
- Line 399: `env.capitalize_next = true` (composing punctuation sentence ender)

**Migration note — `last_text`:** `phah_taibun_commit`'s existing `env.last_text` must be replaced with `state.last_text` from shared state. All 8 references must be updated (lines 110, 174, 178, 185, 189, 209, 332, 334), including the non-composing homophone trigger path (apostrophe handling) and the clear-on-non-modifier path.

### 6. Candidate Selection: Shared Commit Functions

**Problem:** `phah_taibun_commit` has complex commit logic for 全羅 mode (romanization extraction, auto-capitalization, homophone tracking, wildcard/reverse-lookup feed-back). Duplicating this in `phah_taibun_input` creates dual maintenance burden and risks divergence.

**Rejected approach — simulated Space via `process_key`:** The initial idea was to simulate a Space key press via `env.engine:process_key(KeyEvent("space"))`. This is rejected because the `speller` (position 6 in the chain) has `delimiter: " '-"` — it may consume Space as a syllable delimiter before `phah_taibun_commit` (position 7) ever sees it. This would silently break the commit flow.

**Solution — shared commit function:** Extract the core commit logic into a shared function in `phah_taibun_data` that both processors call:

```lua
-- In phah_taibun_data.lua
function M.commit_with_roman(engine, context, cand, state)
  -- 1. Extract romanization via M.extract_roman(cand, context)
  -- 2. Apply auto-capitalization if state.capitalize_next
  -- 3. Commit text via engine:commit_text()
  -- 4. Reset state.capitalize_next
  -- 5. Return the committed text (for homophone tracking)
end
```

**`phah_taibun_input` selection mode flow:**

1. For asdf/number selection:
   - Get candidate at target index via `seg.selected_index`
   - Check `full_romanization` option:
     - **全羅 mode:** Call `data_mod.commit_with_roman(env.engine, context, cand, state)`, then `context:clear()`
     - **漢羅 mode:** Call `context:confirm_current_selection()` (standard Rime API — confirms the current segment and advances to the next, preserving multi-segment composition flow)
   - Update homophone tracking (`last_text`) in shared state
   - Clear `selection_mode`
   - Return `kAccepted`

2. For Space in selection mode:
   - Same as above but using the currently highlighted candidate (no index change)

**`phah_taibun_commit` refactoring:**
- Move `extract_roman`, `tl_to_poj`, `capitalize_first` to `phah_taibun_data`
- Replace inline commit logic with calls to `data_mod.commit_with_roman()`
- Replace `env.capitalize_next` with `state.capitalize_next`
- Homophone tracking (`last_text`) moves to shared state
- Existing special flows (wildcard feed-back, reverse-lookup feed-back, backslash toggle) remain in `phah_taibun_commit` as they are mode-specific

### 7. Schema Changes Summary

```yaml
# ascii_composer: disable Shift mode switching
ascii_composer:
  switch_key:
    Shift_L: noop
    Shift_R: noop
    Caps_Lock: clear

# key_binder: add Ctrl+Space toggle, remove Tab binding
key_binder:
  import_preset: default
  bindings:
    - { when: always, accept: Control+space, toggle: ascii_mode }
    - { when: composing, accept: Shift+Tab, send: Shift+Left }
    - { when: paging, accept: bracketleft, send: Page_Up }
    - { when: paging, accept: bracketright, send: Page_Down }

# menu: keep alternative_select_keys for phah_taibun_commit fallback
menu:
  page_size: 10
  alternative_select_keys: "asdfghjkl;"
```

**Note:** `alternative_select_keys` is retained in config. `phah_taibun_commit` reads this value for its `select_map` (used in wildcard feed-back, reverse-lookup feed-back, and homophone tracking at line 323). In normal (non-selection) mode, the speller still consumes these keys as input — the config value is only effective through the Lua processors.

### 8. Division of Responsibility

| Module | Responsibility |
|--------|---------------|
| `phah_taibun_input` (new) | Uppercase interception (Shift+letter → lowercase + capitalize flag), selection mode toggle (Tab), candidate selection in selection mode (via shared commit utilities) |
| `phah_taibun_data` (existing, extended) | Shared state (`selection_mode`, `capitalize_next`, `last_text`), shared commit utilities (`extract_roman`, `tl_to_poj`, `capitalize_first`, `commit_with_roman`) |
| `phah_taibun_commit` (existing, refactored) | 全羅 mode: romanization output via shared utilities, backslash toggle, homophone lookup, wildcard/reverse-lookup feed-back, punctuation commit. Replaces `env.capitalize_next` with shared state. |
| `phah_taibun_select_char` (existing) | 以詞定字 `[` `]` (unchanged) |
| `phah_taibun_filter` (existing) | Han-Lo conversion, output mode (unchanged) |

### 9. Edge Cases

- **Tab with no composition:** kNoop, falls through to normal Tab behavior.
- **Tab composing but no menu:** Sends `Shift+Right` (next syllable), preserving existing behavior.
- **Selection mode + `[`/`]`:** Clears selection mode, passes key to `phah_taibun_select_char` for 以詞定字.
- **Selection mode + backslash:** Clears selection mode, passes key to `phah_taibun_commit` for output mode toggle.
- **Selection mode + punctuation in 全羅 mode:** Clears selection mode, passes key to `phah_taibun_commit` for punctuation commit.
- **Number keys in selection mode:** Treated as candidate selection (0-9 → candidates 1-10). If the user needs to edit a tone number, they press Escape first to exit selection mode, then edit.
- **Capitalize flag in 漢羅 mode:** Only affects 全羅 output. In 漢羅 mode, Han-ji portions are unaffected and romanization portions follow hanlo rules.
- **Composition cleared externally:** If another processor clears the composition (e.g., `phah_taibun_select_char` commits via `[`/`]`), `phah_taibun_input` should detect empty composition on next key event and clear `selection_mode` from shared state.
- **Enter key in selection mode:** Clears selection mode, returns `kNoop` to let `fluency_editor` handle `commit_raw_input` as configured.
- **Visual indicator:** Selection mode should display a status message (e.g., via `context:set_property()` or engine status area) so users know Escape is needed to return to editing. Implementation detail to be determined during development.

### 10. Known Limitations

- **Mid-sentence proper noun capitalization:** The capitalize flag only applies to the first letter of the entire composition (sentence-start use case). For proper nouns mid-sentence (e.g., "Tâi-pak"), the user must use `\` (backslash) to output romanization and manually type the capitalized form. Supporting per-syllable capitalization would require syllable boundary detection, which adds significant complexity for limited benefit.
- **Number key ambiguity in selection mode:** In selection mode, 0-9 select candidates rather than adding tone numbers. If the user needs to correct a tone, they must press Escape first to exit selection mode. A visual indicator (see above) mitigates confusion.

### 11. Required File Changes

| File | Change |
|------|--------|
| `lua/phah_taibun_input.lua` | New module: uppercase interception + selection mode |
| `lua/phah_taibun_data.lua` | Add shared state, move `extract_roman`/`tl_to_poj`/`capitalize_first` here, add `commit_with_roman` |
| `lua/phah_taibun_commit.lua` | Refactor to use shared utilities from `phah_taibun_data`, replace `env.capitalize_next` with shared state |
| `rime.lua` | Register `phah_taibun_input` module |
| `lua/phah_taibun_filter.lua` | Replace local `tl_to_poj` copy with `data_mod.tl_to_poj` from shared utilities |
| `schema/phah_taibun.schema.yaml` | Add `ascii_composer.switch_key`, add Ctrl+Space binding, remove `Tab` composing binding (keep `Shift+Tab`), add `phah_taibun_input` to processor chain position 1 |
