// 控制器：Chrome 佇 service worker 載入（引擎走 offscreen document），
// Firefox 佇 background.html 載入（引擎佇仝一頁的 EngineHost）。
(function () {
'use strict';
const api = globalThis.browser ?? globalThis.chrome;
const localHost = Boolean(globalThis.EngineHost);
// 內容腳本會使叫的引擎函式（白名單；worker 對毋知的名字會 self.close()，千萬毋通亂轉）
const ENGINE_CALLS = new Set(['process', 'selectCandidateOnCurrentPage', 'changePage']);
const DEFAULTS = { enabled: false, scheme: 'phah_taibun', full_romanization: 0, poj_mode: 0 };

// ---- 佇列：設定切換佮逐个 process 保持 FIFO，袂使插隊 ----
let engineBusy = Promise.resolve();
function serialize(fn) {
  const run = engineBusy.then(fn, fn);
  engineBusy = run.catch(() => {});
  return run;
}

// ---- Chrome：確保 offscreen document 存在 ----
let ensureInflight = null;
function ensureOffscreen() {
  if (localHost) return Promise.resolve(false);
  if (ensureInflight) return ensureInflight;
  ensureInflight = (async () => {
    const contexts = await api.runtime.getContexts({ contextTypes: ['OFFSCREEN_DOCUMENT'] });
    if (contexts.length > 0) return false;
    await api.offscreen.createDocument({
      url: 'offscreen.html',
      reasons: ['WORKERS'],
      justification: 'Run the Rime input method engine (WebAssembly) in a Web Worker',
    });
    return true; // 新建立 → 愛重設方案佮選項
  })();
  return ensureInflight.finally(() => { ensureInflight = null; });
}

function unwrap(r) {
  if (!r || !r.ok) throw new Error(r?.error || '引擎無回應');
  return r.result;
}

async function applySettings() {
  if (!localHost) await ensureOffscreen(); // 冷啟動：先確保 offscreen 有接收端
  const s = await api.storage.local.get();
  await engineTransport('setIME', s.scheme ?? DEFAULTS.scheme);
  // 換方案會重設開關：照設定閣設一擺（setIME 了後才設選項）
  await engineTransport('setOption', 'full_romanization', s.full_romanization ?? DEFAULTS.full_romanization);
  await engineTransport('setOption', 'poj_mode', s.poj_mode ?? DEFAULTS.poj_mode);
  engineConfigured = true;
}

// 純傳輸層：無碰設定狀態（applySettings 家己用這个，袂使遞迴）
async function engineTransport(name, ...args) {
  if (localHost) return globalThis.EngineHost.call(name, ...args);
  return unwrap(await api.runtime.sendMessage({ to: 'engine-host', name, args }));
}

// 引擎設定狀態：applySettings 成功了才算有設定。Chrome 的設定住在 offscreen 內底，
// SW 歇睏醒來 flag 歸零會重設一擺（setIME 清組字）——家己癒合，贏過引擎無設定。
let engineConfigured = false;
async function engineCall(name, ...args) {
  if (localHost) {
    if (!engineConfigured) await applySettings();
    return globalThis.EngineHost.call(name, ...args);
  }
  const created = await ensureOffscreen();
  if (created || !engineConfigured) await applySettings();
  try {
    return unwrap(await api.runtime.sendMessage({ to: 'engine-host', name, args }));
  } catch {
    // offscreen 可能佇 SW 歇睏中予關掉：關掉重庫、重設方案、閣試一擺
    await api.offscreen.closeDocument().catch(() => {});
    await api.offscreen.createDocument({
      url: 'offscreen.html',
      reasons: ['WORKERS'],
      justification: 'Run the Rime input method engine (WebAssembly) in a Web Worker',
    });
    await applySettings();
    return unwrap(await api.runtime.sendMessage({ to: 'engine-host', name, args }));
  }
}

// 上佇一个用引擎的 frame（all_frames 內容腳本）：換人送鍵時先清舊組字（引擎 session 全擴充功能只有一个）
let lastFrame = null;
api.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (!msg || msg.to !== 'engine') return false;
  if (msg.name === 'ping') {
    // 毋轉送予 worker（毋知的名 → worker 自關）：暖引擎＝確保 offscreen＋設定
    serialize(async () => {
      if (!engineConfigured) await applySettings();
      else if (!localHost) await ensureOffscreen();
      sendResponse({ ok: true, result: true });
    }).catch((e) => sendResponse({ ok: false, error: String(e?.message || e) }));
    return true;
  }
  if (!ENGINE_CALLS.has(msg.name)) {
    sendResponse({ ok: false, error: `毋知的引擎呼叫：${msg.name}` });
    return false;
  }
  // 一个引擎 session 佇一擺干焦屬佇一个 frame（仝 tab 的 iframe ↔ 頂層嘛是換人）：
  // 換 owner 送鍵，先清掉舊 owner 的組字
  const frameId = sender.frameId ?? null;
  serialize(async () => {
    if (msg.name === 'process' && frameId !== null && frameId !== lastFrame) {
      if (lastFrame !== null) await engineCall('process', '{Escape}').catch(() => {});
      lastFrame = frameId;
    }
    return engineCall(msg.name, ...msg.args);
  })
    .then((result) => sendResponse({ ok: true, result }))
    .catch((e) => sendResponse({ ok: false, error: String(e?.message || e) }));
  return true;
});

// ---- 設定變動 ----
async function refreshBadge(enabled) {
  const action = api.action ?? api.browserAction;
  await action.setBadgeText({ text: enabled ? '台' : '' });
  await action.setBadgeBackgroundColor({ color: '#1a7f37' });
}

api.storage.onChanged.addListener((changes, area) => {
  if (area !== 'local') return;
  if ('enabled' in changes) refreshBadge(Boolean(changes.enabled.newValue)).catch(console.error);
  if ('scheme' in changes) {
    serialize(() => applySettings()).catch(console.error);
  }
  for (const key of ['full_romanization', 'poj_mode']) {
    if (key in changes) {
      serialize(() => engineCall('setOption', key, changes[key].newValue ?? 0)).catch(console.error);
    }
  }
});

api.commands?.onCommand.addListener(async (command) => {
  if (command !== 'toggle-ime') return;
  const { enabled } = await api.storage.local.get('enabled');
  await api.storage.local.set({ enabled: !enabled });
});

// ---- 啟動：補預設值、徽章、預熱（頭一擺安裝就開始編譯字典）----
(async () => {
  const cur = await api.storage.local.get();
  const patch = {};
  for (const [k, v] of Object.entries(DEFAULTS)) if (!(k in cur)) patch[k] = v;
  if (Object.keys(patch).length) await api.storage.local.set(patch);
  await refreshBadge(Boolean(cur.enabled ?? patch.enabled));
})().catch(console.error);

serialize(async () => {
  if (localHost) {
    if (!engineConfigured) await applySettings();
  } else {
    const created = await ensureOffscreen();
    if (created || !engineConfigured) await applySettings();
  }
}).catch((e) => console.error('寫台文：引擎預熱失敗', e));
})();
