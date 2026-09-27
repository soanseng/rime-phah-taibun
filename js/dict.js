import {
  formatRomanization, tlToPoj, pojFixDiacritics, toNumeric, pojToTl,
  addImplicitTones, stripTones, sandhiNumeric, sandhiWordAll,
} from "./roman.js?v=15";

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
export function render(segs, picks = new Map(), opts = {}) {
  const { sandhi = false, lighttone = null } = opts;
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

  // 句界：。！？；切句；換行視為停頓（flush）。非句尾詞全音節變調
  // （sandhiWordAll），句尾詞用詞內變調（尾音節本調）。輕聰 "--" 不變調。
  const SENT_END = /[。！？；!?;]/;
  const pendWords = [];   // (seg) 待句界決定後輸出
  const flush = () => {
    for (let k = 0; k < pendWords.length; k++) {
      const { seg } = pendWords[k];
      let numeric = seg.readings[Math.min(picks.get(seg.si) ?? 0, seg.readings.length - 1)];
      if (lighttone?.has(seg.han)) numeric = lighttone.get(seg.han);
      const isLast = k === pendWords.length - 1;
      const outNum = !sandhi ? numeric
        : isLast ? sandhiNumeric(numeric)
        : sandhiWordAll(numeric);
      push(
        formatRomanization(outNum),
        pojFixDiacritics(formatRomanization(tlToPoj(outNum))),
      );
    }
    pendWords.length = 0;
  };
  for (const seg of segs) {
    if (seg.t === "r") {
      if (SENT_END.test(seg.s) || /\n|\r/.test(seg.s) || seg.s.trim()) flush();
      push(seg.s, seg.s);
      continue;
    }
    if (seg.t === "miss") {
      flush();
      push(`⟨${seg.s}⟩`, `⟨${seg.s}⟩`);
      continue;
    }
    pendWords.push({ seg });
  }
  flush();
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
    const seen = new Set();
    for (const r of e.r) {
      if (seen.has(r)) continue; // 同詞重複讀音去重
      seen.add(r);
      const syl = r.split(" ").filter(Boolean);
      const key = syl.map((s) => s.replace(/[0-9]/g, "")).join(" ");
      const sane = mixed || syl.length === nHan;
      const cand = { word: w, sane, gloss: e.h ? 1 : 0,
                     toned: syl.map((s) => s.match(/[1-9]$/)?.[0] ?? "0").join("") };
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
  const parts = [];
  let matched = 0, total = 0;
  for (const run of splitLiterals(tlText, tlRuns)) {
    if (run.type === "sep" || run.type === "lit") { parts.push(run.s); continue; }
    const { bare, raws } = romToSylls(run.s);
    if (!bare.length) { parts.push(run.s); continue; }
    total += bare.length;
    const out = [];
    let i = 0;
    while (i < bare.length) {
      let hit = null, hitLen = 0;
      for (let L = Math.min(8, bare.length - i); L >= 1; L--) {
        const list = rev.get(bare.slice(i, i + L).join(" "));
        if (list) { hit = list[0].word; hitLen = L; break; }
      }
      if (hit) { out.push(hit); matched += hitLen; i += hitLen; }
      else { out.push(raws[i]); i++; }
    }
    parts.push(out.join(""));
  }
  return { han: parts.join(""), matched, total };
}

// ---------- bigram LM（identity 語料漢字詞）→ 羅→漢 beam 解碼 ----------
export function buildLM(lmJson) {
  const uni = new Map(Object.entries(lmJson.uni));
  let total = 0;
  for (const v of uni.values()) total += v;
  return {
    uni, total,
    bigrams: new Map(Object.entries(lmJson.bigrams)),
    trigrams: new Map(Object.entries(lmJson.trigrams ?? {})),
    tonefreq: lmJson.tonefreq ?? {},
  };
}

// `...` 反引號內容＝原樣保留（英文專名等，不進解碼）
function splitLiterals(text, runs) {
  const re = /`([^`]*)`/g;
  let last = 0, m;
  const out = [];
  while ((m = re.exec(text))) {
    if (m.index > last) out.push(...runs(text.slice(last, m.index)));
    out.push({ type: "lit", s: m[1] });
    last = m.index + m[0].length;
  }
  if (last < text.length) out.push(...runs(text.slice(last)));
  return out;
}

// 輸入切做 [羅馬字段] × [分隔符]（標點、空白、斷行原樣保留）
function tlRuns(tlText) {
  // 羅馬字段含字母/數字/結合調符/o͘/連字號（-、-- 輕聲、– — dash）；
  // 分隔符只有標點、空白、斷行——原樣保留。
  const re = /[A-Za-z0-9\u00C0-\u024F\u0300-\u036f\u0358\u207F\u2013\u2014-]+/g;
  const runs = [];
  let last = 0, m;
  while ((m = re.exec(tlText))) {
    if (m.index > last) runs.push({ type: "sep", s: tlText.slice(last, m.index) });
    runs.push({ type: "rom", s: m[0] });
    last = m.index + m[0].length;
  }
  if (last < tlText.length) runs.push({ type: "sep", s: tlText.slice(last) });
  return runs;
}

const isHanTok = (tok) => [...tok].some((ch) => {
  const o = ch.codePointAt(0);
  return (o >= 0x3400 && o <= 0x9FFF) || (o >= 0x20000 && o <= 0x3FFFF);
});

// 羅馬字段 → { bare: 去調 TL 音節鍵, raws: 原字音節, tones: 每音節調號 }
function romToSylls(rom) {
  const raws = rom.split(/[-\s]+/).filter(Boolean);
  const nums = toNumeric(rom).split(/[-\s]+/).filter(Boolean);
  if (raws.length !== nums.length) return { bare: [rom], raws: [rom], tones: ["0"] };
  return {
    bare: nums.map((s) => pojToTl(s).replace(/[0-9]/g, "")),
    raws,
    tones: nums.map((s) => s.match(/[1-9]$/)?.[0] ?? "0"),
  };
}

// 羅→漢解碼：整句 log-prob lattice＋backpointer。
// P(w|prev) = interp·min(C12/C(prev),1) + (1−interp)·Puni(w)
// 每詞分數 = log P（≤0，無長度紅利）＋gloss 小紅利−insane 罰。
export function decodeTlToHan(tlText, rev, lm, opts = {}) {
  const words = [];   // 解碼詞序（詞對照卡用）
  const {
    beamWidth = 8, interp = 0.65, unknownCost = 10,
    insaneCost = 3.0, glossBonus = 1.0, pFloor = 1e-5,
    toneBonus = 2.0, tonePenalty = 3.0,
  } = opts;
  const Z = lm.total || 1;
  const pUni = (u) => Math.max((u + 1) / Z, pFloor);
  // 調號完全吻合加分；不合時按語料調形分布減罰（per-key 調號 prior）：
  // 仝鍵內佗一个調形較常出現（親像變調輸入），罰較輕。
  const toneScore = (c, tones, i, L, key, hasExact) => {
    const inT = tones.slice(i, i + L).join("");
    if (inT.includes("0")) return 0; // 使用者免調：不判
    if (c.toned === inT) return toneBonus;
    // 有別个候選全對（本調輸入）→ 保持平罰，鑑別毋通減。
    // 歸鍵無半個全對（變調形輸入）→ 按語料調形分布減罰（per-key 調號 prior）。
    if (!hasExact && key) {
      const dist = lm.tonefreq[key];
      // 愛有 ≥2 个調形記錄才用分布：單一調形鍵 share=1 會變做全面減罰、
      // 無鑑別性（known-vs-unknown 判斷煞來振動）。
      if (dist && dist[c.toned] && Object.keys(dist).length > 1) {
        const total = Object.values(dist).reduce((a, b) => a + b, 0);
        const share = dist[c.toned] / total;
        return -tonePenalty * (1 - 0.7 * share);
      }
    }
    return -tonePenalty;
  };
  // bigram→trigram backoff：有 (a,b,w) 就用 P(w|a,b)，無就退 P(w|b)
  const wordScore = (prev2, prev, c, tones, i, L, key, hasExact) => {
    const w_uni = lm.uni.get(c.word) ?? 0;
    let pCtx = 0;
    if (prev) {
      const c123 = prev2 ? (lm.trigrams.get(`${prev2}\t${prev}\t${c.word}`) ?? 0) : 0;
      if (c123 > 0) {
        const denom = lm.bigrams.get(`${prev2}\t${prev}`) ?? 0;
        pCtx = denom > 0 ? Math.min(c123 / denom, 1) : Math.min(c123, 1);
      } else {
        const c12 = lm.bigrams.get(`${prev}\t${c.word}`) ?? 0;
        const cL = lm.uni.get(prev) ?? 0;
        pCtx = Math.min(c12 / (cL || 1), 1);
      }
    }
    const p = interp * pCtx + (1 - interp) * pUni(w_uni);
    return Math.log(p + 1e-12) + (c.gloss ? glossBonus : 0)
      - (c.sane ? 0 : insaneCost) + toneScore(c, tones, i, L, key, hasExact);
  };
  const parts = [];
  let matched = 0, total = 0;
  const runs = splitLiterals(tlText, tlRuns);

  const decodeSentence = (items) => {

    const bare = [], raws = [], tones = [], runEnd = [];
    const sepAt = new Map(); // 音節 index → 該欄位前的分隔符（空白）
    let pendingSep = "";
    let started = false;
    for (const it of items) {
      if (it.sep !== undefined) { pendingSep += it.sep; continue; }
      const { bare: b, raws: r, tones: tn } = romToSylls(it.rom);
      if (!b.length) { pendingSep += it.rom; continue; }
      if (started) sepAt.set(bare.length, pendingSep);
      pendingSep = "";
      started = true;
      for (let k = 0; k < b.length; k++) {
        bare.push(b[k]); raws.push(r[k]); tones.push(tn[k]);
        runEnd.push(k === b.length - 1);
      }
    }
    const tailSep = pendingSep;
    const N = bare.length;
    total += N;
    if (!N) { parts.push(tailSep); return; }
    const beams = Array.from({ length: N + 1 }, () => []);
    beams[0] = [{ score: 0, last: null, last2: null, node: null }];
    for (let i = 0; i < N; i++) {
      if (!beams[i].length) continue;
      const maxL = runEnd[i] ? 1 : (() => { let j = i; while (j < N && !runEnd[j]) j++; return j - i + 1; })();
      for (const st of beams[i]) {
        for (let L = Math.min(8, maxL, N - i); L >= 1; L--) {
          if (L > 1 && !runEnd[i + L - 1]) continue; // 詞尾須在欄位尾
          const list = rev.get(bare.slice(i, i + L).join(" "));
          if (!list) continue;
          const inT = tones.slice(i, i + L).join("");
          const hasExact = inT.includes("0") || list.some((c) => c.toned === inT);
          for (const c of list.slice(0, 24)) {
            beams[i + L].push({
              score: st.score + wordScore(st.last2, st.last, c, tones, i, L, bare.slice(i, i + L).join(" "), hasExact),
              last: c.word, last2: st.last,
              node: { pos: i, tok: c.word, prev: st.node, syl: L },
            });
          }
        }
        // 未音節：上下文歸零——trigram/bigram 毋通橋過 unknown
        beams[i + 1].push({
          score: st.score - unknownCost,
          last: null, last2: null,
          node: { pos: i, tok: raws[i], prev: st.node, syl: 1 },
        });
      }
      for (let j = i + 1; j <= Math.min(N, i + 8); j++) {
        if (beams[j].length > beamWidth) {
          beams[j].sort((a, b) => b.score - a.score);
          beams[j].length = beamWidth;
        }
      }
    }
    const best = beams[N][0] ?? { node: null };
    // backtrace
    const toks = [];
    for (let n = best.node; n; n = n.prev) toks.unshift(n);
    let out = "";
    for (const t of toks) {
      const s = sepAt.get(t.pos);
      if (s !== undefined) out += s;
      out += t.tok;
      if (isHanTok(t.tok)) {
        matched += t.syl;
        const num = bare.slice(t.pos, t.pos + t.syl)
          .map((b, k) => b + (tones[t.pos + k] === "0" ? "" : tones[t.pos + k])).join(" ");
        words.push({ word: t.tok, reading: num });
      }
    }
    parts.push(out + tailSep);
  };

  let sent = [];
  for (const run of runs) {
    if (run.type === "rom") { sent.push({ rom: run.s }); continue; }
    if (run.type === "lit") { sent.push({ sep: run.s }); continue; }
    if (run.type === "sep" && /[^\s]/.test(run.s)) {
      decodeSentence(sent);              // 句界：先解句內
      parts.push(run.s);                 // 標點原樣
      sent = [];                         // 上下文重置
      continue;
    }
    sent.push({ sep: run.s });           // 空白：句內保留
  }
  decodeSentence(sent);
  return { han: parts.join(""), matched, total, words };
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

