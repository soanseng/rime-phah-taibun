"""網頁試拍練習 (docs/try/practice-*.js) 的純函式測試, 用 node:test 跑."""

import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_practice_js_suites():
    if shutil.which("node") is None:
        pytest.skip("node 未安裝")
    r = subprocess.run(
        ["node", "--test", "tests/js/*.test.mjs"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert r.returncode == 0, r.stdout[-4000:] + r.stderr[-2000:]
