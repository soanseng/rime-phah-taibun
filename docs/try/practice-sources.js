// 練習題目來源：例句庫（轉換工具的 sentences.json）、詞語、維基百科／維基文庫（閩南語，POJ，
// 瀏覽器即時讀，無存檔）、自訂文章（漢羅或羅馬字）。
// 每个來源回 {title, url, license, kind, key, items}；item = {text, slots, gloss?}。
import { alignSentence, romanSlots, splitSentences, sylKey, buildCharKeys } from "./practice-core.js?v=2";
import { loadDict, segment, buildReverseIndex, buildLM, decodeTlToHan, practicePool } from "../thak/js/dict.js?v=26";
import { pojToTl, formatRomanization } from "../thak/js/roman.js?v=26";

// 模組相對：/try/ 佮 /study/*/ 頁攏會當用（資料佇 /thak/data-public/）
const THAK_DATA = new URL("../thak/data-public/", import.meta.url).href;
export const WP_HOST = "zh-min-nan.wikipedia.org";
export const WS_HOST = "zh-min-nan.wikisource.org";

// ---- 例句庫 ----
let bankPromise = null;
export function loadBank() {
  bankPromise ??= fetch(THAK_DATA + "sentences.json")
    .then((r) => (r.ok ? r.json() : Promise.reject(new Error("例句庫載入失敗"))))
    .then(async ({ s }) => {
      const items = [];
      const rows = s ?? [];
      for (let k = 0; k < rows.length; k++) {
        // 一萬外句對齊：每 1000 句讓主線程喘一下，免一个長任務卡牢頁面（TBT）
        if (k && k % 1000 === 0) await new Promise((r) => setTimeout(r, 0));
        const [han, tl, hoabun] = rows[k];
        const slots = alignSentence(han, tl);
        if (slots && slots.length >= 3 && slots.length <= 20) items.push({ text: han, slots, gloss: hoabun || "" });
      }
      return {
        kind: "bank", key: null, title: "教典例句／新北市900例句", url: null,
        license: "教育部臺灣台語常用詞辭典 CC BY-ND 3.0 TW；新北市900例句 MIT", items,
      };
    });
  bankPromise.catch(() => { bankPromise = null; });
  return bankPromise;
}

// 固定 seed 的洗牌（mulberry32）：聽寫題順序逐擺仝款，進度（第幾題）重整了後才對會著
export function seededShuffle(arr, seed) {
  let a = seed >>> 0;
  const rnd = () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
  const out = arr.slice();
  for (let i = out.length - 1; i > 0; i--) {
    const j = Math.floor(rnd() * (i + 1));
    [out[i], out[j]] = [out[j], out[i]];
  }
  return out;
}

// ---- 聽寫（教典例句原音；/study/data/listen.json + /study/audio/*.mp3）----
export function listenItems(json, base = import.meta.url) {
  const items = [];
  for (const { id, han, tl, hoa, audio } of json.items ?? []) {
    const slots = alignSentence(han, tl);
    if (slots) items.push({ id, text: han, slots, gloss: hoa || "", audio: new URL(`../study/audio/${audio}`, base).href });
  }
  return items;
}
let listenPromise = null;
export function loadListen() {
  listenPromise ??= fetch(new URL("../study/data/listen.json", import.meta.url))
    .then((r) => (r.ok ? r.json() : Promise.reject(new Error("聽寫題庫載入失敗"))))
    .then((json) => ({
      kind: "listen", key: "listen", title: "教典例句原音聽寫", url: "https://sutian.moe.edu.tw/",
      license: "教育部臺灣台語常用詞辭典 例句文字佮音檔 CC BY-ND 3.0 TW",
      items: seededShuffle(listenItems(json), 20261008),
    }));
  listenPromise.catch(() => { listenPromise = null; });
  return listenPromise;
}

// ---- 轉換工具的詞典（詞語、自訂文章、維基用；需要才載）----
let dictPromise = null;
export function loadDictBundle() {
  dictPromise ??= loadDict(THAK_DATA + "dict.json").then((dict) => ({
    dict, charKeys: buildCharKeys(dict), rev: buildReverseIndex(dict),
  }));
  dictPromise.catch(() => { dictPromise = null; });
  return dictPromise;
}
let lmPromise = null;
const loadLM = () => {
  lmPromise ??= fetch(THAK_DATA + "bigrams.json")
    .then((r) => (r.ok ? r.json() : Promise.reject(new Error("語言模型載入失敗"))))
    .then(buildLM);
  lmPromise.catch(() => { lmPromise = null; });
  return lmPromise;
};

// 羅馬字句的參考漢羅（羅→漢自動轉寫，可能有誤）
export async function refHanFor(text) {
  const [{ rev }, lm] = await Promise.all([loadDictBundle(), loadLM()]);
  return decodeTlToHan(pojToTl(text), rev, lm).han;
}

