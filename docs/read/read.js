// 讀文章頁：篇單（冊→類）、文章全文四模式（漢羅 ruby／台羅／白話字／對照）、
// 全文音檔佮速度掣、詞彙表、文法說明、練習連結、本機已讀記錄。
import {
  loadReadProgress,
  markArticleRead,
  unmarkArticleRead,
  loadTextMode,
  saveTextMode,
  articleIdFromHash,
  groupArticles,
  sourceLine,
  rubySegments,
} from "./read-core.js?v=1";

const $ = (sel) => document.querySelector(sel);
const esc = (s) =>
  String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);
const MODE_LABELS = { hanlo: "漢羅", tl: "台羅", poj: "白話字", align: "對照" };
const SPEEDS = [1, 0.75];

let ARTS = null; // articles.json .articles
let ROMAN_META_NOTE = ""; // roman.json meta.note：機器轉換的說明
let ROMAN = null; // roman.json .articles[id] = [{tl, poj, w}]（機器轉換＋官方讀音詞）
let mode = "hanlo";
let alignRoman = "tl"; // 對照模式的羅馬字：照使用者上尾揀的 台羅／白話字
let clipAudio = null;
let clipBtn = null;

const byId = (id) => ARTS.find((a) => a.id === id);

// ---------------------------------------------------------------- 音檔

function playClip(src, btn) {
  if (clipBtn === btn && clipAudio && !clipAudio.paused) {
    clipAudio.pause();
    btn.classList.remove("is-playing");
    return;
  }
  if (clipAudio) {
    clipAudio.pause();
    if (clipBtn) clipBtn.classList.remove("is-playing");
  }
  clipAudio = new Audio(src);
  clipBtn = btn;
  btn.classList.add("is-playing");
  clipAudio.addEventListener("ended", () => btn.classList.remove("is-playing"));
  clipAudio.addEventListener("pause", () => btn.classList.remove("is-playing"));
  clipAudio.play().catch(() => btn.classList.remove("is-playing"));
}

// ---------------------------------------------------------------- 篇單（首頁）

function renderHome() {
  const read = loadReadProgress(localStorage);
  const root = $("#read-root");
  const books = groupArticles(ARTS);
  let html = `<section id="read-home"><h2>目錄（${ARTS.length} 篇）</h2>
    <p class="hint">點一篇開始讀。讀過的會記錄佇這台電腦（免登入），讀了會使直接跳去打字練習佮聽寫。</p>`;
  for (const b of books) {
    html += `<section class="rd-book"><h3 class="rd-book-title">0${b.book} 冊</h3>`;
    for (const c of b.categories) {
      html += `<h4 class="rd-cat-title">${esc(c.name)}</h4><div class="rd-arts">`;
      for (const a of c.articles) {
        const done = read.includes(a.id);
        const date = a.source.date || `${a.source.paper}${a.source.issue}期`;
        html += `<a class="rd-art-btn${done ? " is-read" : ""}" href="#${a.id}"
          >${done ? '<span class="rd-read-mark">✓ 讀過</span>' : ""}
          <span class="rd-art-title">${esc(a.title)}</span>
          <span class="rd-art-meta">${esc(a.author)}・${esc(date)}</span></a
        >`;
      }
      html += `</div>`;
    }
    html += `</section>`;
  }
  root.innerHTML = html + `</section>`;
}

// ---------------------------------------------------------------- 文章頁

function hanloParaHtml(p) {
  // 漢羅模式：官方讀音（手冊括號註）標做 ruby 佇字頂
  return rubySegments(p.text, p.readings)
    .map((s) => (s.t === "ruby" ? `<ruby>${esc(s.han)}<rt>${esc(s.tl)}</rt></ruby>` : esc(s.s)))
    .join("");
}

function paraHtml(p, rp) {
  if (mode === "tl" || mode === "poj") return esc(rp[mode]);
  if (mode === "align") {
    return `<span class="rd-align-han">${hanloParaHtml(p)}</span><span class="rd-align-roman">${esc(rp[alignRoman])}</span>`;
  }
  return hanloParaHtml(p);
}

function playBtn(src, label) {
  return `<button type="button" class="rd-play" data-src="${esc(src)}" aria-label="${esc(label)}">🔊</button>`;
}

