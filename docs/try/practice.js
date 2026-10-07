// 網頁試拍「練習／考試／記錄」畫面。引擎頁（index.html）送出的文字逐擺交予 update()，
// 遮負責出題、逐格標對錯、記錄。外部文字（維基、自訂）一律用 textContent，無 innerHTML。
import { grade, readingOf } from "./practice-core.js";
import { createRecords } from "./practice-records.js";
import {
  loadBank, loadDictBundle, refHanFor, fromCustom, CUSTOM_KEY, randomWikipediaFeatured, wikiArticle,
  wikisourceBooks, wikisourceChildren, wikisourcePage, wikisourceChapter,
} from "./practice-sources.js";

const $ = (id) => document.getElementById(id);
const el = (tag, cls, text) => {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (text != null) e.textContent = text;
  return e;
};
const VIEWS = ["free", "practice", "exam", "records"];
const EXAM_SIZE = 10;
const FLASH_MS = 700;
const fmtTime = (ms) => {
  const s = Math.round(ms / 1000);
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
};
const pct = (x) => `${Math.round(x * 100)}%`;

export function initPractice({ out, clearOut, isPoj, focusEditor }) {
  const records = createRecords();
  let view = "free";
  let src = null; // 目前題目來源 {kind, key, title, url, license, items}
  let idx = 0;
  let charKeys = null; // 羅馬字／自訂來源：漢字同音接受
  let sessionId = null;
  let tStart = null;
  let last = null; // 上尾一擺 grade 結果
  let locked = false; // 完成閃爍中
  let exam = null; // {items, i, answers: [{g, ms}], t0}
  let loadToken = 0;

  const item = () => (view === "exam" ? exam?.items[exam.i] : src?.items[idx]) ?? null;
  // 羅馬字來源佮自動標音的格，漢字照讀音接受同音字；例句庫愛仝字（練選字）
  const keysFor = (it) => (it && (it.roman || it.autoReading) ? charKeys : null);

  // ---- 畫面切換 ----
  const typingEls = ["modes", "editor", "panel", "editor-actions", "hint"];
  function setView(v) {
    if (!VIEWS.includes(v)) v = "free";
    view = v;
    for (const b of document.querySelectorAll("#try-tabs [data-view]")) {
      const on = b.dataset.view === v;
      b.classList.toggle("on", on);
      b.setAttribute("aria-selected", String(on));
    }
    $("practice").classList.toggle("hidden", v !== "practice" && v !== "exam");
    $("records").classList.toggle("hidden", v !== "records");
    for (const id of typingEls) $(id).classList.toggle("hidden", v === "records");
    $("pr-src-row").classList.toggle("hidden", v !== "practice");
    $("pr-exam-start").classList.toggle("hidden", v !== "exam" || Boolean(exam && exam.i < EXAM_SIZE));
    $("practice").classList.toggle("exam", v === "exam");
    clearOut();
    tStart = null;
    if (v === "practice" && !src) chooseSource($("pr-source").value);
    if (v === "exam") paintExamIdle();
    if (v === "records") paintRecords();
    paint();
    if (v !== "records") focusEditor();
  }
  window.addEventListener("hashchange", () => setView(location.hash.slice(1) || "free"));
  for (const b of document.querySelectorAll("#try-tabs [data-view]")) {
    b.onclick = () => {
      const v = b.dataset.view;
      history.replaceState(null, "", v === "free" ? location.pathname : `#${v}`);
      setView(v);
    };
  }

  // ---- 題目卡 ----
  function paint() {
    const target = $("pr-target");
    const it = item();
    if ((view !== "practice" && view !== "exam") || !it) {
      target.replaceChildren();
      $("pr-gloss").textContent = "";
      $("pr-ref").textContent = "";
      paintMeta();
      return;
    }
    const poj = isPoj();
    const g = last ?? { marks: [] };
    const curAt = g.marks.length;
    target.replaceChildren(...it.slots.map((s, i) => {
      const reading = readingOf(s, poj);
      const c = el("span", "cell");
      if (view === "practice") {
        if (g.marks[i]) c.classList.add(g.marks[i]);
        else if (i === curAt) c.classList.add("cur");
      } else if (i < curAt) c.classList.add("filled");
      c.append(el("b", null, s.h ?? (view === "exam" ? s.src : reading ?? s.src)));
      if (view === "practice" && s.h != null) c.append(el("i", null, reading ?? "　"));
      return c;
    }));
    if (g.extra) target.append(el("span", "cell bad extra", `＋${g.extra}`));
    $("pr-gloss").textContent = it.gloss ? `華語：${it.gloss}` : it.roman ? `原文：${it.text}` : "";
    $("pr-ref").textContent = it.autoReading && view === "practice" ? "讀音是自動標音，可能有誤。" : "";
    if (it.roman && view === "practice") showRefHan(it);
    paintMeta();
  }

  function showRefHan(it) {
    if (it.refHan) {
      $("pr-ref").textContent = `參考漢羅（自動轉寫，可能有誤）：${it.refHan}`;
      return;
    }
    $("pr-ref").textContent = "參考漢羅轉寫中…";
    refHanFor(it.text).then((h) => {
      it.refHan = h;
      if (item() === it) $("pr-ref").textContent = `參考漢羅（自動轉寫，可能有誤）：${h}`;
    }, () => { if (item() === it) $("pr-ref").textContent = ""; });
  }

  function paintMeta() {
    const title = $("pr-title");
    title.replaceChildren();
    if (view === "exam") {
      if (exam && exam.i < EXAM_SIZE) $("pr-pos").textContent = `考試 第 ${exam.i + 1}／${EXAM_SIZE} 題・干焦看漢羅，Enter 交這題`;
      else $("pr-pos").textContent = "";
      return;
    }
    if (!src) {
      $("pr-pos").textContent = "";
      return;
    }
    if (src.url) {
      const a = el("a", null, src.title);
      a.href = src.url;
      a.target = "_blank";
      a.rel = "noopener";
      title.append(a);
    } else title.append(el("span", null, src.title));
    title.append(el("small", null, `（${src.license}）`));
    $("pr-pos").textContent = `第 ${idx + 1}／${src.items.length} 句`;
  }

  const msg = (text, retry) => {
    const m = $("pr-msg");
    m.replaceChildren(el("span", null, text ?? ""));
    if (retry) {
      const b = el("button", "mode", "重試");
      b.type = "button";
      b.onclick = retry;
      m.append(b);
    }
  };

  // ---- 練習流程 ----
  function startSource(s, { resume = true } = {}) {
    src = s;
    sessionId = null;
    idx = 0;
    if (s.kind === "bank") idx = Math.floor(Math.random() * s.items.length);
    else if (resume && s.key) {
      const p = records.getProgress(s.key);
      if (p && p.i < s.items.length) idx = p.i;
    }
    $("pr-restart").classList.toggle("hidden", !(s.kind !== "bank" && idx > 0));
    if (!s.items.length) msg("這篇揣無通練習的句。");
    else msg("");
    goTo(idx);
  }

  function goTo(i) {
    if (!src?.items.length) return;
    idx = Math.max(0, Math.min(i, src.items.length - 1));
    last = null;
    tStart = null;
    clearOut();
    paint();
    focusEditor();
  }

  function nextItem() {
    if (!src) return;
    if (src.kind === "bank") goTo(Math.floor(Math.random() * src.items.length));
    else if (idx + 1 < src.items.length) goTo(idx + 1);
    else {
      msg("這篇練了矣！揀別篇抑是「從頭開始」。");
      $("pr-restart").classList.remove("hidden");
    }
  }

  function record(g) {
    const it = item();
    if (!it) return;
    if (!sessionId) sessionId = records.startSession("practice", { kind: src.kind, title: src.title, url: src.url });
    records.addSentence(sessionId, { slots: it.slots.length, correct: g.correct, ms: tStart ? Date.now() - tStart : 0 });
    if (src.key && src.kind !== "bank") records.setProgress(src.key, idx + 1, src.items.length);
  }

  function update(text) {
    if ((view !== "practice" && view !== "exam") || locked || !item()) return;
    if (!tStart && text) tStart = Date.now();
    if (view === "exam" && !tStart) return;
    if (view === "exam" && exam?.t0 == null && text) exam.t0 = Date.now();
    last = grade(item().slots, text, keysFor(item()));
    paint();
    if (view === "practice" && last.done) {
      record(last);
      locked = true;
      $("pr-card").classList.add("flash");
      setTimeout(() => {
        $("pr-card").classList.remove("flash");
        locked = false;
        nextItem();
      }, FLASH_MS);
    }
  }

  function submit() {
    if (view === "practice") {
      if (!item() || locked) return;
      const g = last ?? grade(item().slots, out.textContent, keysFor(item()));
      if (out.textContent.trim()) record(g);
      nextItem();
    } else if (view === "exam" && exam && exam.i < EXAM_SIZE) {
      const it = item();
      const g = grade(it.slots, out.textContent);
      exam.answers.push({ g, ms: tStart ? Date.now() - tStart : 0 });
      exam.i++;
      last = null;
      tStart = null;
      clearOut();
      if (exam.i >= EXAM_SIZE) finishExam();
      else paint();
    }
  }

  // ---- 來源揀選 ----
  async function withLoading(text, fn) {
    const token = ++loadToken;
    msg(text);
    try {
      const s = await fn();
      if (token === loadToken && s) startSource(s);
    } catch (e) {
      if (token === loadToken) msg(e.message || String(e), () => withLoading(text, fn));
    }
  }
  const needDict = async () => {
    if (charKeys) return;
    msg("詞典載入中…（第一擺約 8 MB）");
    try {
      ({ charKeys } = await loadDictBundle());
    } catch {
      throw new Error("詞典載入失敗，請重新整理");
    }
  };

  function chooseSource(kind) {
    for (const id of ["pr-wiki-box", "pr-book-box", "pr-custom-box", "pr-again"]) $(id).classList.add("hidden");
    if (kind === "bank") withLoading("例句庫載入中…", loadBank);
    else if (kind === "wp-random") {
      $("pr-again").classList.remove("hidden");
      withLoading("維基百科揣文章中…", async () => { await needDict(); return randomWikipediaFeatured(); });
    } else if (kind === "wp-article") {
      $("pr-wiki-box").classList.remove("hidden");
      $("pr-wiki").focus();
    } else if (kind === "ws-book") {
      $("pr-book-box").classList.remove("hidden");
      loadBooks();
    } else if (kind === "custom") {
      $("pr-custom-box").classList.remove("hidden");
      if (!$("pr-custom").value) $("pr-custom").value = localStorage.getItem(CUSTOM_KEY) ?? "";
      $("pr-custom").focus();
    }
  }
  $("pr-source").onchange = () => chooseSource($("pr-source").value);
  $("pr-again").onclick = () => chooseSource("wp-random");
  $("pr-wiki-go").onclick = () => {
    const v = $("pr-wiki").value;
    withLoading("維基載入中…", async () => { await needDict(); return wikiArticle(v); });
  };
  $("pr-wiki").onkeydown = (e) => { if (e.key === "Enter") $("pr-wiki-go").click(); };
  $("pr-custom-go").onclick = () => {
    const v = $("pr-custom").value;
    if (!v.trim()) return msg("請先貼一篇文章。");
    withLoading("分析文章中…", async () => { await needDict(); return fromCustom(v); });
  };

  // 維基文庫：冊 → （子頁 → …）→ 章
  async function loadBooks() {
    const sel = $("pr-book");
    if (sel.options.length > 1) return;
    msg("維基文庫冊單載入中…");
    const books = await wikisourceBooks();
    sel.replaceChildren(el("option", null, "— 揀一本冊 —"), ...books.map((b) => {
      const o = el("option", null, b);
      o.value = b;
      return o;
    }));
    sel.options[0].value = "";
    msg("");
  }
  $("pr-book").onchange = () => { if ($("pr-book").value) openWsPage($("pr-book").value, []); };

  function crumbs(trail) {
    const c = $("pr-crumbs");
    c.replaceChildren(...trail.map((t, i) => {
      const b = el("button", "crumb", t.split("/").pop());
      b.type = "button";
      b.onclick = () => openWsPage(t, trail.slice(0, i));
      return b;
    }));
  }

  async function openWsPage(title, trail) {
    const token = ++loadToken;
    msg("維基文庫載入中…");
    try {
      const { canonical, children } = await wikisourceChildren(title);
      if (token !== loadToken) return;
      const here = [...trail, canonical];
      crumbs(here);
      const list = $("pr-chapters");
      if (children.length) {
        list.replaceChildren(...children.map((t) => {
          const b = el("button", "chap", t.slice(canonical.length + 1));
          b.type = "button";
          b.onclick = () => openWsPage(t, here);
          return b;
        }));
        msg("揀一章：");
        return;
      }
      await needDict();
      const page = await wikisourcePage(canonical);
      if (token !== loadToken) return;
      if (page.chapters.length === 1) {
        list.replaceChildren();
        startSource(wikisourceChapter(page, page.chapters[0]));
        return;
      }
      list.replaceChildren(...page.chapters.map((ch) => {
        const b = el("button", "chap", ch.name);
        b.type = "button";
        b.onclick = () => { startSource(wikisourceChapter(page, ch)); };
        return b;
      }));
      msg("揀一章：");
    } catch (e) {
      if (token === loadToken) msg(e.message || String(e), () => openWsPage(title, trail));
    }
  }

  $("pr-prev").onclick = () => { goTo(idx - 1); };
  $("pr-next").onclick = () => { nextItem(); };
  $("pr-restart").onclick = () => {
    if (!src) return;
    if (src.key) records.setProgress(src.key, 0, src.items.length);
    $("pr-restart").classList.add("hidden");
    msg("");
    goTo(0);
  };

  // ---- 考試 ----
  function paintExamIdle() {
    if (!exam || exam.i >= EXAM_SIZE) {
      $("pr-exam-start").classList.remove("hidden");
      if (!exam) $("pr-result").replaceChildren();
    }
  }
  $("pr-exam-go").onclick = async () => {
    msg("例句庫載入中…");
    try {
      const bank = await loadBank();
      const pool = bank.items.filter((it) => it.slots.length >= 4 && it.slots.length <= 16);
      const items = [];
      while (items.length < EXAM_SIZE) items.push(pool[Math.floor(Math.random() * pool.length)]);
      exam = { items, i: 0, answers: [], t0: null };
      msg("");
      $("pr-exam-start").classList.add("hidden");
      $("pr-result").replaceChildren();
      last = null;
      tStart = null;
      clearOut();
      paint();
      focusEditor();
    } catch (e) {
      msg(e.message, () => $("pr-exam-go").click());
    }
  };

  function finishExam() {
    const total = exam.items.reduce((a, it) => a + it.slots.length, 0);
    const correct = exam.answers.reduce((a, x) => a + x.g.correct, 0);
    const full = exam.answers.filter((x) => x.g.done).length;
    const ms = exam.answers.reduce((a, x) => a + x.ms, 0);
    const id = records.startSession("exam", { kind: "bank", title: "考試 10 句", url: null });
    exam.items.forEach((it, i) => records.addSentence(id, { slots: it.slots.length, correct: exam.answers[i].g.correct, ms: exam.answers[i].ms }));

    const box = $("pr-result");
    const head = el("div", "res-head");
    head.append(
      el("strong", null, `正確率 ${pct(total ? correct / total : 0)}`),
      el("span", null, `　${correct}／${total} 字・全對 ${full}／${EXAM_SIZE} 句・用時 ${fmtTime(ms)}`),
    );
    const rows = exam.items.map((it, i) => {
      const g = exam.answers[i].g;
      const row = el("div", "res-row");
      const cells = el("div", "res-cells");
      it.slots.forEach((s, k) => cells.append(el("span", `cell ${g.marks[k] === "ok" ? "ok" : "bad"}`, s.h ?? s.src)));
      const reading = it.slots.map((s) => readingOf(s, isPoj()) ?? s.src).join(" ");
      row.append(cells, el("div", "res-reading", reading), el("div", "res-gloss", it.gloss ? `華語：${it.gloss}` : ""));
      return row;
    });
    const again = el("button", "mode", "閣考一擺");
    again.type = "button";
    again.onclick = () => $("pr-exam-go").click();
    const toPractice = el("button", "mode", "轉去練習");
    toPractice.type = "button";
    toPractice.onclick = () => document.querySelector('#try-tabs [data-view="practice"]').click();
    const actions = el("div", "res-actions");
    actions.append(again, toPractice);
    box.replaceChildren(head, ...rows, actions);
    paint();
  }

  // ---- 記錄 ----
  const KIND = { bank: "例句庫", wikipedia: "維基百科", wikisource: "維基文庫", custom: "自訂" };
  function paintRecords() {
    const s = records.summary();
    $("rec-summary").textContent = s.sessions
      ? `共 ${s.sessions} 場、${s.sentences} 句・正確率 ${pct(s.accuracy)}・平均 ${Math.round(s.cpm)} 字／分`
      : "猶無練習記錄。記錄干焦存佇你這台瀏覽器。";
    const body = $("rec-rows");
    body.replaceChildren(...records.list().slice(0, 50).map((x) => {
      const tr = el("tr");
      const when = new Date(x.at);
      const srcCell = el("td");
      const label = `${KIND[x.source?.kind] ?? ""}${x.source?.title ? `・${x.source.title}` : ""}`;
      if (x.source?.url) {
        const a = el("a", null, label);
        a.href = x.source.url;
        a.target = "_blank";
        a.rel = "noopener";
        srcCell.append(a);
      } else srcCell.textContent = label;
      tr.append(
        el("td", null, when.toLocaleString("zh-TW", { hour12: false })),
        el("td", null, x.mode === "exam" ? "考試" : "練習"),
        srcCell,
        el("td", null, String(x.sentences)),
        el("td", null, x.slots ? pct(x.correct / x.slots) : "—"),
        el("td", null, x.ms ? String(Math.round(x.correct / (x.ms / 60000))) : "—"),
      );
      return tr;
    }));
  }
  $("rec-export").onclick = () => {
    const blob = new Blob([records.exportJson()], { type: "application/json" });
    const a = el("a");
    a.href = URL.createObjectURL(blob);
    a.download = `phahtaibun-practice-${new Date().toISOString().slice(0, 10).replace(/-/g, "")}.json`;
    a.click();
    setTimeout(() => URL.revokeObjectURL(a.href), 1000);
  };
  $("rec-clear").onclick = () => {
    if (!confirm("確定欲清除所有練習記錄？")) return;
    records.clear();
    paintRecords();
  };

  setView(location.hash.slice(1) || "free");

  return {
    update,
    submit,
    active: () => view === "practice" || view === "exam",
    refresh: paint,
  };
}
