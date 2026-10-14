"""寫台文瀏覽器擴充功能(scripts/build_extension.py 產出)的套件檢查 + Chromium e2e。

- 靜態檢查永遠跑: manifest 指到的檔案, pack-manifest 檔案, CSP, zip 內容。
- Chromium e2e 標 e2e marker(日常 addopts 跳過), 愛 playwright:
  `uv run --with playwright pytest tests/test_browser_extension.py -v -m e2e`。
  無 playwright 套件抑是無 Chromium 執行檔就 skip。
"""

from __future__ import annotations

import http.server
import json
import tempfile
import threading
import zipfile
from pathlib import Path

import pytest

from scripts.build_extension import build_target, read_version

REPO_ROOT = Path(__file__).resolve().parents[1]
PACK = json.loads((REPO_ROOT / "docs" / "try" / "manifest.json").read_text(encoding="utf-8"))


def build_all(out: Path) -> dict[str, Path]:
    version = read_version()
    return {t: build_target(t, version, out) for t in ("chrome", "firefox")}


def manifest_paths(man: dict) -> list[str]:
    paths: list[str] = []
    for size in ("16", "48", "128"):
        paths.append(man["icons"][size])
    action = man.get("action") or man.get("browser_action")
    paths.append(action["default_popup"])
    paths.extend(action.get("default_icon", {}).values())
    if "service_worker" in man.get("background", {}):
        paths.append(man["background"]["service_worker"])
    if "page" in man.get("background", {}):
        paths.append(man["background"]["page"])
    for cs in man["content_scripts"]:
        paths.extend(cs["js"])
    return paths


@pytest.fixture(scope="module")
def built(tmp_path_factory: pytest.TempPathFactory) -> Path:
    out = tmp_path_factory.mktemp("ext")
    build_all(out)
    return out


@pytest.mark.parametrize("target", ["chrome", "firefox"])
def test_manifest_files_exist(built: Path, target: str) -> None:
    root = built / target
    man = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    version = read_version()
    assert man["version"] == version
    for rel in manifest_paths(man):
        assert (root / rel).is_file(), f"manifest 指著的 {rel} 無佇包內"


@pytest.mark.parametrize("target", ["chrome", "firefox"])
def test_no_remote_scripts(built: Path, target: str) -> None:
    for html in (built / target).rglob("*.html"):
        for line in html.read_text(encoding="utf-8").splitlines():
            if "<script" in line and "src=" in line:
                assert "http://" not in line and "https://" not in line, f"{html.name} 有遠端腳本"


@pytest.mark.parametrize("target", ["chrome", "firefox"])
def test_pack_files_and_csp(built: Path, target: str) -> None:
    root = built / target
    man = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    pack_man = json.loads((root / "pack-manifest.json").read_text(encoding="utf-8"))
    assert pack_man == PACK, "pack-manifest 愛佮 docs/try/manifest.json 仝款"
    for f in pack_man["files"]:
        assert (root / pack_man["dir"] / f).is_file(), f"pack 檔案 {f} 無佇包內"
    csp = man["content_security_policy"]
    csp = csp["extension_pages"] if isinstance(csp, dict) else csp
    assert "'wasm-unsafe-eval'" in csp
    assert "'unsafe-eval'" not in csp.replace("'wasm-unsafe-eval'", "")
    for f in ("rime.js", "rime.wasm", "rime.data", "worker.js", "LICENSE-my-rime.txt"):
        assert (root / f).is_file()


def test_firefox_gecko_id_and_exclusions(built: Path) -> None:
    man = json.loads((built / "firefox" / "manifest.json").read_text(encoding="utf-8"))
    assert man["browser_specific_settings"]["gecko"]["id"] == "phah-taibun@taigi.anatomind.com"
    assert man["manifest_version"] == 2 and man["background"]["persistent"] is True
    assert not (built / "firefox" / "offscreen.html").exists()
    chrome_man = json.loads((built / "chrome" / "manifest.json").read_text(encoding="utf-8"))
    assert chrome_man["manifest_version"] == 3
    assert not (built / "chrome" / "background.html").exists()


@pytest.mark.parametrize("target", ["chrome", "firefox"])
def test_zip_matches_dir(built: Path, target: str) -> None:
    version = read_version()
    zpath = built / f"phah-taibun-{target}-{version}.zip"
    assert zpath.is_file()
    with zipfile.ZipFile(zpath) as zf:
        names = sorted(zf.namelist())
    files = sorted(p.relative_to(built / target).as_posix() for p in (built / target).rglob("*") if p.is_file())
    assert names == files


