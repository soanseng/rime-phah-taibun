"""Telex input must normalize to numeric TL keys before dictionary lookup."""

import shutil
import subprocess

import pytest

LUA_EXECUTABLE = shutil.which("lua") or shutil.which("lua5.4") or shutil.which("lua5.3")

CASES = [
    ("taid", "tai5"),
    ("taiw", "tai7"),
    ("taiy", "tai3"),
    ("taiv", "tai2"),
    ("giv", "gi2"),
    ("tsiahv", "tsiah8"),
    ("ziahv", "tsiah8"),
    ("zhiahv", "tshiah8"),
    ("taidfgiv", "tai5-gi2"),
    ("taid-giv", "tai5-gi2"),
    ("taidgiv", "tai5-gi2"),
    ("tngyflaid", "tng3-lai5"),
    ("tai5-gi2", "tai5-gi2"),
    ("tai5", "tai5"),
    ("tai", "tai"),
    ("tsiah", "tsiah"),
    ("tsiah8 png7", "tsiah8 png7"),
    ("tsiahv pngw", "tsiah8 png7"),
    ("taid--giv", "tai5--gi2"),
    ("z", "ts"),
    ("zh", "tsh"),
    ("chiahv", "chiah8"),
    ("goav", "goa2"),
    ("sannv", "sann2"),
    ("kiauq", "kiau9"),
    ("vvh", "vvh"),
    ("", ""),
    ("ftai", "ftai"),
]


@pytest.fixture(scope="module")
def lua_bin():
    if not LUA_EXECUTABLE:
        pytest.skip("lua not found, skipping Telex parser tests")
    return LUA_EXECUTABLE


def run_normalize(lua_bin: str, samples: list[str]) -> list[str]:
    quoted = ", ".join('"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"' for s in samples)
    script = f"""
    package.path = "lua/?.lua;" .. package.path
    local t = require("phah_taibun_telex")
    for _, sample in ipairs({{ {quoted} }}) do
      print(t.normalize(sample))
    end
    """
    result = subprocess.run(
        [lua_bin, "-"],
        input=script,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    return result.stdout.splitlines()


def test_telex_normalizes_to_numeric_tl_keys(lua_bin):
    samples = [src for src, _ in CASES]
    expected = [dst for _, dst in CASES]
    actual = run_normalize(lua_bin, samples)
    assert actual == expected


def test_zh_is_consumed_before_z(lua_bin):
    assert run_normalize(lua_bin, ["zhiahv"]) == ["tshiah8"]
