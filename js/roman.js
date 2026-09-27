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
  if (pos < 0) pos = base.startsWith("nn") ? 1 : base.search(/[mn]/);
  return pos < 0 ? base : base.slice(0, pos + 1) + mark + base.slice(pos + 1);
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
      if (tone && !/[1-9]$/.test(base)) base += tone;
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
    text.replace(/\u207f/g, "nn").replace(/o\u0358/g, "oo"),
  );
}

const cap = (s) => s.charAt(0).toUpperCase() + s.slice(1);

function replacePair(t, s, d) {
  t = t.split(s).join(d);
  return t.split(cap(s)).join(cap(d));
}

function subPair(t, s, d) {
  const re = new RegExp(`[${s[0].toUpperCase()}${s[0]}]${s.slice(1)}\\b`, "g");
  return t.replace(re, (m) => (m[0] === m[0].toUpperCase() ? cap(d) : d));
}

// TL → POJ, case-preserving (port of tl_to_poj).
export function tlToPoj(tl) {
  if (!tl) return tl;
  let r = replacePair(tl, "tsh", "chh");
  r = replacePair(r, "ts", "ch");
  r = subPair(r, "ing", "eng");
  r = subPair(r, "ik", "ek");
  r = replacePair(r, "ua", "oa");
  r = replacePair(r, "ue", "oe");
  return r;
}

// POJ → TL numeric (port of poj_to_tl).
export function pojToTl(text) {
  if (!text) return text;
  let r = diacriticsToNumbers(text).toLowerCase()
    .replace(/\u207f/g, "nn")
    .replace(/o\u0358/g, "oo")
    .replace(/ou/g, "oo");
  r = r.split("chh").join("tsh").split("ch").join("ts");
  r = r.replace(/eng\b/g, "ing").replace(/ek\b/g, "ik");
  return r.split("oa").join("ua").split("oe").join("ue");
}

// POJ diphthong tone-mark repositioning (port of poj_fix_diacritics):
// open-syllable oa/oe mark the o (goā→gōa, hoé→hōe); ui marks the u (uī→ūi);
// iu unchanged.
const MARK = "[\\u0300-\\u036f]";
export function pojFixDiacritics(text) {
  if (!text) return text;
  return text
    .replace(new RegExp(`oa(${MARK})(?=-|\\u207f|$)`, "g"), "o$1a")
    .replace(new RegExp(`oe(${MARK})(?=-|\\u207f|$)`, "g"), "o$1e")
    .replace(new RegExp(`ui(${MARK})`, "g"), "u$1i");
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
