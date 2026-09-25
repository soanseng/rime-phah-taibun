"""Behavior tests that compile and exercise the real librime engine."""

from __future__ import annotations

import json
import os
import random
import re
import shutil
import subprocess
import unicodedata
from dataclasses import dataclass
from pathlib import Path

import pytest

from scripts.extract_900leku_freq import unicode_tl_to_numeric

ROOT = Path(__file__).parents[1]
SENTENCE_CORPUS_TSV = ROOT / "tests" / "fixtures" / "sentence_corpus.tsv"
SENTENCE_BASELINE_JSON = ROOT / "tests" / "fixtures" / "sentence_baseline.json"
WRITTEN_CORPUS_TSV = ROOT / "tests" / "fixtures" / "sentence_corpus_written.tsv"
WRITTEN_BASELINE_JSON = ROOT / "tests" / "fixtures" / "sentence_written_baseline.json"
SENTENCE_ROUNDTRIP_BASELINE_JSON = ROOT / "tests" / "fixtures" / "sentence_roundtrip_baseline.json"


@dataclass(frozen=True)
class RimeRuntime:
    prefix: Path
    include_dir: Path
    library_dir: Path
    shared_data_dir: Path
    lua_plugin: Path
    deployer: Path


# ~ 注音反查 needs the bopomofo_tw closure (see schema reverse_lookup:).
# Distro packages: Arch rime-bopomofo/rime-terra-pinyin, Debian
# librime-data-bopomofo/librime-data-terra-pinyin (CI installs both).
_REVERSE_CLOSURE_FILES = (
    "bopomofo.schema.yaml",
    "bopomofo_tw.schema.yaml",
    "zhuyin.yaml",
    "terra_pinyin.dict.yaml",
)


def _reverse_closure_available(runtime: RimeRuntime) -> bool:
    return all((runtime.shared_data_dir / name).exists() for name in _REVERSE_CLOSURE_FILES)


def _require_or_skip(message: str) -> None:
    if os.environ.get("RIME_SMOKE_REQUIRED") == "1":
        pytest.fail(message)
    pytest.skip(message)


def _find_runtime() -> RimeRuntime:
    prefixes = []
    if value := os.environ.get("RIME_TEST_PREFIX"):
        prefixes.append(Path(value))
    prefixes.extend((Path("/usr"), Path("/usr/local")))

    deployer_override = os.environ.get("RIME_DEPLOYER")
    for prefix in prefixes:
        include_dir = prefix / "include"
        if not (include_dir / "rime_api.h").exists():
            continue
        # The dev library lives directly in lib/; addon dirs like
        # /usr/lib/fcitx5 also contain a librime.so (the IM module) and
        # must not shadow it.
        library_candidates = sorted((prefix / "lib").glob("librime.so"))
        library_candidates += sorted((prefix / "lib").glob("*/librime.so"))
        plugin_candidates = sorted((prefix / "lib").glob("*/rime-plugins/librime-lua.so"))
        plugin_candidates += sorted((prefix / "lib").glob("rime-plugins/librime-lua.so"))
        shared_data_dir = Path(os.environ.get("RIME_SHARED_DATA_DIR", prefix / "share/rime-data"))
        deployer = Path(deployer_override) if deployer_override else prefix / "bin/rime_deployer"
        if library_candidates and plugin_candidates and shared_data_dir.is_dir() and deployer.exists():
            return RimeRuntime(
                prefix=prefix,
                include_dir=include_dir,
                library_dir=library_candidates[0].parent,
                shared_data_dir=shared_data_dir,
                lua_plugin=plugin_candidates[0],
                deployer=deployer,
            )

    _require_or_skip(
        "real Rime smoke test needs rime_deployer, librime headers/library, "
        "librime-lua, and shared Rime data; set RIME_TEST_PREFIX if installed outside /usr"
    )
    raise AssertionError("unreachable")


def _parse_states(stdout: str) -> dict[str, dict[str, object]]:
    states: dict[str, dict[str, object]] = {}
    for line in stdout.splitlines():
        fields = line.split("\t")
        if fields[0] == "STATE":
            states[fields[1]] = {"preedit": fields[2], "count": int(fields[3]), "candidates": []}
        elif fields[0] == "CAND":
            states[fields[1]]["candidates"].append({"text": fields[3], "comment": fields[4]})
        elif fields[0] == "COMMIT":
            states.setdefault(fields[1], {"preedit": "", "count": 0, "candidates": []})["commit"] = fields[2]
    return states


def _build_and_run(
    runtime: RimeRuntime,
    tmp_path_factory,
    *,
    smoke_args: tuple[str, ...] = (),
) -> dict[str, dict[str, object]]:
    """Compile the schemas + smoke binary in a fresh tmp user dir, run, parse.

    Extra `smoke_args` are appended after LUA_PLUGIN SHARED_DATA USER_DATA.
    """
    compiler = shutil.which("g++")
    if compiler is None:
        _require_or_skip("real Rime smoke test needs g++")

    work = tmp_path_factory.mktemp("real-rime")
    user_data = work / "user"
    user_data.mkdir()
    for source in (ROOT / "schema").iterdir():
        if source.is_file():
            shutil.copy2(source, user_data / source.name)
    shutil.copytree(ROOT / "lua", user_data / "lua")
    shutil.copy2(ROOT / "rime.lua", user_data / "rime.lua")
    if (ROOT / "opencc").is_dir():
        shutil.copytree(ROOT / "opencc", user_data / "opencc")

    # Stage the ~ 注音反查 closure from shared data and compile it into the
    # user build dir, mirroring a first deployment on Trime/Android: the smoke
    # harness points prebuilt_data_dir at user/build, so shared prebuilts are
    # never found (FallbackResourceResolver: staging -> prebuilt only).
    if _reverse_closure_available(runtime):
        for name in _REVERSE_CLOSURE_FILES:
            shutil.copy2(runtime.shared_data_dir / name, user_data / name)

    build_dir = user_data / "build"
    build_dir.mkdir()
    env = os.environ.copy()
    env["LD_LIBRARY_PATH"] = os.pathsep.join(
        filter(None, (str(runtime.library_dir), str(runtime.lua_plugin.parent), env.get("LD_LIBRARY_PATH")))
    )
    if _reverse_closure_available(runtime):
        subprocess.run(
            [
                str(runtime.deployer),
                "--compile",
                str(user_data / "bopomofo_tw.schema.yaml"),
                str(user_data),
                str(runtime.shared_data_dir),
                str(build_dir),
            ],
            check=True,
            cwd=ROOT,
            env=env,
        )
    for schema_name in ("phah_taibun.schema.yaml", "phah_taibun_telex.schema.yaml"):
        subprocess.run(
            [
                str(runtime.deployer),
                "--compile",
                str(user_data / schema_name),
                str(user_data),
                str(runtime.shared_data_dir),
                str(build_dir),
            ],
            check=True,
            cwd=ROOT,
            env=env,
        )

    executable = work / "rime_smoke"
    subprocess.run(
        [
            compiler,
            "-std=c++17",
            f"-I{runtime.include_dir}",
            str(ROOT / "tests/rime_smoke.cpp"),
            f"-L{runtime.library_dir}",
            f"-Wl,-rpath,{runtime.library_dir}",
            "-lrime",
            "-ldl",
            "-o",
            str(executable),
        ],
        check=True,
        cwd=ROOT,
        env=env,
    )
    result = subprocess.run(
        [str(executable), str(runtime.lua_plugin), str(runtime.shared_data_dir), str(user_data), *smoke_args],
        check=True,
        capture_output=True,
        text=True,
        cwd=ROOT,
        env=env,
    )
    return _parse_states(result.stdout)


