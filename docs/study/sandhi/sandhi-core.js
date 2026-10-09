// 變調練習核心：調組切分（標點、輕聲「--」、手動界線）＋逐音節變調＋小測驗出題。
// 純邏輯、無 DOM。變調規則完全用 roman.js 的 sandhiSyllable（主流腔一般變調），
// 遮干焦決定「佗一个音節愛變、佗一个保留本調」。
import {
  pojToTl, sandhiSyllable, formatRomanization, tlToPoj, pojFixDiacritics, addImplicitTone,
} from "../../thak/js/roman.js?v=26";
import { isHan } from "../../thak/js/dict.js?v=26";

// 調組收尾的標點（全形＋半形）；測驗選項的調（6 併入 7，無 9）
export const PUNCT = "，。！？、；：,.!?;:";
export const TONE_OPTIONS = ["1", "2", "3", "4", "5", "7", "8"];

// 非羅馬字集（全形標點、漢字……）前後挵空白：pojToTl 干焦照空白／連字號切音節，
// 若無隔開，兩爿音節的調符會濫做伙（親像「pn̄g。lí」會去了 png 的調）。
const PAD_RE = /([^A-Za-z0-9\u00C0-\u024F\u0300-\u036F\u0358\u207F\u0131·\-–—])/g;
const TOK_RE = /(--)|([a-z]+[0-9]?)|([，。！？、；：,.!?;:])/g;

// 羅馬字段（全羅輸入、segment 的 r 段）→ token 流：syl（音節）／light（--）／punct。
// pojToTl 共白話字／台羅／調符攏轉做數字調；單一連字號是詞內音節隔，直接略過。
export function romanTokens(s) {
  const norm = pojToTl(String(s ?? "").replace(PAD_RE, " $1 "));
  const tokens = [];
  for (const m of norm.matchAll(TOK_RE)) {
    if (m[1]) tokens.push({ t: "light" });
    else if (m[2]) tokens.push({ t: "syl", numeric: m[2] });
    else tokens.push({ t: "punct" });
  }
  return tokens;
}

// token → 音節：標點／「--」予頭前的音節收調組；「--」後壁到句讀為輕聲（無變調）；
// 文字上尾一个音節嘛收調組。無讀音（numeric null）＝不明。
export function buildSyllables(tokens) {
  const syls = [];
  let light = false;
  const close = () => { if (syls.length) syls[syls.length - 1].autoEnd = true; };
  for (const tk of tokens) {
    if (tk.t === "punct") { close(); light = false; continue; }
    if (tk.t === "light") { close(); light = true; continue; }
    syls.push({
      han: tk.han ?? null,
      src: tk.numeric ?? null,
      base: tk.numeric ? addImplicitTone(tk.numeric) : null,
      light, autoEnd: false,
    });
  }
  if (syls.length) syls[syls.length - 1].autoEnd = true;
  return syls;
}

// 全羅／白話字一句 → 音節（含本調音節佮自動調組尾）
export const analyzeRoman = (text) => buildSyllables(romanTokens(text));

// 漢羅：segment() 的結果 → 音節。詞用頭一个讀音逐字對位；音節數佮字數無合、
// miss 段 → 標不明；r 段內底的羅馬字／標點／「--」照羅馬字路徑處理。
export function analyzeHanlo(segs) {
  const tokens = [];
  for (const seg of segs ?? []) {
    if (seg.t === "w") {
      const chars = [...seg.han];
      const syls = (seg.readings?.[0] ?? "").split(/\s+/).filter(Boolean);
      const ok = syls.length === chars.length && syls.every((s) => /^[a-z]+[0-9]?$/.test(s));
      chars.forEach((ch, k) => tokens.push({ t: "syl", han: ch, numeric: ok ? syls[k] : null }));
    } else if (seg.t === "r") {
      tokens.push(...romanTokens(seg.s));
    } else {
      for (const ch of [...seg.s]) tokens.push({ t: "syl", han: ch, numeric: null });
    }
  }
  return buildSyllables(tokens);
}

// 逐音節變調：調組尾（autoEnd／手動界線）保留本調；輕聲佮無讀音無變調結果（out null）；
// 其他用 sandhiSyllable。回新陣列，無改入來的音節。
export function applySandhi(syls, manualEnds = []) {
  const ends = new Set(manualEnds);
  return syls.map((s, i) => {
    const end = s.autoEnd || ends.has(i);
    const out = !s.base || s.light ? null : end ? s.base : sandhiSyllable(s.base);
    return {
      ...s, end, out,
      baseTone: toneOf(s.base),
      outTone: out ? toneOf(out) : null,
      changed: Boolean(out) && out !== s.base,
    };
  });
}

