// 讀文章蓋趣味：純函式（建置腳本 scripts/thak/article-roman.mjs 佮頁面共用）。
import { segment, render } from "../thak/js/dict.js?v=26";
import { toNumeric, addImplicitTone } from "../thak/js/roman.js?v=26";

// 手冊台羅（調符、- 連音、-- 輕聲、空白分詞）→ 詞典格式數字調：
// 音節用空白隔，輕聲音節頭前留 "--"，無調號的 1/4 聲補數字。
export function officialNumeric(tl) {
  const out = [];
  for (const m of tl.normalize("NFC").matchAll(/(--)?([^\s-]+)/g)) {
    out.push((m[1] || "") + addImplicitTone(toNumeric(m[2]).toLowerCase()));
  }
  return out.join(" ");
}

// 一段清本文 + 官方讀音（{han,tl,at}，at＝codepoint 位置）→ {tl, poj, words}。
// 官方讀音的詞固定做一个詞，中間的本文用轉換詞典切詞；
// words: {h,r} 詞典詞、{h,r,o:1} 官方讀音、{h,miss:1} 詞典查無的字。
export function romanizeParagraph(text, readings, dict, rev = null) {
  const cps = [...text];
  const segs = [];
  let si = 0;
  const pushText = (s) => {
    if (!s) return;
    for (const seg of segment(s, dict, rev)) segs.push(seg.t === "w" ? { ...seg, si: si++ } : seg);
  };
  let pos = 0;
  for (const r of [...readings].sort((a, b) => a.at - b.at)) {
    pushText(cps.slice(pos, r.at).join(""));
    segs.push({ t: "w", han: r.han, readings: [officialNumeric(r.tl)], gloss: "", si: si++, official: true });
    pos = r.at + [...r.han].length;
  }
  pushText(cps.slice(pos).join(""));
  const { tl, poj } = render(segs);
  const words = [];
  for (const seg of segs) {
    if (seg.t === "miss") words.push({ h: seg.s, miss: 1 });
    else if (seg.t === "w") words.push(seg.official ? { h: seg.han, r: seg.readings[0], o: 1 } : { h: seg.han, r: seg.readings[0] });
  }
  return { tl, poj, words };
}

// ---------------------------------------------------------------- 本頁 UI 用純函式
// storage 是 localStorage 抑測試的假物件（getItem/setItem）。

export const READ_PROGRESS_KEY = "read-progress-v1";
export const READ_MODE_KEY = "read-mode-v1";
export const READ_MODES = ["hanlo", "tl", "poj", "align"];

/** 讀過的篇（id 陣列）；歹 JSON 當做無記錄。 */
export function loadReadProgress(store) {
  try {
    const raw = JSON.parse(store.getItem(READ_PROGRESS_KEY) || "[]");
    return [...new Set(Array.isArray(raw) ? raw.filter((x) => typeof x === "string") : [])];
  } catch {
    return [];
  }
}

export function saveReadProgress(store, ids) {
  store.setItem(READ_PROGRESS_KEY, JSON.stringify([...new Set(ids)]));
}

/** 標做讀過（重號無副作用），回新的 id 陣列。 */
export function markArticleRead(store, id) {
  const ids = loadReadProgress(store);
  if (!ids.includes(id)) ids.push(id);
  saveReadProgress(store, ids);
  return ids;
}

export function unmarkArticleRead(store, id) {
  const ids = loadReadProgress(store).filter((x) => x !== id);
  saveReadProgress(store, ids);
  return ids;
}

export function isArticleRead(ids, id) {
  return ids.includes(id);
}

/** 顯示模式：漢羅｜台羅｜白話字｜對照；歹值鉤轉預設漢羅。 */
export function loadTextMode(store) {
  const v = store.getItem(READ_MODE_KEY);
  return READ_MODES.includes(v) ? v : "hanlo";
}

export function saveTextMode(store, mode) {
  if (READ_MODES.includes(mode)) store.setItem(READ_MODE_KEY, mode);
}

/** #0401-06 → "0401-06"；毋是篇號的 hash → null。 */
export function articleIdFromHash(hash) {
  const m = /^#(\d{4}-\d{2})$/.exec(hash || "");
  return m ? m[1] : null;
}

/** 篇清單 → [{book, categories:[{name, articles}]}]：冊 01→02、類照出現順。 */
export function groupArticles(articles) {
  const books = [];
  for (const a of articles) {
    let b = books.find((x) => x.book === a.book);
    if (!b) books.push((b = { book: a.book, categories: [] }));
    let c = b.categories.find((x) => x.name === a.category);
    if (!c) b.categories.push((c = { name: a.category, articles: [] }));
    c.articles.push(a);
  }
  return books.sort((x, y) => x.book - y.book);
}

/** 出處行：教育部電子報—{paper}{issue}期（{date}）；無日期就免括號。 */
export function sourceLine(article) {
  const s = article.source;
  const head = `教育部電子報—${s.paper}${s.issue}期`;
  return s.date ? `${head}（${s.date}）` : head;
}

/** 漢羅本文＋官方讀音 → [{t:"text",s}|{t:"ruby",han,tl}]；位置歹（字對袂牢、重疊）跳過。 */
export function rubySegments(text, readings) {
  const cps = [...text];
  const out = [];
  let pos = 0;
  const sorted = [...readings].sort((a, b) => a.at - b.at);
  for (const r of sorted) {
    const han = [...r.han];
    if (r.at < pos || r.at + han.length > cps.length) continue;
    if (cps.slice(r.at, r.at + han.length).join("") !== r.han) continue;
    const s = cps.slice(pos, r.at).join("");
    if (s) out.push({ t: "text", s });
    out.push({ t: "ruby", han: r.han, tl: r.tl });
    pos = r.at + han.length;
  }
  const tail = cps.slice(pos).join("");
  if (tail) out.push({ t: "text", s: tail });
  return out;
}