def _serve_dir(directory: Path) -> tuple[threading.Thread, int]:
    def handler(*args, **kwargs):
        return http.server.SimpleHTTPRequestHandler(*args, directory=str(directory), **kwargs)

    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    port = server.server_address[1]
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    return t, port


@pytest.mark.e2e
def test_chromium_e2e_typing(built: Path) -> None:
    pytest.importorskip("playwright.sync_api")
    from playwright.sync_api import sync_playwright

    page_dir = Path(tempfile.mkdtemp())
    (page_dir / "index.html").write_text(
        """<!DOCTYPE html><html><body>
<textarea id="t" rows="4" cols="40"></textarea>
<div id="ce" contenteditable="true" style="width: 300px; height: 60px; border: 1px solid #999"></div>
<p id="events">0</p>
<script>
let n = 0;
for (const id of ['t', 'ce']) {
  document.getElementById(id).addEventListener('input', () => {
    n++; document.getElementById('events').textContent = String(n);
  });
}
</script>
""",
        encoding="utf-8",
    )
    _, port = _serve_dir(page_dir)
    ext = str(built / "chrome")
    with sync_playwright() as p:
        try:
            context = p.chromium.launch_persistent_context(
                tempfile.mkdtemp(),
                headless=False,
                args=["--headless=new", f"--disable-extensions-except={ext}", f"--load-extension={ext}"],
            )
        except Exception as e:
            # 干焦「瀏覽器執行檔無安裝」准 skip; manifest/載入回歸愛失敗, 袂使靜靜跳過
            if "Executable doesn't exist" in str(e):
                pytest.skip(f"Chromium 執行檔無安裝: {e}")
            raise

        try:
            # SW 起來了才有 storage: 等 service worker
            sw = None
            for _ in range(60):
                for w in context.service_workers:
                    if "background" in w.url:
                        sw = w
                        break
                if sw:
                    break
                context.wait_for_timeout(500)
            assert sw is not None, "service worker 無起來(manifest 抑是載入錯誤)"
            sw.evaluate("chrome.storage.local.set({enabled: true})")

            page = context.new_page()
            page.goto(f"http://127.0.0.1:{port}/")
            page.focus("#t")
            page.keyboard.type("chiahpng")
            # 頭一擺部署愛數十秒: 等候選面板出現(反白候選寫佇 host 的 data-phah-hl)
            # 字母是分批送的: 等 data-phah-hl 穩定(無閣變)才讀, 免得捉著半組字的中間狀態
            page.wait_for_selector(
                "#phah-taibun-panel[data-phah-hl]:not([data-phah-hl='']):not([data-phah-pending])",
                timeout=180_000,
            )
            hl = page.get_attribute("#phah-taibun-panel", "data-phah-hl")
            # 面板愛綴游標: 佇 textarea 下底附近, 袂超出版面
            box = page.locator("#phah-taibun-panel").bounding_box()
            tbox = page.locator("#t").bounding_box()
            vw, vh = page.viewport_size["width"], page.viewport_size["height"]
            assert box and tbox and box["y"] >= tbox["y"], "面板應該佇 textarea 下方附近"
            assert box["x"] >= 0 and box["y"] >= 0, f"面板超出版面: {box}"
            assert box["x"] + box["width"] <= vw and box["y"] + box["height"] <= vh, f"面板超出版面: {box}"
            page.keyboard.press(" ")
            page.wait_for_function("v => document.getElementById('t').value === v", arg=hl, timeout=10_000)
            assert "食" in hl, f"chiahpng 頭一个候選應該是食物詞, 實際: {hl}"
            events = int(page.text_content("#events") or "0")
            assert events >= 1, "插入文字了頁面愛看著 input 事件"
            # 歇睏時的標點: 逗號經過引擎變全形
            page.keyboard.type(",")
            page.wait_for_function("v => document.getElementById('t').value === v", arg=hl + "\uff0c", timeout=10_000)
            # contenteditable(GitHub 留言框這款): 仝條路愛會得出字
            page.focus("#ce")
            page.keyboard.type("taigi")
            page.wait_for_selector(
                "#phah-taibun-panel[data-phah-hl]:not([data-phah-hl='']):not([data-phah-pending])",
                timeout=30_000,
            )
            hl2 = page.get_attribute("#phah-taibun-panel", "data-phah-hl")
            assert hl2, "contenteditable 應該有反白候選"
            page.keyboard.press(" ")
            page.wait_for_function("v => document.getElementById('ce').textContent === v", arg=hl2, timeout=10_000)
        finally:
            context.close()
