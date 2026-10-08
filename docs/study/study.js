// 檢定練習總覽：進度（到期卡、各工具統計、錯誤分類）、備份匯出／匯入、清除。
import { createStudy, backupAll, restoreAll } from "./study-store.js?v=1";
import { createRecords } from "../try/practice-records.js?v=2";

const $ = (id) => document.getElementById(id);
const el = (tag, cls, text) => {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (text != null) e.textContent = text;
  return e;
};
const pct = (x) => `${Math.round(x * 100)}%`;
const TOOLS = { listen: "聽寫", iongji: "推薦用字", hoa2tai: "華語→台語", sandhi: "變調", review: "複習" };
const MISTAKES = { tone: "聲調", aspiration: "送氣", initial: "聲母", final: "韻母", nasal: "鼻音", hanji: "用字", sandhi: "變調", other: "其他" };

const study = createStudy();
const records = createRecords();

function stat(label, value) {
  const s = el("span", null, `${label} `);
  s.append(el("b", null, value));
  return s;
}

function paint() {
  const due = study.dueCards().length;
  const total = study.allCards().length;
  const dueEl = $("st-due");
  dueEl.replaceChildren();
  if (due) {
    dueEl.append(`今仔日有 ${due} 張卡愛複習。`);
    const a = el("a", null, "開始複習 ›");
    a.href = "review/";
    dueEl.append(" ", a);
  } else {
    dueEl.textContent = total ? `今仔日的複習做了矣（總共 ${total} 張卡）。` : "猶無複習卡：練習的時拍毋著、揀毋著的字詞，會自動收入來。";
  }

  const p = records.summary();
  const stats = study.stats();
  const items = [];
  if (p.sessions) items.push(stat("打字練習", `${p.sentences} 句・${pct(p.accuracy)}`));
  for (const [k, label] of Object.entries(TOOLS)) {
    const s = stats[k];
    if (s?.n) items.push(stat(label, `${s.n} 題・答著 ${pct(s.correct / s.n)}`));
  }
  $("st-stats").replaceChildren(...(items.length ? items : [el("span", null, "猶無練習記錄。")]));

  const m = Object.entries(study.mistakes()).sort((a, b) => b[1] - a[1]);
  $("st-mistakes").replaceChildren(...(m.length
    ? [el("span", null, "上捷錯："), ...m.map(([k, n]) => stat(MISTAKES[k] ?? k, String(n)))]
    : []));
}

$("st-export").onclick = () => {
  const blob = new Blob([backupAll(localStorage)], { type: "application/json" });
  const a = el("a");
  a.href = URL.createObjectURL(blob);
  a.download = `phahtaibun-backup-${new Date().toISOString().slice(0, 10).replace(/-/g, "")}.json`;
  a.click();
  setTimeout(() => URL.revokeObjectURL(a.href), 1000);
  $("st-msg").textContent = "已經匯出。";
};

$("st-import").onchange = async (ev) => {
  const file = ev.target.files?.[0];
  ev.target.value = "";
  if (!file) return;
  if (!confirm("匯入會用備份檔蓋過這台瀏覽器現有的進度，確定？")) return;
  try {
    restoreAll(localStorage, await file.text());
    $("st-msg").textContent = "匯入成功。";
    paint();
  } catch (e) {
    $("st-msg").textContent = e.message;
  }
};

$("st-clear").onclick = () => {
  if (!confirm("確定欲清除檢定進度（複習卡、各工具統計）？打字練習記錄袂受影響。")) return;
  study.clear();
  $("st-msg").textContent = "已經清除。";
  paint();
};

paint();
