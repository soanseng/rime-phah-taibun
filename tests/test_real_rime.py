"""Behavior tests that compile and exercise the real librime engine."""

from __future__ import annotations

import os
import shutil
import subprocess
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
    subprocess.run(
        [
            str(runtime.deployer),
            "--compile",
            str(user_data / "phah_taibun.schema.yaml"),
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
