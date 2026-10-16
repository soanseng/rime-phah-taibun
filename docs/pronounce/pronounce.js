// 拼音發音教學頁：課程列表、逐課（說明、發音圖、官方音檔）、聽音練習、本機進度。
import { makeQuestion, isCorrect, loadProgress, recordResult, audioUrl } from "./pronounce-core.js?v=1";

const $ = (sel) => document.querySelector(sel);
const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);
const QUIZ_LEN = 10;
let DATA = null;
let player = null;

// ---------------------------------------------------------------- 發音圖（自畫 SVG）

const PLACES = {
  lips: { x: 52, y: 112, label: "雙脣" },
  alveolar: { x: 82, y: 92, label: "舌尖＋上齒齦" },
  velar: { x: 150, y: 86, label: "舌根＋軟顎" },
  glottis: { x: 168, y: 176, label: "聲門（喉嚨）" },
  nasal: { x: 120, y: 58, label: "氣對鼻空出來" },
};

/** 頭殼側面圖：鼻、嘴脣、齒、上顎、軟顎、舌、喉，標出發音部位。 */
export function headSvg(place, caption = "") {
  const p = PLACES[place];
  const nose = place === "nasal"
    ? '<path d="M150 92 C 140 60, 110 50, 70 52" fill="none" stroke="var(--pr-hi)" stroke-width="4" stroke-dasharray="6 5" marker-end="url(#arr)"/>'
    : "";
  return `<svg class="pr-diagram" viewBox="0 0 230 220" role="img" aria-label="發音部位：${esc(p.label)}">
  <defs><marker id="arr" viewBox="0 0 10 10" refX="5" refY="5" markerWidth="5" markerHeight="5" orient="auto"><path d="M0 0L10 5L0 10z" fill="var(--pr-hi)"/></marker></defs>
  <path d="M60 20 C 30 30, 28 50, 40 62 L 22 82 L 40 90 L 36 104 C 30 108, 32 116, 40 118 L 38 128 C 30 132, 34 142, 42 144 L 46 170 C 60 196, 110 200, 130 210" fill="none" stroke="currentColor" stroke-width="3"/>
  <path d="M44 66 L 70 64 C 120 60, 150 66, 168 84 L 176 120 L 172 210" fill="none" stroke="currentColor" stroke-width="2.5"/>
  <path d="M58 104 L 64 98 L 70 104" fill="#fff" stroke="currentColor" stroke-width="2"/>
  <path d="M58 122 L 64 128 L 70 122" fill="#fff" stroke="currentColor" stroke-width="2"/>
  <path d="M70 98 C 90 86, 130 78, 160 86 C 168 92, 170 100, 168 108" fill="none" stroke="currentColor" stroke-width="2.5"/>
  <path d="M66 118 C 80 100, 120 92, 150 100 C 162 108, 164 130, 160 176 L 120 176 C 96 160, 80 140, 66 126 Z" fill="var(--pr-tongue)" stroke="currentColor" stroke-width="2"/>
  <path d="M160 170 L 176 174 M160 182 L 176 178" stroke="currentColor" stroke-width="2"/>
  ${nose}
  <circle cx="${p.x}" cy="${p.y}" r="13" fill="var(--pr-hi)" fill-opacity="0.35" stroke="var(--pr-hi)" stroke-width="3"/>
  <text x="115" y="214" text-anchor="middle" font-size="15" fill="currentColor">${esc(caption || p.label)}</text>
</svg>`;
}

const MOUTHS = { // 嘴形：寬、開、圓（照手冊單元音發音方法）
  a: { w: 60, h: 46, r: 0.6, label: "口開大" },
  i: { w: 78, h: 14, r: 0.2, label: "扁扁、嘴角後拉" },
  u: { w: 28, h: 26, r: 1, label: "圓圓、細孔" },
  e: { w: 70, h: 24, r: 0.3, label: "扁、半開" },
  o: { w: 50, h: 32, r: 0.7, label: "半開、橢圓" },
  oo: { w: 42, h: 40, r: 1, label: "嘴脣圓" },
};

/** 正面嘴形圖。 */
export function mouthSvg(v) {
  const m = MOUTHS[v];
  if (!m) return "";
  const ry = m.h / 2;
  const rx = m.w / 2;
  return `<svg class="pr-mouth" viewBox="0 0 120 120" role="img" aria-label="${esc(v)} 的嘴形：${esc(m.label)}">
  <circle cx="60" cy="56" r="52" fill="var(--pr-face)" stroke="currentColor" stroke-width="2"/>
  <circle cx="40" cy="36" r="5" fill="currentColor"/><circle cx="80" cy="36" r="5" fill="currentColor"/>
  <ellipse cx="60" cy="72" rx="${rx + 6}" ry="${ry + 6}" fill="var(--pr-lip)"/>
  <ellipse cx="60" cy="72" rx="${rx}" ry="${ry}" fill="#5a1f2a"/>
  <text x="60" y="118" text-anchor="middle" font-size="13" fill="currentColor">${esc(v)}：${esc(m.label)}</text>
</svg>`;
}

