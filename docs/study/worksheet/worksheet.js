// 學習單列印：例句庫隨機揀句抑是貼家己的文章，產生四種版型的學習單。
// 邏輯佇 worksheet-core.js（有 node 測試）；這檔干焦負責畫圖佮事件。
import { loadBank, fromCustom, CUSTOM_KEY } from "../../try/practice-sources.js?v=3";
import { buildSheet, pickBankItems } from "./worksheet-core.js?v=1";

const $ = (id) => document.getElementById(id);
const el = (tag, cls, text) => {
  const n = document.createElement(tag);
  if (cls) n.className = cls;
  if (text != null) n.textContent = text;
  return n;
};

const state = { source: "bank", type: "pair", poj: false, answers: false, n: 10 };
let bank = null; // loadBank() 結果
let meta = null; // 這張單的來源（例句庫抑是自訂文章）
let items = [];
let titleEl = null;

function status(msg, retry) {
  const box = $("ws-status");
  box.replaceChildren(msg ?? "");
  if (retry) {
    const b = el("button", "btn-ghost", "重試");
    b.type = "button";
    b.addEventListener("click", retry);
    box.append(" ", b);
  }
}

function segWire(id, cb) {
  $(id).addEventListener("click", (ev) => {
    const btn = ev.target.closest("button");
    if (!btn || btn.disabled || btn.classList.contains("is-active")) return;
    $(id).querySelector(".is-active")?.classList.remove("is-active");
    btn.classList.add("is-active");
    cb(btn);
  });
}

const today = () => {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
};

// 羅馬字文章無漢字通寫：寫漢字版型退做對照
function effectiveType() {
  if (state.type === "hanji" && items.length && !items.some((it) => it.slots.some((s) => s.h))) return "pair";
  return state.type;
}

function sourceNote() {
  if (meta?.kind === "bank") return `例句庫 ${items.length} 句。`;
  if (meta?.kind === "custom") return `自訂文章 ${items.length} 句。`;
  return "";
}

function attribution() {
  return meta?.kind === "bank" ? meta.license : "自訂文章";
}

function renderRow(row) {
  const item = el("div", "sheet-item");
  if (row.kind === "pair") {
    const line = el("p", "sheet-pair");
    for (const c of row.cells) {
      if (c.reading == null) {
        line.append(c.top);
        continue;
      }
      const ruby = document.createElement("ruby");
      ruby.append(c.top);
      const rt = document.createElement("rt");
      rt.textContent = c.reading;
      ruby.append(rt);
      line.append(ruby);
    }
    item.append(line);
  } else if (row.kind === "roman") {
    item.append(el("p", "sheet-han", row.han), el("div", "wline"));
  } else if (row.kind === "hanji") {
    item.append(el("p", "sheet-roman", row.roman));
    const boxes = el("div", "box-row");
    for (let i = 0; i < row.boxes; i++) boxes.append(el("span", "box"));
    if (row.boxes) item.append(boxes);
  } else {
    item.append(el("p", "sheet-gloss", row.gloss), el("div", "wline"), el("div", "wline"));
  }
  return item;
}

function renderSheet() {
  document.getElementById("app-loading")?.remove();
  const sheet = $("ws-sheet");
  if (!items.length) {
    sheet.replaceChildren();
    sheet.hidden = true;
    $("ws-print").disabled = true;
    titleEl = null;
    return;
  }
  const data = buildSheet(items, { type: effectiveType(), poj: state.poj, answers: state.answers });
  sheet.replaceChildren();

  const head = el("header", "sheet-head");
  titleEl = el("h2", null, $("ws-title").value.trim() || "台語學習單");
  head.append(titleEl);
  const metaLine = el("div", "sheet-meta");
  metaLine.append(el("span", null, today()), el("span", null, "姓名：＿＿＿＿＿"));
  head.append(metaLine);
  sheet.append(head);

  if (items.some((it) => it.autoReading)) sheet.append(el("p", "sheet-note", "讀音是自動標音，可能有誤。"));

  for (const row of data.rows) sheet.append(renderRow(row));

  if (data.answers.length) {
    const ans = el("section", "sheet-answers");
    ans.append(el("h2", null, "答案"));
    for (const a of data.answers) {
      const r = el("div", "ans-row");
      r.append(el("span", "han", a.han));
      const roman = el("span", "roman", a.roman);
      r.append(roman);
      ans.append(r);
    }
    sheet.append(ans);
  }

  sheet.append(el("footer", "sheet-foot", `資料來源：${attribution()} ・ taigi.anatomind.com`));
  sheet.hidden = false;
  $("ws-print").disabled = false;
}

function update(note) {
  renderSheet();
  const fallback = effectiveType() !== state.type ? "羅馬字文章無漢字通寫，這馬用對照版型。" : sourceNote();
  status(note ?? fallback);
}

async function initBank() {
  if (bank) return;
  status("例句庫載入中…");
  try {
    bank = await loadBank();
    reshuffle();
  } catch {
    status("例句庫載入失敗。", initBank);
  }
}

function reshuffle() {
  if (!bank) return;
  items = pickBankItems(bank.items, state.n);
  meta = bank;
  update();
}

async function makeCustom() {
  const text = $("ws-text").value.trim();
  if (!text) {
    status("請先貼文章。");
    return;
  }
  status("處理中…（漢羅愛載詞典，第一擺約 8 MB）");
  try {
    const src = await fromCustom(text);
    if (!src.items.length) {
      status("揣無會使練習的句子，請換一段文章。");
      return;
    }
    meta = src;
    items = src.items;
    update();
  } catch {
    status("詞典載入失敗，請閣試一擺。", makeCustom);
  }
}

function setSource(source) {
  state.source = source;
  $("ws-bank-ctl").hidden = source === "custom";
  $("ws-custom").hidden = source !== "custom";
  // 華語→台語干焦例句庫有華語釋義
  const glossBtn = $('ws-type').querySelector('[data-type="gloss"]');
  glossBtn.disabled = source === "custom";
  if (source === "custom" && state.type === "gloss") {
    state.type = "pair";
    glossBtn.classList.remove("is-active");
    $('ws-type').querySelector('[data-type="pair"]').classList.add("is-active");
  }
  if (source === "bank") {
    if (bank) reshuffle();
    else initBank();
  } else {
    status("貼文章了後按「產生」。");
  }
}

function init() {
  try {
    $("ws-text").value = localStorage.getItem(CUSTOM_KEY) ?? "";
  } catch { /* 私密模式：無要緊 */ }

  segWire("ws-src", (btn) => setSource(btn.dataset.src));
  segWire("ws-type", (btn) => {
    state.type = btn.dataset.type;
    update();
  });
  segWire("ws-rom", (btn) => {
    state.poj = btn.dataset.rom === "poj";
    update();
  });
  $("ws-n").addEventListener("change", (ev) => {
    state.n = Number(ev.target.value);
    if (bank) reshuffle();
  });
  $("ws-shuffle").addEventListener("click", () => (bank ? reshuffle() : initBank()));
  $("ws-make").addEventListener("click", makeCustom);
  $("ws-answers").addEventListener("change", (ev) => {
    state.answers = ev.target.checked;
    update();
  });
  $("ws-title").addEventListener("input", (ev) => {
    if (titleEl) titleEl.textContent = ev.target.value.trim() || "台語學習單";
  });
  $("ws-print").addEventListener("click", () => window.print());

  initBank();
}

init();
