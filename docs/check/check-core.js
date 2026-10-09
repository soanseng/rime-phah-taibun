// 寫作檢查核心（純函式，無 DOM／fetch）：貼入的台文（TL／POJ／漢羅）→ 問題清單。
// 每條 issue = { start, end, cat, msg, fix? }：fix 是 [start, end) 的機械替換字串。
// 拼寫檢查（系統、數字調、調號/韻尾、調符位置）毋免詞典；
// 音節／連字符／用字／華語直譯的資料（詞典鍵集、segments、iongji、hints）由呼叫者注入。
// import 指定字串愛佮工具頁仝款（?v=26／?v=5），模組才袂載兩擺。
import {
  pojToTl, stripTones, formatRomanization, tlToPoj, pojFixDiacritics, toNumeric, addImplicitTone,
} from "../thak/js/roman.js?v=26";
import { sylKey } from "../try/practice-core.js?v=2";
import {
  findGrammar, wordSpans, calqueAllowed, lighttoneAllowed,
} from "./grammar-rules.js?v=2";

// 分類（UI 分組用）：拼寫 1–4、音節 5、連字符 6、用字 7、華語直譯／輕聲 8、華語用字 10、
// 華語句式 11（連文法筆記）、舊式寫法（白話字舊式調符，提醒毋是錯）。
export const CATS = [
  ["spelling", "拼寫"],
  ["syllable", "音節"],
  ["hyphen", "連字符"],
  ["hanji", "用字"],
  ["calque", "華語直譯／輕聲"],
  ["hoabun", "華語用字"],
  ["grammar", "華語句式（文法）"],
  ["legacy", "舊式寫法（提醒）"],
];

// ---------- 基礎：正規化佮詞掃描 ----------

// 舊式 o· 中點→o͘ 結合符、無點 ı→i（佮 practice-core sylKey 仝款）。
const normSyl = (s) => s.normalize("NFC").replace(/ı/g, "i").replace(/·/g, "\u0358");

// 羅馬字詞：字母（含調符、o͘、⁵、ı、·）＋調數字，連字號黏音節。`--`（輕聲）毋算。
const LEAD = "A-Za-z\\u00C0-\\u024F\\u0131";
const CH = "A-Za-z\\u00C0-\\u024F\\u0300-\\u036f\\u0358\\u207F\\u0131\\u00B71-9";
const WORD_RE = new RegExp(`[${LEAD}][${CH}]*(?:-[${LEAD}][${CH}]*)*`, "gu");

// text → [{ text, start, end, syls: [{ s, start, end }] }]
export function scanRomanWords(text) {
  const out = [];
  for (const m of String(text ?? "").matchAll(WORD_RE)) {
    const w = { text: m[0], start: m.index, end: m.index + m[0].length, syls: [] };
    let pos = 0;
    for (const part of m[0].split(/(-+)/)) {
      if (!part) continue;
      if (part[0] === "-") { pos += part.length; continue; }
      w.syls.push({ s: part, start: w.start + pos, end: w.start + pos + part.length });
      pos += part.length;
    }
    out.push(w);
  }
  return out;
}

// ---------- 拼音系統判定佮轉換 ----------

// 一个音節的系統標記：TL（ts/tsh、oo、ua/ue、ing/ik、nn）vs POJ（ch/chh、o͘/o·、oa/oe、eng/ek、ⁿ）。
// o͘ 佮 ⁿ 先轉做 oo/nn 了後，就佮 TL 的 oo/nn 分袂出來，所以愛用原字判斷。
export function sylSystem(s) {
  const n = normSyl(s);
  const pojDot = /[\u0358\u00B7]/.test(n);
  const pojSup = n.includes("\u207F");
  const num = toNumeric(n);
  const numClean = (pojSup ? num.replace(/nn/g, "n") : num);
  const numNoDot = (pojDot ? numClean.replace(/oo/g, "o") : numClean);
  const tl = /^ts/.test(numNoDot) || /oo/.test(numNoDot) || /ua|ue/.test(numNoDot)
    || /(?:ing|ik)$/.test(numNoDot) || /nn/.test(numNoDot);
  const poj = /^ch/.test(numNoDot) || pojDot || pojSup || /oa|oe/.test(numNoDot)
    || /(?:eng|ek)$/.test(numNoDot);
  if (tl && !poj) return "tl";
  if (poj && !tl) return "poj";
  return null; // 模糊／中性
}

