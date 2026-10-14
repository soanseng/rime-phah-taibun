// 轉換頁語音的純函式（瀏覽器佮 node 測試共用）：
// 任何輸入（漢羅／TL／POJ／數字調）→ 模型字母句（POJ 調符、本調、細寫），閣編碼做模型 token。
// 模型 Meta MMS-TTS nan 的字母表是 POJ（有 c、o͘、無 z），毋認得 ⁿ 佮標點。
import { render } from "./dict.js?v=26";
import { pojToTl, tlToPoj, formatRomanization, pojFixDiacritics } from "./roman.js?v=26";

const ROMAN_CH = "A-Za-z\\u00C0-\\u024F\\u0300-\\u036f\\u0358\\u207F0-9";
const ROMAN_WORD = new RegExp(`[${ROMAN_CH}]+(?:-+[${ROMAN_CH}]+)*`, "g");
// 句界：全形／半形句讀、換行
const SENTENCE_BREAK = /[，。！？；：、,.!?;:\n\r]+/;
// ⁿ：模型字母表無，MMS 前處理（normalize）會共伊刣掉——仝款略過，毋算 OOV
const DROPPED = new Set(["\u207F"]);

// 羅馬字段（TL／POJ／數字調混用）→ POJ 調符：逐音節處理，連字號保留
const romanToPoj = (s) => s.replace(ROMAN_WORD, (word) =>
  word.split(/-+/).map((syl) => pojFixDiacritics(formatRomanization(tlToPoj(pojToTl(syl))))).join("-"));

// segment() 的結果＋使用者點過的讀音（picks）→ 逐句模型字串；詞典揣無的字收入 unread。
export function speechSentences(segs, picks = new Map(), lighttone = null) {
  const unread = segs.filter((s) => s.t === "miss").map((s) => s.s);
  const ready = segs
    .filter((s) => s.t !== "miss")
    .map((s) => (s.t === "r" ? { ...s, s: romanToPoj(s.s) } : s));
  // 本調：模型用本調文本訓練（推論），變調交予模型家己
  const { poj } = render(ready, picks, { sandhi: false, lighttone });
  const sentences = poj
    .normalize("NFC")
    .toLowerCase()
    .split(SENTENCE_BREAK)
    .map((s) => s.replace(/\s+/g, " ").trim())
    .filter((s) => /[a-z]/.test(s));
  return { sentences, unread };
}

// tokens.txt（「字元 id」逐行；空白字元本身嘛是一个 token）→ Map
export function parseTokens(text) {
  const map = new Map();
  for (const line of text.split("\n")) {
    if (!line) continue;
    const i = line.lastIndexOf(" ");
    map.set(line.slice(0, i), Number(line.slice(i + 1)));
  }
  return map;
}

// 句 → 模型輸入 id（add_blank：頭尾佮逐字中間插 blank 0）；認袂得的字元回報 oov
export function encodeForModel(sentence, tokens) {
  const ids = [0];
  const oov = [];
  for (const ch of sentence.normalize("NFC").toLowerCase()) {
    if (DROPPED.has(ch)) continue;
    const id = tokens.get(ch);
    if (id === undefined) oov.push(ch);
    else ids.push(id, 0);
  }
  return { ids, oov };
}
