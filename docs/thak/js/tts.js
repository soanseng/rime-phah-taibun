// 轉換頁語音引擎：Meta MMS-TTS 台語模型（VITS，ONNX）佇瀏覽器本機用 ONNX Runtime Web（WASM）合成。
// 模型兩版（細版 int8 權重約 30 MB 預設、原版 fp16 權重約 58 MB），切塊放 docs/tts/parts/（Cloudflare 單檔上限
// 25 MiB）；頭一擺下載了存入 Cache Storage，後擺通常直接對快取讀。只有使用者家己開「唸予我聽」才會載。
import { encodeForModel, parseTokens } from "./tts-core.js?v=1";

const ORT_VERSION = "1.22.0";
const ORT_BASE = `https://cdn.jsdelivr.net/npm/onnxruntime-web@${ORT_VERSION}/dist/`;
const MODEL_BASE = new URL("../../tts/", import.meta.url);
const CACHE_NAME = "phah-tts-model";
const SENTENCE_GAP_SEC = 0.25;

let enginePromise = null;

async function sha256Hex(buf) {
  const h = await crypto.subtle.digest("SHA-256", buf);
  return [...new Uint8Array(h)].map((b) => b.toString(16).padStart(2, "0")).join("");
}

// 一塊：先揣 Cache Storage，無才下載閣存入去
async function loadPart(cache, url, size, onBytes) {
  const hit = cache && (await cache.match(url));
  if (hit) {
    const buf = new Uint8Array(await hit.arrayBuffer());
    onBytes(buf.length);
    return buf;
  }
  const res = await fetch(url);
  if (!res.ok) throw new Error(`模型下載失敗（HTTP ${res.status}）`);
  const reader = res.body.getReader();
  const chunks = [];
  let got = 0;
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    chunks.push(value);
    got += value.length;
    onBytes(value.length);
  }
  if (got !== size) throw new Error(`模型檔大細無合（${got}／${size}）`);
  const buf = new Uint8Array(got);
  let o = 0;
  for (const c of chunks) { buf.set(c, o); o += c.length; }
  if (cache) await cache.put(url, new Response(buf)).catch(() => {}); // 空間無夠：照用，干焦無快取
  return buf;
}

// 載入引擎（single-flight，照模型版本）。variant："small"（預設）｜"full"；null＝manifest 預設。
// 換版本：放掉舊 session；快取干焦留這馬用的版本（免得兩版加起來 88 MB 佔空間）。
// onProgress({phase, loaded, total, cached})
let engineVariant = null;
export function loadEngine(variant = null, onProgress = () => {}) {
  if (enginePromise && engineVariant !== variant) {
    const old = enginePromise;
    enginePromise = null;
    old.then((e) => e.session.release?.()).catch(() => {});
  }
  if (!enginePromise) {
    engineVariant = variant;
    enginePromise = doLoad(variant, onProgress).catch((e) => { enginePromise = null; throw e; });
  }
  return enginePromise;
}

async function doLoad(variant, onProgress) {
  const manifest = await (await fetch(new URL("manifest.json", MODEL_BASE), { cache: "no-cache" })).json();
  const spec = manifest.models[variant ?? manifest.default] ?? manifest.models[manifest.default];
  const cache = "caches" in self ? await caches.open(CACHE_NAME) : null;
  // 毋是這馬版本的模型塊（舊版、抑是另一个大細）清掉，免得佔空間
  if (cache) {
    for (const req of await cache.keys()) {
      if (!spec.parts.some((p) => req.url.endsWith(p.name))) await cache.delete(req);
    }
  }
  const urls = spec.parts.map((p) => new URL(p.name, MODEL_BASE).href);
  const cached = cache ? (await Promise.all(urls.map((u) => cache.match(u)))).every(Boolean) : false;
  if (navigator.storage?.persist) navigator.storage.persist().catch(() => {});
  let loaded = 0;
  const total = spec.size;
  const bump = (n) => { loaded += n; onProgress({ phase: "model", loaded, total, cached }); };
  onProgress({ phase: "model", loaded: 0, total, cached });
  const parts = [];
  for (let i = 0; i < urls.length; i++) parts.push(await loadPart(cache, urls[i], spec.parts[i].size, bump));
  const model = new Uint8Array(total);
  let o = 0;
  for (const p of parts) { model.set(p, o); o += p.length; }
  if ((await sha256Hex(model)) !== spec.sha256) {
    if (cache) await caches.delete(CACHE_NAME);
    throw new Error("模型檔驗證失敗（已清掉快取，請閣試一擺）");
  }
  onProgress({ phase: "runtime", loaded: total, total, cached });
  const ort = await import(`${ORT_BASE}ort.wasm.min.mjs`);
  ort.env.wasm.wasmPaths = ORT_BASE;
  ort.env.wasm.numThreads = self.crossOriginIsolated ? Math.min(4, navigator.hardwareConcurrency || 1) : 1;
  const [session, tokens] = await Promise.all([
    ort.InferenceSession.create(model, { executionProviders: ["wasm"] }),
    fetch(new URL("tokens.txt", MODEL_BASE)).then((r) => r.text()).then(parseTokens),
  ]);
  onProgress({ phase: "ready", loaded: total, total, cached });
  return { ort, session, tokens, sampleRate: manifest.sampleRate };
}

async function synthSentence(engine, sentence) {
  const { ort, session, tokens } = engine;
  const { ids } = encodeForModel(sentence, tokens);
  if (ids.length < 3) return null;
  const { y } = await session.run({
    x: new ort.Tensor("int64", BigInt64Array.from(ids, BigInt), [1, ids.length]),
    x_length: new ort.Tensor("int64", BigInt64Array.from([BigInt(ids.length)]), [1]),
    noise_scale: new ort.Tensor("float32", Float32Array.from([0.667]), [1]),
    length_scale: new ort.Tensor("float32", Float32Array.from([1.0]), [1]),
    noise_scale_w: new ort.Tensor("float32", Float32Array.from([0.8]), [1]),
  });
  return y.data;
}

// 逐句合成、頭一句好就先放（後壁的句邊放邊合成）。回傳 stop()。
export function speak(engine, sentences, { onSentence = () => {}, onDone = () => {} } = {}) {
  const ctx = new AudioContext({ sampleRate: engine.sampleRate });
  let stopped = false;
  let finished = false;
  let at = ctx.currentTime + 0.05;
  const sources = [];
  const finish = (err) => {
    if (finished) return;
    finished = true;
    ctx.close().catch(() => {});
    onDone(err);
  };
  (async () => {
    for (let i = 0; i < sentences.length && !stopped; i++) {
      onSentence(i, sentences.length);
      const pcm = await synthSentence(engine, sentences[i]);
      if (stopped || !pcm) continue;
      const buf = ctx.createBuffer(1, pcm.length, engine.sampleRate);
      buf.copyToChannel(pcm, 0);
      const src = ctx.createBufferSource();
      src.buffer = buf;
      src.connect(ctx.destination);
      at = Math.max(at, ctx.currentTime + 0.02);
      src.start(at);
      at += buf.duration + SENTENCE_GAP_SEC;
      sources.push(src);
    }
    const last = sources.at(-1);
    if (!last || stopped) finish();
    else last.onended = () => finish();
  })().catch((e) => finish(e));
  return () => {
    stopped = true;
    for (const s of sources) { try { s.stop(); } catch { /* 猶未開始 */ } }
    finish();
  };
}
