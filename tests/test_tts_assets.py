"""轉換頁語音模型 (docs/tts/, scripts/build_tts_model.py 產生) 的部署把關.

Cloudflare Workers 靜態資產單檔上限 25 MiB: 一个檔案超過, 規个網站部署就失敗。
前端照 manifest 合塊閣驗 sha256: 塊缺、大細無合, 語音就載袂起來。
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DOCS = REPO_ROOT / "docs"
TTS = DOCS / "tts"
CLOUDFLARE_ASSET_LIMIT = 25 * 1024 * 1024


def test_every_site_asset_fits_cloudflare_limit():
    too_big = [
        str(p.relative_to(DOCS)) for p in DOCS.rglob("*") if p.is_file() and p.stat().st_size > CLOUDFLARE_ASSET_LIMIT
    ]
    assert too_big == [], f"超過 Cloudflare 25 MiB 單檔上限, 部署會失敗: {too_big}"


def load_manifest() -> dict:
    return json.loads((TTS / "manifest.json").read_text(encoding="utf-8"))


def test_default_model_is_the_small_one():
    manifest = load_manifest()
    models = manifest["models"]
    assert manifest["default"] in models
    assert models[manifest["default"]]["size"] == min(m["size"] for m in models.values()), "預設愛是上細的模型"


def test_tts_manifest_parts_reassemble_to_verified_model():
    for name, model in load_manifest()["models"].items():
        digest = hashlib.sha256()
        total = 0
        for part in model["parts"]:
            data = (TTS / part["name"]).read_bytes()
            assert len(data) == part["size"], part["name"]
            digest.update(data)
            total += len(data)
        assert total == model["size"], name
        assert digest.hexdigest() == model["sha256"], f"{name}: 合起來的模型愛佮 manifest sha256 仝款(前端會驗)"


def test_tts_parts_are_content_addressed_under_immutable_cache_path():
    models = load_manifest()["models"].values()
    for model in models:
        for part in model["parts"]:
            assert part["name"].startswith("parts/"), "永久快取規則干焦對 /tts/parts/*"
            assert model["version"] in part["name"], "檔名愛含版本雜湊, 換模型才袂食著舊快取"
    headers = (DOCS / "_headers").read_text(encoding="utf-8")
    assert "/tts/parts/*\n  Cache-Control: public, max-age=31536000, immutable" in headers
    on_disk = {str(p.relative_to(TTS)) for p in (TTS / "parts").iterdir()}
    assert on_disk == {p["name"] for m in models for p in m["parts"]}, "parts/ 毋通留舊版塊"


def test_tts_disclosure_is_readable_before_opting_in():
    """下載量/授權說明愛佇勾選進前就看會著: 毋通囥入去 #tts-panel(hidden, 勾了才出現)."""
    html = (DOCS / "convert" / "index.html").read_text(encoding="utf-8")
    about = html.index('class="tts-about"')
    panel = html.index('id="tts-panel"')
    assert about < panel, "tts-about 愛佇 tts-panel 頭前"
    panel_end = html.index("</div>", html.index('id="tts-sentences"'))
    assert not (panel < about < panel_end)
    assert "30 MB" in html[about:panel] and "CC BY-NC 4.0" in html[about:panel]