// 一个詞（連字號音節）的系統；音節內底兩種標記相沗 → 模糊算 null。
export function wordSystem(word) {
  let tl = false;
  let poj = false;
  for (const part of String(word ?? "").split(/-+/)) {
    const s = sylSystem(part);
    if (s === "tl") tl = true;
    else if (s === "poj") poj = true;
  }
  if (tl && poj) return null;
  return tl ? "tl" : poj ? "poj" : null;
}

// 詞 → 目標系統的標準寫法（調符、字母攏轉），保持頭字大寫佮連字號。
export function convertWord(word, target) {
  const out = String(word ?? "").split("-").map((p) => {
    const num = pojToTl(normSyl(p));
    const diac = target === "poj"
      ? pojFixDiacritics(formatRomanization(tlToPoj(num)))
      : formatRomanization(num);
    return diac;
  }).join("-").normalize("NFC");
  if (/^[A-Z]/.test(word)) return out[0].toUpperCase() + out.slice(1);
  return out;
}

// 全文大多數系統（tl 平手贏）；無標記詞 → null。
export function detectMajority(text) {
  let tl = 0;
  let poj = 0;
  for (const w of scanRomanWords(text)) {
    const s = wordSystem(w.text);
    if (s === "tl") tl++;
    else if (s === "poj") poj++;
  }
  if (!tl && !poj) return null;
  return tl >= poj ? "tl" : "poj";
}

// ---------- 檢查 1–4（拼寫，毋免詞典） ----------

// 1. 拼音系統沗著：目標系統（target 有指定就用；無就照大多數）以外的詞建議轉換。
export function checkSystemMixing(text, target = null) {
  let goal = target === "tl" || target === "poj" ? target : null;
  const words = scanRomanWords(text);
  // 外語詞（Door、Formosa）毋算系統
  const sys = words.map((w) => (FOREIGN_RE.test(lettersOf(w.text)) ? null : wordSystem(w.text)));
  if (!goal) {
    const nTl = sys.filter((s) => s === "tl").length;
    const nPoj = sys.filter((s) => s === "poj").length;
    if (nTl === 0 || nPoj === 0) return [];
    goal = nTl >= nPoj ? "tl" : "poj";
  }
  const out = [];
  words.forEach((w, i) => {
    if (!sys[i] || sys[i] === goal) return;
    const fx = convertWord(w.text, goal);
    if (fx === w.text.normalize("NFC")) return; // 轉了無變（親像 eng 尾中性詞）就免建議
    const from = sys[i] === "tl" ? "台羅（TL）" : "白話字（POJ）";
    const to = goal === "tl" ? "台羅（TL）" : "白話字（POJ）";
    out.push({
      start: w.start,
      end: w.end,
      cat: "spelling",
      msg: `「${w.text}」是${from}拼法，建議統一做${to}：「${fx}」。`,
      fix: fx,
    });
  });
  return out;
}

// 2. 數字調 → 調符（目標系統）。
export function checkNumericTones(text, target = "tl") {
  const goal = target === "poj" ? "poj" : "tl";
  return scanRomanWords(text)
    .filter((w) => /[1-9]/.test(w.text))
    .map((w) => {
      const fx = convertWord(w.text, goal);
      return {
        start: w.start,
        end: w.end,
        cat: "spelling",
        msg: `「${w.text}」用數字調，建議改用調符：「${fx}」。`,
        fix: fx,
      };
    });
}

// 3. 調號 × 韻尾：p/t/k/h 尾干焦 4（無標）抑 8；無入聲尾毋標 8。無 auto-fix。
export function checkToneFinals(text) {
  const out = [];
  for (const w of scanRomanWords(text)) {
    for (const syl of w.syls) {
      const num = toNumeric(normSyl(syl.s));
      const t = num.match(/[1-9]$/)?.[0];
      if (!t) continue; // 無標調（1/4）免管
      const stop = /[ptkh]$/.test(num.slice(0, -1));
      if (stop ? !"23579".includes(t) : t !== "8") continue;
      out.push({
        start: syl.start,
        end: syl.end,
        cat: "spelling",
        msg: stop
          ? `「${syl.s}」有入聲韻尾（-p/-t/-k/-h），建議干焦用第4調（無標）抑是第8調。`
          : `「${syl.s}」無入聲韻尾，建議毋免標第8調。`,
      });
    }
  }
  return out;
}

