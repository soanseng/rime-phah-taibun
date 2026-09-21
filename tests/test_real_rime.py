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
        library_candidates = sorted((prefix / "lib").glob("*/librime.so"))
        library_candidates += sorted((prefix / "lib").glob("librime.so"))
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
            states.setdefault(fields[1], {"preedit": "", "count": 0, "candidates": []})[
                "commit"
            ] = fields[2]
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
    assert real_rime_states["main_taid"]["preedit"] == "taid"
    assert real_rime_states["telex_taid"]["preedit"] == "tai5"
