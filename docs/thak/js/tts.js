// 轉換頁語音引擎：Meta MMS-TTS 台語模型（VITS，ONNX）佇瀏覽器本機用 ONNX Runtime Web（WASM，tts-worker.js）合成。
// 模型兩版（細版 int8 權重約 30 MB 預設、原版 fp16 權重約 58 MB），切塊放 docs/tts/parts/（Cloudflare 單檔上限
// 25 MiB）；頭一擺下載了存入 Cache Storage，後擺通常直接對快取讀。只有使用者家己開「唸予我聽」才會載。
import { encodeForModel, parseTokens, splitPhrases, wordTimeline } from "./tts-core.js?v=4";

const ORT_VERSION = "1.22.0";
const ORT_BASE = `https://cdn.jsdelivr.net/npm/onnxruntime-web@${ORT_VERSION}/dist/`;
const MODEL_BASE = new URL("../../tts/", import.meta.url);
const CACHE_NAME = "phah-tts-model";
const SENTENCE_GAP_SEC = 0.35;
const PHRASE_GAP_SEC = 0.15; // 句內逗號的短停

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
    old.then((e) => e.release()).catch(() => {});
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
  const worker = startWorker(model);
  let run;
  let tokens;
  try {
    [run, tokens] = await Promise.all([
      worker,
      fetch(new URL("tokens.txt", MODEL_BASE)).then((r) => r.text()).then(parseTokens),
    ]);
  } catch (e) {
    worker.then((w) => w.release()).catch(() => {}); // tokens 失敗：worker 已經起來嘛愛收
    throw e;
  }
  onProgress({ phase: "ready", loaded: total, total, cached });
  return { ...run, tokens, sampleRate: manifest.sampleRate };
}

// 推論放 worker（tts-worker.js）：合成的時主執行緒閒閒，畫面、詞光才袂頓。
// 回傳 { run(ids) → Promise<Float32Array>, release() }
function startWorker(model) {
  const worker = new Worker(new URL("./tts-worker.js?v=1", import.meta.url), { type: "module" });
  const pending = new Map();
  let nextId = 0;
  return new Promise((resolve, reject) => {
    worker.onerror = (e) => {
      worker.terminate();
      reject(new Error(e.message || "語音 worker 起袂來"));
    };
    worker.onmessage = ({ data }) => {
      if (data.type === "ready") {
        resolve({
          run: (ids) => new Promise((ok, fail) => {
            const id = nextId++;
            pending.set(id, { ok, fail });
            worker.postMessage({ type: "run", id, ids });
          }),
          release: () => worker.terminate(),
        });
      } else if (data.id === undefined) {
        worker.terminate();
        reject(new Error(data.message));
      } else {
        const p = pending.get(data.id);
        pending.delete(data.id);
        if (data.type === "pcm") p?.ok(data.pcm);
        else p?.fail(new Error(data.message));
      }
    };
    worker.postMessage({ type: "init", model: model.buffer, ortBase: ORT_BASE }, [model.buffer]);
  });
}

async function synthPhrase(engine, phrase) {
  const { ids } = encodeForModel(phrase, engine.tokens);
  if (ids.length < 3) return null;
  return engine.run(ids);
}

// 一句：句內停頓（逗號、頓號、冒號）切做短語分別合成，中央插短停（模型本身毋認得標點）。
// durs：逐短語的聲音長度（秒；null = 無合成），予詞光推算時間。
async function synthSentence(engine, sentence) {
  const gap = new Float32Array(Math.round(engine.sampleRate * PHRASE_GAP_SEC));
  const pieces = [];
  const durs = [];
  for (const phrase of splitPhrases(sentence)) {
    const pcm = await synthPhrase(engine, phrase);
    durs.push(pcm ? pcm.length / engine.sampleRate : null);
    if (!pcm) continue;
    if (pieces.length) pieces.push(gap);
    pieces.push(pcm);
  }
  if (!pieces.length) return null;
  const out = new Float32Array(pieces.reduce((n, p) => n + p.length, 0));
  let o = 0;
  for (const p of pieces) { out.set(p, o); o += p.length; }
  return { pcm: out, durs };
}

// 逐句合成、頭一句好就先放（後壁的句邊放邊合成）。回傳 stop()。
// onWord(句, 詞)：照聲音時鐘報這馬唸到第幾詞（推算，見 wordTimeline）；唸煞報 onWord(null)。
export function speak(engine, sentences, { onSentence = () => {}, onWord = () => {}, onDone = () => {} } = {}) {
  const ctx = new AudioContext({ sampleRate: engine.sampleRate });
  let stopped = false;
  let finished = false;
  let at = ctx.currentTime + 0.05;
  const sources = [];
  const marks = []; // { start, end, s, w }（聲音時鐘），照時間排
  let shown = null;
  let raf = 0;
  const tick = () => {
    const now = ctx.currentTime;
    const m = marks.find((x) => now >= x.start && now < x.end);
    const key = m ? `${m.s}:${m.w}` : null;
    if (key !== shown) { shown = key; onWord(m ? m.s : null, m ? m.w : null); }
    raf = requestAnimationFrame(tick);
  };
  const finish = (err) => {
    if (finished) return;
    finished = true;
    cancelAnimationFrame(raf);
    if (shown !== null) onWord(null, null);
    ctx.close().catch(() => {});
    onDone(err);
  };
  (async () => {
    for (let i = 0; i < sentences.length && !stopped; i++) {
      onSentence(i, sentences.length);
      const out = await synthSentence(engine, sentences[i]);
      if (stopped || !out) continue;
      const buf = ctx.createBuffer(1, out.pcm.length, engine.sampleRate);
      buf.copyToChannel(out.pcm, 0);
      const src = ctx.createBufferSource();
      src.buffer = buf;
      src.connect(ctx.destination);
      at = Math.max(at, ctx.currentTime + 0.02);
      src.start(at);
      wordTimeline(sentences[i], out.durs, PHRASE_GAP_SEC).forEach((t, w) => {
        if (t) marks.push({ start: at + t.start, end: at + t.end, s: i, w });
      });
      if (!raf) raf = requestAnimationFrame(tick);
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
