// 變調練習頁：A. 變調分析（漢羅／全羅 → 逐音節本調佮變調、點音節手動切調組）
// B. 變調小測驗（教典例句的連字號詞、問連讀變調、10 題一輪、記錄入 study-store）。
// 外部資料（詞典＝分析、listen.json＝測驗）干焦用讀的；畫面一律 textContent，無 innerHTML。
import { createStudy } from "../study-store.js?v=1";
import { segment, isHan } from "../../thak/js/dict.js?v=26";
import { loadDictBundle } from "../../try/practice-sources.js?v=3";
import {
  analyzeRoman, analyzeHanlo, applySandhi, toggleEnd, romanOf,
  sentencePool, makeRound, TONE_OPTIONS, cardId,
} from "./sandhi-core.js?v=2";

const $ = (id) => document.getElementById(id);
const el = (tag, cls, text) => {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (text != null) e.textContent = text;
  return e;
};

const QUIZ_N = 10;
const study = createStudy();

// ---- 詞典（分析漢羅愛用；第一擺約 8 MB，需要才載）＋教典例句（測驗詞池，約 200 KB）----
let bundlePromise = null;
function ensureBundle() {
  bundlePromise ??= loadDictBundle();
  bundlePromise.catch(() => { bundlePromise = null; });
  return bundlePromise;
}
let lekuPromise = null;
function ensureLeku() {
  lekuPromise ??= fetch(new URL("../data/listen.json", import.meta.url)).then((r) => {
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    return r.json();
  });
  lekuPromise.catch(() => { lekuPromise = null; });
  return lekuPromise;
}
let poolCache = null;

function setStatus(msg, bad = false) {
  const s = $("sd-status");
  s.textContent = msg ?? "";
  s.classList.toggle("bad-text", bad);
}

// ---- A. 變調分析 ----
let syls = [];
let manualEnds = [];
let pojOn = false;

async function analyze() {
  const text = $("sd-text").value.trim();
  manualEnds = [];
  if (!text) {
    setStatus("請輸入一句台文。", true);
    renderAnalysis();
    return;
  }
  try {
    if ([...text].some(isHan)) {
      setStatus("詞典載入中…（第一擺約 8 MB）");
      const { dict, rev } = await ensureBundle();
      syls = analyzeHanlo(segment(text, dict, rev));
    } else {
      syls = analyzeRoman(text);
    }
    setStatus("");
  } catch {
    setStatus("詞典載入失敗，請重新整理", true);
    return;
  }
  renderAnalysis();
}

const toneLabel = (s) =>
  s.light ? "輕聲"
  : !s.base ? "不明"
  : s.changed ? `${s.baseTone}→${s.outTone}`
  : s.baseTone;

function renderAnalysis() {
  const box = $("sd-result");
  box.replaceChildren();
  const out = applySandhi(syls, manualEnds);
  if (!out.length) {
    box.append(el("p", "muted", "揣無音節。"));
    return;
  }
  out.forEach((s, i) => {
    const cell = document.createElement("button");
    cell.type = "button";
    cell.className = "sd-syl"
      + (s.end ? " sd-end" : "")
      + (manualEnds.includes(i) ? " sd-manual" : "")
      + (s.light ? " sd-light" : "");
    cell.title = "切／接調組（手動界限）";
    if (s.han) cell.append(el("span", "sd-han", s.han));
    cell.append(el("span", "sd-reading", s.base ? romanOf(s.base, pojOn) : "—"));
    cell.append(el("span", "sd-tone" + (s.changed ? " changed" : ""), toneLabel(s)));
    cell.addEventListener("click", () => {
      manualEnds = toggleEnd(manualEnds, i);
      renderAnalysis();
    });
    box.append(cell);
    if (s.end && i < out.length - 1) box.append(el("span", "sd-sep", "｜"));
  });
}

// ---- B. 變調小測驗 ----
let quiz = null; // {qs, qi, correct}
let answered = false;

function startQuiz() {
  setStatus("教典例句載入中…");
  $("sd-quiz-start").disabled = true;
  ensureLeku().then(({ items }) => {
    poolCache ??= sentencePool(items);
    quiz = { qs: makeRound(poolCache, QUIZ_N), qi: 0, correct: 0 };
    answered = false;
    $("sd-quiz-result").hidden = true;
    $("sd-quiz").hidden = false;
    $("sd-quiz-start").disabled = false;
    setStatus("");
    renderQuestion();
  }).catch(() => {
    $("sd-quiz-start").disabled = false;
    setStatus("例句載入失敗，請重新整理", true);
  });
}

