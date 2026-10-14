// 寫台文擴充功能：內容腳本。佇 input/textarea/contenteditable 攔鍵、顯示浮動候選框、
// 揀字了插入文字。RPC 佇 controller（service worker / Firefox background page）。
// 鍵映射佮批次邏輯對 docs/try/index.html 抄來；面板 UI 對仝檔 render() 簡化。
(function () {
'use strict';
const api = globalThis.browser ?? globalThis.chrome;
const K = globalThis.PhahKeys;
const UNHANDLED = K.UNHANDLED;

// ---- 狀態 ----
let enabled = false;
let target = null;        // 這馬組字的欄位
let composing = false;    // 頂一擺結果有候選
let keyBuf = [];          // [{name, raw}] 連續印字鍵的緩衝（引擎無閒時囥等待）
let inflight = 0;

api.storage.local.get('enabled').then((s) => { enabled = Boolean(s.enabled); }).catch(console.error);
api.storage.onChanged.addListener((changes, area) => {
  if (area !== 'local' || !('enabled' in changes)) return;
  enabled = Boolean(changes.enabled.newValue);
  if (!enabled) abortComposition();
});

// ---- 逐个欄位判斷 ----
function editableTarget(ev) {
  const el = ev.composedPath?.()[0] || ev.target;
  if (!el || el.nodeType !== 1) return null;
  if (el.isContentEditable) {
    // 事件目標可能是編輯區內底的 span：揪 contenteditable 根，focus/插入才有正確對象
    const root = el.closest('[contenteditable]') || el;
    return (!root.readOnly && !root.disabled) ? root : null;
  }
  const tag = el.tagName;
  if (tag === 'TEXTAREA') return (!el.readOnly && !el.disabled) ? el : null;
  if (tag === 'INPUT') {
    const type = (el.type || 'text').toLowerCase();
    if (!['text', 'search', 'url', 'email', 'tel'].includes(type)) return null;
    return (!el.readOnly && !el.disabled) ? el : null;
  }
  return null;
}

// ---- 插入文字：先 execCommand（會生出 input 事件，framework 看會著），fallback setRangeText ----
function insertText(text) {
  if (!text || !target) return;
  if (document.activeElement !== target) target.focus();
  let ok = false;
  try { ok = document.execCommand('insertText', false, text); } catch { ok = false; }
  if (!ok && (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA')) {
    const s = target.selectionStart ?? target.value.length;
    const e = target.selectionEnd ?? s;
    target.setRangeText(text, s, e, 'end');
    target.dispatchEvent(new InputEvent('input', { bubbles: true, inputType: 'insertText', data: text }));
  }
}

// ---- 面板（closed shadow root）----
let host = null, shadow = null, els = null, noticeTimer = null;
const STYLE = `
* { box-sizing: border-box; margin: 0; padding: 0; }
:host { all: initial; }
.panel {
  /* host 是 position:fixed 的定位框（placePanel 共伊設 left/top）；面板本體按 normal flow */
  min-width: 180px; max-width: 460px;
  border-radius: 10px; padding: 6px 8px;
  font-family: "Iansui", "PingFang TC", "Noto Sans TC", "Microsoft JhengHei", sans-serif;
  font-size: 14px; line-height: 1.5;
  color: #1f2328; background: rgba(255, 255, 255, 0.98);
  border: 1px solid rgba(0, 0, 0, 0.18);
  box-shadow: 0 6px 24px rgba(0, 0, 0, 0.18);
}
@media (prefers-color-scheme: dark) {
  .panel { color: #e6e6e6; background: rgba(34, 37, 42, 0.98); border-color: rgba(255, 255, 255, 0.18); }
}
.panel[hidden] { display: none; }
.preedit { padding: 2px 4px; }
.preedit .sel { background: #d0e4ff; border-radius: 3px; }
@media (prefers-color-scheme: dark) { .preedit .sel { background: #2c4a75; } }
.cands { display: grid; grid-template-columns: 1fr; gap: 1px 10px; margin-top: 4px; }
.cands.two-col { grid-template-columns: 1fr 1fr; }
.cand { display: flex; gap: 6px; padding: 2px 4px; border-radius: 4px; cursor: pointer; }
.cand.hl { background: #d0e4ff; }
@media (prefers-color-scheme: dark) { .cand.hl { background: #2c4a75; } }
.cand .k { color: #1a7f37; min-width: 1em; }
.cand .t { white-space: nowrap; }
.cand .c { color: #8b949e; font-size: 12px; margin-left: auto; padding-left: 8px; }
.foot { display: flex; gap: 8px; align-items: center; margin-top: 4px; font-size: 12px; color: #8b949e; }
.foot .tip { flex: 1; }
.foot button { border: 1px solid rgba(127, 127, 127, 0.4); background: transparent; color: inherit;
  border-radius: 4px; padding: 0 6px; cursor: pointer; font: inherit; }
.foot button:disabled { opacity: 0.4; cursor: default; }
.loading { padding: 4px; color: #8b949e; }
`;

function ensurePanel() {
  if (host) return;
  host = document.createElement('div');
  host.id = 'phah-taibun-panel';
  host.style.position = 'fixed';
  host.style.zIndex = '2147483647';
  host.style.top = '-10000px'; // 未有位置進前毋通出現佇畫面頂
  shadow = host.attachShadow({ mode: 'closed' });
  const style = document.createElement('style');
  style.textContent = STYLE;
  const panel = document.createElement('div');
  panel.className = 'panel';
  panel.hidden = true;
  const preedit = document.createElement('div'); preedit.className = 'preedit';
  const cands = document.createElement('div'); cands.className = 'cands';
  const foot = document.createElement('div'); foot.className = 'foot';
  const mode = document.createElement('span');
  const tip = document.createElement('span'); tip.className = 'tip';
  const prev = document.createElement('button'); prev.textContent = '‹';
  const pgno = document.createElement('span');
  const next = document.createElement('button'); next.textContent = '›';
  foot.append(mode, tip, prev, pgno, next);
  panel.append(preedit, cands, foot);
  shadow.append(style, panel);
  (document.documentElement || document.body).append(host);
  els = { panel, preedit, cands, foot, mode, tip, prev, next, pgno };
  prev.onclick = () => { focusTarget(); callEngine('changePage', true).then(render, engineError); };
  next.onclick = () => { focusTarget(); callEngine('changePage', false).then(render, engineError); };
}

function focusTarget() { if (target && document.activeElement !== target) target.focus(); }

function hidePanel() {
  if (!host) return;
  els.panel.hidden = true;
  host.removeAttribute('data-phah-hl');
  clearTimeout(noticeTimer);
}

function showLoadingNotice() {
  ensurePanel();
  clearTimeout(noticeTimer);
  noticeTimer = setTimeout(() => {
    if (inflight === 0) return;
    els.panel.hidden = false;
    els.preedit.replaceChildren();
    els.cands.replaceChildren();
    els.foot.replaceChildren();
    const el = document.createElement('div');
    el.className = 'loading';
    el.textContent = '寫台文：字典準備中（第一擺約數十秒）…';
    els.panel.append(el);
    placePanel();
  }, 300);
}

// line-height "normal"（大多數頁面）parseFloat 會變 NaN → 用 font-size × 1.2 頂替
const lineHeightOf = (cs) => {
  const n = parseFloat(cs.lineHeight);
  return Number.isNaN(n) ? parseFloat(cs.fontSize) * 1.2 : n;
};
function caretRect(el) {
  if (el.isContentEditable) {
    const sel = getSelection();
    if (sel && sel.rangeCount > 0) {
      const r = sel.getRangeAt(0).getBoundingClientRect();
      if (r && (r.top || r.left || r.width || r.height)) return { left: r.left, bottom: r.bottom, top: r.top };
    }
    const b = el.getBoundingClientRect();
    return { left: b.left, bottom: b.bottom, top: b.top };
  }
  const b = el.getBoundingClientRect();
  const pos = el.selectionStart ?? 0;
  const cs = getComputedStyle(el);
  if (el.tagName === 'TEXTAREA') return textareaCaret(el, cs, b, pos);
  // input：單行，用 canvas 量文字闊
  const canvas = document.createElement('canvas').getContext('2d');
  canvas.font = `${cs.fontStyle} ${cs.fontWeight} ${cs.fontSize} ${cs.fontFamily}`;
  const x = canvas.measureText(el.value.slice(0, pos)).width;
  const padL = parseFloat(cs.paddingLeft) || 0, padT = parseFloat(cs.paddingTop) || 0;
  return {
    left: b.left + padL + Math.min(x, el.clientWidth) - el.scrollLeft,
    bottom: b.top + padT + lineHeightOf(cs) - el.scrollTop,
    top: b.top,
  };
}

function textareaCaret(el, cs, b, pos) {
  const mirror = document.createElement('div');
  for (const p of ['fontFamily', 'fontSize', 'fontWeight', 'fontStyle', 'letterSpacing',
    'textTransform', 'wordSpacing', 'textIndent', 'boxSizing', 'width', 'paddingTop',
    'paddingRight', 'paddingBottom', 'paddingLeft', 'borderTopWidth', 'borderRightWidth',
    'borderBottomWidth', 'borderLeftWidth', 'whiteSpace', 'lineHeight']) {
    mirror.style[p] = cs[p];
  }
  mirror.style.position = 'absolute';
  mirror.style.visibility = 'hidden';
  mirror.style.left = '-9999px';
  mirror.style.top = '0';
  mirror.style.height = 'auto';
  mirror.style.overflow = 'hidden';
  mirror.style.whiteSpace = 'pre-wrap';
  mirror.style.wordBreak = cs.wordBreak;
  mirror.textContent = el.value.slice(0, pos);
  const marker = document.createElement('span');
  marker.textContent = '\u200b';
  mirror.append(marker);
  (document.body || document.documentElement).append(mirror);
  const rect = {
    left: b.left + marker.offsetLeft - el.scrollLeft,
    bottom: b.top + marker.offsetTop - el.scrollTop + lineHeightOf(cs),
    top: b.top,
  };
  mirror.remove();
  return rect;
}

function placePanel() {
  if (!host || els.panel.hidden || !target) return;
  const c = caretRect(target);
  const w = host.offsetWidth || 220, h = host.offsetHeight || 120;
  const vw = window.innerWidth, vh = window.innerHeight, M = 8;
  let left = Math.min(Math.max(c.left, M), vw - w - M);
  let top = c.bottom + 4;
  if (top + h > vh - M) top = Math.max(c.top - h - 4, M); // 下底放袂落就翻頂面
  host.style.left = `${Math.round(left)}px`;
  host.style.top = `${Math.round(top)}px`;
}

// ---- render：結果 → 面板（對 docs/try/index.html render() 簡化）；逐擺攏回傳結果 ----
function render(r) {
  if (typeof r === 'string') r = JSON.parse(r); // selectCandidateOnCurrentPage/changePage 回傳未 parse 的 JSON
  if (!target) { hidePanel(); return r; } // 中斷了（blur／關掉）的殘留結果：干焦藏面板
  clearTimeout(noticeTimer);
  syncPending();
  if ('committed' in r && r.committed) insertText(r.committed);
  composing = Boolean(r.candidates);
  if (!composing) { hidePanel(); return r; }
  ensurePanel();
  // loading notice 鬥的節點清掉，還原面板結構
  if (!els.cands.isConnected) {
    els.panel.replaceChildren(els.preedit, els.cands, els.foot);
  }
  const selecting = K.SELECT_PROMPT.test((r.head || '') + (r.body || '') + (r.tail || ''));
  const strip = (s) => (s || '').replace(K.SELECT_PROMPT, '');
  const h = document.createElement('span'); h.textContent = strip(r.head);
  const b = document.createElement('span'); b.textContent = strip(r.body);
  const t = document.createElement('span'); t.textContent = strip(r.tail);
  els.preedit.replaceChildren(h, b, t);
  els.mode.textContent = selecting ? '選字模式' : '候選';
  els.tip.textContent = selecting ? '按候選頭前的鍵揀字，Esc 退出' : '空白鍵送出反白，Tab 揀別个';
  const page = r.page ?? 0;
  els.pgno.textContent = `第 ${page + 1} 頁`;
  els.prev.disabled = page === 0;
  els.next.disabled = Boolean(r.isLastPage);
  els.cands.classList.toggle('two-col', r.candidates.length > 5);
  els.cands.replaceChildren(...r.candidates.map((c, i) => {
    const el = document.createElement('div');
    el.className = 'cand' + (i === r.highlighted ? ' hl' : '');
    const k = document.createElement('span'); k.className = 'k';
    k.textContent = selecting ? K.SELECT_KEYS[i] ?? '' : (i === r.highlighted ? '␣' : '');
    const tx = document.createElement('span'); tx.className = 't'; tx.textContent = c.text;
    el.append(k, tx);
    if (c.comment) {
      const cc = document.createElement('span'); cc.className = 'c'; cc.textContent = c.comment.trim();
      el.append(cc);
    }
    // mousedown 取消 default：焦點袂走，選字了 keep 佇欄位
    el.addEventListener('mousedown', (ev) => ev.preventDefault());
    el.addEventListener('click', () => { focusTarget(); callEngine('selectCandidateOnCurrentPage', i).then(render, engineError); });
    return el;
  }));
  els.panel.hidden = false;
  // 測試／除錯 hook：封閉 shadow 外底看會著反白候選
  const hlText = r.candidates[r.highlighted]?.text ?? '';
  host.setAttribute('data-phah-hl', hlText);
  placePanel();
  return r;
}

// ---- 引擎 RPC ----
function callEngine(name, ...args) {
  return api.runtime.sendMessage({ to: 'engine', name, args }).then((r) => {
    if (!r || !r.ok) throw new Error(r?.error || '引擎無回應');
    return r.result;
  });
}

// 測試 hook：猶有鍵佇處理／緩衝 → host 標 data-phah-pending（e2e 等完全穩定才讀候選）
function syncPending() {
  if (!host) return;
  if (inflight > 0 || keyBuf.length > 0) host.setAttribute('data-phah-pending', '1');
  else host.removeAttribute('data-phah-pending');
}

function send(keys, onUnhandled) {
  inflight++;
  syncPending();
  showLoadingNotice();
  callEngine('process', keys)
    .then((r) => { if (render(r).state === UNHANDLED && onUnhandled) onUnhandled(); }, engineError)
    .finally(() => { inflight--; if (inflight === 0) sendBuf(); syncPending(); });
}

function engineError(e) {
  clearTimeout(noticeTimer);
  composing = false;
  keyBuf = [];
  ensurePanel();
  if (!els.cands.isConnected) els.panel.replaceChildren(els.preedit, els.cands, els.foot);
  els.preedit.replaceChildren();
  els.cands.replaceChildren();
  els.foot.replaceChildren();
  const el = document.createElement('div');
  el.className = 'loading';
  el.textContent = `寫台文引擎錯誤：${e?.message || e}`;
  els.panel.append(el);
  els.panel.hidden = false;
  placePanel();
  console.error('寫台文：', e);
}

function sendBuf() {
  if (!keyBuf.length) return;
  const keys = keyBuf.map((p) => p.name).join('');
  const raws = keyBuf.map((p) => p.raw).join('');
  keyBuf = [];
  send(keys, () => insertText(raws));
}

// ---- 鍵盤攔截 ----
window.addEventListener('keydown', (ev) => {
  if (!enabled || ev.defaultPrevented) return;
  const el = editableTarget(ev);
  if (!el) return;
  const busy = composing || keyBuf.length > 0 || inflight > 0;
  const name = K.keyName(ev);
  if (!K.shouldIntercept(ev, busy)) return;
  ev.preventDefault();
  ev.stopImmediatePropagation();
  target = el;
  if (name.length === 1) {
    keyBuf.push({ name, raw: ev.key });
    if (inflight === 0) sendBuf();
    return;
  }
  sendBuf();
  send(name, () => {
    // 引擎無處理的特殊鍵：Backspace 補刪一个字，其餘（罕有，組字變化中的競爭）放棄
    if (ev.key === 'Backspace') {
      if (document.activeElement !== target) target.focus();
      try { document.execCommand('delete'); } catch { /* 嘸通做 */ }
    }
  });
}, true);

// ---- 共用引擎衛生：組字毋通跨欄位／跨 tab 殼留 ----
function abortComposition() {
  keyBuf = [];
  syncPending();
  target = null;
  // inflight > 0 時 composing 可能猶未反映出來：結果會予 render 的 target guard 棄掉，
  // 毋過引擎組字猶佇 —— Escape 佇 controller FIFO 排佇 in-flight 後壁，一定清會著
  if (composing || inflight > 0) {
    composing = false;
    callEngine('process', '{Escape}').catch(() => {});
  }
  hidePanel();
}

window.addEventListener('blur', abortComposition);
document.addEventListener('visibilitychange', () => { if (document.hidden) abortComposition(); });
document.addEventListener('focusout', (ev) => {
  if (target && ev.target === target) abortComposition();
});
})();
