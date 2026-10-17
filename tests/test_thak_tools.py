"""讀台文 (docs/thak) 羅→漢轉換核心的回歸斷言, 佇 monorepo 內照常會跑."""

import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_romanization_to_hanji_regression_suite_passes():
    if shutil.which("bun") is None:
        pytest.skip("bun 未安裝")
    r = subprocess.run(
        ["bun", "scripts/thak/regress-r2h.mjs"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=600,
    )
    assert r.returncode == 0, r.stdout[-2000:] + r.stderr[-2000:]
    assert "ALL PASS" in r.stdout


def test_article_official_reading_r2h_regression_passes():
    """讀文章官方讀音 (vocab + 段落 readings) 逐詞羅→漢 exact-match 未退化."""
    if shutil.which("bun") is None:
        pytest.skip("bun 未安裝")
    r = subprocess.run(
        ["bun", "scripts/thak/article-r2h.mjs"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=600,
    )
    assert r.returncode == 0, r.stdout[-2000:] + r.stderr[-2000:]
    assert "exact-match" in r.stdout