// 手動切調組（開關）：回新的排序陣列
export function toggleEnd(ends, i) {
  const set = new Set(ends);
  if (set.has(i)) set.delete(i); else set.add(i);
  return [...set].sort((a, b) => a - b);
}

export const toneOf = (numeric) => (numeric?.match(/[1-9]$/)?.[0] ?? null);

// 顯示用讀音（TL 或 POJ 調符）
export function romanOf(numeric, poj) {
  if (!numeric) return null;
  return poj
    ? pojFixDiacritics(formatRomanization(tlToPoj(numeric)))
    : formatRomanization(numeric);
}

// 詞內連讀的完整變調型（非尾音節變調、尾音節本調）——小測驗的解答說明用
export function sandhiPattern(numeric) {
  const syls = numeric.split(/\s+/).filter(Boolean);
  return syls.map((s, i) => (i < syls.length - 1 ? sandhiSyllable(s) : s)).join(" ");
}

// ---- 小測驗 ----
// 詞池：教典例句（listen.json items）裡連字號連做伙的詞——
// TL 佇詞內音節中間畫連字號，敢若 khuànn-huat，所以詞內非尾音節一定愛變調，答案無歧義。
// 條件：全漢 2–3 字、逐音節提會出調、無 仔（仔前變調無固定）、無三疊音；詞佮讀音對位。
const LATIN_EDGE = /^[^A-Za-z0-9\u00c0-\u024f\u0131]+|[^A-Za-z0-9\u00c0-\u024f\u0131\u0300-\u036f\u0358\u207f]+$/g;
export function sentencePool(items) {
  const out = [];
  const seen = new Set();
  for (const it of items ?? []) {
    const hanRaw = String(it.han ?? "");
    // 漢羅例句（han 內底有羅馬字）對位複雜，這馬無收；標點（，。？！）毋算 slot。
    if (/[A-Za-z\u00C0-\u024F\u0131]/.test(hanRaw)) continue;
    const han = [...hanRaw].filter(isHan);
    let k = 0; // 例句漢字對位游標
    for (const raw of String(it.tl ?? "").split(/\s+/).filter(Boolean)) {
      const tk = raw.replace(LATIN_EDGE, "");
      if (!tk) continue; // 標點／別的符號：無食音節
      const parts = tk.split("--");
      const syls = parts[0].split("-").filter(Boolean)
        .map((s) => addImplicitTone(pojToTl(s)));
      const total = parts.reduce((n, p) => n + p.split("-").filter(Boolean).length, 0);
      const hanWord = han.slice(k, k + syls.length).join("");
      k += total;
      if (syls.length < 2 || syls.length > 3) continue;
      if (syls.some((s) => !/[1-9]$/.test(s))) continue;
      if ([...hanWord].length !== syls.length || ![...hanWord].every(isHan)) continue;
      if (hanWord.includes("仔")) continue;
      if (syls.length === 3 && syls[0] === syls[1] && syls[1] === syls[2]) continue;
      const numeric = syls.join(" ");
      if (seen.has(`${hanWord}|${numeric}`)) continue;
      seen.add(`${hanWord}|${numeric}`);
      out.push({ han: hanWord, numeric, sent: it.han ?? "", sentTl: it.tl ?? "", hoa: it.hoa ?? "" });
    }
  }
  return out;
}

// 揀一个非尾音節問變調；correct ＝ sandhiSyllable 出來的調（數字字串）
export function makeQuestion(entry, rng = Math.random) {
  const syls = entry.numeric.split(/\s+/).filter(Boolean);
  const i = Math.floor(rng() * (syls.length - 1));
  const numeric = syls.join(" ");
  return {
    han: entry.han, numeric, i,
    correct: toneOf(sandhiSyllable(syls[i])),
    options: [...TONE_OPTIONS],
    pattern: sandhiPattern(numeric),
    sent: entry.sent ?? "", sentTl: entry.sentTl ?? "", hoa: entry.hoa ?? "",
  };
}


// 一輪 n 題，對詞池無重複抽（池仔細就出甲了）
export function makeRound(pool, n = 10, rng = Math.random) {
  const left = pool.map((_, k) => k);
  const qs = [];
  for (let k = 0; k < n && left.length; k++) {
    const pick = left.splice(Math.floor(rng() * left.length), 1)[0];
    qs.push(makeQuestion(pool[pick], rng));
  }
  return qs;
}

// 弱點複習卡的 id（佮 study-store 的 sandhi 卡契約一致）
export const cardId = (q) => `sandhi:${q.han}|${q.numeric}|${q.i}`;
