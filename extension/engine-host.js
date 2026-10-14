// 寫台文擴充功能：引擎宿主。Chrome 佇 offscreen.html、Firefox 佇 background.html 載入。
// RPC 佮 boot 邏輯對 docs/try/index.html（worker 佇列＋IDBFS 部署）抄來，路徑改 runtime.getURL。
(function () {
'use strict';
const api = globalThis.browser ?? globalThis.chrome;

// ---- worker RPC：回應無帶 id → 一擺干焦一个請求，照順序佇列 ----
const worker = new Worker(api.runtime.getURL('worker.js'));
let current = null;
let deployResolve = null;
let deployReject = null;
worker.onmessage = (e) => {
  const m = e.data;
  if (m.type === 'control') {
    if (m.name === 'deployStatus') {
      if (m.args[0] === 'success') deployResolve?.();
      else if (m.args[0] === 'failure') deployReject?.(new Error('字典部署失敗'));
    }
    return;
  }
  const p = current;
  current = null;
  if (!p) return;
  m.type === 'success' ? p.resolve(m.result) : p.reject(new Error(m.error?.message || m.error?.name));
};
let queue = Promise.resolve();
function rawCall(name, ...args) {
  const run = () => new Promise((resolve, reject) => {
    current = { resolve, reject };
    worker.postMessage({ name, args, transferableIndices: [] });
  });
  const result = queue.then(run);
  queue = result.catch(() => {});
  return result;
}
const FS = (op, ...args) => rawCall('fsOperate', op, ...args);

// ---- boot：比對 pack-manifest 版本 → 寫檔 → deploy ----
let bootError = null;
async function boot() {
  try {
    const { version, dir, files } = await (await fetch(api.runtime.getURL('pack-manifest.json'))).json();
    // 版本（全部資料內容雜湊）無仝 → 清掉 IndexedDB 裡的舊 /rime 再重建
    const old = await FS('readFile', '/rime/.webversion').then(
      (b) => new TextDecoder().decode(b), () => null);
    if (old !== version) {
      await rawCall('resetUserDirectory');
      const dirs = new Set();
      for (const f of files) { const d = f.split('/').slice(0, -1).join('/'); if (d) dirs.add(d); }
      for (const d of dirs) await FS('mkdir', '/rime/' + d).catch(() => {});
      for (const f of files) {
        const res = await fetch(api.runtime.getURL(`${dir}/` + encodeURIComponent(f).replace(/%2F/g, '/')));
        if (!res.ok) throw new Error(`方案檔案載入失敗：${f}`);
        const buf = new Uint8Array(await res.arrayBuffer());
        await FS('writeFile', '/rime/' + f, buf);
      }
      await FS('writeFile', '/rime/.webversion', version);
    }
    // 每擺攏 deploy：worker 未 deploy 過時 setIME 會去 CDN 揣內建方案；已有 build 時只做增量檢查
    const deployed = new Promise((res, rej) => { deployResolve = res; deployReject = rej; });
    await rawCall('deploy');
    await deployed;
  } catch (e) {
    bootError = e;
    throw e;
  }
}
const ready = boot();

globalThis.EngineHost = {
  // 對外呼叫：等 boot 了才送（boot 家己用 rawCall 插隊）
  call(name, ...args) {
    if (bootError) return Promise.reject(bootError);
    return ready.then(() => rawCall(name, ...args));
  },
};
})();