// ---- 詞語（2–4 字、有華語釋義的詞；看漢字＋讀音拍，愛仝字）----
let wordsPromise = null;
export function loadWords() {
  wordsPromise ??= loadDictBundle().then(({ dict }) => {
    const items = [];
    for (const { han, r, h } of practicePool(dict)) {
      const chars = [...han];
      const syls = r[0].split(" ").filter(Boolean);
      if (syls.length !== chars.length || /[A-Za-z]/.test(han)) continue;
      items.push({
        text: han, gloss: h,
        slots: chars.map((c, i) => ({ h: c, k: sylKey(syls[i]), src: formatRomanization(syls[i]) })),
      });
    }
    return { kind: "words", key: null, title: "詞語（2–4 字）", url: null, license: "本站轉換詞典（來源見轉換頁）", items };
  });
  wordsPromise.catch(() => { wordsPromise = null; });
  return wordsPromise;
}

const fromRomanText = (text) => splitSentences(text).map((s) => ({ text: s, slots: romanSlots(s), roman: true }));

// 漢羅句 → 格：轉換工具的詞典斷詞，詞的頭一个讀音逐字對位（自動標音，可能有誤）
function hanloSlots(sentence, dict, rev) {
  const slots = [];
  for (const seg of segment(sentence, dict, rev)) {
    if (seg.t === "w") {
      const chars = [...seg.han];
      const syls = seg.readings[0].split(" ").filter(Boolean);
      if (syls.length === chars.length) {
        chars.forEach((c, i) => slots.push({ h: c, k: sylKey(syls[i]), src: formatRomanization(syls[i]) }));
      } else {
        for (const c of chars) slots.push({ h: c, k: null, src: c });
      }
    } else if (seg.t === "r") {
      slots.push(...romanSlots(seg.s));
    } else {
      slots.push({ h: seg.s, k: null, src: seg.s });
    }
  }
  return slots;
}

// ---- 自訂文章 ----
export const CUSTOM_KEY = "phahtaibun.practice.custom";
export async function fromCustom(text) {
  try { localStorage.setItem(CUSTOM_KEY, text); } catch { /* 私密模式：袂存無要緊 */ }
  const han = [...text].filter((c) => /\p{Script=Han}/u.test(c)).length;
  const latin = (text.match(/[A-Za-z]/g) ?? []).length;
  const base = { kind: "custom", key: `custom:${text.trim().slice(0, 32)}`, title: "自訂文章", url: null, license: "—" };
  if (han >= latin / 3) {
    const { dict, rev } = await loadDictBundle();
    const items = splitSentences(text)
      .map((s) => ({ text: s, slots: hanloSlots(s, dict, rev), autoReading: true }))
      .filter((it) => it.slots.length >= 2);
    return { ...base, items };
  }
  return { ...base, items: fromRomanText(text) };
}

// ---- MediaWiki ----
async function mw(host, params) {
  let r;
  try {
    r = await fetch(`https://${host}/w/api.php?` + new URLSearchParams({
      format: "json", formatversion: "2", origin: "*", ...params,
    }));
  } catch {
    throw new Error("維基連線失敗");
  }
  if (!r.ok) throw new Error("維基連線失敗");
  return r.json();
}
const pageUrl = (host, title) => `https://${host}/wiki/${encodeURIComponent(title.replace(/ /g, "_"))}`;
const LIC = { [WP_HOST]: "CC BY-SA 4.0（維基百科）", [WS_HOST]: "維基文庫（各篇授權詳見原頁）" };

async function extract(host, title, intro) {
  const d = await mw(host, {
    action: "query", prop: "extracts", explaintext: "1", redirects: "1", titles: title,
    ...(intro ? { exintro: "1" } : {}),
  });
  const p = d.query?.pages?.[0];
  if (!p || p.missing) throw new Error(`揣無這篇：${title}`);
  return { title: p.title, text: p.extract ?? "" };
}

const DAYS = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
// 維基百科「媠氣的文章」每日精選（約 700 字精選散文）；隨機揀一工
export async function randomWikipediaFeatured() {
  for (let tries = 0; tries < 3; tries++) {
    const m = 1 + Math.floor(Math.random() * 12);
    const day = 1 + Math.floor(Math.random() * DAYS[m - 1]);
    const { title, text } = await extract(WP_HOST, `Wikipedia:Súi-khùi ê bûn-chiuⁿ/${m} goe̍h ${day} ji̍t`, false)
      .catch(() => ({ title: "", text: "" }));
    const items = fromRomanText(text);
    if (items.length) {
      return {
        kind: "wikipedia", key: `wikipedia:${title}`, title: `維基百科媠氣文章・${m} goe̍h ${day} ji̍t`,
        url: pageUrl(WP_HOST, title), license: LIC[WP_HOST], items,
      };
    }
  }
  throw new Error("揣無今仔日的媠氣文章");
}