const TONE_MARK_RE = /[\u0300\u0301\u0302\u0304\u0306\u030B\u030D]/;
const STRIP_MARK_RE = /[\u0300\u0301\u0302\u0304\u0306\u030B\u030D]/g;
const hasToneMark = (s) => TONE_MARK_RE.test(normSyl(s).normalize("NFD"));
// 去調符了 ê 字母（o͘ 點、ı 攏正規化，免大細寫）。
const lettersOf = (s) => normSyl(s).normalize("NFD").replace(STRIP_MARK_RE, "")
  .normalize("NFC").toLowerCase();

// 4. 調符位置：字母佮標準寫法仝、干焦調符囥別位 → fix 做標準位（照家己的系統；
//    無系統記號的詞（súi、tùi）照全文大多數 goal）。
//    白話字雙元音 oa／oe／ui 的調符「囥頭一个抑是第二个元音」有舊式／另一派寫法
//    （十項管見 Tâi-ôan、教會公報 toā、tuì）——毋是拍毋著，用 legacy 類提醒現代標準寫法。
const PAIR_MARK = "[\\u0300\\u0301\\u0302\\u0304\\u0306\\u030B\\u030D]";
const PAIRS = [["oO", "aeAE"], ["uU", "iI"]];
const swapPairMark = (s) => {
  const d = s.normalize("NFD");
  for (const [a, b] of PAIRS) {
    const onFirst = d.replace(new RegExp(`([${a}])(${PAIR_MARK})([${b}])`), "$1$3$2");
    if (onFirst !== d) return onFirst.normalize("NFC");
    const onSecond = d.replace(new RegExp(`([${a}])([${b}])(${PAIR_MARK})`), "$1$3$2");
    if (onSecond !== d) return onSecond.normalize("NFC");
  }
  return s;
};
export function checkMarkPosition(text, goal = null) {
  const out = [];
  for (const w of scanRomanWords(text)) {
    const wsys = wordSystem(w.text);
    for (const syl of w.syls) {
      if (/[1-9]/.test(syl.s)) continue; // 數字調是規則 2
      if (!hasToneMark(syl.s)) continue;
      const num = toNumeric(normSyl(syl.s));
      const sys = sylSystem(syl.s) ?? wsys ?? goal ?? "tl";
      const std = (sys === "poj"
        ? pojFixDiacritics(formatRomanization(tlToPoj(num)))
        : formatRomanization(num)).normalize("NFC");
      const inN = syl.s.normalize("NFC");
      if (inN.toLowerCase() === std) continue;
      if (lettersOf(syl.s) !== lettersOf(std)) continue;
      const fx = /^[A-Z]/.test(inN) ? std[0].toUpperCase() + std.slice(1) : std;
      const legacy = sys === "poj" && swapPairMark(std) === inN.toLowerCase();
      out.push({
        start: syl.start,
        end: syl.end,
        cat: legacy ? "legacy" : "spelling",
        msg: legacy
          ? `「${syl.s}」是舊式（抑是另一派）白話字的調符位置，毋是拍毋著；現代白話字標準寫「${fx}」（oa／oe 後壁無韻尾囥 o、有韻尾囥 a／e；ui 囥 u）。`
          : `「${syl.s}」調符位置建議照標準寫做「${fx}」。`,
        fix: fx,
      });
    }
  }
  return out;
}

// 重疊去予（已照 start 排好、k 是優先權）：掃過去，佮頭前一條相沗就跋棄。
function dedupeOverlap(sorted) {
  const out = [];
  let end = -1;
  for (const i of sorted) {
    if (i.start < end) continue;
    out.push(i);
    end = i.end;
  }
  return out;
}