// 手冊「基本聲調排序」：調序、例字、調值描述（照原文；第 6 調學習時以第 2 調代之）。無標數字調值。
const TONES = [[1, "東", "高平"], [2, "黨", "高降"], [3, "棟", "低降"], [4, "督", "中入"],
  [5, "同", "低升"], [6, "黨", "以第2調代之"], [7, "洞", "中平"], [8, "毒", "高入"]];

/** 八聲調卡：照手冊的調序、例字、調值描述。 */
export function toneSvg() {
  const g = TONES.map(([t, han, desc], i) => {
    const x = 8 + (i % 4) * 92;
    const y = 8 + Math.floor(i / 4) * 92;
    return `<rect x="${x}" y="${y}" width="84" height="84" rx="12" fill="var(--pr-face)" stroke="currentColor"/>
  <text x="${x + 42}" y="${y + 26}" text-anchor="middle" font-size="18" font-weight="700" fill="var(--pr-hi)">第 ${t} 調</text>
  <text x="${x + 42}" y="${y + 56}" text-anchor="middle" font-size="24" fill="currentColor">${han}</text>
  <text x="${x + 42}" y="${y + 76}" text-anchor="middle" font-size="${desc.length > 3 ? 11 : 14}" fill="currentColor">${desc}</text>`;
  }).join("");
  return `<svg class="pr-diagram wide" viewBox="0 0 376 192" role="img" aria-label="八聲調：1 東 高平、2 黨 高降、3 棟 低降、4 督 中入、5 同 低升、6 以第 2 調代之、7 洞 中平、8 毒 高入">${g}</svg>`;
}

function spellSvg() {
  return `<svg class="pr-diagram wide" viewBox="0 0 360 90" role="img" aria-label="聲母加韻母就是音節">
  <rect x="10" y="20" width="90" height="50" rx="10" fill="var(--pr-tongue)"/><text x="55" y="53" text-anchor="middle" font-size="24" fill="currentColor">p</text>
  <text x="120" y="53" text-anchor="middle" font-size="28" fill="currentColor">＋</text>
  <rect x="140" y="20" width="90" height="50" rx="10" fill="var(--pr-face)"/><text x="185" y="53" text-anchor="middle" font-size="24" fill="currentColor">a</text>
  <text x="250" y="53" text-anchor="middle" font-size="28" fill="currentColor">＝</text>
  <rect x="268" y="20" width="84" height="50" rx="10" fill="var(--pr-hi)" fill-opacity="0.3"/><text x="310" y="53" text-anchor="middle" font-size="24" fill="currentColor">pa</text>
  <text x="55" y="86" text-anchor="middle" font-size="12" fill="currentColor">聲母</text><text x="185" y="86" text-anchor="middle" font-size="12" fill="currentColor">韻母</text>
</svg>`;
}

function lessonDiagram(ls) {
  switch (ls.id) {
    case "vowels": return `<div class="pr-figs">${["a", "i", "u", "e", "o", "oo"].map(mouthSvg).join("")}</div>`;
    case "diphthongs": return `<div class="pr-figs">${mouthSvg("i")}<span class="pr-arrow">→</span>${mouthSvg("a")}<span class="pr-arrow">→</span>${mouthSvg("u")}</div><p class="hint">例：iau 嘴形 i → a → u 滑過去。</p>`;
    case "nasalized": return `<div class="pr-figs">${headSvg("nasal", "鼻化：氣對鼻空出來")}</div>`;
    case "nasal": return `<div class="pr-figs">${headSvg("lips", "-m 雙脣合")}${headSvg("alveolar", "-n 舌尖頂齒齦")}${headSvg("velar", "-ng 舌根頂軟顎")}</div>`;
    case "checked": return `<div class="pr-figs">${headSvg("lips", "-p 雙脣合")}${headSvg("alveolar", "-t 舌尖頂齒齦")}${headSvg("velar", "-k 舌根頂軟顎")}${headSvg("glottis", "-h 喉嚨頓")}</div>`;
    case "tones": case "sandhi": return `<div class="pr-figs">${toneSvg()}</div>`;
    case "tables": return `<div class="pr-figs">${spellSvg()}</div>`;
    case "poj": return `<div class="pr-figs">${mouthSvg("oo")}</div><p class="hint">台羅 oo ＝ 白話字 o͘（o 正爿頂懸一點）。</p>`;
    default: {
      const places = [...new Set(ls.sections.flatMap((s) => s.items).map((i) => i.place).filter(Boolean))];
      return `<div class="pr-figs">${places.map((p) => headSvg(p)).join("")}</div>`;
    }
  }
}