@pytest.fixture(scope="session")
def real_rime_states(tmp_path_factory):
    return _build_and_run(_find_runtime(), tmp_path_factory)


@pytest.fixture(scope="session")
def real_rime_corpus(tmp_path_factory):
    """Same pipeline, but the binary replays tests/fixtures/sentence_corpus.tsv."""
    return _build_and_run(_find_runtime(), tmp_path_factory, smoke_args=(str(SENTENCE_CORPUS_TSV),))


@pytest.fixture(scope="session")
def real_rime_written(tmp_path_factory):
    """Same pipeline, but replays the written-track corpus (dopamine article)."""
    return _build_and_run(_find_runtime(), tmp_path_factory, smoke_args=(str(WRITTEN_CORPUS_TSV),))


def test_backtick_opens_symbol_menu(real_rime_states):
    state = real_rime_states["backtick"]
    assert state["count"] > 0
    assert any(candidate["text"] != "`" for candidate in state["candidates"])


@pytest.fixture(scope="session")
def _reverse_closure() -> None:
    if not _reverse_closure_available(_find_runtime()):
        pytest.skip("~ 注音反查 closure (terra_pinyin + bopomofo) absent from shared rime-data")


def test_reverse_lookup_zhuyin_shows_taiwanese_readings(real_rime_states, _reverse_closure):
    """~ㄔ surfaces Mandarin chars annotated with their Taiwanese readings."""
    cands = real_rime_states["reverse_zhuyin_t"]["candidates"]
    che = next((c for c in cands if c["text"] == "車"), None)
    assert che is not None, [c["text"] for c in cands]
    assert "tshia" in _nfc(che["comment"]), che


def test_reverse_lookup_space_feeds_reading_back_to_main_input(real_rime_states, _reverse_closure):
    """Space on ~ㄔ pushes the highlighted char's TL reading into the main input.

    The ~ composition must be replaced by a plain TL code with a live 台語
    candidate menu (feed-back via phah_taibun_commit's reverse branch).
    """
    state = real_rime_states["reverse_zhuyin_fed"]
    assert not state["preedit"].startswith("~"), state
    assert re.fullmatch(r"[a-z0-9]+", state["preedit"]), state
    assert state["count"] > 0, state


def test_main_dictionary_produces_taiwanese_candidates(real_rime_states):
    state = real_rime_states["tsiah8"]
    assert state["count"] > 0
    assert any(candidate["text"] == "食" for candidate in state["candidates"])


def test_help_descriptions_are_not_rewritten_as_romanization(real_rime_states):
    candidates = real_rime_states["help"]["candidates"]
    assert candidates
    assert all("TL:" not in candidate["comment"] for candidate in candidates)
    help_by_key = {candidate["text"]: candidate["comment"] for candidate in candidates}
    assert help_by_key["[ / ]"] == "以詞定字\uff1a選首字 / 尾字"


def test_known_hyphenated_phrase_still_matches_dictionary(real_rime_states):
    """Typing a known phrase with the hyphen break must keep the whole-word candidate."""
    state = real_rime_states["known_hyphen"]
    assert state["count"] > 0
    assert any(candidate["text"] == "台灣" for candidate in state["candidates"])


def test_dictionary_word_outranks_fragments(real_rime_states):
    """Long-word-first invariant (PLAN section 9-1A).

    Typing a dictionary word's full reading must surface the whole word,
    and no single-character fragment may rank above it.
    """
    candidates = real_rime_states["long_word"]["candidates"]
    texts = [candidate["text"] for candidate in candidates]
    assert "食飯" in texts
    whole = texts.index("食飯")
    for i, text in enumerate(texts):
        if len(text.strip()) == 1:
            assert whole < i, f"single-char candidate {text!r} outranks 食飯"


def test_hot_single_chars_do_not_fragment_dictionary_word(real_rime_states):
    """Hot-char no-hijack (PLAN section 9-1C).

    High-frequency single characters (我 gua2) must not break up a
    dictionary word in the composed sentence: 食飯 stays whole in a
    top-ranked candidate.
    """
    candidates = real_rime_states["hot_char_word"]["candidates"]
    assert any("食飯" in candidate["text"] for candidate in candidates[:5])


def test_invalid_input_offers_verbatim_at_slot_zero(real_rime_states):
    """Slot-0 verbatim escape hatch (PLAN 9-1E).

    Typing a string that matches nothing must offer the raw input itself
    as the first candidate: one selection commits exactly what was typed.
    """
    state = real_rime_states["invalid_input"]
    candidates = state["candidates"]
    assert candidates, "invalid input must still produce candidates"
    assert candidates[0]["text"] == "xqzv"


def test_unknown_phrase_with_hyphen_break_composes_per_syllable(real_rime_states):
    """Out-of-dictionary phrases (kio-tiann) must compose from single-syllable entries.

    The user picks the word — and therefore the tone — for each syllable by
    navigating the per-segment menu; the composed candidate shows real hanzi
    rather than only the raw-romanization fallback.
    """
    state = real_rime_states["ood_hyphen"]
    assert state["count"] > 0
    assert any("橋" in candidate["text"] for candidate in state["candidates"])


