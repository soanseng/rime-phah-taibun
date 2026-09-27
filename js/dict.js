// Dictionary loading, segmentation and conversion.

import {
  formatRomanization, tlToPoj, pojFixDiacritics, toNumeric, pojToTl,
  addImplicitTones, stripTones,
} from "./roman.js";

const MAX_WORD = 8; // longest dictionary key (chars) considered per match

export const isHan = (ch) => {
  const o = ch.codePointAt(0);
  return (o >= 0x3400 && o <= 0x9FFF) || (o >= 0x20000 && o <= 0x3FFFF);
};

export async function loadDict(url) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`詞典載入失敗 HTTP ${res.status}`);
  return res.json();
}

// Greedy longest-match segmentation (codepoint-based: astral chars such as
// 𤆬/𨑨 are single units, unlike UTF-16 string indices).
// Returns segments: {t:"w",han,readings,gloss,si} | {t:"r",s} | {t:"miss",s}
export function segment(text, dict) {
  const cps = [...text];
  const segs = [];
  let i = 0;
  let si = 0; // word index for pick cycling
  while (i < cps.length) {
    if (!isHan(cps[i])) {
      let j = i;
      while (j < cps.length && !isHan(cps[j])) j++;
      segs.push({ t: "r", s: cps.slice(i, j).join("") });
      i = j;
      continue;
    }
    let hit = null;
    let hitLen = 0;
    for (let L = Math.min(MAX_WORD, cps.length - i); L > 0; L--) {
      const cand = cps.slice(i, i + L).join("");
      if ([...cand].some((c) => !isHan(c))) continue;
      if (dict[cand]) { hit = cand; hitLen = L; break; }
    }
    if (hit) {
      const e = dict[hit];
      segs.push({ t: "w", han: hit, readings: e.r, gloss: e.h || "", si });
      si++;
      i += hitLen;
    } else {
      segs.push({ t: "miss", s: cps[i] });
      i++;
    }
  }
  return segs;
}

// Segments → {tl, poj} lines. picks: Map(wordIndex → reading offset).
// Spacing: space between latin-ending and latin-starting tokens only;
// CJK punctuation binds tight. Tests ignore combining tone marks.
export function render(segs, picks = new Map()) {
  const base = (s) => s.normalize("NFD").replace(/[\u0300-\u036f]/g, "").normalize("NFC");
  const startLatin = (s) => /^[a-z0-9⟨]/i.test(base(s));
  const endLatin = (s) => /[a-z0-9⟩]/i.test(base(s).slice(-1));

  const tlParts = [];
  const pojParts = [];
  const push = (tl, poj) => {
    const lastTl = tlParts[tlParts.length - 1];
    const lastPoj = pojParts[pojParts.length - 1];
    tlParts.push(lastTl && endLatin(lastTl) && startLatin(tl) ? ` ${tl}` : tl);
    pojParts.push(lastPoj && endLatin(lastPoj) && startLatin(poj) ? ` ${poj}` : poj);
  };

  for (const seg of segs) {
    if (seg.t === "r") {
      push(seg.s, seg.s);
      continue;
    }
    if (seg.t === "miss") {
      push(`⟨${seg.s}⟩`, `⟨${seg.s}⟩`);
      continue;
    }
    const numeric = seg.readings[Math.min(picks.get(seg.si) ?? 0, seg.readings.length - 1)];
    push(
      formatRomanization(numeric),
      pojFixDiacritics(formatRomanization(tlToPoj(numeric))),
    );
  }
  return { tl: cap(tlParts.join("")), poj: cap(pojParts.join("")) };
}

const cap = (s) => s.replace(/[a-z]/, (c) => c.toUpperCase());

// All romanization renderings of one word for the annotation view.
export function wordVariants(seg, picks) {
  const n = picks.get(seg.si) ?? 0;
  return seg.readings.map((numeric, k) => ({
    numeric,
    tl: formatRomanization(numeric),
    poj: pojFixDiacritics(formatRomanization(tlToPoj(numeric))),
    active: k === Math.min(n, seg.readings.length - 1),
  }));
}