// ---------------------------------------------------------------- 音檔

function play(name, btn) {
  if (player) { // 舊的 Audio 愛放掉連線，無，Chrome 仝一个主機的連線會予佔滿，新的音檔等袂到
    player.pause();
    player.removeAttribute("src");
    player.load();
  }
  document.querySelectorAll(".is-playing").forEach((b) => b.classList.remove("is-playing"));
  player = new Audio(audioUrl(DATA.audioBase, name));
  btn?.classList.add("is-playing");
  player.onended = () => btn?.classList.remove("is-playing");
  player.onerror = () => {
    btn?.classList.remove("is-playing");
    $("#pr-status").textContent = "音檔載入失敗，請檢查網路（音檔對教育部官方網站播放）。";
  };
  return player.play().catch(() => {});
}

const playBtn = (name, label, cls = "") =>
  `<button type="button" class="pr-play ${cls}" data-audio="${esc(name)}" aria-label="播放 ${esc(label)}">🔊 ${esc(label)}</button>`;

// ---------------------------------------------------------------- 畫面

function renderList() {
  const prog = loadProgress(localStorage);
  $("#pr-lessons").innerHTML = DATA.lessons.map((ls, i) => {
    const p = prog[ls.id];
    const badge = p ? (p.done ? "⭐ 完成" : `${p.best}/${p.total}`) : "";
    return `<a class="pr-lesson-btn${p?.done ? " is-done" : ""}" href="#${esc(ls.id)}"><span class="pr-num">${i + 1}</span><span class="pr-part">${esc(ls.part)}</span><b>${esc(ls.title)}</b><span class="pr-badge">${badge}</span></a>`;
  }).join("");
}

function itemCard(it) {
  const info = it.info ? `<dl>${Object.entries(it.info).map(([k, v]) => `<dt>${esc(k)}</dt><dd>${esc(v)}</dd>`).join("")}</dl>` : "";
  const exs = it.examples
    ? `<p class="pr-ex">${it.examples.map((e) => `${esc(e.tl)} ${esc(e.han)}`).join("、")}${it.examplesAudio ? " " + playBtn(it.examplesAudio, "例字", "small") : ""}</p>`
    : "";
  const extra = it.poj ? `<p class="pr-poj">白話字：<b>${esc(it.poj)}</b>　<span class="hint">${esc(it.rule)}</span></p>` : "";
  const tone = it.tone ? `<p class="hint">第 ${it.tone} 調${it.desc ? `・${esc(it.desc)}` : ""}</p>` : "";
  const fig = it.place ? headSvg(it.place) : "";
  return `<div class="pr-card">${fig}<div class="pr-card-main"><p class="pr-big">${esc(it.tl)} <span class="pr-han">${esc(it.han || "")}</span></p>${tone}${playBtn(it.audio, it.tl)}${exs}${extra}${info}</div></div>`;
}

function tableHtml(t) {
  const inis = [...new Set(t.cells.map((c) => c.ini))];
  const at = new Map(t.cells.map((c) => [`${c.ini}|${c.rime}`, c]));
  const head = `<tr><th></th>${t.rimes.map((r) => `<th scope="col">${esc(r)}</th>`).join("")}</tr>`;
  const rows = inis.map((ini) => `<tr><th scope="row">${esc(ini || "Ø")}</th>${t.rimes.map((r) => {
    const c = at.get(`${ini}|${r}`);
    return `<td>${c ? `<button type="button" class="pr-cell" data-audio="${esc(c.audio)}">${esc(c.tl)}</button>` : ""}</td>`;
  }).join("")}</tr>`).join("");
  return `<h3>${esc(t.title)}</h3><div class="pr-table-wrap"><table class="pr-table">${head}${rows}</table></div>`;
}

function videoHtml(v) {
  if (!v) return "";
  const id = encodeURIComponent(v.youtube);
  return `<section class="pr-section pr-video"><h3>${esc(v.label)}</h3><p>${esc(v.title)}</p>
    <div class="pr-video-frame"><iframe src="https://www.youtube-nocookie.com/embed/${id}" title="${esc(v.title)}" loading="lazy"
      allow="accelerometer; encrypted-media; gyroscope; picture-in-picture" allowfullscreen referrerpolicy="strict-origin-when-cross-origin"></iframe></div>
    <p class="hint">${esc(v.note)}　<a href="https://www.youtube.com/watch?v=${id}" rel="noopener">佇 YouTube 看</a></p></section>`;
}