// 1–4 合做伙，仝 span 照優先權（1→2→3→4）留一條。
export function checkSpelling(text, target = null) {
  const goal = target === "tl" || target === "poj" ? target : detectMajority(text) ?? "tl";
  return dedupeOverlap([
    ...checkSystemMixing(text, target),
    ...checkNumericTones(text, goal),
    ...checkToneFinals(text),
    ...checkMarkPosition(text, goal),
  ].map((i, k) => ({ ...i, k }))
    .sort((a, b) => a.start - b.start || a.k - b.k));
}

// ---------- 檢查 5：詞典揣無的音節 ----------

// 詞典 → 逐音節的去調鍵 Set（tsiah8 png7 → tsiah、png）。
export function buildSyllableSet(dict) {
  const set = new Set();
  for (const e of Object.values(dict ?? {})) {
    for (const r of e.r ?? []) {
      for (const syl of String(r).split(/\s+/)) {
        const k = sylKey(syl);
        if (k) set.add(k);
      }
    }
  }
  return set;
}

// 編輯距離 1 的候選（代換→刪→插），頂懸 limit 个。
function nearKeys(key, set, limit = 3) {
  const AZ = "abcdefghijklmnopqrstuvwxyz";
  const found = [];
  for (let i = 0; i < key.length; i++) {
    const a = key.slice(0, i);
    const b = key.slice(i + 1);
    for (const c of AZ) if (c !== key[i] && set.has(a + c + b)) found.push(a + c + b);
    if (set.has(b)) found.push(b);
  }
  for (let i = 0; i <= key.length; i++) {
    for (const c of AZ) if (set.has(key.slice(0, i) + c + key.slice(i))) found.push(key.slice(0, i) + c + key.slice(i));
  }
  return [...new Set(found)].slice(0, limit);
}

// 台語羅馬字無 f q r v w x y z，c 干焦佇 ch／chh：有這款字母的詞是外語（Formosa、sic），毋檢查。
const FOREIGN_RE = /[fqrvwxyz]|c(?!h)/;

export function checkSyllables(text, syllableSet) {
  if (!syllableSet) return [];
  const out = [];
  for (const w of scanRomanWords(text)) {
    if (FOREIGN_RE.test(lettersOf(w.text))) continue;
    for (const syl of w.syls) {
      const k = sylKey(syl.s);
      if (!k || syllableSet.has(k)) continue;
      const near = nearKeys(k, syllableSet, 3);
      const sug = near.length ? `敢若是：${near.join("、")}？` : "";
      out.push({
        start: syl.start,
        end: syl.end,
        cat: "syllable",
        msg: `詞典揣無這个音節「${syl.s}」。${sug}建議檢查敢有拍毋著。`,
      });
    }
  }
  return out;
}

// ---------- 檢查 6：連字符 ----------

// 詞典 → 2–4 音節讀音（數字調、空白隔）Set。
// src:"rime" 是主詞庫對語料算出來的連紲音節（有一、是一、的大），毋是詞，袂收。
// moeWords（教典詞目 Set）有予 → 干焦收教典詞目：iTaigi／台華內底的片語
// （攏無 lóng bô、予人 hōo lâng）教典台羅是分開寫的，連字符照教育部詞目較穩。
export function buildMultiReadings(dict, moeWords = null) {
  const set = new Set();
  for (const [w, e] of Object.entries(dict ?? {})) {
    if (e.src === "rime") continue;
    if (moeWords && !moeWords.has(w)) continue;
    for (const r of e.r ?? []) {
      const syls = String(r).split(/\s+/).filter(Boolean);
      if (syls.length >= 2 && syls.length <= 4) set.add(syls.join(" "));
    }
  }
  return set;
}

// 隔空白連紲的單音節詞，讀音（含調）佮詞典多音節讀音仝 → 建議用連字符接做伙。
export function checkHyphens(text, multiReadings) {
  if (!multiReadings) return [];
  const t = String(text ?? "");
  const words = scanRomanWords(t);
  const numeric = (w) => pojToTl(normSyl(w.text));
  const out = [];
  let i = 0;
  while (i < words.length) {
    if (words[i].syls.length !== 1) { i++; continue; }
    const run = [words[i]];
    while (i + run.length < words.length && words[i + run.length].syls.length === 1
      && /^\s+$/.test(t.slice(words[i + run.length - 1].end, words[i + run.length].start))) {
      run.push(words[i + run.length]);
    }
    let step = 1;
    for (let L = Math.min(4, run.length); L >= 2; L--) {
      const grp = run.slice(0, L);
      if (multiReadings.has(grp.map(numeric).join(" "))) {
        out.push({
          start: grp[0].start,
          end: grp[grp.length - 1].end,
          cat: "hyphen",
          msg: `「${grp.map((w) => w.text).join(" ")}」是一个詞，建議用連字符寫做「${grp.map((w) => w.text).join("-")}」。`,
          fix: grp.map((w) => w.text).join("-"),
        });
        step = L;
        break;
      }
    }
    i += step;
  }
  return out;
}