// 網址或標題 → {host, title}；毋是這兩个維基的網址當做維基百科標題
export function parseWikiInput(input) {
  const s = String(input ?? "").trim();
  try {
    const u = new URL(s);
    if ((u.hostname === WP_HOST || u.hostname === WS_HOST) && u.pathname.startsWith("/wiki/")) {
      return { host: u.hostname, title: decodeURIComponent(u.pathname.slice(6)).replace(/_/g, " ") };
    }
  } catch {
    // 毋是網址：當做標題
  }
  return { host: WP_HOST, title: s.replace(/_/g, " ") };
}

export async function wikiArticle(input) {
  const { host, title: asked } = parseWikiInput(input);
  if (!asked) throw new Error("請貼維基網址抑是文章標題");
  const { title, text } = await extract(host, asked, host === WP_HOST);
  const items = fromRomanText(text);
  if (!items.length) throw new Error(`這篇無通練習的羅馬字內文：${title}`);
  const kind = host === WP_HOST ? "wikipedia" : "wikisource";
  return { kind, key: `${kind}:${title}`, title, url: pageUrl(host, title), license: LIC[host], items };
}

// ---- 維基文庫：揀冊、揀章 ----
const FALLBACK_BOOKS = [
  "Cha̍p-hāng Koán-kiàn", "Pit-soàn ê Chho͘-ha̍k", "Hông-hun ê Kò͘-hiong", "An-lo̍k-ke", "Ín Ka Tòng Tō",
  "Pan-iâng", "Sin-kū-iok ê Sèng-keng", "Lāi Gōa Kho Khàn-hō·-ha̍k", "Chú ê Kî-tó-bûn", "Sú-tô͘ Sìn-keng",
];
let booksPromise = null;
export function wikisourceBooks() {
  booksPromise ??= mw(WS_HOST, { action: "parse", page: "Thâu-ia̍h", prop: "links" })
    .then((d) => (d.parse?.links ?? []).filter((l) => l.ns === 0 && !l.title.includes(":")).map((l) => l.title))
    .then((titles) => (titles.length >= 3 ? titles : FALLBACK_BOOKS).sort((a, b) => a.localeCompare(b)))
    .catch(() => FALLBACK_BOOKS.slice().sort((a, b) => a.localeCompare(b)));
  return booksPromise;
}

// 自然排序：先比標題內頭一个數字（Tē 2 hāng < Tē 10 hāng），才比文字
export function naturalCompare(a, b) {
  const na = Number(a.match(/\d+/)?.[0] ?? NaN);
  const nb = Number(b.match(/\d+/)?.[0] ?? NaN);
  if (!Number.isNaN(na) && !Number.isNaN(nb) && na !== nb) return na - nb;
  return a.localeCompare(b);
}

// 冊／章的子頁（直接下一層）；無子頁就回 []。title 先解轉址（舊標題）
export async function wikisourceChildren(title) {
  const q = await mw(WS_HOST, { action: "query", titles: title, redirects: "1" });
  const canonical = q.query?.pages?.[0]?.title ?? title;
  const d = await mw(WS_HOST, { action: "query", list: "allpages", apprefix: `${canonical}/`, aplimit: "500" });
  const children = (d.query?.allpages ?? [])
    .map((p) => p.title)
    .filter((t) => !t.slice(canonical.length + 1).includes("/"))
    .sort((a, b) => naturalCompare(a.slice(canonical.length + 1), b.slice(canonical.length + 1)));
  return { canonical, children };
}

// 單頁的冊：照 == 標題 == 切章；無標題就每 30 句一段
export function splitChapters(text) {
  const chapters = [];
  let cur = null;
  for (const line of String(text ?? "").split("\n")) {
    const h = line.match(/^\s*==+\s*(.+?)\s*==+\s*$/);
    if (h) {
      cur = { name: h[1], text: "" };
      chapters.push(cur);
    } else {
      if (!cur) chapters.push((cur = { name: "", text: "" }));
      cur.text += line + "\n";
    }
  }
  const real = chapters.filter((c) => splitSentences(c.text).length);
  if (real.length > 1 || (real.length === 1 && real[0].name)) {
    return real.map((c, i) => ({ name: c.name || `第 ${i + 1} 段`, text: c.text }));
  }
  const sents = splitSentences(text);
  const out = [];
  for (let i = 0; i < sents.length; i += 30) out.push({ name: `第 ${out.length + 1} 段`, text: sents.slice(i, i + 30).join("\n") });
  return out;
}

export async function wikisourcePage(title) {
  const { title: real, text } = await extract(WS_HOST, title, false);
  return { title: real, url: pageUrl(WS_HOST, real), chapters: splitChapters(text) };
}

export function wikisourceChapter(page, chapter) {
  const items = fromRomanText(chapter.text);
  const name = chapter.name ? `${page.title}・${chapter.name}` : page.title;
  return {
    kind: "wikisource", key: `wikisource:${page.title}#${chapter.name}`,
    title: name, url: page.url, license: LIC[WS_HOST], items,
  };
}
