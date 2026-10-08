// 寫作檢查核心（純函式，無 DOM／fetch）：貼入的台文（TL／POJ／漢羅）→ 問題清單。
// 每條 issue = { start, end, cat, msg, fix? }：fix 是 [start, end) 的機械替換字串。
// 拼寫檢查（系統、數字調、調號/韻尾、調符位置）毋免詞典；
// 音節／連字符／用字／華語直譯的資料（詞典鍵集、segments、iongji、hints）由呼叫者注入。
// import 指定字串愛佮工具頁仝款（?v=26／?v=2），模組才袂載兩擺。
import {
  pojToTl, stripTones, formatRomanization, tlToPoj, pojFixDiacritics, toNumeric,
} from "../thak/js/roman.js?v=26";
import { sylKey } from "../try/practice-core.js?v=2";

// 分類（UI 分組用）：拼寫 1–4、音節 5、連字符 6、用字 7、華語直譯／輕聲 8。
export const CATS = [
  ["spelling", "拼寫"],
  ["syllable", "音節"],
  ["hyphen", "連字符"],
  ["hanji", "用字"],
  ["calque", "華語直譯／輕聲"],
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
  const sys = words.map((w) => wordSystem(w.text));
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

// 4. 調符位置：字母佮標準寫法仝、干焦調符囥別位 → fix 做標準位（照家己的系統）。
export function checkMarkPosition(text) {
  const out = [];
  for (const w of scanRomanWords(text)) {
    const wsys = wordSystem(w.text);
    for (const syl of w.syls) {
      if (/[1-9]/.test(syl.s)) continue; // 數字調是規則 2
      if (!hasToneMark(syl.s)) continue;
      const num = toNumeric(normSyl(syl.s));
      const sys = sylSystem(syl.s) ?? wsys ?? "tl";
      const std = (sys === "poj"
        ? pojFixDiacritics(formatRomanization(tlToPoj(num)))
        : formatRomanization(num)).normalize("NFC");
      const inN = syl.s.normalize("NFC");
      if (inN.toLowerCase() === std) continue;
      if (lettersOf(syl.s) !== lettersOf(std)) continue;
      const fx = /^[A-Z]/.test(inN) ? std[0].toUpperCase() + std.slice(1) : std;
      out.push({
        start: syl.start,
        end: syl.end,
        cat: "spelling",
        msg: `「${syl.s}」調符位置建議照標準寫做「${fx}」。`,
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
    ...checkMarkPosition(text),
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

export function checkSyllables(text, syllableSet) {
  if (!syllableSet) return [];
  const out = [];
  for (const w of scanRomanWords(text)) {
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
export function buildMultiReadings(dict) {
  const set = new Set();
  for (const e of Object.values(dict ?? {})) {
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

// 干焦 segment() 共異用字切做獨立詞（w／miss）的所在才受點；
// 按呢「重要」內底的「要」袂冤枉受點。位置用游標 indexOf 對原文。
export function checkHanji(text, segs, altMap) {
  if (!altMap) return [];
  const t = String(text ?? "");
  const out = [];
  let cursor = 0;
  for (const seg of segs ?? []) {
    const piece = seg.t === "w" ? seg.han : seg.s;
    if (!piece || !altMap.has(piece)) { // 無 hit 嘛愛行過去（推進 cursor 用）
      const idx = t.indexOf(piece ?? "", cursor);
      if (piece && idx >= 0) cursor = idx + piece.length;
      continue;
    }
    const idx = t.indexOf(piece, cursor);
    if (idx < 0) continue;
    cursor = idx + piece.length;
    const info = altMap.get(piece);
    out.push({
      start: idx,
      end: idx + piece.length,
      cat: "hanji",
      msg: `教育部推薦用字：${info.word}（${info.tl}）`,
      fix: info.word,
    });
  }
  return out;
}

// ---------- 檢查 8：華語直譯／輕聲 ----------

export function checkCalqueLighttone(text, hints) {
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
  for (const c of [...(hints?.calque ?? [])].sort((a, b) => b.han.length - a.han.length)) {
    let idx = 0;
    while ((idx = t.indexOf(c.han, idx)) !== -1) {
      if (free(idx, c.han.length)) {
        out.push({
          start: idx,
          end: idx + c.han.length,
          cat: "calque",
          msg: `華語直譯「${c.han}」：台語建議寫「${c.suggest}」。`,
        });
        take(idx, c.han.length);
      }
      idx += c.han.length;
    }
  }
  for (const lt of hints?.lighttone ?? []) {
    let idx = 0;
    while ((idx = t.indexOf(lt.han, idx)) !== -1) {
      if (free(idx, lt.han.length)) {
        out.push({
          start: idx,
          end: idx + lt.han.length,
          cat: "calque",
          msg: `「${lt.han}」建議標輕聲：「${lt.marked}」。`,
          fix: lt.marked,
        });
        take(idx, lt.han.length);
      }
      idx += lt.han.length;
    }
  }
  return out;
}

// ---------- 總匣 ----------

// 全部檢查合做伙（照 CATS 順序做優先權），重疊 span 留頭先那條。
// 詞典相關資料（syllableSet／multiReadings／altMap／hints／segments）有才做 5–8。
export function runChecks(text, opts = {}) {
  const t = String(text ?? "");
  const sorted = [
    ...checkSpelling(t, opts.target ?? null),
    ...checkHyphens(t, opts.multiReadings),
    ...checkSyllables(t, opts.syllableSet),
    ...checkHanji(t, opts.segments, opts.altMap),
    ...checkCalqueLighttone(t, opts.hints),
  ].map((i, k) => ({ ...i, k }))
    .sort((a, b) => a.start - b.start || a.k - b.k);
  return dedupeOverlap(sorted).map(({ k, ...i }) => i);
}
