// 寫作檢查頁 UI：貼台文 → 即時檢查（拼寫先；詞典載好了後規尾 9 條），
// 逐條建議會當一鍵「採用」，拼寫類閣有「全部採用」。改了隨時閣檢查。
// 用字規範會當揀「教育部 700（全漢字）」抑是「LKK 漢羅」（揀了記佇瀏覽器）。
// 檢查邏輯攏佇 check-core.js（純函式，有 node 測試）。
import { runChecks, buildSyllableSet, buildMultiReadings, buildAltMap, buildLkkMap, CATS } from "./check-core.js?v=2";
import { segment } from "../thak/js/dict.js?v=26";
import { loadDictBundle } from "../try/practice-sources.js?v=3";

const SAMPLES = [
  "Goá beh khì ha̍k-hāu, tsia̍h png7.",
  "伊𣍐曉泅水。你為什麼欲轉來？",
  "gua2 ai3 khì Tâi-pak, tsiah8 tsit8-e7 png7.",
];

const el = (tag, attrs = {}, ...kids) => {
  const n = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === "class") n.className = v;
    else if (k === "text") n.textContent = v;
    else if (k.startsWith("on")) n.addEventListener(k.slice(2), v);
    else n.setAttribute(k, v);
  }
  for (const kid of kids) if (kid != null) n.append(kid);
  return n;
};

const app = document.getElementById("app");
if (app) init();

function init() {
  const input = document.getElementById("chk-input");
  const status = document.getElementById("chk-status");
  const summary = document.getElementById("chk-summary");
  const fixAll = document.getElementById("chk-fix-all");
  const preview = document.getElementById("chk-preview");
  const issuesBox = document.getElementById("chk-issues");
  const sel = document.getElementById("chk-target");
  const yongjiSel = document.getElementById("chk-yongji");
  if (!input || !status || !summary || !fixAll || !preview || !issuesBox || !sel || !yongjiSel) return;
  const YONGJI_KEY = "phahtaibun.check.yongji";
  if (yongjiSel.value !== "lkk") yongjiSel.value = localStorage.getItem(YONGJI_KEY) === "lkk" ? "lkk" : "moe";

  let issues = [];
  let data = null; // { syllableSet, multiReadings, altMap, hints, dict, rev }
  let timer = 0;

  const checkNow = () => {
    const text = input.value;
    const target = sel.value === "auto" ? null : sel.value;
    const segs = data && text ? segment(text, data.dict, data.rev) : null;
    issues = runChecks(text, {
      target,
      mode: yongjiSel.value === "lkk" ? "lkk" : "moe",
      syllableSet: data?.syllableSet,
      multiReadings: data?.multiReadings,
      segments: segs,
      altMap: data?.altMap,
      lkkMap: data?.lkkMap,
      hints: data?.hints,
    });
    render();
  };

  const schedule = () => {
    clearTimeout(timer);
    timer = setTimeout(checkNow, 300);
  };

  const applyFixes = (list) => {
    let t = input.value;
    for (const i of [...list].sort((a, b) => b.start - a.start)) {
      t = t.slice(0, i.start) + i.fix + t.slice(i.end);
    }
    input.value = t;
    checkNow();
  };

  // 預覽：照 start 切段，問題的字串包 <mark>（title 有說明、點了跳去彼條）。
  const renderPreview = () => {
    const text = input.value;
    preview.replaceChildren();
    let pos = 0;
    issues.forEach((i, idx) => {
      if (i.start > pos) preview.append(text.slice(pos, i.start));
      preview.append(el("mark", {
        class: "chk-mark",
        "data-idx": String(idx),
        "data-cat": i.cat,
        title: i.msg,
        text: text.slice(i.start, i.end),
        onclick: () => {
          const li = issuesBox.querySelector(`[data-idx="${idx}"]`);
          if (!li) return;
          li.scrollIntoView({ block: "nearest", behavior: "smooth" });
          li.classList.add("flash");
          setTimeout(() => li.classList.remove("flash"), 900);
        },
      }));
      pos = i.end;
    });
    if (pos < text.length) preview.append(text.slice(pos));
  };

  const renderIssues = () => {
    issuesBox.replaceChildren();
    if (!issues.length) {
      summary.textContent = input.value ? "無揣著問題" : "佇頂懸貼台文，就開始檢查。";
      fixAll.hidden = true;
      return;
    }
    summary.textContent = `揣著 ${issues.length} 項建議`;
    for (const [key, label] of CATS) {
      const group = issues.map((i, idx) => ({ i, idx })).filter((x) => x.i.cat === key);
      if (!group.length) continue;
      const ul = el("ul");
      for (const { i, idx } of group) {
        const li = el("li", { class: "chk-issue", "data-idx": String(idx) },
          el("span", { class: "chk-msg", text: i.msg }));
        if (i.fix) li.append(el("button", {
          class: "btn", type: "button", text: "採用",
          onclick: () => applyFixes([i]),
        }));
        ul.append(li);
      }
      issuesBox.append(el("p", { class: "chk-cat", text: `${label}（${group.length}）` }), ul);
    }
    const spellFixes = issues.filter((i) => i.cat === "spelling" && i.fix);
    fixAll.hidden = !spellFixes.length;
    fixAll.onclick = () => applyFixes(spellFixes);
  };

  const render = () => {
    renderPreview();
    renderIssues();
  };

  input.addEventListener("input", schedule);
  sel.addEventListener("change", checkNow);
  yongjiSel.addEventListener("change", () => {
    try { localStorage.setItem(YONGJI_KEY, yongjiSel.value); } catch { /* 無 localStorage 嘛無妨 */ }
    checkNow();
  });
  for (const btn of document.querySelectorAll(".chk-sample")) {
    btn.addEventListener("click", () => {
      input.value = SAMPLES[Number(btn.dataset.i)] ?? "";
      checkNow();
      input.focus();
    });
  }
  checkNow();

  // 詞典（檢查 5–9 愛）：載好了隨閣檢查一擺。載敗猶會用拼寫檢查。
  Promise.all([
    loadDictBundle(),
    fetch(new URL("../study/data/iongji.json", import.meta.url)).then((r) => r.json()),
    fetch(new URL("../thak/data-public/hints.json", import.meta.url)).then((r) => r.json()),
    fetch(new URL("../study/data/yongji.json", import.meta.url)).then((r) => r.json()),
  ]).then(([bundle, iongji, hints, yongji]) => {
    data = {
      dict: bundle.dict,
      rev: bundle.rev,
      syllableSet: buildSyllableSet(bundle.dict),
      multiReadings: buildMultiReadings(bundle.dict),
      altMap: buildAltMap(iongji.items),
      lkkMap: buildLkkMap(yongji.items),
      hints,
    };
    status.textContent = "詞典載入好矣：音節、連字符、推薦用字／LKK 漢羅、華語直譯／輕聲檢查攏開矣。";
    checkNow();
  }).catch(() => {
    status.textContent = "詞典載入失敗，請重新整理（拼寫檢查猶會用）。";
  });
}