// ---------- 檢查 7：推薦用字 ----------

// iongji.json items → Map 異用字 → { word, tl }。recAlts（家嘛嘛是推薦字）毋入。
export function buildAltMap(items) {
  const map = new Map();
  for (const it of items ?? []) {
    for (const alt of it.alts ?? []) {
      if (alt === it.word || (it.recAlts ?? []).includes(alt)) continue;
      if (!map.has(alt)) map.set(alt, { word: it.word, tl: it.tl ?? "" });
    }
  }
  return map;
}

// 700 表讀音（調符）→ 數字調集合（「hia--ê」「kan-na」攏轉，空白／連字號隔音節）。
const readingNums = (tl) =>
  pojToTl(String(tl ?? "")).split(/[\s-]+/).filter(Boolean).map(addImplicitTone).join(" ");

// yongji.json items（700 全表）→ 單字的「華語字／異用字 → 推薦字」對照：
// 字 → [{ word, tl, num }]。來源：① 單字推薦字的單字異用字（recAlts 除外）；
// ② 單字推薦字的「對應華語」單字（个←個、跤←腳、食←吃）。毋是推薦字家己。
// 詞內有用著才會比對讀音（num），所以「重要」的 要（iàu）袂去對著 欲（beh）。
export function buildCharMap(items) {
  const map = new Map();
  const words = new Set((items ?? []).map((it) => it.word));
  const add = (ch, it) => {
    if (ch === it.word || [...ch].length !== 1) return;
    const num = readingNums(it.tl);
    const arr = map.get(ch) ?? [];
    if (!arr.some((e) => e.word === it.word && e.num === num)) arr.push({ word: it.word, tl: it.tl, num });
    map.set(ch, arr);
  };
  for (const it of items ?? []) {
    if ([...it.word].length !== 1) continue;
    for (const a of it.alts ?? []) if (!words.has(a)) add(a, it);
    for (const h of String(it.hoa ?? "").split(/[、，,]/)) add(h.trim(), it);
  }
  return map;
}

// yongji.json items → 推薦字 → 讀音（數字調）Set；LKK 模式詞內比對讀音用。
export function buildWordReadings(items) {
  const map = new Map();
  for (const it of items ?? []) {
    if (!map.has(it.word)) map.set(it.word, new Set());
    map.get(it.word).add(readingNums(it.tl));
  }
  return map;
}

// segment 的 w 段 → 逐字 { ch, start, end, nums }：nums 是逐讀音對位的音節（音節數＝字數才算）。
function wordChars(seg, start) {
  const chars = [...seg.han];
  const per = chars.map(() => new Set());
  for (const r of seg.readings ?? []) {
    const syls = r.split(/\s+/).filter(Boolean);
    if (syls.length !== chars.length) continue;
    syls.forEach((s, k) => per[k].add(addImplicitTone(s)));
  }
  const out = [];
  let pos = start;
  chars.forEach((ch, k) => {
    out.push({ ch, start: pos, end: pos + ch.length, nums: per[k] });
    pos += ch.length;
  });
  return out;
}

// segment 的獨立詞（w／miss）→ 位置（游標 indexOf 對原文，mergeMixed 的短詞嘛穩）。
function walkSegments(text, segs, cb) {
  const t = String(text ?? "");
  let cursor = 0;
  for (const seg of segs ?? []) {
    const piece = seg.t === "w" ? seg.han : seg.s;
    if (!piece) continue;
    const idx = t.indexOf(piece, cursor);
    if (idx < 0) continue;
    cursor = idx + piece.length;
    cb({ seg, piece, start: idx, end: idx + piece.length });
  }
}

