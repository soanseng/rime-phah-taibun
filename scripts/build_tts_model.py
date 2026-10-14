#!/usr/bin/env python3
"""轉換頁語音: Meta MMS-TTS 台語(nan)模型 -> docs/tts/ (fp16 權重, 切塊, 瀏覽器快取用).

來源: willwade/mms-tts-multilingual-models-onnx 的 nan/(facebook/mms-tts-nan 轉 sherpa-onnx ONNX),
授權 CC BY-NC 4.0(非商用; 寫台文網站免費非商用, 頁面有標示)。

處理:
1. 下載 (釘 revision) model.onnx + tokens.txt, 驗 sha256。
2. fp16 儲存 / fp32 計算: 大 float 權重改存 fp16, 前面加 Cast->fp32(ORT 載入時常數折疊)。
   114 MB -> 58 MB, 輸出佮 fp32 相關係數約 0.9998。直接轉 fp16 計算的模型 onnxruntime-web WASM 袂起。
3. 切塊: Cloudflare Workers 靜態資產單檔上限 25 MiB -> 每塊 <= 20 MiB。
   檔名含內容雜湊(會使永久快取); manifest.json 列塊佮全模型 sha256(前端驗證)。

需要 onnx/numpy(毋是專案依賴, 用 uv 臨時裝):
  uv run --with onnx --with 'numpy<2.4' python scripts/build_tts_model.py
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import tempfile
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = REPO_ROOT / "docs" / "tts"
SOURCE_REPO = "willwade/mms-tts-multilingual-models-onnx"
SOURCE_REV = "4f49fc254f11ddb0e35fbf25b6e48b04463a6779"
SOURCE_FILES = {
    "nan/model.onnx": "2b0e5eba284bf54cb99c7ac5c117b9a35c1f177c535d118699a9f3421391f73a",
    "nan/tokens.txt": "552c7e173ff6deb99224ab59f19feb4292d8d64c7943fe5b0eb01401688b8366",
}
CHUNK_BYTES = 20 * 1024 * 1024  # Cloudflare 靜態資產單檔上限 25 MiB, 留餘裕
FP16_MIN_ELEMENTS = 1024  # 細的權重(偏差等)保持 fp32


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def fetch_source(name: str, cache: Path) -> bytes:
    dest = cache / name.replace("/", "_")
    if not dest.is_file():
        url = f"https://huggingface.co/{SOURCE_REPO}/resolve/{SOURCE_REV}/{name}"
        with urllib.request.urlopen(url) as r, dest.open("wb") as f:
            shutil.copyfileobj(r, f)
    data = dest.read_bytes()
    if sha256(data) != SOURCE_FILES[name]:
        raise SystemExit(f"錯誤: {name} sha256 無合(來源改過?) {sha256(data)}")
    return data


def to_fp16_storage(model_bytes: bytes) -> bytes:
    import numpy as np
    import onnx
    from onnx import TensorProto, helper, numpy_helper

    m = onnx.load_from_string(model_bytes)
    g = m.graph
    inits, casts = [], []
    for init in g.initializer:
        if init.data_type == TensorProto.FLOAT and int(np.prod(init.dims)) >= FP16_MIN_ELEMENTS:
            half = numpy_helper.from_array(numpy_helper.to_array(init).astype(np.float16), init.name + "__fp16")
            inits.append(half)
            casts.append(helper.make_node("Cast", [half.name], [init.name], to=TensorProto.FLOAT))
        else:
            inits.append(init)
    del g.initializer[:]
    g.initializer.extend(inits)
    nodes = list(g.node)
    del g.node[:]
    g.node.extend(casts + nodes)
    return m.SerializeToString()


def write_chunks(model: bytes, tokens: bytes, out: Path) -> dict:
    if out.exists():
        shutil.rmtree(out)
    (out / "parts").mkdir(parents=True)
    digest = sha256(model)
    parts = []
    for i in range(0, len(model), CHUNK_BYTES):
        chunk = model[i : i + CHUNK_BYTES]
        # parts/ 底下檔名含雜湊: _headers 只對 /tts/parts/* 設永久快取 (manifest 毋通)
        name = f"parts/mms-nan-{digest[:12]}.part{len(parts)}"
        (out / name).write_bytes(chunk)
        parts.append({"name": name, "size": len(chunk)})
    (out / "tokens.txt").write_bytes(tokens)
    manifest = {
        "version": digest[:12],
        "sha256": digest,
        "size": len(model),
        "sampleRate": 16000,
        "parts": parts,
        "source": f"https://huggingface.co/{SOURCE_REPO}/tree/{SOURCE_REV}/nan",
        "license": "CC BY-NC 4.0 (Meta MMS-TTS, facebook/mms-tts-nan)",
    }
    (out / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--output", type=Path, default=OUT_DIR)
    parser.add_argument("--cache", type=Path, default=Path(tempfile.gettempdir()) / "phah-tts-cache")
    args = parser.parse_args(argv)
    args.cache.mkdir(parents=True, exist_ok=True)
    model = to_fp16_storage(fetch_source("nan/model.onnx", args.cache))
    manifest = write_chunks(model, fetch_source("nan/tokens.txt", args.cache), args.output)
    print(f"{args.output}: {manifest['size'] / 1e6:.1f} MB, {len(manifest['parts'])} 塊, version {manifest['version']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
