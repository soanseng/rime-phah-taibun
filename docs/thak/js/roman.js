// TL/POJ romanization core.
// Ported from rime-phah-taibun/scripts/tl_poj_convert.py
// (tl_to_poj / poj_to_tl / poj_diacritics_to_tone_numbers) and
// lua/phah_taibun_data.lua (add_tone_to_syllable / format_romanization /
// poj_fix_diacritics). Keep 1:1 with upstream logic; do not simplify.

const TONE_MARKS = {
  "2": "\u0301", "3": "\u0300", "5": "\u0302",
  "7": "\u0304", "8": "\u030D", "9": "\u0306",
};

// 教育部台羅 tone mark placement (Lua add_tone_to_syllable):
//   priority a > oo > e > o; ere marks the 2nd e;
//   iu/ui mark the 2nd vowel (main vowel); syllabic nn̄g marks the 2nd n;
//   tone 1/4: strip the digit only.
export function addToneToSyllable(syl) {
  const tone = syl.slice(-1);
  if (!/[1-9]/.test(tone)) return syl;
  const base = syl.slice(0, -1);
  const mark = TONE_MARKS[tone];
  if (!mark) return base;
  let pos = base.indexOf("oo");
  if (pos < 0) pos = base.indexOf("a");
  if (pos < 0) {
    const ere = base.indexOf("ere");
    pos = ere >= 0 ? ere + 2 : base.indexOf("e");
  }
  if (pos < 0) pos = base.indexOf("o");
  if (pos < 0) {
    const pi = base.indexOf("i");
    const pu = base.indexOf("u");
    pos = pi >= 0 && pu >= 0 ? Math.max(pi, pu) : pi >= 0 ? pi : pu;
  }
  if (pos < 0) {
    // 韻化輔音：標 ng 的 n（mn̂g、nn̄g、n̂g）；乾若 m 標 m（m̄）
    const ng = base.indexOf("ng");
    pos = ng >= 0 ? ng : base.search(/[mn]/);
  }
  return pos < 0 ? base : base.slice(0, pos + 1) + mark + base.slice(pos + 1);
}

// ---------- 連續變調（主流腔，詞內近似）----------
// 舒聲：1→7、2→1、3→2、5→7、7→3
// 入聲 p/t/k 尾：4↔8；h 尾：4→2、8→3；尾音節不變。
const SANDHI_PLAIN = { "1": "7", "2": "1", "3": "2", "5": "7", "7": "3" };
const SANDHI_PTK = { "4": "8", "8": "4" };
const SANDHI_H = { "4": "2", "8": "3" };

export function sandhiSyllable(syl) {
  const tone = syl.match(/[1-9]$/)?.[0];
  if (!tone) return syl;
  const base = syl.slice(0, -1);
  let next;
  if (/[ptk]$/.test(base)) next = SANDHI_PTK[tone];
  else if (/h$/.test(base)) next = SANDHI_H[tone];
  else next = SANDHI_PLAIN[tone];
  return next ? base + next : syl;
}

// 詞內連讀：非尾音節變調、尾音節本調（詞組/句尾規則未做，屬近似）。
export function sandhiNumeric(numeric) {
  const groups = numeric.split("--");
  return groups
    .map((g) => {
      const syl = g.split(/\s+/).filter(Boolean);
      return syl
        .map((s, k) => (k === syl.length - 1 ? s : sandhiSyllable(s)))
        .join(" ");
    })
    .join("--");
}

// 句內連讀：非句尾詞的所有音節（輕聲 -- 後音節除外）皆變調。
export function sandhiWordAll(numeric) {
  return numeric
    .split("--")
    .map((g, k) =>
      k === 0 ? g.split(/\s+/).filter(Boolean).map(sandhiSyllable).join(" ") : g)
    .join("--");
}

// "kin1 a2 jit8" → "kin-á-ji̍t"; "--" light-tone groups preserved.
export function formatRomanization(roman) {
  if (!roman) return roman;
  return roman
    .split("--")
    .map((g) => g.split(/\s+/).filter(Boolean).map(addToneToSyllable).join("-"))
    .join("--");
}

// Shared diacritics→tone-number pass over hyphen/space separated groups.
function diacriticsToNumbers(text) {
  return text
    .replace(/\u3000/g, " ")
    .split(/([-\s]+)/)
    .map((part) => {
      if (!part || /^[-\s]+$/.test(part)) return part;
      let tone = "";
      const chars = [];
      for (const ch of part.normalize("NFD")) {
        if (COMBINING_TONE_TO_NUMBER[ch]) tone = COMBINING_TONE_TO_NUMBER[ch];
        else chars.push(ch);
      }
      let base = chars.join("").normalize("NFC").replace(/\u0131/g, "i").toLowerCase();
      if (tone && !/[1-9]$/.test(base)) {
        // 調號數字愛黏音節：尾隨標點（"ê,"→"e5,"）先剝起，綴尾閣接轉去。
        const tail = base.match(/[^\p{L}\p{M}]*$/u)[0];
        base = base.slice(0, base.length - tail.length) + tone + tail;
      }
      return base;
    })
    .join("");
}