function renderQuestion() {
  const q = quiz.qs[quiz.qi];
  $("sd-quiz-n").textContent = `第 ${quiz.qi + 1}／${quiz.qs.length} 題`;
  $("sd-quiz-score").textContent = `著 ${quiz.correct} 題`;
  $("sd-quiz-q").textContent = `『${q.han}』第 ${q.i + 1} 字連讀時讀第幾聲？`;
  $("sd-quiz-sent").textContent = q.sent ? `例句：${q.sent}（${q.hoa || q.sentTl}）` : "";
  const base = $("sd-quiz-base");
  base.replaceChildren();
  base.append("本調：");
  q.numeric.split(" ").forEach((s, k) => {
    if (k) base.append(" ");
    base.append(el("span", k === q.i ? "sd-ask" : "", romanOf(s, pojOn)));
  });
  const box = $("sd-quiz-choices");
  box.replaceChildren();
  for (const t of TONE_OPTIONS) {
    const b = el("button", "choice", t);
    b.type = "button";
    b.addEventListener("click", () => answer(t));
    box.append(b);
  }
  $("sd-quiz-fb").hidden = true;
  $("sd-quiz-next").hidden = true;
  answered = false;
}


function answer(digit) {
  if (!quiz || answered) return;
  answered = true;
  const q = quiz.qs[quiz.qi];
  const ok = digit === q.correct;
  for (const b of $("sd-quiz-choices").children) {
    b.disabled = true;
    if (b.textContent === q.correct) b.classList.add("ok");
    else if (b.textContent === digit) b.classList.add("bad");
  }
  const fb = $("sd-quiz-fb");
  fb.hidden = false;
  fb.replaceChildren(
    el("p", ok ? "ok-text" : "bad-text", ok ? "著！" : `拍毋著，正確是第 ${q.correct} 聲。`),
  );
  const pat = el("p");
  pat.append(`連讀：${romanOf(q.numeric, pojOn)} → `);
  pat.append(el("b", null, romanOf(q.pattern, pojOn)));
  fb.append(pat);
  study.record("sandhi", { n: 1, correct: ok ? 1 : 0 });
  if (ok) quiz.correct += 1;
  else {
    study.addCard({
      id: cardId(q),
      kind: "sandhi",
      front: { han: q.han, numeric: q.numeric, i: q.i },
      back: { tone: q.correct },
    });
    study.logMistake("sandhi");
  }
  $("sd-quiz-score").textContent = `著 ${quiz.correct} 題`;
  const next = $("sd-quiz-next");
  next.hidden = false;
  next.textContent = quiz.qi + 1 < quiz.qs.length ? "下一題" : "看結果";
}

function nextQuestion() {
  if (!quiz || !answered) return;
  if (quiz.qi + 1 < quiz.qs.length) {
    quiz.qi += 1;
    renderQuestion();
    return;
  }
  const n = quiz.qs.length;
  const res = $("sd-quiz-result");
  res.hidden = false;
  res.replaceChildren(
    el("p", "q-prompt", `${n} 題著 ${quiz.correct} 題（${Math.round((quiz.correct / n) * 100)}%）`),
    el("p", "muted", "拍毋著的已經加入弱點複習，會當佇「弱點複習」閣練習。"),
  );
  $("sd-quiz").hidden = true;
  $("sd-quiz-start").textContent = "閣考一擺";
}

// 鍵盤：測驗進行中直接用鍵盤 1 2 3 4 5 7 8 應答；應答了 Enter 下一題
document.addEventListener("keydown", (ev) => {
  if (!quiz || $("sd-quiz").hidden) return;
  const t = ev.target;
  if (t instanceof HTMLTextAreaElement || t instanceof HTMLInputElement
    || t instanceof HTMLSelectElement || t.isContentEditable) return;
  if (!answered && TONE_OPTIONS.includes(ev.key)) {
    ev.preventDefault();
    answer(ev.key);
  } else if (answered && (ev.key === "Enter" || ev.key === " ")) {
    ev.preventDefault();
    nextQuestion();
  }
});

// ---- 初始化 ----
for (const btn of document.querySelectorAll("#sd-script .seg-btn")) {
  btn.addEventListener("click", () => {
    pojOn = btn.dataset.poj === "1";
    for (const b of document.querySelectorAll("#sd-script .seg-btn")) {
      b.classList.toggle("is-active", b === btn);
    }
    renderAnalysis();
  });
}
$("sd-run").addEventListener("click", analyze);
$("sd-text").addEventListener("keydown", (ev) => {
  if (ev.key === "Enter" && (ev.ctrlKey || ev.metaKey)) {
    ev.preventDefault();
    analyze();
  }
});
$("sd-quiz-start").addEventListener("click", startQuiz);
$("sd-quiz-next").addEventListener("click", nextQuestion);