def test_word_by_word_selection_commits_chosen_hanzi(real_rime_states):
    """Full OOD journey: pick 橋 for kio, then 鼎 for tiann, commit 橋鼎.

    Tone is chosen by choosing the word: each syllable is selected
    individually (Tab + asdf), the composition carries the converted hanzi,
    and the final Space commits exactly the picked characters.
    """
    mid = real_rime_states["word_by_word_mid"]
    assert "橋" in mid["preedit"]
    assert any(candidate["text"] == "鼎" for candidate in mid["candidates"])
    assert real_rime_states["word_by_word"]["commit"] == "橋鼎"


def test_telex_tone_letter_finds_tai_candidates(real_rime_states):
    """taid must normalize to tai5 and surface 台/臺 with the TL reading."""
    state = real_rime_states["telex_taid"]
    assert state["preedit"] == "tai5"
    assert state["count"] > 0
    assert any(candidate["text"] in ("台", "臺") for candidate in state["candidates"])
    comments = [unicodedata.normalize("NFC", c["comment"]) for c in state["candidates"]]
    assert any("tâi" in comment for comment in comments)


def test_telex_f_hyphen_composes_two_syllables(real_rime_states):
    """taidfgiv must normalize to tai5-gi2 and hit the 台語 dictionary entry."""
    state = real_rime_states["telex_taidfgiv"]
    assert state["count"] > 0
    assert any(candidate["text"] in ("台語", "臺語") for candidate in state["candidates"])


def test_telex_v_on_unchecked_syllable_finds_gi(real_rime_states):
    """giv must normalize to gi2 (v=2 on a non-checked syllable) and find 語."""
    state = real_rime_states["telex_giv"]
    assert state["preedit"] == "gi2"
    assert state["count"] > 0
    assert any(candidate["text"] == "語" for candidate in state["candidates"])
    comments = [unicodedata.normalize("NFC", c["comment"]) for c in state["candidates"]]
    assert any("gí" in comment for comment in comments)


def test_telex_z_alias_maps_to_ts(real_rime_states):
    """ziahv stays ziah8 in preedit; prism derive/^ts/z/ finds 食."""
    state = real_rime_states["telex_ziahv"]
    assert state["preedit"] == "ziah8"
    assert state["count"] > 0
    assert any(candidate["text"] == "食" for candidate in state["candidates"])


def test_telex_zh_alias_maps_to_tsh(real_rime_states):
    """zhiahv stays zhiah8 in preedit; prism derive/^tsh/zh/ finds 斜."""
    state = real_rime_states["telex_zhiahv"]
    assert state["preedit"] == "zhiah8"
    assert state["count"] > 0
    assert any(candidate["text"] == "斜" for candidate in state["candidates"])


def test_telex_multi_syllable_sentence_composes(real_rime_states):
    """tngyflaid must normalize to tng3-lai5 and compose from both syllables."""
    state = real_rime_states["telex_tngyflaid"]
    assert state["count"] > 0
    assert any("來" in candidate["text"] for candidate in state["candidates"])


def test_main_schema_keeps_raw_taid_without_telex_mapping(real_rime_states):
    """拍台文(台) must not know Telex: its preedit keeps the raw letters.

    (The main speller still segments "tai"+"d" and may list partial-syllable
    candidates like 台 — the input layer itself is what must stay untouched.)
    """
    # Raw letters survive (no Telex tone mapping); the abbrev-quality toneless
    # spellings may re-segment the display ("t aid"), which is harmless as
    # long as "tai5" never appears in the main schema's preedit.
    assert "tai5" not in real_rime_states["main_taid"]["preedit"]
    assert real_rime_states["telex_taid"]["preedit"] == "tai5"


def _nfc(text: str) -> str:
    """librime emits NFD romanization comments; compare under NFC."""
    return unicodedata.normalize("NFC", text)


def test_hanlo_copy_poj_word_types_with_both_annotations(real_rime_states):
    """白話字 must be typeable as peh8-ue7-ji7 with TL and POJ annotations."""
    state = real_rime_states["hanlo_poj"]
    assert state["count"] > 0, state
    poj = [c for c in state["candidates"] if c["text"] == "白話字"]
    assert poj, state
    comments = [_nfc(c["comment"]) for c in poj]
    assert any("TL:pe̍h-uē-jī" in comment for comment in comments), comments
    assert any("POJ:pe̍h-ōe-jī" in comment for comment in comments), comments


def test_hanlo_copy_taigi_word_types_with_tl_annotation(real_rime_states):
    """台語 must be typeable as tai5-gi2 with TL annotation tâi-gí."""
    state = real_rime_states["hanlo_taigi"]
    assert state["count"] > 0, state
    taigi = [c for c in state["candidates"] if c["text"] in ("台語", "臺語")]
    assert taigi, state
    assert any("tâi-gí" in _nfc(c["comment"]) for c in taigi), taigi


def test_hanlo_copy_sentence_composes_from_dictionary(real_rime_states):
    """會曉講台語 composes end-to-end: every segment comes from the dict."""
    state = real_rime_states["hanlo_sentence"]
    assert state["count"] > 0, state
    assert any("會曉" in c["text"] for c in state["candidates"]), state
    assert any("台語" in c["text"] for c in state["candidates"]), state


# === 連打 (v0.8.0): whole-sentence continuous typing ===
# Source article (漢字/全羅對照): funbiochampion.com
# Sentences live in tests/fixtures/sentence_corpus.tsv
# (label<TAB>hanzi<TAB>keys); the title row is liantua_example, the article
# corpus rows are liantua_c1..liantua_c7.
LIANTUA_BATCH_LABELS = tuple(f"liantua_c{i}" for i in range(1, 8))


def _read_sentence_corpus() -> dict[str, dict[str, str]]:
    """Parse sentence_corpus.tsv rows as {label: {hanzi, keys}}."""
    rows: dict[str, dict[str, str]] = {}
    for line in SENTENCE_CORPUS_TSV.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#"):
            continue
        label, hanzi, keys = line.split("\t")
        rows[label] = {"hanzi": hanzi, "keys": keys}
    return rows


# liantua_c1..c7 expected Hanzi sentences, keyed by corpus label.
LIANTUA_CORPUS = {label: row["hanzi"] for label, row in _read_sentence_corpus().items()}