function renderLesson(id) {
  const ls = DATA.lessons.find((l) => l.id === id);
  if (!ls) { $("#pr-lesson").hidden = true; $("#pr-home").hidden = false; renderList(); return; }
  $("#pr-home").hidden = true;
  const idx = DATA.lessons.indexOf(ls);
  const next = DATA.lessons[idx + 1];
  const sections = ls.sections.map((s) => `<section class="pr-section"><h3>${esc(s.title)}</h3>
    ${s.items.length ? `<div class="pr-cards">${s.items.map(itemCard).join("")}</div>` : ""}
    ${(s.notes || []).length ? `<ul class="hint">${s.notes.map((n) => `<li>${esc(n)}</li>`).join("")}</ul>` : ""}</section>`).join("");
  $("#pr-lesson").innerHTML = `<p><a class="btn" href="#">← 課程列表</a></p>
    <h2>第 ${idx + 1} 課　${esc(ls.title)}</h2>
    ${ls.intro.map((p) => `<p class="pr-intro">${esc(p)}</p>`).join("")}
    ${lessonDiagram(ls)}
    ${sections}${(ls.tables || []).map(tableHtml).join("")}${videoHtml(ls.video)}
    <section class="pr-quiz q-card" id="pr-quiz"><h3>練習：聽看覓</h3>
      <p class="hint">手冊的音檔出題，一擺 ${QUIZ_LEN} 題。先按「🔊 聽」，才揀答案。</p>
      <button type="button" class="btn primary pr-start">開始練習</button><div class="pr-q"></div></section>
    <p class="pr-nav">${next ? `<a class="btn primary" href="#${esc(next.id)}">下一課：${esc(next.title)} →</a>` : ""}</p>`;
  $("#pr-lesson").hidden = false;
  $("#pr-lesson").querySelector(".pr-start").addEventListener("click", () => startQuiz(ls));
  window.scrollTo(0, 0);
}

function startQuiz(ls) {
  const box = $("#pr-quiz .pr-q");
  let n = 0;
  let score = 0;
  const ask = () => {
    if (n >= QUIZ_LEN) {
      recordResult(localStorage, ls.id, score, QUIZ_LEN);
      box.innerHTML = `<p class="pr-result">${score === QUIZ_LEN ? "⭐ 全對！真厲害！" : `答著 ${score}／${QUIZ_LEN} 題`}</p><button type="button" class="btn primary">閣練一擺</button>`;
      box.querySelector("button").addEventListener("click", () => startQuiz(ls));
      return;
    }
    const q = makeQuestion(ls.quiz);
    n += 1;
    box.innerHTML = `<p class="stat-row"><b>第 ${n}／${QUIZ_LEN} 題</b>　答著 ${score}</p>
      <p class="q-prompt">${esc(ls.quiz.prompt || "聽看覓，是佗一个？")}${q.item.show ? `　<b>${esc(q.item.show)}</b>` : ""}</p>
      ${playBtn(q.item.audio, "聽", "pr-listen")}
      <div class="pr-choices">${q.options.map((o) => `<button type="button" class="pr-choice" data-v="${esc(o)}">${esc(o)}</button>`).join("")}</div>
      <p class="pr-fb" aria-live="polite"></p>`;
    const listen = box.querySelector(".pr-listen");
    play(q.item.audio, listen);
    box.querySelectorAll(".pr-choice").forEach((b) => b.addEventListener("click", () => {
      const ok = isCorrect(q, b.dataset.v);
      if (ok) score += 1;
      box.querySelectorAll(".pr-choice").forEach((c) => {
        c.disabled = true;
        if (c.dataset.v === q.item.answer) c.classList.add("is-right");
      });
      if (!ok) b.classList.add("is-wrong");
      box.querySelector(".pr-fb").innerHTML = `${ok ? "✔ 著！" : `✘ 毋著，答案是 <b>${esc(q.item.answer)}</b>`} <button type="button" class="btn primary pr-next">下一題</button>`;
      box.querySelector(".pr-next").addEventListener("click", ask);
    }));
  };
  ask();
}

document.addEventListener("click", (e) => {
  const b = e.target.closest("[data-audio]");
  if (b) play(b.dataset.audio, b);
});

async function main() {
  try {
    DATA = await (await fetch("./data/lessons.json?v=2")).json();
  } catch {
    $("#pr-status").textContent = "課程資料載入失敗，請重新整理。";
    return;
  }
  const route = () => renderLesson(location.hash.slice(1));
  window.addEventListener("hashchange", route);
  route();
}

if (typeof document !== "undefined" && document.getElementById("pr-app")) main();
