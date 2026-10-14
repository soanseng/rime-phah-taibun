#!/usr/bin/env python3
"""轉換頁語音: Meta MMS-TTS 台語(nan)模型 -> docs/tts/ (細版 int8 權重 + 原版 fp16 權重, 切塊).

來源: willwade/mms-tts-multilingual-models-onnx 的 nan/(facebook/mms-tts-nan 轉 sherpa-onnx ONNX),
授權 CC BY-NC 4.0(非商用; 寫台文網站免費非商用, 頁面有標示)。

處理:
1. 下載 (釘 revision) model.onnx + tokens.txt, 驗 sha256。
2. 兩版, 攏是「縮細儲存 / fp32 計算」(onnxruntime-web WASM 速度佮 fp32 仝款):
   - small (預設, 約 30 MB): 大權重逐 output channel 量化做 int8, DequantizeLinear->fp32。
   - full (約 58 MB): 大權重存 fp16, Cast->fp32; 輸出佮 fp32 相關係數約 0.9998。
   MFCC+DTW 距離(VITS 有隨機性, fp32 對 fp32 本身約 22.7): small 24.9、full 25.5 攏佇自然差異內;
   動態 int8 計算(QUInt8)36.7 明顯較差閣較慢, 毋用。直接 fp16 計算 WASM 袂起。
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
VARIANTS = {"small": "int8", "full": "fp16"}  # manifest 模型名 -> 權重儲存格式


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


def compress_weights(model_bytes: bytes, kind: str) -> bytes:
    """大 float 權重改做 fp16 (kind="fp16") 抑是逐 channel int8 (kind="int8") 儲存, 圖頭插還原節點做 fp32."""
    import numpy as np
    import onnx
    from onnx import TensorProto, helper, numpy_helper

    m = onnx.load_from_string(model_bytes)
    g = m.graph
    inits, restore = [], []
    for init in g.initializer:
        if init.data_type != TensorProto.FLOAT or int(np.prod(init.dims)) < FP16_MIN_ELEMENTS:
            inits.append(init)
            continue
        w = numpy_helper.to_array(init)
        name = init.name
        if kind == "fp16":
            inits.append(numpy_helper.from_array(w.astype(np.float16), name + "__fp16"))
            restore.append(helper.make_node("Cast", [name + "__fp16"], [name], to=TensorProto.FLOAT))
            continue
        # int8: 對稱量化, 多維權重逐 output channel (axis 0), 一維整條仝一个 scale
        if w.ndim > 1:
            scale = (np.abs(w).max(axis=tuple(range(1, w.ndim))) / 127).astype(np.float32)
            scale[scale == 0] = 1.0
            q = np.round(w / scale.reshape((-1,) + (1,) * (w.ndim - 1)))
            zero = np.zeros(scale.shape, np.int8)
            attrs = {"axis": 0}
        else:
            scale = np.array(np.abs(w).max() / 127 or 1.0, np.float32)
            q = np.round(w / scale)
            zero = np.array(0, np.int8)
            attrs = {}
        inits += [
            numpy_helper.from_array(np.clip(q, -127, 127).astype(np.int8), name + "__q"),
            numpy_helper.from_array(scale, name + "__s"),
            numpy_helper.from_array(zero, name + "__z"),
        ]
        restore.append(
            helper.make_node("DequantizeLinear", [name + "__q", name + "__s", name + "__z"], [name], **attrs)
        )
    del g.initializer[:]
    g.initializer.extend(inits)
    nodes = list(g.node)
    del g.node[:]
    g.node.extend(restore + nodes)
    return m.SerializeToString()


def write_chunks(model: bytes, out: Path) -> dict:
    """模型切塊寫入 out/parts/, 回傳 manifest 的一个模型項目."""
    digest = sha256(model)
    parts = []
    for i in range(0, len(model), CHUNK_BYTES):
        chunk = model[i : i + CHUNK_BYTES]
        # parts/ 底下檔名含雜湊: _headers 只對 /tts/parts/* 設永久快取 (manifest 毋通)
        name = f"parts/mms-nan-{digest[:12]}.part{len(parts)}"
        (out / name).write_bytes(chunk)
        parts.append({"name": name, "size": len(chunk)})
    return {"version": digest[:12], "sha256": digest, "size": len(model), "parts": parts}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--output", type=Path, default=OUT_DIR)
    parser.add_argument("--cache", type=Path, default=Path(tempfile.gettempdir()) / "phah-tts-cache")
    args = parser.parse_args(argv)
    args.cache.mkdir(parents=True, exist_ok=True)
    source = fetch_source("nan/model.onnx", args.cache)
    out = args.output
    if out.exists():
        shutil.rmtree(out)
    (out / "parts").mkdir(parents=True)
    models = {name: write_chunks(compress_weights(source, kind), out) for name, kind in VARIANTS.items()}
    (out / "tokens.txt").write_bytes(fetch_source("nan/tokens.txt", args.cache))
    manifest = {
        "default": "small",
        "sampleRate": 16000,
        "models": models,
        "source": f"https://huggingface.co/{SOURCE_REPO}/tree/{SOURCE_REV}/nan",
        "license": "CC BY-NC 4.0 (Meta MMS-TTS, facebook/mms-tts-nan)",
    }
    (out / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    for name, m in models.items():
        print(f"{name}: {m['size'] / 1e6:.1f} MB, {len(m['parts'])} 塊, version {m['version']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
