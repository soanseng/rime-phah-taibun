// 華語→台語造句：看華語句、家己寫台語（漢羅抑是羅馬字）、對參考答案、家己評。
// 進度（句長過濾、順序 seed、第幾句、今仔日 tally）存佇 study-store 的 pos.hoa2tai，
// 重整了後照原順序繼續。參考答案佮華語攏照原句顯示（textContent）。
import { createStudy } from "../study-store.js?v=1";
import { loadBank } from "../../try/practice-sources.js?v=3";
import { readingOf } from "../../try/practice-core.js?v=2";
import { overlap, seededOrder, matchesLength } from "./hoa2tai-core.js?v=1";

const $ = (id) => document.getElementById(id);
const el = (tag, cls, text) => {
  const n = document.createElement(tag);
  if (cls) n.className = cls;
  if (text != null) n.textContent = text;
  return n;
};

const FILTERS = ["short", "mid", "long", "all"];
const localDate = () => {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
};

const study = createStudy();
const saved = study.getPos("hoa2tai") ?? {};
const state = {
  filter: FILTERS.includes(saved.filter) ? saved.filter : "all",
  seed: Number.isInteger(saved.seed) ? saved.seed : Math.floor(Math.random() * 0x7fffffff),
  i: Number.isInteger(saved.i) ? Math.max(0, saved.i) : 0,
  today:
    saved.today && saved.today.d === localDate()
      ? saved.today
      : { d: localDate(), n: 0, correct: 0 },
  poj: false,
  items: [], // 有華語 gloss 的例句
  pool: [], // 照這馬的句長過濾了後
  item: null,
  revealed: false,
};

const savePos = () =>
  study.setPos("hoa2tai", { filter: state.filter, seed: state.seed, i: state.i, today: state.today });

const currentItem = () =>
  state.pool.length
    ? state.pool[seededOrder(state.pool.length, state.seed)[state.i % state.pool.length]]
    : null;

function renderTally() {
  const t = state.today;
  $("ht-tally").replaceChildren(
    el("span", null, `今仔日：練 ${t.n} 句`),
    el("span", null, `會 ${t.correct} 句`),
  );
}

function renderRead() {
  if (!state.item) return;
  $("ht-read").textContent = state.item.slots
    .map((s) => readingOf(s, state.poj))
    .filter(Boolean)
    .join(" ");
}

function show() {
  const n = state.pool.length;
  $("ht-count").textContent = n ? `第 ${state.i + 1}／${n} 句` : "";
  state.item = currentItem();
  state.revealed = false;
  if (!state.item) {
    $("ht-card").hidden = true;
    $("ht-status").textContent = "這个句長揣無句子，請換另外一个句長。";
    renderTally();
    return;
  }
  $("ht-card").hidden = false;
  $("ht-status").textContent = "";
  $("ht-hoa").textContent = state.item.gloss;
  const input = $("ht-input");
  input.value = "";
  input.readOnly = false;
  $("ht-ans").hidden = true;
  $("ht-reveal").disabled = false;
  renderTally();
  input.focus();
}

function setFilter(filter, keepI = false) {
  if (!FILTERS.includes(filter)) return;
  state.filter = filter;
  state.pool = state.items.filter((it) => matchesLength(it.slots.length, filter));
  if (!keepI || state.i >= state.pool.length) state.i = 0;
  savePos();
  show();
}

function reveal() {
  if (!state.item || state.revealed) return;
  state.revealed = true;
  const hits = overlap(state.item.slots, $("ht-input").value);
  const ref = $("ht-ref");
  ref.replaceChildren();
  state.item.slots.forEach((s, idx) => {
    ref.append(el("span", hits[idx] ? "hit" : null, s.h ?? s.src));
  });
  renderRead();
  $("ht-ans").hidden = false;
  $("ht-input").readOnly = true;
  $("ht-reveal").disabled = true;
  $("ht-rate").querySelector("button").focus();
}

function rate(n) {
  if (!state.item || !state.revealed) return;
  const ok = n === 1;
  study.record("hoa2tai", { n: 1, correct: ok ? 1 : 0 });
  if (!ok) {
    // 毋會／差一屑仔 → 加入弱點複習卡（身份：漢羅原句＋讀音）
    study.addCard({ ...cardFor(state.item), src: "hoa2tai" });
  }
  state.today.n += 1;
  if (ok) state.today.correct += 1;
  state.i += 1;
  if (state.i >= state.pool.length) {
    state.seed = (state.seed + 1) >>> 0; // 一輪了，換一个 seed 閣洗一遍
    state.i = 0;
  }
  savePos();
  show();
}

async function init() {
  for (const b of $("ht-filter").querySelectorAll(".seg-btn")) {
    b.classList.toggle("is-active", b.dataset.len === state.filter);
  }
  try {
    const bank = await loadBank();
    state.items = bank.items.filter((it) => it.gloss && it.gloss.trim());
    setFilter(state.filter, true);
  } catch {
    $("ht-status").textContent = "例句庫載入失敗，請重新整理閣試一擺。";
    $("ht-count").textContent = "";
  }
}

$("ht-filter").addEventListener("click", (ev) => {
  const b = ev.target.closest(".seg-btn");
  if (b && b.dataset.len !== state.filter) setFilter(b.dataset.len);
});

$("ht-reveal").addEventListener("click", reveal);

$("ht-input").addEventListener("keydown", (ev) => {
  if ((ev.ctrlKey || ev.metaKey) && ev.key === "Enter") {
    ev.preventDefault();
    reveal();
  }
});

$("ht-roman").addEventListener("click", (ev) => {
  const b = ev.target.closest(".seg-btn");
  if (!b) return;
  const poj = b.dataset.roman === "poj";
  if (poj === state.poj) return;
  state.poj = poj;
  for (const x of $("ht-roman").querySelectorAll(".seg-btn")) x.classList.toggle("is-active", x === b);
  renderRead();
});

$("ht-rate").addEventListener("click", (ev) => {
  const b = ev.target.closest("button[data-rate]");
  if (b) rate(Number(b.dataset.rate));
});

// 評分快捷 1／2／3：答案掀開了後才作用，嘛袂去攪著猇咧拍字的 textarea／input
document.addEventListener("keydown", (ev) => {
  if (!state.revealed || ev.ctrlKey || ev.metaKey || ev.altKey) return;
  const tag = document.activeElement?.tagName;
  if (tag === "TEXTAREA" || tag === "INPUT") return;
  if (ev.key >= "1" && ev.key <= "3") {
    ev.preventDefault(); // 免得這个數字綴落去下一句的 textarea
    rate(Number(ev.key));
  }
});

init();
