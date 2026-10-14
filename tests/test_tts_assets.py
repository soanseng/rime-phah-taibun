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


def test_tts_manifest_parts_reassemble_to_verified_model():
    manifest = json.loads((TTS / "manifest.json").read_text(encoding="utf-8"))
    digest = hashlib.sha256()
    total = 0
    for part in manifest["parts"]:
        data = (TTS / part["name"]).read_bytes()
        assert len(data) == part["size"], part["name"]
        digest.update(data)
        total += len(data)
    assert total == manifest["size"]
    assert digest.hexdigest() == manifest["sha256"], "合起來的模型愛佮 manifest sha256 仝款(前端會驗)"


def test_tts_parts_are_content_addressed_under_immutable_cache_path():
    manifest = json.loads((TTS / "manifest.json").read_text(encoding="utf-8"))
    for part in manifest["parts"]:
        assert part["name"].startswith("parts/"), "永久快取規則干焦對 /tts/parts/*"
        assert manifest["version"] in part["name"], "檔名愛含版本雜湊, 換模型才袂食著舊快取"
    headers = (DOCS / "_headers").read_text(encoding="utf-8")
    assert "/tts/parts/*\n  Cache-Control: public, max-age=31536000, immutable" in headers
    on_disk = {str(p.relative_to(TTS)) for p in (TTS / "parts").iterdir()}
    assert on_disk == {p["name"] for p in manifest["parts"]}, "parts/ 毋通留舊版塊"
