// 網頁試拍「練習／考試」的純函式核心（無 DOM）：目標文字切做對位格、
// 使用者送出的文字逐格評分。TL／POJ、有調／免調、漢字／羅馬字攏當做仝音。
// 拼音轉換用讀台文（../thak）的核心，import 指定字串愛佮讀台文內底仝款（?v=24），
// 模組才袂載兩擺。
import { pojToTl, stripTones, formatRomanization, tlToPoj, pojFixDiacritics } from "../thak/js/roman.js?v=24";
import { isHan } from "../thak/js/dict.js?v=24";

// 一个音節的去調 TL 鍵：POJ 先轉 TL（pojToTl 對 TL 本身無影響），閣除調號。
// 舊式 o· 中點佮無點 ı（維基文庫 1920 年代文本）先正規化。
export const sylKey = (s) =>
  stripTones(pojToTl(s.normalize("NFC").replace(/ı/g, "i").replace(/·/g, "\u0358"))).replace(/-/g, "");

// 羅馬字詞：字母（含調符、POJ 的 o͘ 點、ⁿ、ı、舊式中點）＋連字號連接
const ROMAN_CH = "A-Za-z\\u00C0-\\u024F\\u0300-\\u036f\\u0358\\u207F\\u0131·";
const ROMAN_WORD = new RegExp(`^[${ROMAN_CH}]+(?:-+[${ROMAN_CH}]+)*`, "u");

// 文字 → 練習 token：漢字逐字 {h}、羅馬字逐音節 {k}；數字、標點、空白、其他文字略過。
export function tokenize(text) {
  const out = [];
  const s = String(text ?? "").normalize("NFC");
  let i = 0;
  while (i < s.length) {
    const ch = String.fromCodePoint(s.codePointAt(i));
    if (isHan(ch)) {
      out.push({ h: ch, src: ch });
      i += ch.length;
      continue;
    }
    const m = ROMAN_WORD.exec(s.slice(i));
    if (m) {
      for (const part of m[0].split(/-+/)) out.push({ k: sylKey(part), src: part });
      i += m[0].length;
      continue;
    }
    i += ch.length;
  }
  return out;
}

// 格（slot）：{h: 目標漢字或 null（羅馬字格）, k: 去調音節鍵或 null（讀音不明）, src: 顯示用原文}

// 漢羅句＋TL 讀音 → 逐格對位；字數佮音節數無合、或漢羅內底的羅馬字讀音佮 TL 無合 → null。
export function alignSentence(han, tl) {
  const H = tokenize(han);
  const R = tokenize(tl).filter((t) => t.k !== undefined);
  if (H.length !== R.length) return null;
  if (H.some((t, i) => t.k !== undefined && t.k !== R[i].k)) return null;
  return H.map((t, i) => ({ h: t.h ?? null, k: R[i].k, src: R[i].src }));
}

// 羅馬字文本（維基、自訂）→ 格；夾佇內底的漢字（親像括號註解）做無讀音的漢字格。
export const romanSlots = (text) =>
  tokenize(text).map((t) => (t.h ? { h: t.h, k: null, src: t.h } : { h: null, k: t.k, src: t.src }));

// 讀台文詞典 {詞: {r: ["tsit8 lui2 hue1", …]}} → 漢字 → 去調讀音集合；
// 只收字數＝音節數的讀音（逐字對位才準）。
export function buildCharKeys(dict) {
  const map = new Map();
  for (const [word, e] of Object.entries(dict)) {
    const chars = [...word];
    if (!chars.every((c) => isHan(c))) continue;
    for (const r of e.r ?? []) {
      const syls = r.split(" ").filter(Boolean);
      if (syls.length !== chars.length) continue;
      chars.forEach((c, i) => {
        let set = map.get(c);
        if (!set) map.set(c, (set = new Set()));
        set.add(sylKey(syls[i]));
      });
    }
  }
  return map;
}

// 逐格評分：漢字愛仝字（或羅馬字來源的格：charKeys 有收這字的讀音）；
// 羅馬字照去調讀音比。多拍的 token 算 extra；全對而且數量拄好才 done。
export function grade(slots, typed, charKeys = null) {
  const toks = tokenize(typed);
  const marks = [];
  for (let i = 0; i < toks.length && i < slots.length; i++) {
    const t = toks[i];
    const slot = slots[i];
    let ok;
    if (t.h !== undefined) ok = t.h === slot.h || (slot.k != null && Boolean(charKeys?.get(t.h)?.has(slot.k)));
    else ok = slot.k != null && t.k === slot.k;
    marks.push(ok ? "ok" : "bad");
  }
  const correct = marks.filter((m) => m === "ok").length;
  return {
    marks,
    extra: Math.max(0, toks.length - slots.length),
    done: toks.length === slots.length && correct === slots.length,
    correct,
  };
}

// 格的讀音顯示：TL 或 POJ（調符）；讀音不明的格回 null。
export function readingOf(slot, poj) {
  if (slot.k == null) return null;
  const tl = pojToTl(slot.src.normalize("NFC").replace(/ı/g, "i").replace(/·/g, "\u0358"));
  return (poj ? pojFixDiacritics(formatRomanization(tlToPoj(tl))) : formatRomanization(tl)).normalize("NFC");
}

const MAX_SLOTS = 30;
const slotCount = (s) => tokenize(s).length;

// 長文 → 練習句：拿掉 == 標題 == 行，照句尾標點切；超過 30 格的句閣照逗號／冒號
// 貪婪湊做 ≤30 格的段；賰無 2 格的段毋收。
export function splitSentences(text) {
  const out = [];
  for (const line of String(text ?? "").split(/\n+/)) {
    if (/^\s*=+.*=+\s*$/.test(line)) continue;
    for (const piece of line.split(/(?<=[.!?;])\s+|(?<=[。！？；])\s*/u)) {
      if (slotCount(piece) <= MAX_SLOTS) {
        out.push(piece);
        continue;
      }
      let cur = "";
      for (const clause of piece.split(/(?<=[,:])\s+|(?<=[，：])\s*/u)) {
        const next = cur ? `${cur} ${clause}` : clause;
        if (cur && slotCount(next) > MAX_SLOTS) {
          out.push(cur);
          cur = clause;
        } else cur = next;
      }
      if (cur) out.push(cur);
    }
  }
  return out.map((s) => s.trim()).filter((s) => slotCount(s) >= 2);
}
