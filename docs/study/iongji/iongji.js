// 推薦用字選擇題：一輪 10 題；揀 1–4 抑是滑鼠點。進度存佇瀏覽器（localStorage）。
import { buildQuestion, shuffle } from "./iongji-core.js?v=1";
import { createStudy } from "../study-store.js?v=1";
import { toNumeric } from "../../thak/js/roman.js?v=26";

const ROUND = 10;
const study = createStudy();

const $ = (id) => document.getElementById(id);
const el = (tag, cls, text) => {
  const n = document.createElement(tag);
  if (cls) n.className = cls;
  if (text != null) n.textContent = text;
  return n;
};

let items = [];
let order = [];
let i = 0; // 這馬題目佇 order 內面的位置（0 起）
let q = null;
let phase = "loading"; // loading | ask | feedback | done
let roundK = 0; // 這輪第幾題（1 起）
let roundN = ROUND;
let roundOk = 0;
let roundWrong = [];

const validPos = (pos) =>
  pos &&
  Array.isArray(pos.order) &&
  pos.order.length === items.length &&
  pos.order.every((n) => Number.isInteger(n) && n >= 0 && n < items.length) &&
  new Set(pos.order).size === items.length;

function showQuestion() {
  if (i >= order.length) {
    // 229 題攏行一輪矣：重新㨦順序
    order = shuffle(items.map((_, k) => k));
    i = 0;
  }
  q = buildQuestion(items[order[i]]);
  study.setPos("iongji", { order, i });
  phase = "ask";

  $("ig-i").textContent = String(i + 1);
  $("ig-total").textContent = String(items.length);
  $("ig-round-k").textContent = String(roundK);
  $("ig-round-n").textContent = String(roundN);
  $("ig-round-ok").textContent = String(roundOk);
  $("ig-progress").hidden = false;
  $("ig-done").hidden = true;
  $("ig-card").hidden = false;

  $("ig-prompt").textContent = q.prompt;
  const box = $("ig-choices");
  box.replaceChildren();
  q.options.forEach((opt, k) => {
    const b = el("button", "choice");
    b.type = "button";
    b.append(el("span", "ig-no", String(k + 1)), document.createTextNode(opt));
    b.addEventListener("click", () => answer(k));
    box.append(b);
  });
  $("ig-answer").hidden = true;
  $("ig-answer").replaceChildren();
  $("ig-next-row").hidden = true;
}

function answer(k) {
  if (phase !== "ask" || k < 0 || k >= q.options.length) return;
  const ok = q.options[k] === q.answer;
  phase = "feedback";

  const btns = [...$("ig-choices").children];
  btns.forEach((b, j) => {
    b.disabled = true;
    if (q.options[j] === q.answer) b.classList.add("ok");
  });
  btns[k].classList.add(ok ? "ok" : "bad");

  study.record("iongji", { n: 1, correct: ok ? 1 : 0 });
  if (ok) {
    roundOk++;
  } else {
    roundWrong.push(q);
    study.addCard({
      id: `iongji:${q.item.word}|${toNumeric(q.item.tl)}`,
      kind: "iongji",
      front: { q: q.prompt, hoa: q.item.hoa, options: [...q.options] },
      back: { word: q.item.word, tl: q.item.tl },
    });
    study.logMistake("hanji");
  }
  $("ig-round-ok").textContent = String(roundOk);
  $("ig-card").classList.add(ok ? "flash-ok" : "flash-bad");
  setTimeout(() => $("ig-card").classList.remove("flash-ok", "flash-bad"), 450);

  const ans = $("ig-answer");
  ans.replaceChildren(
    el("p", ok ? "ok-text verdict" : "bad-text verdict", ok ? "答著！" : `拍毋著，推薦是用「${q.answer}」。`),
  );
  if (q.blankedFrom) {
    ans.append(
      el("p", "han", `原文：${q.blankedFrom[0]}`),
      el("p", "roman", `讀音：${q.blankedFrom[1]}`),
    );
  }
  const facts = [
    `推薦用字：${q.item.word}（${q.item.tl}）`,
    `華語：${q.item.hoa}`,
    q.item.alts?.length ? `異用字：${q.item.alts.join("、")}` : null,
    q.item.examples?.length ? `用例（照表原文）：${q.item.examples.join("；")}` : null,
  ].filter(Boolean);
  for (const f of facts) ans.append(el("p", "q-sub", f));
  ans.hidden = false;
  $("ig-next-row").hidden = false;
}

function advance() {
  if (phase !== "feedback") return;
  if (roundK >= roundN) return endRound();
  i++;
  roundK++;
  showQuestion();
}

function endRound() {
  phase = "done";
  $("ig-card").hidden = true;
  const score = $("ig-done-score");
  score.replaceChildren(
    el("span", roundOk === roundN ? "ok-text" : null, `這輪答著 ${roundOk}／${roundN} 題。`),
    document.createTextNode(roundWrong.length ? " 拍毋著的：" : " 全對，誠𠢕！"),
  );
  const list = $("ig-wrong-list");
  list.replaceChildren();
  for (const w of roundWrong) {
    const row = el("p", "ig-wrong");
    row.append(
      el("b", null, w.item.word),
      document.createTextNode(`${w.item.tl}｜華語：${w.item.hoa}`),
    );
    list.append(row);
  }
  $("ig-done").hidden = false;
}

function startRound() {
  roundK = 1;
  roundN = Math.min(ROUND, order.length - i) || ROUND;
  roundOk = 0;
  roundWrong = [];
  showQuestion();
}

function nextRound() {
  i++;
  startRound();
}

document.addEventListener("keydown", (ev) => {
  const t = ev.target;
  const tag = t instanceof HTMLElement ? t.tagName : "";
  if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return;
  // 焦點佇鈕仔面頂就予原生 click 處理，才袂應兩擺
  if (t instanceof HTMLElement && t.closest("button")) return;
  if (phase === "ask" && ev.key >= "1" && ev.key <= "4") {
    ev.preventDefault();
    answer(Number(ev.key) - 1);
  } else if (ev.key === "Enter" && phase === "feedback") {
    ev.preventDefault();
    advance();
  } else if (ev.key === "Enter" && phase === "done") {
    ev.preventDefault();
    nextRound();
  }
});

$("ig-next").addEventListener("click", advance);
$("ig-again").addEventListener("click", nextRound);

async function init() {
  try {
    const data = await (await fetch(new URL("../data/iongji.json", import.meta.url))).json();
    items = data.items;
  } catch {
    $("app-loading").textContent = "資料載入失敗，請重新整理。";
    return;
  }
  const pos = study.getPos("iongji");
  if (validPos(pos)) {
    order = pos.order;
    i = Number.isInteger(pos.i) && pos.i >= 0 && pos.i < order.length ? pos.i : 0;
  } else {
    order = shuffle(items.map((_, k) => k));
    i = 0;
  }
  $("app-loading").remove();
  startRound();
}

init();
