// offscreen document ↔ service worker 橋：{to:'engine-host'} 轉做 EngineHost.call。
// offscreen 干焦有 chrome.runtime，袂使摸 storage。
(function () {
'use strict';
const api = globalThis.browser ?? globalThis.chrome;
api.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  if (!msg || msg.to !== 'engine-host') return false;
  globalThis.EngineHost.call(msg.name, ...msg.args)
    .then((result) => sendResponse({ ok: true, result }))
    .catch((e) => sendResponse({ ok: false, error: String(e?.message || e) }));
  return true; // 非同步回應
});
})();
