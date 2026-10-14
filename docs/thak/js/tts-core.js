// 轉換頁語音的純函式（瀏覽器佮 node 測試共用）：
// 任何輸入（漢羅／TL／POJ／數字調）→ 模型字母句（POJ 調符、本調、細寫），閣編碼做模型 token。
// 模型 Meta MMS-TTS nan 的字母表是 POJ（有 c、o͘、無 z），毋認得 ⁿ 佮標點。
import { render } from "./dict.js?v=26";
import { pojToTl, tlToPoj, formatRomanization, pojFixDiacritics } from "./roman.js?v=26";

const ROMAN_CH = "A-Za-z\\u00C0-\\u024F\\u0300-\\u036f\\u0358\\u207F0-9";
const ROMAN_WORD = new RegExp(`[${ROMAN_CH}]+(?:-+[${ROMAN_CH}]+)*`, "g");
// 句界干焦句尾標點佮換行；逗號、頓號、冒號是句內停頓（短語）
const SENTENCE_END = /[。．？！；.!?;\n\r]/;
const PHRASE_BREAK = /[，、,：:]/g;
// 送模型前干焦留：字母、調符、POJ o͘ 點、ⁿ（encode 時略過）、連字號、apostrophe、空白、短語逗號
const NOT_SPEECH = /[^\p{L}\u0300-\u036f\u0358\u207F'\- ,]/gu;
// ⁿ：模型字母表無，MMS 前處理（normalize）會共伊刣掉——仝款略過，毋算 OOV
const DROPPED = new Set(["\u207F"]);

// 羅馬字段（TL／POJ／數字調混用）→ POJ 調符：逐音節處理，連字號保留
const romanToPoj = (s) => s.replace(ROMAN_WORD, (word) =>
  word.split(/-+/).map((syl) => pojFixDiacritics(formatRomanization(tlToPoj(pojToTl(syl))))).join("-"));

// 羅馬字段照句尾標點切開：標點（佮後壁的空白）綴頭前彼段
function splitRomanAtSentenceEnds(s) {
  const pieces = [];
  let cur = "";
  const chars = [...s];
  for (let i = 0; i < chars.length; i++) {
    cur += chars[i];
    if (SENTENCE_END.test(chars[i]) && !SENTENCE_END.test(chars[i + 1] ?? "")) {
      while (i + 1 < chars.length && /[ \t]/.test(chars[i + 1])) cur += chars[++i];
      pieces.push({ text: cur, ends: true });
      cur = "";
    }
  }
  if (cur) pieces.push({ text: cur, ends: false });
  return pieces;
}

// segment() 結果 → 逐句的 seg 組（句尾標點收佇該句尾）；seg 物件（含 si）照原本，picks 照用。
export function sentenceGroups(segs) {
  const groups = [];
  let cur = [];
  for (const seg of segs) {
    if (seg.t !== "r") { cur.push(seg); continue; }
    for (const piece of splitRomanAtSentenceEnds(seg.s)) {
      cur.push({ ...seg, s: piece.text });
      if (piece.ends) { groups.push(cur); cur = []; }
    }
  }
  if (cur.length) groups.push(cur);
  return groups;
}

// 逐組 render；接起來佮規篇 render 仝款（render 干焦共規篇頭一字大寫，後壁組的頭字還原）
export function renderGroups(groups, picks = new Map(), opts = {}) {
  return groups.map((g, i) => {
    const out = render(g, picks, opts);
    const first = g[0];
    const capped = i > 0 && (first.t === "w" || (first.t === "r" && /^[a-z]/.test(first.s)));
    const uncap = (s) => (capped && /^[A-Z]/.test(s) ? s[0].toLowerCase() + s.slice(1) : s);
    return { tl: uncap(out.tl), poj: uncap(out.poj) };
  });
}

// 一組 seg → 模型句（POJ 本調細寫；句內停頓寫做「, 」）；無字母就回 null
function groupToSentence(group, picks, lighttone) {
  const ready = group
    .filter((s) => s.t !== "miss")
    .map((s) => (s.t === "r" ? { ...s, s: romanToPoj(s.s) } : s));
  // 本調：模型用本調文本訓練（推論），變調交予模型家己
  const sentence = render(ready, picks, { sandhi: false, lighttone }).poj
    .normalize("NFC")
    .toLowerCase()
    .replace(PHRASE_BREAK, ",")
    .replace(NOT_SPEECH, " ")
    .replace(/\s*,[\s,]*/g, ", ")
    .replace(/\s+/g, " ")
    .replace(/^[\s,]+|[\s,]+$/g, "");
  return /\p{L}/u.test(sentence) ? sentence : null;
}

// segment() 的結果＋使用者點過的讀音（picks）→ 逐句模型字串；詞典揣無的字收入 unread。
export function speechSentences(segs, picks = new Map(), lighttone = null) {
  const unread = segs.filter((s) => s.t === "miss").map((s) => s.s);
  const sentences = sentenceGroups(segs)
    .map((g) => groupToSentence(g, picks, lighttone))
    .filter(Boolean);
  return { sentences, unread };
}

// 模型句 → 短語（句內停頓處切開，合成時中央加短停）
export function splitPhrases(sentence) {
  return sentence.split(/\s*,\s*/).filter((p) => /\p{L}/u.test(p));
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
