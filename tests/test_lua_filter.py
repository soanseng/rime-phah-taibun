"""Syntax validation for Lua filter scripts.

Lua scripts run inside Rime's sandbox and can't be unit tested via pytest.
This test validates basic Lua syntax by checking with luac if available.
"""

import subprocess
from pathlib import Path

import pytest

LUA_DIR = Path(__file__).parent.parent / "lua"


def lua_files():
    """Collect all .lua files in the lua/ directory."""
    if LUA_DIR.exists():
        return list(LUA_DIR.glob("*.lua"))
    return []


@pytest.mark.parametrize("lua_file", lua_files(), ids=lambda p: p.name)
def test_lua_syntax(lua_file):
    """Validate Lua file syntax using luac (if available)."""
    for cmd in [["luac", "-p", str(lua_file)], ["lua5.3", "-e", f"loadfile('{lua_file}')"]]:
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                pytest.fail(f"Lua syntax error in {lua_file.name}:\n{result.stderr}")
            return
        except FileNotFoundError:
            continue
    pytest.skip("luac/lua not found, skipping Lua syntax check")