function renderArticle(id) {
  const a = byId(id);
  if (!a) return renderHome();
  const idx = ARTS.indexOf(a);
  const roman = ROMAN[a.id];
  markArticleRead(localStorage, id); // 開來讀就當做讀過；毋愛會使按掣取消
  const read = loadReadProgress(localStorage);
  const root = $("#read-root");
  const prev = ARTS[idx - 1];
  const next = ARTS[idx + 1];
  const note =
    mode === "hanlo"
      ? ""
      : `<p class="rd-roman-note">${esc(ROMAN_META_NOTE)}</p>`;
  root.innerHTML = `
  <article id="read-art" data-id="${esc(id)}">
    <div class="rd-top">
      <a class="rd-back" href="#">← 轉目錄</a><span class="rd-cat">${esc(a.category)}</span>
    </div>
    <h2 class="rd-title">${esc(a.title)}</h2>
    <p class="rd-author">作者 ${esc(a.author)}</p>
    <div class="rd-audio-row">
      <audio controls preload="metadata" src="${esc(a.audio)}"></audio>
      ${SPEEDS.map((s) => `<button type="button" class="rd-speed" data-rate="${s}" aria-pressed="false">${s}×</button>`).join("")}
    </div>
    <div class="rd-modes" role="group" aria-label="顯示模式">
      ${Object.entries(MODE_LABELS)
        .map(([k, v]) => `<button type="button" class="rd-mode" data-mode="${k}" aria-pressed="${k === mode}">${v}</button>`)
        .join("")}
    </div>
    ${note}
    <div class="rd-body">
      ${a.paragraphs.map((p, i) => `<p class="rd-para${mode === "tl" || mode === "poj" ? " is-roman" : ""}">${paraHtml(p, roman[i])}</p>`).join("")}
    </div>
    <div class="rd-actions">
      <a class="rd-btn primary" href="../try/?article=${esc(id)}#practice">⌨ 打字練習這篇</a>
      <a class="rd-btn" href="../try/?listen=article:${esc(id)}#listen">🎧 聽寫這篇的詞彙</a>
      <button type="button" class="rd-btn rd-mark" aria-pressed="${read.includes(id)}">
        ${read.includes(id) ? "✓ 讀過（點予取消）" : "標做讀過"}
      </button>
    </div>
    ${
      a.vocab.length
        ? `<h3>詞彙</h3><div class="rd-vocab-wrap"><table class="rd-vocab">
      <thead><tr><th>漢字</th><th>台羅</th><th>華語</th><th>音檔</th></tr></thead>
      <tbody>${a.vocab
        .map((v) => `<tr><td class="rd-v-han">${esc(v.han)}</td><td>${esc(v.tl || "—")}</td><td>${esc(v.hoa)}</td><td>${playBtn(v.audio, `聽 ${v.han}`)}</td></tr>`)
        .join("")}</tbody></table></div>`
        : ""
    }
    ${
      a.grammar.length
        ? `<h3>文法說明</h3><div class="rd-grammar">${a.grammar
            .map(
              (g) => `<div class="rd-grammar-item"><div class="rd-grammar-head"><b>${esc(g.han)}</b>
              <span class="rd-tl">${esc(g.tl)}</span>${g.audio.map((u) => playBtn(u, `聽 ${g.han} 的說明`)).join("")}</div>
              <p class="rd-grammar-text">${esc(g.text)}</p></div>`
            )
            .join("")}</div>`
        : ""
    }
    ${a.notes.length ? `<h3>註</h3><ol class="rd-notes">${a.notes.map((n) => `<li>${esc(n)}</li>`).join("")}</ol>` : ""}
    <p class="rd-source">出處：${esc(sourceLine(a))}</p>
    <nav class="rd-prevnext" aria-label="上一篇下一篇">
      ${prev ? `<a href="#${prev.id}">← 上一篇 ${esc(prev.title)}</a>` : "<span></span>"}
      ${next ? `<a href="#${next.id}">下一篇 ${esc(next.title)} →</a>` : "<span></span>"}
    </nav>
  </article>`;

  const audio = root.querySelector("audio");
  const speedBtns = [...root.querySelectorAll(".rd-speed")];
  const syncSpeed = () => speedBtns.forEach((b) => b.setAttribute("aria-pressed", String(Math.abs(audio.playbackRate - +b.dataset.rate) < 1e-6)));
  syncSpeed();
  speedBtns.forEach((b) =>
    b.addEventListener("click", () => {
      audio.playbackRate = +b.dataset.rate;
      syncSpeed();
    })
  );

  root.querySelectorAll(".rd-mode").forEach((b) =>
    b.addEventListener("click", () => {
      const m = b.dataset.mode;
      if (m === "tl" || m === "poj") alignRoman = m; // 對照跟著上尾揀的羅馬字系統
      mode = m;
      saveTextMode(localStorage, mode);
      renderArticle(id);
    })
  );
  root.querySelectorAll(".rd-play").forEach((b) => b.addEventListener("click", () => playClip(b.dataset.src, b)));
  const markBtn = root.querySelector(".rd-mark");
  markBtn.addEventListener("click", () => {
    if (loadReadProgress(localStorage).includes(id)) unmarkArticleRead(localStorage, id);
    else markArticleRead(localStorage, id);
    renderArticle(id);
  });
}

// ---------------------------------------------------------------- 啟動

function render() {
  const id = articleIdFromHash(location.hash);
  if (id && byId(id)) renderArticle(id);
  else renderHome();
  window.scrollTo({ top: 0 });
}

async function init() {
  const status = $("#read-status");
  try {
    const [arts, roman] = await Promise.all([fetch("./data/articles.json"), fetch("./data/roman.json")]);
    if (!arts.ok || !roman.ok) throw new Error("資料載入失敗");
    ARTS = (await arts.json()).articles;
    const rj = await roman.json();
    ROMAN = rj.articles;
    ROMAN_META_NOTE = rj.meta.note;
    mode = loadTextMode(localStorage);
    if (mode === "poj") alignRoman = "poj";
    render();
    status.textContent = "";
  } catch (e) {
    status.textContent = "文章資料載入失敗，請重新整理再試一擺。";
  }
}

window.addEventListener("hashchange", render);
init();