const COMBINING_TONE_TO_NUMBER = {
  "\u0301": "2", "\u0300": "3", "\u0302": "5",
  "\u0304": "7", "\u030D": "8", "\u030B": "9", "\u0306": "9",
};

// Any TL/POJ typing (diacritic, numeric, toneless) → numeric TL syllables.
// Port of unicode_tones_to_numeric: ⁿ→nn, o͘→oo, ı→i. No spelling conversion.
export function toNumeric(text) {
  if (!text) return text;
  return diacriticsToNumbers(
    text.replace(/\u207f/g, "nn").replace(/o\u0358/g, "oo")
      .replace(/([oO\u00F2-\u00F6\u00D2-\u00D6\u014D\u014E][\u0300-\u036f]?)·/g, "$1o"),
  );
}

const cap = (s) => s.charAt(0).toUpperCase() + s.slice(1);

function replacePair(t, s, d) {
  t = t.split(s).join(d);
  return t.split(cap(s)).join(cap(d));
}

function subPair(t, s, d) {
  const re = new RegExp(`[${s[0].toUpperCase()}${s[0]}]${s.slice(1)}(?=[^a-z]|$)`, "g");
  return t.replace(re, (m) => (m[0] === m[0].toUpperCase() ? cap(d) : d));
}

// TL → POJ, case-preserving (port of tl_to_poj).
export function tlToPoj(tl) {
  if (!tl) return tl;
  let r = replacePair(tl, "tsh", "chh");
  r = replacePair(r, "ts", "ch");
  r = subPair(r, "ing", "eng");
  r = subPair(r, "ik", "ek");
  // POJ 正式字形（lua tl_to_poj）：鼻化 nn→ⁿ（U+207F）——nng 音節鼻音、
  // n 帶調符（nn̄g）袂換；oo→o͘（U+0358，調符綴佇頭一个 o 後壁）。
  r = r.replace(/nn([^g\u0300-\u036f])/g, "\u207F$1").replace(/nn$/g, "\u207F");
  r = r.replace(/o([\u0300-\u036f]?)o/g, "o$1\u0358");
  r = replacePair(r, "ua", "oa");
  r = replacePair(r, "ue", "oe");
  // 上游 v0.9.4 parity：Python tl_to_poj 內嵌調符位置修正（oa/oe 音節尾
  // 標 o、ui 標 u、大小寫攏支援、空白係音節邊界）——tlToPoj 單獨用嘛
  // 佇 Lua commit 路徑（tl_to_poj→format→fix）输出一致。
  return pojFixDiacritics(r);
}

// POJ → TL numeric (port of poj_to_tl).
export function pojToTl(text) {
  if (!text) return text;
  let r = diacriticsToNumbers(text).toLowerCase()
    .replace(/\u207f/g, "nn")
    .replace(/o\u0358/g, "oo")
    .replace(/ou/g, "oo");
  r = r.split("chh").join("tsh").split("ch").join("ts");
  r = r.replace(/eng(?=[^a-z]|$)/g, "ing").replace(/ek(?=[^a-z]|$)/g, "ik");
  return r.split("oa").join("ua").split("oe").join("ue");
}

// POJ diphthong tone-mark repositioning (port of poj_fix_diacritics;
// aligned with upstream scripts/tl_poj_convert.py v0.9.4):
// open-syllable oa/oe mark the o (goā→gōa, hoé→hōe); ui marks the u (uī→ūi);
// iu unchanged. Case-aware (Uē→Ōe); whitespace is a syllable boundary
// (upstream Lua hyphen-joins first, Python added \s for end-to-end parity).
// Mark class \u0300-\u033f mirrors Lua \204[\128-\191] exactly.
const MARK = "[\\u0300-\\u033f]";
export function pojFixDiacritics(text) {
  if (!text) return text;
  return text
    .replace(new RegExp(`([oO])([ae])(${MARK})(?=[-\\s\\u207f]|$)`, "g"), "$1$3$2")
    .replace(new RegExp(`([uU])i(${MARK})`, "g"), "$1$2i");
}

// Bare syllable → explicit tone (Lua add_implicit_tone).
export function addImplicitTone(syl) {
  if (!syl || /[1-9]$/.test(syl) || !/^[A-Za-z]+$/.test(syl)) return syl;
  const s = syl.toLowerCase();
  return /[ptkh]$/.test(s) ? s + "4" : s + "1";
}

export function addImplicitTones(numeric) {
  return numeric.split(/\s+/).filter(Boolean).map(addImplicitTone).join(" ");
}

export const stripTones = (numeric) => numeric.replace(/[1-9]/g, "");
