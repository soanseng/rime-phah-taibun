"""Behavior tests that compile and exercise the real librime engine."""

from __future__ import annotations

import os
import shutil
import subprocess
import unicodedata
from dataclasses import dataclass
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[1]


@dataclass(frozen=True)
class RimeRuntime:
    prefix: Path
    include_dir: Path
    library_dir: Path
    shared_data_dir: Path
    lua_plugin: Path
    deployer: Path


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


@pytest.fixture(scope="session")
def real_rime_states(tmp_path_factory):
    runtime = _find_runtime()
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

    build_dir = user_data / "build"
    build_dir.mkdir()
    env = os.environ.copy()
    env["LD_LIBRARY_PATH"] = os.pathsep.join(
        filter(None, (str(runtime.library_dir), str(runtime.lua_plugin.parent), env.get("LD_LIBRARY_PATH")))
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
        [str(executable), str(runtime.lua_plugin), str(runtime.shared_data_dir), str(user_data)],
        check=True,
        capture_output=True,
        text=True,
        cwd=ROOT,
        env=env,
    )
    return _parse_states(result.stdout)


def test_backtick_opens_symbol_menu(real_rime_states):
    state = real_rime_states["backtick"]
    assert state["count"] > 0
    assert any(candidate["text"] != "`" for candidate in state["candidates"])


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
# 是按怎人退酒了後定定會袂記得啉酒醉的時所做的代誌
LIANTUA_TARGET = "是按怎人退酒了後定定會袂記得啉酒醉的時所做的代誌"


def test_liantua_example_sentence_in_top3(real_rime_states):
    """Typing the article title's full romanization must surface the exact
    Hanzi sentence within the first three candidates (goal: 連打)."""
    candidates = real_rime_states["liantua_example"]["candidates"]
    top3 = [c["text"] for c in candidates[:3]]
    assert LIANTUA_TARGET in top3, top3


LIANTUA_CORPUS = {
    "liantua_c1": "這主要是酒精造成的",
    "liantua_c2": "親像你家己的名、電話號碼",
    "liantua_c3": "事後退酒了後",
    "liantua_c4": "袂記得家己啉酒",
    "liantua_c5": "完全無印象",
    "liantua_c6": "人攏認為",
    "liantua_c7": "是按怎會按呢",
}


def test_liantua_corpus_batch_hit_rate(real_rime_states):
    """Article sentences: ≥70% must have the exact Hanzi text in top-3."""
    hits = 0
    for label, expected in LIANTUA_CORPUS.items():
        candidates = real_rime_states[label]["candidates"]
        top3 = [c["text"] for c in candidates[:3]]
        if expected in top3:
            hits += 1
    assert hits / len(LIANTUA_CORPUS) >= 0.7, f"hit rate {hits}/{len(LIANTUA_CORPUS)}"


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
    """手動漢羅: 多段標記依序組裝, 漢字緊鄰不加空格."""
    mid = real_rime_states["mixmark_two_mid"]
    assert mid.get("commit", "") == "", mid
    commit = _nfc(real_rime_states["mixmark_two"]["commit"])
    assert commit == "sī-án-tsuánn 人替", commit


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


@pytest.mark.xfail(
    reason="已知限制(實測): POJ 無調輸入 chhia 被引擎切成 chhi a 雙段, "
    "車 不在候選前 10; 帶調 chhia1 正常. "
    "成因推測(未單獨驗證)是單段 abbrev 邊信度懲罰輸給兩段 derive 邊的分段選擇; "
    "修復涉及分段信度語意, 另行處理."
)
def test_poj_digitless_tone1_fragments_today(real_rime_states):
    poj = real_rime_states["tone1_chhia"]
    texts = [c["text"] for c in poj["candidates"]]
    assert poj["preedit"] == "chhia", poj
    assert "車" in texts[:10], texts