// 干焦 segment() 共異用字切做獨立詞（w／miss）的所在才受點；
// 按呢「重要」內底的「要」袂冤枉受點。
// 「這個」這款詞典詞：詞內的華語字（個）讀音佮推薦字（个 ê）仝，而且換了後是詞典詞
// （這个），才建議（opts.charMap／opts.dict）——按呢 香水 袂建議 芳水／香媠。
// LKK 模式（opts.mode === "lkk"）：推薦字家己 LKK 寫羅馬字（一式）→ 建議直接改 LKK 寫法。
export function checkHanji(text, segs, altMap, opts = {}) {
  if (!altMap) return [];
  const out = [];
  const lkkMap = opts.mode === "lkk" ? opts.lkkMap : null;
  const suggest = (start, end, info) => {
    const loForms = lkkMap
      ? (lkkMap.get(info.word) ?? []).filter((e) => e.kind === "lo")
      : [];
    if (loForms.length === 1) {
      out.push({
        start,
        end,
        cat: "hanji",
        msg: `教育部推薦用字：${info.word}（${info.tl}）；LKK 漢羅表建議寫「${loForms[0].form}」`,
        fix: loForms[0].form,
      });
      return;
    }
    out.push({
      start,
      end,
      cat: "hanji",
      msg: `教育部推薦用字：${info.word}（${info.tl}）`,
      fix: info.word,
    });
  };
  walkSegments(text, segs, ({ seg, piece, start, end }) => {
    if (altMap.has(piece)) {
      suggest(start, end, altMap.get(piece));
      return;
    }
    if (seg.t !== "w" || !opts.charMap || !opts.dict) return;
    for (const c of wordChars(seg, start)) {
      const hit = (opts.charMap.get(c.ch) ?? []).find((e) => {
        if (!c.nums.has(e.num)) return false;
        const fixed = piece.replace(c.ch, e.word);
        return fixed !== piece && fixed in opts.dict;
      });
      if (hit) suggest(c.start, c.end, hit);
    }
  });
  return out;
}

// ---------- 檢查 9：LKK 漢羅用字（用字規範「LKK 漢羅」模式） ----------

// yongji.json items → Map 推薦字 → lkk 寫法 [{form, kind}]（lo 羅馬字／mix 漢羅混）。
// 同字重複項目（homograph 讀音拆開）愛合併，{form, kind} 去重。
export function buildLkkMap(items) {
  const map = new Map();
  for (const it of items ?? []) {
    for (const e of it.lkk ?? []) {
      if (!map.has(it.word)) map.set(it.word, []);
      const arr = map.get(it.word);
      if (!arr.some((x) => x.form === e.form && x.kind === e.kind)) {
        arr.push({ form: e.form, kind: e.kind });
      }
    }
  }
  return map;
}

const lkkForms = (lkk) => (lkk ?? []).filter((e) => e.kind === "lo" || e.kind === "mix");

// 推薦字獨立成詞而且 LKK 表寫羅馬字／漢羅混 → 建議 LKK 寫法。
// 一式→有 fix；幾若式→列出來無 auto-fix（親像 遐的 hia ê／hia--ê／hia-ê）。
// 單字推薦字佇詞典詞內底（我的 guá ê）：讀音佮 700 表仝（opts.wordReadings）才建議，
// 按呢「目的 bo̍k-tik」的 的 袂受點；多字推薦字（按呢）佇長詞內底照舊免。
export function checkLkk(text, segs, lkkMap, opts = {}) {
  if (!lkkMap) return [];
  const out = [];
  const push = (start, end, piece, forms) => {
    if (forms.length === 1) {
      const e = forms[0];
      out.push({
        start,
        end,
        cat: "hanji",
        msg: e.kind === "lo"
          ? `LKK 漢羅表建議寫羅馬字：${e.form}（教育部推薦漢字：${piece}）`
          : `LKK 漢羅表建議漢羅混寫：${e.form}（教育部推薦漢字：${piece}）`,
        fix: e.form,
      });
      return;
    }
    out.push({
      start,
      end,
      cat: "hanji",
      msg: `LKK 漢羅表有幾若種寫法：${forms.map((e) => e.form).join("、")}（教育部推薦漢字：${piece}）`,
    });
  };
  walkSegments(text, segs, ({ seg, piece, start, end }) => {
    const forms = lkkForms(lkkMap.get(piece));
    if (forms.length) {
      push(start, end, piece, forms);
      return;
    }
    if (seg.t !== "w" || !opts.wordReadings || [...piece].length < 2) return;
    for (const c of wordChars(seg, start)) {
      const cf = lkkForms(lkkMap.get(c.ch));
      const nums = opts.wordReadings.get(c.ch);
      if (cf.length && nums && [...nums].some((n) => c.nums.has(n))) push(c.start, c.end, c.ch, cf);
    }
  });
  return out;
}

