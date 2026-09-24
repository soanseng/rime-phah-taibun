"""Behavior tests for the phah_taibun learning filter (phah_taibun_learn).

The learning design: every committed dictionary candidate increments a
per-(word, reading) commit counter stored in the Rime user dir; the filter
boosts learned candidates by

    B = B_MAX * min(1, commits / C_SAT) * 0.5 ** (age_days / H_DAYS)

and adds B to the candidate's quality in one stable sort (unlearned boost 0),
so learning wins ties and near-ties only. Tests drive the real Lua
modules through a plain-Lua subprocess harness (rime_api/os.time stubbed),
like test_lua_filter_behavior.py.
"""

import re
import shutil
import subprocess
import textwrap
from pathlib import Path

import yaml

ROOT = Path(__file__).parent.parent
LUA_EXECUTABLE = shutil.which("lua") or shutil.which("lua5.4") or "lua"

# Fixed wall-clock epoch for deterministic decay tests (2023-11-14).
BASE_EPOCH = 1_700_000_000


def run_lua(script: str) -> str:
    result = subprocess.run(
        [LUA_EXECUTABLE, "-"],
        input=script,
        capture_output=True,
        text=True,
        cwd=ROOT,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    return result.stdout


def learn_harness(store_dir: Path, now: int = BASE_EPOCH) -> str:
    """Common preamble: stub rime_api + clock, load the learn module."""
    return textwrap.dedent(
        f"""
        package.path = "lua/?.lua;" .. package.path
        rime_api = {{ get_user_data_dir = function() return {json_str(str(store_dir))} end }}
        __now__ = {now}
        if os and os.time then os.time = function() return __now__ end end
        function Candidate(typ, start, end_pos, text, comment, quality)
          return {{
            type = typ,
            start = start,
            _end = end_pos,
            text = text,
            comment = comment,
            quality = quality or 0,
          }}
        end
        function yield(cand) end
        local learn = require("phah_taibun_learn")
        learn.init({{}})
        """
    ).replace("__now__ =", "__now__ =")  # keep a mutable global named __now__


def json_str(s: str) -> str:
    """Quote a path as a Lua string literal."""
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def set_now(lines: list[str], now: int) -> list[str]:
    return [*lines, f"__now__ = {now}"]


def test_learn_module_exposes_init_and_func(tmp_path):
    script = learn_harness(tmp_path) + textwrap.dedent(
        """
        assert(type(learn.init) == "function", "init missing")
        assert(type(learn.func) == "function", "func missing")
        print("OK")
        """
    )
    assert run_lua(script).strip() == "OK"


def test_observe_learns_selected_reading_only(tmp_path):
    """重/tāng observed three times boosts 重/tāng, never 重/tîng."""
    script = learn_harness(tmp_path) + textwrap.dedent(
        r"""
        local cand = Candidate("table", 0, 1, "重", " [tāng]")
        learn.observe(cand)
        learn.observe(cand)
        learn.observe(cand)

        -- 重 tāng stored (3 commits), 重 tîng untouched: identity = (text, reading).
        -- Rank displacement is NOT asserted here: 3 commits is B=0.15 ->
        -- floor 0 -> no movement (bounded displacement, see other tests).
        local data = require("phah_taibun_data")
        local learned = learn.get(data.word_identity("重", "tang7"))
        assert(learned ~= nil, "tang7 must be learned")
        assert(learned.commits == 3, "expected 3 commits, got " .. learned.commits)
        assert(learn.get(data.word_identity("重", "ting5")) == nil,
               "different reading must stay unlearned")

        print("OK")
        """
    )
    assert run_lua(script).strip() == "OK"


def test_diacritic_and_numbered_comments_share_identity(tmp_path):
    """Learning via the display comment must boost the numbered-code candidate.

    Candidates reach the learn filter with diacritic comments (the core
    filter rewrites [tang7] to [tāng]); observe must recover the numbered
    code so both forms map onto one identity.
    """
    script = learn_harness(tmp_path) + textwrap.dedent(
        r"""
        local cand = Candidate("table", 0, 1, "重", " [tāng]")
        for _ = 1, 40 do learn.observe(cand) end

        local items = {
          Candidate("table", 0, 1, "重", " [tîng]"),
          Candidate("table", 0, 1, "重", " [tang7]"),
        }
        local pos = 0
        local input = {
          iter = function()
            return function()
              pos = pos + 1
              return items[pos]
            end
          end,
        }
        local out = {}
        yield = function(c) table.insert(out, c) end
        learn.func(input, {})
        assert(out[1].comment == " [tang7]",
               "numbered-code twin of the learned display form must rank first, got "
               .. tostring(out[1].comment))
        print("OK")
        """
    )
    assert run_lua(script).strip() == "OK"


def test_poj_display_and_tl_display_share_identity(tmp_path):
    """POJ-mode display (chhiáⁿ) and TL-mode display (tshiánn) are one word."""
    script = learn_harness(tmp_path) + textwrap.dedent(
        r"""
        -- Observed while in POJ mode (saturated so the boost displaces).
        for _ = 1, 40 do
          learn.observe(Candidate("table", 0, 3, "請", " [chhiáⁿ]"))
        end

        -- Later rendered in TL mode: same word must still be boosted.
        local items = {
          Candidate("table", 0, 3, "請", " [thiânn]"),
          Candidate("table", 0, 3, "請", " [tshiánn]"),
        }
        local pos = 0
        local input = {
          iter = function()
            return function()
              pos = pos + 1
              return items[pos]
            end
          end,
        }
        local out = {}
        yield = function(c) table.insert(out, c) end
        learn.func(input, {})
        assert(out[1].comment == " [tshiánn]",
               "TL display twin of the learned POJ display must rank first, got "
               .. tostring(out[1].comment))
        print("OK")
        """
    )
    assert run_lua(script).strip() == "OK"


def test_saturation_caps_boost_at_40_commits(tmp_path):
    """60 observes must score exactly like 40 (B_MAX = 2.0); growth is monotonic."""
    script = learn_harness(tmp_path) + textwrap.dedent(
        r"""
        local data = require("phah_taibun_data")
        local cand = Candidate("table", 0, 1, "重", " [tāng]")
        for _ = 1, 10 do learn.observe(cand) end
        local id = data.word_identity("重", "tang7")
        local b10 = learn.boost(learn.get(id).commits, learn.get(id).last)
        for _ = 1, 30 do learn.observe(cand) end
        local b40 = learn.boost(learn.get(id).commits, learn.get(id).last)
        for _ = 1, 20 do learn.observe(cand) end
        local b60 = learn.boost(learn.get(id).commits, learn.get(id).last)

        assert(b10 < b40, "boost must grow before saturation")
        assert(math.abs(b40 - 2.0) < 1e-9, "40 commits must saturate at B_MAX, got " .. b40)
        assert(math.abs(b60 - b40) < 1e-9, "60 commits must not exceed the cap, got " .. b60)
        print("OK")
        """
    )
    assert run_lua(script).strip() == "OK"


def test_half_life_halves_boost_and_clock_skew_clamps(tmp_path):
    """B halves after H_DAYS; a last stamp in the future must not go negative."""
    script = learn_harness(tmp_path) + textwrap.dedent(
        f"""
        local data = require("phah_taibun_data")
        local cand = Candidate("table", 0, 1, "重", " [tāng]")
        for _ = 1, 40 do learn.observe(cand) end
        local id = data.word_identity("重", "tang7")
        local e = learn.get(id)

        assert(math.abs(learn.boost(e.commits, e.last) - 2.0) < 1e-9,
               "fresh saturated word must be at B_MAX")

        __now__ = {BASE_EPOCH + 30 * 86400}
        local b_half = learn.boost(e.commits, e.last)
        assert(math.abs(b_half - 1.0) < 1e-6,
               "after one half-life boost must halve, got " .. tostring(b_half))

        -- Clock skew: stamp lies in the future, age clamps to zero.
        __now__ = {BASE_EPOCH - 999}
        local b_skew = learn.boost(e.commits, e.last)
        assert(math.abs(b_skew - 2.0) < 1e-9,
               "future stamp must clamp to full boost, got " .. tostring(b_skew))
        print("OK")
        """
    )
    assert run_lua(script).strip() == "OK"


def test_decay_disabled_without_os_time(tmp_path):
    """Without a clock the stamp is 0 and decay never applies."""
    script = learn_harness(tmp_path) + textwrap.dedent(
        f"""
        local data = require("phah_taibun_data")
        local real_os = os
        os = nil  -- sandbox without os.* (feature-detect path)
        local cand = Candidate("table", 0, 1, "重", " [tāng]")
        for _ = 1, 40 do learn.observe(cand) end
        os = real_os
        local e = learn.get(data.word_identity("重", "tang7"))
        assert(e.commits == 40, "commits must still count, got " .. e.commits)
        assert(e.last == 0, "stamp must be 0 without a clock, got " .. tostring(e.last))

        __now__ = {BASE_EPOCH + 365 * 86400}
        assert(math.abs(learn.boost(e.commits, e.last) - 2.0) < 1e-9,
               "last == 0 must disable decay, got " .. tostring(learn.boost(e.commits, e.last)))
        print("OK")
        """
    )
    assert run_lua(script).strip() == "OK"


def test_store_roundtrip_and_corrupt_lines_skipped(tmp_path):
    """TSV persists '<identity>\\t<commits> <last>'; malformed lines are ignored."""
    store = tmp_path / "phah_taibun_learning.tsv"
    store.write_text(
        "重\ttang7\t3 1700000000\nno tab at all\n重\tbad xx\n飯\tpng7\tabc def\n\n",
        encoding="utf-8",
    )
    script = learn_harness(tmp_path) + textwrap.dedent(
        r"""
        local data = require("phah_taibun_data")

        -- Corrupt lines skipped, valid line loaded.
        local e = learn.get(data.word_identity("重", "tang7"))
        assert(e ~= nil, "valid line must load")
        assert(e.commits == 3 and e.last == 1700000000,
               "unexpected load: " .. tostring(e.commits) .. " " .. tostring(e.last))
        assert(learn.get(data.word_identity("重", "bad")) == nil,
               "garbage line must not load")

        -- Roundtrip: two more observes append a well-formed line.
        local cand = Candidate("table", 0, 1, "飯", " [png7]")
        learn.observe(cand)
        learn.observe(cand)

        local f = io.open(rime_api.get_user_data_dir() .. "/phah_taibun_learning.tsv", "r")
        assert(f ~= nil, "store file must exist after observe")
        local roundtripped = false
        for line in f:lines() do
          local identity, commits, last = line:match("^(.-)\t(%d+) (%d+)$")
          if identity == data.word_identity("飯", "png7") then
            assert(commits == "2", "expected 2 commits on disk, got " .. commits)
            assert(tonumber(last) > 0, "expected a real stamp on disk")
            roundtripped = true
          end
        end
        f:close()
        assert(roundtripped, "observed word must persist in TSV form")

        -- Fresh module state reloads from disk.
        package.loaded["phah_taibun_learn"] = nil
        local learn2 = require("phah_taibun_learn")
        learn2.init({})
        local e2 = learn2.get(data.word_identity("飯", "png7"))
        assert(e2 ~= nil and e2.commits == 2, "store must survive a reload")
        print("OK")
        """
    )
    assert run_lua(script).strip() == "OK"


def test_empty_store_passthrough_is_byte_identical(tmp_path):
    """With no learning data the filter re-yields candidates untouched."""
    script = learn_harness(tmp_path) + textwrap.dedent(
        r"""
        local items = {
          Candidate("table", 0, 3, "你姆", " [li2 m2]", 0.2),
          Candidate("table", 0, 3, "林", " [lím]", 0.5),
          Candidate("table", 2, 3, "姆", " [m̄]", 0),
        }
        local pos = 0
        local input = {
          iter = function()
            return function()
              pos = pos + 1
              return items[pos]
            end
          end,
        }
        local out = {}
        yield = function(c) table.insert(out, c) end
        learn.func(input, {})
        assert(#out == #items, "must yield every candidate")
        for i = 1, #items do
          assert(rawequal(out[i], items[i]), "candidates must pass through untouched")
        end
        print("OK")
        """
    )
    assert run_lua(script).strip() == "OK"


def test_filter_reorders_learned_within_bounded_displacement(tmp_path):
    """Bounded displacement: learned candidates rise by floor(B) slots (cap 3).

    Saturated (B=2.0) rises 2 slots — past nearby rivals but never floods
    the window; a barely-learned word (B<1) does not move at all.
    """
    script = learn_harness(tmp_path) + textwrap.dedent(
        r"""
        local heavy = Candidate("table", 0, 1, "重", " [tāng]")
        for _ = 1, 40 do learn.observe(heavy) end   -- B = 2.0 -> nudge 2

        local items = {
          Candidate("table", 0, 1, "糖", " [thn̂g]", 0),   -- pos1 slot1
          Candidate("table", 0, 1, "新", " [sin]", 0),     -- pos2 slot2
          Candidate("table", 0, 1, "重", " [tāng]", 0),    -- pos3 -> slot1(tie, order3)
          Candidate("table", 0, 1, "鮮", " [tshinn]", 0),  -- pos4 slot4
          Candidate("table", 0, 1, "林", " [lîm]", 0),     -- pos5 slot5
        }
        local pos = 0
        local input = {
          iter = function()
            return function()
              pos = pos + 1
              return items[pos]
            end
          end,
        }
        local out = {}
        yield = function(c) table.insert(out, c) end
        learn.func(input, {})
        local order = {}
        for i, c in ipairs(out) do order[i] = c.text end
        -- 糖(slot1,order1) then 重(slot1,order3): stable tie by original order
        local expected = { "糖", "重", "新", "鮮", "林" }
        for i = 1, 5 do
          assert(order[i] == expected[i],
                 "position " .. i .. ": expected " .. expected[i] .. ", got " .. order[i])
        end
        print("OK")
        """
    )
    assert run_lua(script).strip() == "OK"


def test_observe_skips_origin_and_readingless_candidates(tmp_path):
    """Origin candidates and candidates without a recoverable reading never learn."""
    script = learn_harness(tmp_path) + textwrap.dedent(
        r"""
        local data = require("phah_taibun_data")

        -- Origin-type candidate, even with a plausible comment.
        learn.observe(Candidate("origin", 0, 1, "重", " [tāng]"))
        -- Sentence composition: no comment at all.
        learn.observe(Candidate("table", 0, 5, "我愛你", ""))
        -- Non-romanization comment (date/symbol/help style).
        learn.observe(Candidate("date", 0, 1, "2026年", "台語日期"))
        -- Bracket content that is not a reading.
        learn.observe(Candidate("table", 0, 1, "查", " [查無此音]"))

        assert(learn.get(data.word_identity("重", "tang7")) == nil,
               "origin candidates must not be learned")
        local path = rime_api.get_user_data_dir() .. "/phah_taibun_learning.tsv"
        local f = io.open(path, "r")
        assert(f == nil or f:read("a") == "",
               "skipped candidates must not create store entries")
        if f then f:close() end
        print("OK")
        """
    )
    assert run_lua(script).strip() == "OK"


def test_schema_registers_learn_filter_between_synonym_and_long_word():
    schema = yaml.safe_load((ROOT / "schema" / "phah_taibun.schema.yaml").read_text(encoding="utf-8"))
    filters = schema["engine"]["filters"]
    learn = "lua_filter@*phah_taibun_learn"
    assert learn in filters, "learn filter must be registered in the engine"
    assert filters.index(learn) == filters.index("lua_filter@*phah_taibun_synonym") + 1
    assert filters.index(learn) == filters.index("lua_filter@*phah_taibun_long_word") - 1


def test_rime_lua_registers_learn_module():
    rime_lua = (ROOT / "rime.lua").read_text(encoding="utf-8")
    assert re.search(r'phah_taibun_learn\s*=\s*require\("phah_taibun_learn"\)', rime_lua), (
        "rime.lua must register the learn module for legacy librime-lua"
    )


def test_commit_processor_observes_committed_candidates():
    """observe() must fire on the TRACK block (Space/select), the 全羅
    backslash commit and the 全羅 punctuation commit — and nowhere else."""
    src = (ROOT / "lua" / "phah_taibun_commit.lua").read_text(encoding="utf-8")

    assert 'pcall(require, "phah_taibun_learn")' in src

    def window(start_marker: str, end_marker: str) -> str:
        i = src.index(start_marker)
        j = src.index(end_marker, i)
        return src[i:j]

    track = window("TRACK last committed character", "local full_roman")
    assert "observe(" in track, "TRACK block must observe Space/select commits"

    full_roman_backslash = window(
        "全羅 mode: output the Han-Lo display text",
        "漢羅 mode: output full romanization",
    )
    assert "observe(" in full_roman_backslash, "全羅 backslash commit must observe"

    punct = window("Handle punctuation while composing", "kNoop for all other keys")
    assert "observe(" in punct, "全羅 punctuation commit must observe"

    ret = window("Return commits the sound the user typed", "以下只在全羅模式下攔截")
    assert "observe(" not in ret, "the Return path must not observe"


def test_learn_single_observe_does_not_displace(tmp_path):
    """One selection (B < 1 -> floor 0) must not move the candidate at all.

    The kio-tiann production incident: additive quality sorts flooded the
    candidate window. Displacement is bounded and earned gradually.
    """
    script = learn_harness(tmp_path) + textwrap.dedent(
        r"""
        local cand = Candidate("table", 0, 1, "重", " [tāng]")
        learn.observe(cand)   -- B = 2.0 * (1/40) = 0.05 -> floor 0

        local items = {
          Candidate("table", 0, 1, "糖", " [thn̂g]", 0),
          Candidate("table", 0, 1, "重", " [tāng]", 0),
        }
        local pos = 0
        local input = {
          iter = function()
            return function()
              pos = pos + 1
              return items[pos]
            end
          end,
        }
        local out = {}
        yield = function(c) table.insert(out, c) end
        learn.func(input, {})
        assert(out[1].text == "糖", "one observe must not displace, got " .. out[1].text)
        assert(out[2].text == "重")
        print("OK")
        """
    )
    assert run_lua(script).strip() == "OK"
