// 弱點複習：到期卡一張一張複習（讀音／用字／華台／變調四種）。
// 答著升一格仔延後閣出；答毋著退轉第一格、10 分鐘後閣出。進度佇 study-store。
import { createStudy, INTERVAL_DAYS } from "../study-store.js?v=1";
import { gradeReading } from "./review-core.js?v=1";
import { formatRomanization, tlToPoj, pojFixDiacritics } from "../../thak/js/roman.js?v=26";

const MAX_BOX = INTERVAL_DAYS.length + 1;
const DAY = 86400000;
const study = createStudy();

const $ = (id) => document.getElementById(id);
const el = (tag, cls, text) => {
  const n = document.createElement(tag);
  if (cls) n.className = cls;
  if (text != null) n.textContent = text;
  return n;
};

const KIND_LABEL = { reading: "讀音", iongji: "用字", hoa2tai: "華台", sandhi: "變調" };
const CAT_LABEL = {
  tone: "聲調", aspiration: "送氣", initial: "聲母", final: "韻母",
  nasal: "鼻音", hanji: "用字", sandhi: "變調", other: "其他",
};
const CAT_TIP = {
  tone: "數字調 1–8 愛記牢：入聲是 4、8（-p/-t/-k/-h 結尾）。",
  aspiration: "p／ph、t／th、k／kh、ts／tsh 愛分清楚。",
  initial: "b／m、l／n、g／ng 愛分清楚，多聽多唸。",
  final: "韻尾 -m/-n/-ng 佮 -p/-t/-k/-h 愛分清楚。",
  nasal: "鼻化韻 nn（親像 sann 三）袂使拍毋見。",
  hanji: "同音字真濟，記教育部推薦用字。",
  sandhi: "連讀變調：前字變調，上尾一字維持本調。",
  other: "共正確讀音唸幾擺，隔轉工閣複習一擺。",
};

let answered = 0; // 這擺複習已經應了幾張
let phase = "idle"; // idle | ask | feedback
let keys = null; // 這馬卡片的全域鍵盤 listener

function armKeys(handler) {
  keys?.abort();
  keys = new AbortController();
  document.addEventListener("keydown", handler, { signal: keys.signal });
}

const fmtTime = (t) =>
  new Date(t).toLocaleString("zh-TW", { month: "numeric", day: "numeric", hour: "2-digit", minute: "2-digit" });

// ---------- 統計／弱點／卡片清單 ----------

function refreshStats() {
  const cards = study.allCards();
  const now = Date.now();
  const stat = (label, n, unit) => {
    const s = el("span");
    s.append(`${label} `, el("b", null, String(n)), ` ${unit}`);
    return s;
  };
  $("rv-stat-line").replaceChildren(
    stat("今仔日到期", cards.filter((c) => c.due <= now).length, "張"),
    stat("全部卡片", cards.length, "張"),
    stat("7 工內複習過", cards.filter((c) => c.last >= now - 7 * DAY).length, "張"),
  );
  const counts = new Array(MAX_BOX + 1).fill(0);
  for (const c of cards) counts[Math.min(c.box ?? 1, MAX_BOX)] += 1;
  const max = Math.max(1, ...counts.slice(1));
  const boxes = $("rv-boxes");
  boxes.replaceChildren();
  for (let b = 1; b <= MAX_BOX; b++) {
    const col = el("div", "rv-box-col");
    const bar = el("div", "rv-box-bar");
    bar.style.height = `${Math.round((counts[b] / max) * 40)}px`;
    col.append(el("span", "rv-box-n", String(counts[b])), bar, el("span", null, `第${b}格`));
    boxes.append(col);
  }
  $("rv-stats").hidden = cards.length === 0;
}

function refreshMistakes() {
  const entries = Object.entries(study.mistakes()).sort((a, b) => b[1] - a[1]);
  const list = $("rv-mist-list");
  list.replaceChildren();
  for (const [cat, n] of entries) {
    const li = el("li");
    li.append(el("b", null, CAT_LABEL[cat] ?? cat), el("span", "rv-mist-n", `× ${n}`));
    if (CAT_TIP[cat]) li.append(el("span", "rv-mist-tip", CAT_TIP[cat]));
    list.append(li);
  }
  $("rv-mistakes").hidden = entries.length === 0;
}

function frontSummary(c) {
  const f = c.front ?? {};
  switch (c.kind) {
    case "reading": return f.ctx ? `${f.h}（${f.ctx}）` : `${f.h ?? ""}`;
    case "iongji": return `${f.q ?? ""}（${f.hoa ?? ""}）`;
    case "hoa2tai": return `${f.hoa ?? ""}`;
    case "sandhi": return `${f.han ?? ""} ${f.numeric ?? ""}`;
    default: return c.id;
  }
}