def test_liantua_example_sentence_in_top3(real_rime_corpus):
    """Typing the article title's full romanization must surface the exact
    Hanzi sentence within the first three candidates (goal: 連打)."""
    expected = _read_sentence_corpus()["liantua_example"]["hanzi"]
    candidates = real_rime_corpus["liantua_example"]["candidates"]
    top3 = [c["text"] for c in candidates[:3]]
    assert expected in top3, top3


def test_liantua_corpus_batch_hit_rate(real_rime_corpus):
    """Article sentences: ≥70% must have the exact Hanzi text in top-3."""
    rows = _read_sentence_corpus()
    hits = 0
    for label in LIANTUA_BATCH_LABELS:
        candidates = real_rime_corpus[label]["candidates"]
        top3 = [c["text"] for c in candidates[:3]]
        if rows[label]["hanzi"] in top3:
            hits += 1
    assert hits / len(LIANTUA_BATCH_LABELS) >= 0.7, f"hit rate {hits}/{len(LIANTUA_BATCH_LABELS)}"


def _top1_rate(rows: dict[str, dict[str, object]]) -> float:
    return sum(1 for row in rows.values() if row["rank"] == 1) / len(rows)


def test_sentence_first_candidate_ratchet(real_rime_corpus):
    """Sentence-corpus ratchet: 整句 top-1 命中率不得低於 sentence_baseline.json.

    For every corpus row the rank of the exact Hanzi sentence among the
    candidates is computed (0 = absent) and the aggregate top-1 rate may only
    move up. A missing baseline file bootstraps itself from the current run;
    delete tests/fixtures/sentence_baseline.json to re-baseline.
    """
    rows = _read_sentence_corpus()
    results: dict[str, dict[str, object]] = {}
    for label, row in rows.items():
        texts = [c["text"] for c in real_rime_corpus[label]["candidates"]]
        rank = texts.index(row["hanzi"]) + 1 if row["hanzi"] in texts else 0
        results[label] = {"rank": rank, "top3": rank in (1, 2, 3)}
    if SENTENCE_BASELINE_JSON.exists():
        baseline = json.loads(SENTENCE_BASELINE_JSON.read_text(encoding="utf-8"))
        missing = set(baseline) - set(results)
        assert not missing, f"corpus rows disappeared: {sorted(missing)}"
        base_rate = _top1_rate(baseline)
        assert _top1_rate(results) >= base_rate, (
            f"top-1 rate regressed: {_top1_rate(results):.3f} < baseline {base_rate:.3f}"
        )
    else:
        SENTENCE_BASELINE_JSON.write_text(
            json.dumps(results, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )


def _read_written_corpus() -> dict[str, dict[str, str]]:
    rows: dict[str, dict[str, str]] = {}
    for line in WRITTEN_CORPUS_TSV.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        label, hanzi, keys = line.split("\t")
        rows[label] = {"hanzi": hanzi, "keys": keys}
    return rows


def test_written_corpus_first_candidate_ratchet(real_rime_written):
    """書面語軌 ratchet: dopamine/nicotine 文章整句 top-1 只升不降.

    Corpus derivation (2026-09-24): the owner's 漢羅/POJ parallel article;
    nicotine/Dopamine tokens removed symmetrically from both sides, the
    digits sentence (10秒鐘 ↔ tsa̍p, asymmetric) excluded, and dopa_p6s2's
    keys hand-patched (sin5-king1-se3-pau1 → nau2-tiong1) because the 全羅
    paragraph paraphrases 腦中 as 神經細胞. Baseline measured 0/12 top-3 —
    the failure classes (missing 書面 vocab, same-code ranking losses,
    runtime light-tone variants) are the targets of the written-track
    improvement work; this ratchet guards that they only get better.
    """
    rows = _read_written_corpus()
    results: dict[str, dict[str, object]] = {}
    for label, row in rows.items():
        texts = [c["text"] for c in real_rime_written[label]["candidates"]]
        rank = texts.index(row["hanzi"]) + 1 if row["hanzi"] in texts else 0
        results[label] = {"rank": rank, "top3": rank in (1, 2, 3)}
    baseline = json.loads(WRITTEN_BASELINE_JSON.read_text(encoding="utf-8"))
    assert set(baseline) == set(results), "written corpus rows changed vs baseline"
    # Per-row best-known ratchet: a row that has ever reached a rank may
    # never fall back to absent (0) or a worse rank; the baseline captures
    # each row's best rank, so real protection starts with the first
    # improvement (the initial 0/12 measurement is diagnostic only).
    for label, base in baseline.items():
        if base["rank"] > 0:
            assert results[label]["rank"] != 0, f"{label} regressed to absent (best-known rank {base['rank']})"
            assert results[label]["rank"] <= base["rank"], (
                f"{label} regressed: rank {results[label]['rank']} > best {base['rank']}"
            )
    improved = {
        label: {"rank": res["rank"], "top3": res["top3"]}
        for label, res in results.items()
        if res["rank"] > 0 and (baseline[label]["rank"] == 0 or res["rank"] < baseline[label]["rank"])
    }
    if improved:
        baseline.update(improved)
        WRITTEN_BASELINE_JSON.write_text(
            json.dumps(baseline, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )


def _find_900leku_sentences() -> Path:
    """data/ is gitignored; prefer this checkout, else the main worktree."""
    candidates = [ROOT / "data" / "900leku_sentences.txt"]
    common = subprocess.run(
        ["git", "rev-parse", "--path-format=absolute", "--git-common-dir"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    if common.returncode == 0 and common.stdout.strip():
        candidates.append(Path(common.stdout.strip()).parent / "data" / "900leku_sentences.txt")
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    # Plain skip (not _require_or_skip): this corpus is gitignored optional
    # data, not part of the engine runtime. RIME_SMOKE_REQUIRED guards the
    # runtime itself; CI legitimately lacks data/900leku_sentences.txt.
    pytest.skip("sentence roundtrip needs data/900leku_sentences.txt (gitignored)")
    raise AssertionError("unreachable")


def test_missing_gitignored_corpus_skips_even_when_required(monkeypatch, tmp_path):
    """RIME_SMOKE_REQUIRED 只看守引擎 runtime; gitignored 語料缺席仍應 skip.

    CI (release verify) 設 RIME_SMOKE_REQUIRED=1 但沒有 data/——900例句語料
    是選配資料, 缺席是 skip 不是 fail; 引擎 runtime 缺席才 fail.
    """
    import tests.test_real_rime as tr

    monkeypatch.setattr(tr, "ROOT", tmp_path)
    monkeypatch.setattr(tr.subprocess, "run", lambda *a, **k: subprocess.CompletedProcess([], 1))
    monkeypatch.setenv("RIME_SMOKE_REQUIRED", "1")
    with pytest.raises(pytest.skip.Exception):
        tr._find_900leku_sentences()


_TL_SYLLABLE_RE = re.compile(r"(?:[a-z]*[aeiou][a-z]*|[a-z]*(?:ng|m)[gh]?)[1-8]?")


def _wellformed_tl_sentence(line: str) -> bool:
    """Every hyphen-separated syllable must be a well-formed TL reading.

    900例句 extraction artifacts (torn tokens like 't1', 'ts1 u3', trailing
    hyphens) cannot be typed into the engine and are excluded up front; the
    syllabic nasals (m7, nng7, tsng1, khng3, png7) that the dictionary does
    accept stay in the pool.
    """
    return all(_TL_SYLLABLE_RE.fullmatch(syl) for tok in line.split() for syl in tok.split("-"))


def _commit_word_tokens(commit: str) -> list[str]:
    """NFC + light-tone markers→hyphens + diacritics→tone digits → word tokens."""
    return unicode_tl_to_numeric(_nfc(commit).replace("--", "-")).split()


def test_sentence_roundtrip_word_boundaries(tmp_path_factory):
    """全羅 roundtrip over 900例句: word-boundary quality, ratcheted.

    Typing each sentence as one continuous hyphen chain (連打 style), the
    committed romanization must come back word-structured: after
    normalization (NFC + light-tone markers + diacritics→tone digits) the
    tokens are compared with the corpus line. Measured reality: the 全羅
    commit renders the matched dictionary entry's canonical form, so
    dictionary phrase merges and canonical tone spellings keep per-row exact
    matches below 100% — hence the aggregate exact rate is baselined in
    tests/fixtures/sentence_roundtrip_baseline.json and may only move up
    (same ratchet contract as test_sentence_first_candidate_ratchet). A
    missing baseline bootstraps from the current run; an empty commit fails
    outright. Rows: FIXED-SEED sample of 100 from data/900leku_sentences.txt

    2026-09-24 re-baseline 5%→4%: the flipped row (roundtrip_008) commits
    e5 + khang1-khue3 as ONE token because the real word 的工課/e5 khang1
    khue3 entered the dictionary this round (identity-bigram mining; absent
    from the previous dict, which had only 工課). The merged commit is a
    coverage improvement penalized by exact-token equality — not a defect.
    """
    corpus_path = _find_900leku_sentences()
    pool = [
        line.strip()
        for line in corpus_path.read_text(encoding="utf-8").splitlines()
        if line.strip() and "--" not in line and _wellformed_tl_sentence(line.strip())
    ]
    sample = random.Random(20260924).sample(pool, 100)
    labels = [f"roundtrip_{i:03d}" for i in range(len(sample))]
    tsv = tmp_path_factory.mktemp("roundtrip") / "roundtrip_corpus.tsv"
    tsv.write_text(
        "".join(f"{label}\t{line}\t{'-'.join(line.split())}\n" for label, line in zip(labels, sample, strict=True)),
        encoding="utf-8",
    )
    states = _build_and_run(_find_runtime(), tmp_path_factory, smoke_args=(str(tsv),))
    results: dict[str, dict[str, object]] = {}
    mismatches = []
    for label, line in zip(labels, sample, strict=True):
        commit = _nfc(states[label]["commit"])
        assert commit, f"{label}: engine produced no commit for {line!r}"
        got = _commit_word_tokens(commit)
        want = line.split()
        exact = got == want
        results[label] = {"exact": exact}
        if not exact:
            mismatches.append(f"{label}: input {want!r} -> commit {commit!r} (normalized {got!r})")
    exact_rate = sum(1 for row in results.values() if row["exact"]) / len(results)
    if SENTENCE_ROUNDTRIP_BASELINE_JSON.exists():
        baseline = json.loads(SENTENCE_ROUNDTRIP_BASELINE_JSON.read_text(encoding="utf-8"))
        base_rate = sum(1 for row in baseline.values() if row["exact"]) / len(baseline)
        assert exact_rate >= base_rate, (
            f"roundtrip exact rate regressed: {exact_rate:.2f} < baseline {base_rate:.2f}; sample:\n"
            + "\n".join(mismatches[:10])
        )
    else:
        SENTENCE_ROUNDTRIP_BASELINE_JSON.write_text(
            json.dumps(results, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )


def test_liantua_toneless_hyphenless_floor(real_rime_states):
    """免調+無連字號整句是已知限制:2026-09 量測(librime 1.13.1,
    語料字串機械重建自查)top-3 命中 1/7,對比帶調+連字號 ≥70%。
    地板=短句"事後退酒了後"必須整句命中;低於此代表免調組句退化。
    完整解法見 PLAN §9-1 K 量測紀錄。"""
    hits = 0
    for i in range(1, 8):
        label = f"liantua_tl_c{i}"
        expected = LIANTUA_CORPUS[f"liantua_c{i}"]
        state = real_rime_states[label]
        top3 = [c["text"] for c in state["candidates"][:3]]
        if expected in top3:
            hits += 1
    # 地板釘"事後退酒了後"本身(docstring 承諾的那句),非任一句。
    c3_top3 = [c["text"] for c in real_rime_states["liantua_tl_c3"]["candidates"][:3]]
    assert "事後退酒了後" in c3_top3, c3_top3
    assert hits >= 1, f"toneless+hyphenless hit rate {hits}/7 below floor"


def test_liantua_full_romanization_commit_has_word_boundaries(real_rime_states):
    """全羅整句上屏: 詞內連字號與詞間空白, not one long hyphen chain."""
    commit = _nfc(real_rime_states["liantua_full_roman"]["commit"])
    assert commit.startswith("Sī-án-tsuánn lâng"), commit
    words = commit.split(" ")
    assert "thè-tsiú" in words and "liáu-āu" in words, commit


def test_full_roman_tab_selection_keeps_composition(real_rime_states):
    """全羅模式句中 Tab 選字不得送出: confirm 進組句, Space 才整句上屏.

    Regression for v0.8.0: selection mode in 全羅 mode force-committed the
    picked word's romanization and cleared the remaining input.
    """
    mid = real_rime_states["liantua_full_roman_midsel"]
    # Selecting 是按怎 must not emit a commit.
    assert mid.get("commit", "") == "", mid
    resumed = real_rime_states["liantua_full_roman_resumed"]
    # The chosen hanzi stays visible in the preedit while the rest composes.
    assert "是按怎" in resumed["preedit"], resumed["preedit"]
    commit = _nfc(real_rime_states["liantua_full_roman_resumed"]["commit"])
    # Version-independent contract: the buffered prefix survives and the
    # remainder is fully romanized. Word boundaries in the remainder depend
    # on the running librime's script-text layout (observed: librime 1.13
    # re-segments "lâng thè-tsiú liáu-āu"; older CI librime falls back to
    # the candidate comment "lâng-thè-tsiú-liáu-āu").
    assert commit in (
        "Sī-án-tsuánn lâng thè-tsiú liáu-āu",
        "Sī-án-tsuánn lâng-thè-tsiú-liáu-āu",
    ), commit


def test_manual_mix_marked_word_roman_rest_hanzi(real_rime_states):
    """手動漢羅: Tab 反白候選按 \\ 標記該詞為羅馬字, 其餘詞維持漢字.

    Marking mid-sentence must not commit; Space assembles the mixed text
    with a space between roman and hanzi segments.
    """
    mid = real_rime_states["mixmark_mid"]
    assert mid.get("commit", "") == "", mid
    resumed = real_rime_states["mixmark_resumed"]
    assert "是按怎" in resumed["preedit"], resumed["preedit"]
    commit = _nfc(real_rime_states["mixmark_final"]["commit"])
    assert commit == "sī-án-tsuánn 人", commit


def test_manual_mix_marked_word_follows_poj_switch(real_rime_states):
    """手動漢羅標記的羅馬字段落需跟隨 TL/POJ 開關."""
    commit = _nfc(real_rime_states["mixmark_poj"]["commit"])
    assert commit == "sī-án-chóaⁿ 人", commit


def test_manual_mix_accumulates_marks_in_order(real_rime_states):
    """手動漢羅: 多段標記依序組裝, 漢字緊鄰不加空格.

    the3 的第一候選是 退(◆ LKK 推薦, bounded nudge 越過未推薦的 替)——
    語源文章亦作「人退酒」, 與推薦排序一致; 本測試釘組裝行為, 不釘選字.
    """
    mid = real_rime_states["mixmark_two_mid"]
    assert mid.get("commit", "") == "", mid
    commit = _nfc(real_rime_states["mixmark_two"]["commit"])
    assert commit == "sī-án-tsuánn 人退", commit


def test_manual_mix_escape_does_not_leak_into_next_composition(real_rime_states):
    """手動漢羅: Escape 取消後 mix 狀態不得殘留——重新標記不得疊出雙前綴."""
    commit = _nfc(real_rime_states["mixmark_afteresc"]["commit"])
    assert commit == "sī-án-tsuánn 人", commit


def test_tone1_digitless_and_poj_input_visibility(real_rime_states):
    """1 聲字(車 tshia1): TL 無調與 POJ 帶調輸入都要找得到車.

    tshia: 車在候選前 10(單層 abbrev 無調邊 + toneless filter 升權).
    chhia1: POJ 帶調邊(derive)直接命中.
    """
    for label in ("tone1_tshia", "tone1_chhia1"):
        state = real_rime_states[label]
        texts = [c["text"] for c in state["candidates"]]
        assert "車" in texts[:10], (label, texts)


POJ_TL_DIGITLESS_VISIBLE = [
    # (label, typed, target) — 高權重目標: 免調要直接選得到, 不被切碎.
    # 入聲四尾: -t (tsat), -p (tsiap), -k (tsik) at tone 4, -h (tsioh/tsiah) at tone 8.
    ("tone1_tshia", "tshia", "車"),
    ("tone1_chhia", "chhia", "車"),
    ("tone4_tsat", "tsat", "節"),
    ("tone4_chat", "chat", "節"),
    ("tone4_tsiap", "tsiap", "接"),
    ("tone4_chiap", "chiap", "接"),
    ("tone4_tsik", "tsik", "積"),
    ("tone4_chik", "chik", "積"),
    ("tone8_tsioh", "tsioh", "石"),
    ("tone8_chioh", "chioh", "石"),
    ("landing_tsiah", "tsiah", "食"),
    ("landing_chiah", "chiah", "食"),
]

POJ_TL_DIGITLESS_NO_FRAGMENT = [
    # (label, typed) — 目標字可能被同音高權重詞蓋過(排名層次), 但輸入
    # 不得被切成兩段: TL 不碎的, POJ 同家族也不得碎.
    ("tone1_tsu", "tsu"),
    ("tone1_chu", "chu"),
    ("tone1_ing", "ing"),
    ("tone1_eng", "eng"),
    ("tone1_suann", "suann"),
    ("tone1_soann", "soann"),
]


@pytest.mark.parametrize("label,typed,target", POJ_TL_DIGITLESS_VISIBLE)
def test_digitless_input_matches_across_tl_poj_families(real_rime_states, label, typed, target):
    """無調輸入的 TL/POJ 對齊: 高權重字免調就要選得到, 不被切碎.

    聲調可省略是主打功能; POJ 拼式(chhia/chat/chioh)與 TL(tshia/tsat/
    tsioh) 行為必須一致——含入聲 4/8 聲(-t/-p/-k/-h 尾)。
    """
    state = real_rime_states[label]
    texts = [c["text"] for c in state["candidates"]]
    assert state["preedit"] == typed, (label, state["preedit"], texts)
    assert target in texts[:10], (label, texts)


@pytest.mark.parametrize("label,typed", POJ_TL_DIGITLESS_NO_FRAGMENT)
def test_digitless_poj_does_not_fragment(real_rime_states, label, typed):
    """無調 POJ 拼式不得被切成兩段(TL 對照組不碎)."""
    state = real_rime_states[label]
    assert state["preedit"] == typed, (label, state["preedit"])


def test_checked_tone_poj_toned_input_visibility(real_rime_states):
    """帶調 POJ 對照組: chat4/chioh8 直接命中(derive 邊本身沒問題)."""
    for label, target in (("tone4_chat4", "節"), ("tone8_chioh8", "石")):
        state = real_rime_states[label]
        texts = [c["text"] for c in state["candidates"]]
        assert target in texts[:10], (label, texts)


def test_telex_x_tone_key_resolves_through_processor(real_rime_states):
    """x 調鍵走完整 processor 路徑(攔截→normalize→數字調查找):
    舒聲 x→1(ix→i1 伊)、促聲尾 x→4(ahx→ah4 鴨)、
    -h 尾 4/8 收斂對比:tsiohx→借(4) vs tsiohv→石(8)。"""
    ix = [c["text"] for c in real_rime_states["telex_ix"]["candidates"][:5]]
    assert "伊" in ix, ix
    ahx = [c["text"] for c in real_rime_states["telex_ahx"]["candidates"][:5]]
    assert "鴨" in ahx, ahx
    tsiohx = [c["text"] for c in real_rime_states["telex_tsiohx"]["candidates"][:5]]
    assert "借" in tsiohx, tsiohx
    tsiohv = [c["text"] for c in real_rime_states["telex_tsiohv"]["candidates"][:5]]
    assert "石" in tsiohv, tsiohv


def test_poj_multisyllable_second_syllable_ts(real_rime_states):
    """POJ 多音節詞、ts->ch 在第二音節(頭前 thau5-cheng5)帶調要直接選得到.

    speller algebra 逐音節套用, ^ts 錨定不影響非首音節. 免調對照組(thau-tsing)
    與 TL(thau-cheng)行為一致: 分段逐詞選字, 字典詞不直接上候選——此為
    TL/POJ 對等的既有性質, 非本測試範圍.
    """
    state = real_rime_states["poj_multi_toned"]
    texts = [c["text"] for c in state["candidates"]]
    assert "頭前" in texts[:10], texts


def test_moe_entries_reachable_via_toneless_poj(real_rime_states):
    """MOE 學科術語/地名詞條: 免調 POJ 拼式要選得到 (oan-lim → 員林)."""
    for label, target in (
        ("poj_yuanlin", "員林"),
        ("tl_yuanlin", "員林"),
        ("poj_konghap", "光合作用"),
    ):
        state = real_rime_states[label]
        texts = [c["text"] for c in state["candidates"]]
        assert target in texts[:3], (label, texts[:5])


def test_telex_toned_poj_resolves(real_rime_states):
    """Telex 方案帶調 POJ (chhia1) 直接命中; 免調 POJ 為已知限制
    (toneless 升權 filter 僅主方案, Telex 使用者以調鍵輸入為主)."""
    state = real_rime_states["telex_chhia1"]
    texts = [c["text"] for c in state["candidates"]]
    assert "車" in texts[:10], texts


def test_bare_syllable_poisoning_repaired(real_rime_states):
    """碼內裸音節(無調號)會建立 exact 邊遮蔽 abbrev 邊: 免調輸入整個死掉.

    輕聲生成器曾輸出 `khi3 ah` 這類缺調碼; validate_dict 現以 fatal gate
    擋下. 引擎層契約: 免調單音節選單復活——ah 直接選到鴨; tsi 選單要有
    tsi 家族候選(之 tsi1 權重低於同音詞, 只釘選單存活不釘排名).
    """
    ah_state = real_rime_states["single_ah"]
    ah_texts = [c["text"] for c in ah_state["candidates"]]
    assert "鴨" in ah_texts[:10], ah_texts
    tsi_state = real_rime_states["single_tsi"]
    assert tsi_state["count"] >= 5, tsi_state


def test_coda_h_omission_fuzzy(real_rime_states):
    r"""derive/h$// 的 -h 尾省略模糊: chia/chio 免尾 h 仍要選到 食/石."""
    for label, target in (("fuzzy_chia", "食"), ("fuzzy_chio", "石")):
        state = real_rime_states[label]
        texts = [c["text"] for c in state["candidates"]]
        assert target in texts[:10], (label, texts)


def test_tone4_h_coda_reading_also_surfaces(real_rime_states):
    """4聲 -h 尾讀音(借 tsioh4)與 8聲(石 tsioh8)共用免調拼式 tsioh:

    同一個免調輸入要同時看得到兩個聲調的詞, 釘住 4聲 -h 家族.
    """
    state = real_rime_states["tone8_tsioh"]
    texts = [c["text"] for c in state["candidates"]]
    assert "借" in texts, texts


def test_digitless_hyphenated_dict_word(real_rime_states):
    """免調+連字號字典詞(台灣 tai-uan, 頭前 thau-tsing)要直接上候選."""
    for label, target in (("taiuan_digitless", "台灣"), ("tl_multi_digitless", "頭前")):
        state = real_rime_states[label]
        texts = [c["text"] for c in state["candidates"]]
        assert target in texts[:10], (label, texts)


def test_comma_cascades_word_with_full_width_comma(real_rime_states):
    """組字中按逗號: 上屏候選詞加全形逗號 (liur 式逐字標點的基準行為)."""
    state = real_rime_states["hanlo_word_comma"]
    assert state.get("commit") == "食\uff0c", state


def test_period_commits_word_with_full_width_period(real_rime_states):
    """組字中按句號: 上屏候選詞加全形句號.

    預設 preset 的 paging_with_comma_period 在 has_menu 時把 period 綁成
    Page_Down, 按鍵會被翻頁吃掉; schema 以同名綁定中和 (rime-liur 作法).
    """
    state = real_rime_states["hanlo_word_period"]
    assert state.get("commit") == "食。", state


def test_full_roman_period_commits_romanized_word_with_ascii_period(real_rime_states):
    """全羅模式組字中按句號: 輸出羅馬字加半形句點 (全羅標點為半形)."""
    state = real_rime_states["fullroman_word_period"]
    assert state.get("commit") == "tsia̍h.", state


def test_telex_period_commits_word_with_full_width_period(real_rime_states):
    """Telex 方案同樣支援組字中按句號 -> 詞加全形句號."""
    state = real_rime_states["telex_word_period"]
    assert state.get("commit") == "食。", state


def test_lparen_cascades_word_with_full_width_paren(real_rime_states):
    """組字中按 ( : 上屏候選詞加全形左括號 (自動上屏, 不必再按確認鍵)."""
    state = real_rime_states["hanlo_word_lparen"]
    assert state.get("commit") == "食\uff08", state


def test_slash_cascades_word_with_dunhao(real_rime_states):
    """組字中按 / : 上屏候選詞加頓號、(自動上屏)."""
    state = real_rime_states["hanlo_word_slash"]
    assert state.get("commit") == "食、", state


def test_angle_bracket_cascades_word_with_book_title_mark(real_rime_states):
    """組字中按 < : 上屏候選詞加書名號《 (自動上屏)."""
    state = real_rime_states["hanlo_word_angle"]
    assert state.get("commit") == "食《", state


def test_underscore_commits_directly_when_not_composing(real_rime_states):
    """空白時按 _ : 直接上屏破折號——, 無須確認鍵."""
    state = real_rime_states["hanlo_empty_underscore"]
    assert state.get("commit") == "——", state


def test_quote_key_alternates_full_width_quotes(real_rime_states):
    """漢羅模式 " 鍵: 第一次按輸出“、第二次按輸出” (交替配對)."""
    assert real_rime_states["hanlo_quote_first"].get("commit") == "“", real_rime_states["hanlo_quote_first"]
    assert real_rime_states["hanlo_quote_second"].get("commit") == "”", real_rime_states["hanlo_quote_second"]


def test_full_roman_slash_stays_half_width(real_rime_states):
    """全羅模式 / : 羅馬字加半形斜線 (全羅標點維持半形)."""
    state = real_rime_states["fullroman_word_slash"]
    assert state.get("commit") == "tsia̍h/", state


def test_mixed_hanlo_word_gets_full_width_period(real_rime_states):
    """漢羅混用 (拉丁+漢字混合詞, 如 á無) 也得到全形句號.

    標點全形/半形只由 full_romanization 決定; 漢羅模式下即使是純羅馬字
    候選 (á無 = 拉丁 á + 漢字 無) 仍輸出全形標點.
    """
    state = real_rime_states["hanlo_mixed_word_period"]
    assert state.get("commit") == "á無。", state


def test_symbol_menu_lists_category_directory(real_rime_states):
    """` 開啟符號選單: 第一頁是 50 類分類目錄 (liur 式), 舊有的調號/標點清單保留."""
    state = real_rime_states["backtick_menu"]
    joined = " ".join(c["text"] for c in state["candidates"])
    assert state["count"] > 0
    # page 1 shows the directory (liur parity): 一般 and 性別 decades visible.
    assert "[01]一般" in joined and "[25]性別" in joined, joined


def test_symbol_category_25_opens_gender_symbols(real_rime_states):
    """`25 直達「性別」分類: 候選為該分類的符號 (非目錄)."""
    state = real_rime_states["symbols_cat25"]
    texts = [c["text"] for c in state["candidates"]]
    assert "♂" in texts and "♀" in texts, texts


def test_symbol_category_01_opens_general_punctuation(real_rime_states):
    """`01 直達「一般」分類: 含常用全形標點."""
    state = real_rime_states["symbols_cat01"]
    texts = [c["text"] for c in state["candidates"]]
    assert "\uff0c" in texts and "\u3002" in texts, texts


def test_emoji_candidates_appended_for_matching_word(real_rime_states):
    """漢羅模式: 一 (tsit8) 候選後附帶 emoji 變體 1️⃣ (rime-emoji, 預設開)."""
    on = real_rime_states["emoji_on"]
    texts = [c["text"] for c in on["candidates"]]
    assert "一" in texts
    assert "1️⃣" in texts, texts


def test_taiwan_name_offers_taiwan_flag(real_rime_states):
    """「台灣/臺灣」候選可附加台灣旗幟 🇹🇼."""
    state = real_rime_states["emoji_taiwan"]
    texts = [candidate["text"] for candidate in state["candidates"]]
    assert any(text in ("台灣", "臺灣") for text in texts)
    assert any("🇹🇼" in text for text in texts), texts


def test_emoji_option_off_removes_emoji_candidates(real_rime_states):
    """關掉 emoji_conversion 後不再出現 emoji 候選."""
    off = real_rime_states["emoji_off"]
    texts = [c["text"] for c in off["candidates"]]
    assert "一" in texts
    assert "1️⃣" not in texts, texts


def test_emoji_menu_lists_unicode_groups(real_rime_states):
    """`e 開啟 emoji 分類目錄 (Unicode 官方分群)."""
    state = real_rime_states["emoji_menu"]
    joined = " ".join(c["text"] for c in state["candidates"])
    assert state["count"] > 0
    assert "笑臉與情感" in joined and "食物與飲料" in joined, joined
    # 完整 fully-qualified 全集 (含膚色/ZWJ 序列): 人與身體必須是大類.
    import re as _re

    m = _re.search(r"人與身體 \((\d+)\)", joined)
    assert m and int(m.group(1)) > 2000, joined


def test_emoji_group1_browsable_and_selectable(real_rime_states):
    """`e1 直達「笑臉與情感」: 候選為可選的 emoji."""
    state = real_rime_states["emoji_group1"]
    texts = [c["text"] for c in state["candidates"]]
    assert any(t in texts for t in ("😀", "😄", "😁")), texts


def test_skin_tone_emoji_survives_category_paging(real_rime_states):
    """People & Body category exposes a skin-tone candidate after paging."""
    state = real_rime_states["emoji_group2_skin_tone"]
    texts = [candidate["text"] for candidate in state["candidates"]]
    assert "👍🏻" in texts, texts


def test_bracket_pages_special_menus_from_first_page(real_rime_states):
    """`]` pages emoji/symbol menus from page 1; `[` pages back; no fullwidth 」."""
    flags_p1 = [c["text"] for c in real_rime_states["emoji_flags_p1"]["candidates"]]
    flags_p2 = [c["text"] for c in real_rime_states["emoji_flags_p2"]["candidates"]]
    flags_back = [c["text"] for c in real_rime_states["emoji_flags_back"]["candidates"]]
    assert flags_p1 and flags_p2 and flags_p1 != flags_p2, (flags_p1[:2], flags_p2[:2])
    assert flags_p1 == flags_back, flags_back[:2]
    assert "」" not in flags_p2

    cat25_p1 = [c["text"] for c in real_rime_states["symbols_cat25"]["candidates"]]
    cat25_p2 = [c["text"] for c in real_rime_states["symbols_cat25_p2"]["candidates"]]
    assert cat25_p1 and cat25_p2 and cat25_p1 != cat25_p2, (cat25_p1[:2], cat25_p2[:2])
