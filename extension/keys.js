// 寫台文擴充功能：按鍵映射佮攔截判斷（純函式，content script 佮 node 測試共用）。
// keyName 對 docs/try/index.html（my-rime 前端鍵 map）抄來，勿任意改——愛佮引擎 simulate_key_sequence 對應。
(function () {
'use strict';
const SPECIAL = {
  Escape: 'Escape', F4: 'F4', Backspace: 'BackSpace', Delete: 'Delete', Tab: 'Tab',
  Enter: 'Return', Home: 'Home', End: 'End', PageUp: 'Page_Up', PageDown: 'Page_Down',
  ArrowUp: 'Up', ArrowRight: 'Right', ArrowDown: 'Down', ArrowLeft: 'Left',
};
const SYMBOL = {
  '~': 'asciitilde', '`': 'quoteleft', '!': 'exclam', '@': 'at', '#': 'numbersign', '$': 'dollar',
  '%': 'percent', '^': 'asciicircum', '&': 'ampersand', '*': 'asterisk', '(': 'parenleft', ')': 'parenright',
  '-': 'minus', '_': 'underscore', '+': 'plus', '=': 'equal', '{': 'braceleft', '[': 'bracketleft', '}': 'braceright',
  ']': 'bracketright', ':': 'colon', ';': 'semicolon', '"': 'quotedbl', "'": 'apostrophe', '|': 'bar', '\\': 'backslash',
  '<': 'less', ',': 'comma', '>': 'greater', '.': 'period', '?': 'question', '/': 'slash', ' ': 'space',
};
// simulate_key_sequence：英數字直接送；其餘按鍵名愛用 {} 包（無包會變做逐字母輸入）
function keyName(ev) {
  if (ev.metaKey || ev.altKey) return null;
  if (ev.ctrlKey) {
    // 方案有用著的 Ctrl 組合：Ctrl+Enter 送出轉換後文字、Ctrl+Backspace 刪音節
    const ctrl = { Enter: 'Control+Return', Backspace: 'Control+BackSpace' }[ev.key];
    return ctrl ? `{${ctrl}}` : null;
  }
  if (/^[a-zA-Z0-9]$/.test(ev.key)) return ev.key;
  const name = ev.key.length === 1 ? SYMBOL[ev.key] : SPECIAL[ev.key];
  if (!name) return null;
  return ev.shiftKey && ev.key.length > 1 ? `{Shift+${name}}` : `{${name}}`;
}
function isPrintable(ev) {
  return ev.key.length === 1 && !ev.ctrlKey && !ev.metaKey && !ev.altKey;
}
// busy = 組字中（頂一擺結果有候選）抑是猶有鍵佇緩衝／處理中。
// 歇睏時：會印的字（字母、數字、空白、標點）攔起來送引擎（標點愛出全形）；
//         非印字鍵（Enter/Backspace/Tab…）留予網頁。組字中：引擎會用的鍵攏攔。
function shouldIntercept(ev, busy) {
  if (ev.isComposing) return false;
  if (keyName(ev) === null) return false;
  return busy ? true : isPrintable(ev);
}

globalThis.PhahKeys = {
  keyName,
  isPrintable,
  shouldIntercept,
  SELECT_PROMPT: /〔選字[^〕]*〕/,
  SELECT_KEYS: 'asdfghjkl;',
  UNHANDLED: 3, // api.cpp: COMMITTED, ACCEPTED, REJECTED, UNHANDLED
};
})();