// ---------- 檢查 8：華語直譯／輕聲 ----------
// 把關（詞內毋報、了 干焦句尾、量詞 把、輕聲干焦句尾）佇 grammar-rules.js，佮轉換頁共用。

// opts.recWords（700 推薦字）：hints 內底本身就是推薦字的（的 → ê）毋報——
// 教育部 700 寫「的」無毋著；LKK 寫 ê 由檢查 9 照讀音判（目的 bo̍k-tik 袂冤枉）。
// opts.spans（wordSpans）有予：落佇詞典長詞內底的毋報。
export function checkCalqueLighttone(text, hints, opts = {}) {
  const t = String(text ?? "");
  const used = new Array(t.length).fill(false);
  const free = (start, len) => {
    for (let i = 0; i < len; i++) if (used[start + i]) return false;
    return true;
  };
  const take = (start, len) => {
    for (let i = 0; i < len; i++) used[start + i] = true;
  };
  const out = [];
  const calque = (hints?.calque ?? []).filter((c) => !opts.recWords?.has(c.han));
  for (const c of calque.sort((a, b) => b.han.length - a.han.length)) {
    let idx = 0;
    while ((idx = t.indexOf(c.han, idx)) !== -1) {
      const end = idx + c.han.length;
      const ok = free(idx, c.han.length) && calqueAllowed(t, idx, end, c.han, opts.spans);
      if (ok) {
        out.push({
          start: idx,
          end,
          cat: "calque",
          msg: `華語直譯「${c.han}」：台語建議寫「${c.suggest}」。`,
          ...(c.note ? { note: c.note } : {}),
        });
        take(idx, c.han.length);
      }
      idx += c.han.length;
    }
  }
  for (const lt of hints?.lighttone ?? []) {
    let idx = 0;
    while ((idx = t.indexOf(lt.han, idx)) !== -1) {
      const end = idx + lt.han.length;
      if (free(idx, lt.han.length) && lighttoneAllowed(t, idx, end, opts.spans)) {
        out.push({
          start: idx,
          end,
          cat: "calque",
          msg: `「${lt.han}」佇句尾通常讀輕聲，建議標：「${lt.marked}」。`,
          fix: lt.marked,
        });
        take(idx, lt.han.length);
      }
      idx += lt.han.length;
    }
  }
  return out;
}

// ---------- 檢查 11：華語句式（grammar-rules.js；逐條連文法筆記）----------
export function checkGrammar(text, spans) {
  return findGrammar(text, spans).map((g) => ({ ...g, cat: "grammar" }));
}

// ---------- 檢查 10：華語用字（打華語／華語直寫） ----------

// 詞典 → 華語義索引：華語詞 → 推薦的台語詞（音節數＝字數、有讀音）。
// 阿嬤（華語義）→ 阿媽（a1 ma2）；詞佮華語義仝字（伊←他）就袂入——伊 是台語字。
export function buildGlossIndex(dict) {
  const map = new Map();
  for (const [w, e] of Object.entries(dict ?? {})) {
    if (!e.h || !e.r?.length || !Array.isArray(e.r)) continue;
    const chars = [...w];
    if (!chars.length || !chars.every(isHanChar)) continue;
    if (chars.length !== e.r[0].split(/\s+/).filter(Boolean).length) continue;
    for (const g of String(e.h).split(/[、，,；;／/]/).map((s) => s.trim())) {
      if (!g || g === w || /[()（）=]/.test(g)) continue;
      const arr = map.get(g) ?? [];
      if (!arr.some((x) => x.word === w)) arr.push({ word: w, r: e.r[0] });
      map.set(g, arr);
    }
  }
  return map;
}