function refreshList() {
  const now = Date.now();
  const cards = study.allCards().sort((a, b) => a.due - b.due);
  const body = $("rv-table-body");
  body.replaceChildren();
  for (const c of cards) {
    const tr = el("tr");
    tr.append(
      el("td", null, KIND_LABEL[c.kind] ?? c.kind),
      el("td", "rv-front", frontSummary(c)),
      el("td", null, `${c.box ?? 1}／${MAX_BOX}`),
      el("td", null, c.due <= now ? "到期矣" : fmtTime(c.due)),
      el("td", null, `${c.right ?? 0}／${c.wrong ?? 0}`),
    );
    const td = el("td");
    const del = el("button", "btn-ghost rv-del", "刪除");
    del.type = "button";
    del.addEventListener("click", () => {
      if (!confirm("確定欲刪除這張卡片？")) return;
      study.removeCard(c.id);
      refreshAll();
    });
    td.append(del);
    tr.append(td);
    body.append(tr);
  }
  $("rv-list").hidden = cards.length === 0;
}

// ---------- 複習流程 ----------

function nextCard() {
  keys?.abort();
  $("rv-done").hidden = true;
  const [card] = study.dueCards(1);
  if (!card) {
    showDone();
    return;
  }
  phase = "ask";
  $("rv-progress").textContent = `第 ${answered + 1} 張・猶有 ${study.dueCards().length} 張`;
  const body = $("rv-body");
  body.replaceChildren();
  $("rv-session").hidden = false;
  (RENDER[card.kind] ?? renderUnknown)(card, body);
}

// 答案揭曉了後：記進度、記弱點、閣出「後一張」
function settle(card, ok, cats = []) {
  study.answer(card.id, ok);
  study.record("review", { n: 1, correct: ok ? 1 : 0 });
  for (const c of cats) study.logMistake(c);
  answered += 1;
  phase = "feedback";
  refreshStats();
  refreshMistakes();
  refreshList();
  const next = el("button", "btn primary", "後一張");
  next.type = "button";
  next.addEventListener("click", nextCard);
  const row = el("div", "btn-row");
  row.append(next);
  $("rv-body").append(row);
  const session = $("rv-session");
  session.classList.add(ok ? "flash-ok" : "flash-bad");
  setTimeout(() => session.classList.remove("flash-ok", "flash-bad"), 700);
  next.focus();
}

function showDone() {
  $("rv-session").hidden = true;
  keys?.abort();
  const cards = study.allCards();
  if (!cards.length) return;
  const next = Math.min(...cards.map((c) => c.due));
  $("rv-done-next").textContent = next <= Date.now()
    ? "閣有卡片到期矣。"
    : `後一張 ${fmtTime(next)} 閣出；這擺複習了 ${answered} 張。`;
  $("rv-done").hidden = false;
}

// ---------- 四種卡片 ----------

function renderReading(card, body) {
  const f = card.front;
  body.append(el("p", "q-prompt", f.h));
  if (f.ctx) {
    const ctx = el("p", "rv-ctx");
    const i = f.ctx.indexOf(f.h);
    if (i >= 0) ctx.append(f.ctx.slice(0, i), el("mark", "rv-hl", f.h), f.ctx.slice(i + f.h.length));
    else ctx.textContent = f.ctx;
    body.append(ctx);
  }
  if (f.hoa) body.append(el("p", "q-sub", `華語：${f.hoa}`));
  const input = el("input", "rv-input");
  input.type = "text";
  input.autocomplete = "off";
  input.autocapitalize = "none";
  input.spellcheck = false;
  input.placeholder = "拍讀音（TL／POJ）";
  input.setAttribute("aria-label", `${f.h} 的讀音`);
  body.append(input, el("p", "hint", "會使拍數字調，親像 png7；嘛會使用調符。"));
  input.focus({ preventScroll: true });
  input.addEventListener("keydown", (ev) => {
    if (ev.key !== "Enter" || phase !== "ask") return;
    ev.preventDefault();
    const raw = input.value.trim();
    if (!raw) return;
    const r = gradeReading(card.back.numeric, raw);
    input.disabled = true;
    const ans = el("div", "answer");
    ans.append(
      el("div", "han", `${f.h}：${formatRomanization(card.back.numeric)}`),
      el("div", "roman", `POJ：${pojFixDiacritics(formatRomanization(tlToPoj(card.back.numeric)))}`),
    );
    body.append(
      r.ok ? el("p", "ok-text", "答著矣！") : el("p", "bad-text", `拍毋著——${r.categories.map((c) => CAT_LABEL[c] ?? c).join("、")}無合。`),
      ans,
    );
    settle(card, r.ok, r.categories);
  });
}