// User romanization input (toneless / numeric / POJ / diacritics) →
// { numeric, toneless, hasTones } for practice checking.
export function normalizeAnswer(input) {
  const numeric = addImplicitTones(toNumeric(String(input || "").trim()).replace(/-/g, " "))
    .split(/\s+/).filter(Boolean).join(" ");
  return {
    numeric,
    toneless: stripTones(numeric),
    hasTones: /[1-9]/.test(String(input || "")),
  };
}

export const readingToneless = (numeric) => stripTones(numeric.replace(/-/g, " "));

// 教育部臺灣台語常用詞辭典（漢字查詢）
export const sutianUrl = (word) =>
  `https://sutian.moe.edu.tw/und-hani/tshiau/?tsha=${encodeURIComponent(word)}&lui=tai_su`;

// ---------- TL → 漢字（實驗功能）----------
// 反向索引：去調音節序列 → 詞。同音詞歧義無詞頻/LM 時靠 sane+gloss 排序，
// 準度有限（真實文章字元相似度約 6 成）；輸出僅供輔助閱讀。
export function buildReverseIndex(dict) {
  const rev = new Map();
  for (const [w, e] of Object.entries(dict)) {
    const nHan = [...w].filter(isHan).length;
    const mixed = /[A-Za-z]/.test(w);
    for (const r of e.r) {
      const syl = r.split(" ").filter(Boolean);
      const key = syl.map((s) => s.replace(/[0-9]/g, "")).join(" ");
      const sane = mixed || syl.length === nHan;
      const cand = { word: w, sane, gloss: e.h ? 1 : 0 };
      const list = rev.get(key);
      if (list) list.push(cand);
      else rev.set(key, [cand]);
    }
  }
  for (const list of rev.values())
    list.sort((a, b) => b.sane - a.sane || b.gloss - a.gloss);
  return rev;
}

export function tlToHan(tlText, rev) {
  const raw = toNumeric(tlText.replace(/--/g, " ").replace(/-/g, " "))
    .split(/[\s,.;:!?()"“”《》〈〉·]+/)
    .filter((t) => /^[a-z0-9]+$/.test(t));
  const bare = raw.map((s) => pojToTl(s).replace(/[0-9]/g, ""));
  const out = [];
  let i = 0, matched = 0;
  while (i < bare.length) {
    let hit = null, hitLen = 0;
    for (let L = Math.min(8, bare.length - i); L >= 1; L--) {
      const list = rev.get(bare.slice(i, i + L).join(" "));
      if (list) { hit = list[0].word; hitLen = L; break; }
    }
    if (hit) { out.push(hit); matched += hitLen; i += hitLen; }
    else { out.push(raw[i]); i++; }
  }
  return { han: out.join(""), matched, total: bare.length };
}

// Candidate pool for practice: words with a gloss and 2–4 Han characters,
// keeping only readings whose syllable count matches the Han char count
// (mixed-script words exempt). Words with no qualifying reading are excluded;
// the quiz must never present a truncated reading as the answer.
export function practicePool(dict) {
  const pool = [];
  for (const [han, e] of Object.entries(dict)) {
    const n = [...han].length;
    if (!e.h || n < 2 || n > 4 || !e.r.length) continue;
    if (/[A-Za-z]/.test(han)) {
      pool.push({ han, r: e.r, h: e.h });
      continue;
    }
    const safe = e.r.filter(
      (r) => r.split(" ").filter(Boolean).length === n,
    );
    if (safe.length) pool.push({ han, r: safe, h: e.h });
  }
  return pool;
}

// Vocab lookup: word prefix → word substring → gloss substring. Capped.
export function lookup(dict, query, limit = 100) {
  const q = query.trim();
  if (!q) return [];
  const ql = q.toLowerCase();
  const byWord = [];
  const byGloss = [];
  for (const [han, e] of Object.entries(dict)) {
    if (han.startsWith(q)) byWord.push({ han, ...e });
    else if (han.includes(q)) byWord.push({ han, ...e });
    else if (e.h && e.h.toLowerCase().includes(ql)) byGloss.push({ han, ...e });
    if (byWord.length >= limit) break;
  }
  const out = byWord.slice(0, limit);
  for (const row of byGloss) {
    if (out.length >= limit) break;
    out.push(row);
  }
  return out;
}