const isHanChar = (ch) => {
  const c = ch.codePointAt(0);
  return (0x3400 <= c && c <= 0x9fff) || (0x20000 <= c && c <= 0x3ffff);
};

// 「嗎」這款華語語氣詞改由文法規則（q-final）報，連文法筆記。

// 詞典揣無讀音的漢字（miss）→ 揣華語義：就只是華語字／詞，建議台語講法。
// 「我的阿嬤」→ 阿嬤 → 教育部辭典寫 阿媽（a-má）；「這個對嗎？」→ 嗎 是華語語氣詞。
// span 會向左攑 1–2 字（阿 是詞典詞、嬤 是 miss，阿嬤 才揣會著）佮向右 1–3 字，
// 揣上短的華語義 hit；重疊的 span 佇 runChecks 去重。
export function checkHoabun(text, segs, glossIndex) {
  if (!glossIndex) return [];
  const out = [];
  walkSegments(text, segs, ({ seg, piece, start }) => {
    if (seg.t !== "miss" || !isHanChar(piece)) return;
    let hitSpan = null;
    for (let len = 1; len <= 4 && !hitSpan; len++) {
      for (let s = Math.max(0, start - (len - 1)); s <= start && !hitSpan; s++) {
        if (s + len <= start) continue; // span 愛攬著 miss 字
        const span = text.slice(s, s + len);
        if ([...span].every(isHanChar) && glossIndex.has(span)) hitSpan = { span, start: s, end: s + len };
      }
    }
    const span = hitSpan?.span ?? piece;
    const s0 = hitSpan?.start ?? start;
    const width = hitSpan ? hitSpan.end - hitSpan.start : 1;
    const uniq = [...new Map((glossIndex.get(span) ?? []).map((x) => [x.word, x])).values()].slice(0, 3);
    if (uniq.length) {
      out.push({
        start: s0,
        end: s0 + width,
        cat: "hoabun",
        msg: `「${span}」是華語用字：台語辭典無這个讀音，建議寫「${uniq.map((x) => x.word).join("」、「")}」（${formatRomanization(uniq[0].r)}）。`,
        fix: uniq.length === 1 ? uniq[0].word : undefined,
      });
      return;
    }
    if (width === 1) {
      out.push({
        start,
        end: start + 1,
        cat: "hoabun",
        msg: `「${piece}」佇台語詞典揣無讀音，可能是華語字——台語敢有別的講法？`,
      });
    }
  });
  return out;
}

// ---------- 總匣 ----------

// 全部檢查合做伙（照 CATS 順序做優先權），重疊 span 留頭先那條。
// 詞典相關資料（syllableSet／multiReadings／altMap／charMap／wordReadings／recWords／
// glossIndex／hints／segments）有才做 5–11；opts.mode === "lkk" → rule 9 佮 7 的 LKK 講法。
// 文法規則（11）排佇華語直譯（8）佮華語用字（10）頭前：仝一个 span（不會、嗎）留文法彼條。
export function runChecks(text, opts = {}) {
  const t = String(text ?? "");
  const mode = opts.mode === "lkk" ? "lkk" : "moe";
  const spans = opts.segments ? wordSpans(t, opts.segments) : null;
  const sorted = [
    ...checkSpelling(t, opts.target ?? null),
    ...checkHyphens(t, opts.multiReadings),
    ...checkSyllables(t, opts.syllableSet),
    ...checkHanji(t, opts.segments, opts.altMap, {
      mode, lkkMap: opts.lkkMap, charMap: opts.charMap, dict: opts.dict,
    }),
    ...(mode === "lkk"
      ? checkLkk(t, opts.segments, opts.lkkMap, { wordReadings: opts.wordReadings })
      : []),
    ...(spans ? checkGrammar(t, spans) : []),
    ...checkCalqueLighttone(t, opts.hints, { recWords: opts.recWords, spans }),
    ...checkHoabun(t, opts.segments, opts.glossIndex),
  ].map((i, k) => ({ ...i, k }))
    .sort((a, b) => a.start - b.start || a.k - b.k);
  return dedupeOverlap(sorted).map(({ k, ...i }) => i);
}