function renderIongji(card, body) {
  const f = card.front;
  const opts = f.options ?? [];
  body.append(el("p", "q-prompt", f.q), el("p", "q-sub", `華語：${f.hoa}`));
  const box = el("div", "choices");
  opts.forEach((opt, k) => {
    const b = el("button", "choice");
    b.type = "button";
    b.append(el("span", "rv-no", String(k + 1)), document.createTextNode(opt));
    b.addEventListener("click", () => answerIongji(card, k));
    box.append(b);
  });
  body.append(box, el("p", "hint", "揀 1–4 抑是直接點字。"));
  armKeys((ev) => {
    if (phase !== "ask") return;
    const k = Number(ev.key) - 1;
    if (k >= 0 && k < opts.length) {
      ev.preventDefault();
      answerIongji(card, k);
    }
  });
}

function answerIongji(card, k) {
  if (phase !== "ask") return;
  const opts = card.front.options ?? [];
  const ok = opts[k] === card.back.word;
  const buttons = [...$("rv-body").querySelectorAll(".choice")];
  buttons.forEach((b, j) => {
    b.disabled = true;
    if (opts[j] === card.back.word) b.classList.add("ok");
  });
  if (!ok) buttons[k]?.classList.add("bad");
  const ans = el("div", "answer");
  ans.append(el("div", "han", `${card.back.word}（${card.back.tl}）`));
  $("rv-body").append(ans);
  settle(card, ok, ok ? [] : ["hanji"]);
}

function renderHoa2tai(card, body) {
  body.append(el("p", "q-prompt", card.front.hoa));
  body.append(el("p", "q-sub", "這句華語台語按怎講？看了答案了，家己評分。"));
  const look = el("button", "btn", "看答案");
  look.type = "button";
  const row = el("div", "btn-row");
  row.append(look);
  body.append(row);
  look.addEventListener("click", () => {
    look.hidden = true;
    const ans = el("div", "answer");
    ans.append(el("div", "han", card.back.han), el("div", "roman", card.back.tl));
    body.append(ans);
    const rate = el("div", "btn-row");
    const yes = el("button", "btn primary", "會");
    const no = el("button", "btn", "毋會");
    yes.type = "button";
    no.type = "button";
    yes.addEventListener("click", () => phase === "ask" && settle(card, true));
    no.addEventListener("click", () => phase === "ask" && settle(card, false));
    rate.append(yes, no);
    body.append(rate);
    yes.focus();
  });
}

function renderSandhi(card, body) {
  const f = card.front;
  const syls = String(f.numeric ?? "").split(/\s+/).filter(Boolean);
  body.append(el("p", "q-prompt", f.han));
  const line = el("p", "q-prompt");
  syls.forEach((s, j) => {
    if (j) line.append(" ");
    line.append(j === f.i ? el("mark", "rv-hl", formatRomanization(s)) : document.createTextNode(formatRomanization(s)));
  });
  body.append(line, el("p", "q-sub", "連讀的時，標黃彼字會變做偌濟聲調？"));
  const tones = [1, 2, 3, 4, 5, 7, 8];
  const box = el("div", "choices");
  tones.forEach((t) => {
    const b = el("button", "choice rv-tone", String(t));
    b.type = "button";
    b.addEventListener("click", () => answerSandhi(card, t, b));
    box.append(b);
  });
  body.append(box, el("p", "hint", "揀聲調數字，抑是直接點。"));
  armKeys((ev) => {
    if (phase !== "ask") return;
    const t = Number(ev.key);
    if (tones.includes(t)) {
      ev.preventDefault();
      answerSandhi(card, t, null);
    }
  });
}

function answerSandhi(card, tone, btn) {
  if (phase !== "ask") return;
  const ok = String(tone) === String(card.back.tone);
  const buttons = [...$("rv-body").querySelectorAll(".choice")];
  buttons.forEach((b) => {
    b.disabled = true;
    if (b.textContent === String(card.back.tone)) b.classList.add("ok");
  });
  if (!ok && btn) btn.classList.add("bad");
  $("rv-body").append(el("p", ok ? "ok-text" : "bad-text", `正確：第 ${card.back.tone} 聲`));
  settle(card, ok, ok ? [] : ["sandhi"]);
}

function renderUnknown(card, body) {
  body.append(el("p", "q-sub", `未知的卡片類型：${card.kind}`));
  const next = el("button", "btn", "後一張");
  next.type = "button";
  next.addEventListener("click", nextCard);
  const row = el("div", "btn-row");
  row.append(next);
  body.append(row);
}

const RENDER = { reading: renderReading, iongji: renderIongji, hoa2tai: renderHoa2tai, sandhi: renderSandhi };

// ---------- 開始 ----------

function refreshAll() {
  refreshStats();
  refreshMistakes();
  refreshList();
  const total = study.allCards().length;
  $("rv-empty").hidden = total > 0;
  $("rv-session").hidden = true;
  $("rv-done").hidden = true;
  if (total > 0) nextCard();
}

$("rv-recheck").addEventListener("click", () => {
  answered = 0;
  nextCard();
});

refreshAll();
