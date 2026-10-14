// 語音合成 worker：ONNX Runtime Web 佇遮跑，主執行緒（畫面、詞光、播放排程）袂予合成卡牢。
// 訊息：{type:"init", model: ArrayBuffer, ortBase} → {type:"ready"}｜{type:"error", message}
//       {type:"run", id, ids: number[]} → {type:"pcm", id, pcm: Float32Array}｜{type:"error", id, message}
let ort = null;
let session = null;

self.onmessage = async ({ data }) => {
  try {
    if (data.type === "init") {
      ort = await import(`${data.ortBase}ort.wasm.min.mjs`);
      ort.env.wasm.wasmPaths = data.ortBase;
      ort.env.wasm.numThreads = self.crossOriginIsolated ? Math.min(4, navigator.hardwareConcurrency || 1) : 1;
      session = await ort.InferenceSession.create(new Uint8Array(data.model), { executionProviders: ["wasm"] });
      self.postMessage({ type: "ready" });
    } else if (data.type === "run") {
      const { ids } = data;
      const { y } = await session.run({
        x: new ort.Tensor("int64", BigInt64Array.from(ids, BigInt), [1, ids.length]),
        x_length: new ort.Tensor("int64", BigInt64Array.from([BigInt(ids.length)]), [1]),
        noise_scale: new ort.Tensor("float32", Float32Array.from([0.667]), [1]),
        length_scale: new ort.Tensor("float32", Float32Array.from([1.0]), [1]),
        noise_scale_w: new ort.Tensor("float32", Float32Array.from([0.8]), [1]),
      });
      const pcm = Float32Array.from(y.data);
      self.postMessage({ type: "pcm", id: data.id, pcm }, [pcm.buffer]);
    }
  } catch (e) {
    self.postMessage({ type: "error", id: data.id, message: e?.message ?? String(e) });
  }
};
