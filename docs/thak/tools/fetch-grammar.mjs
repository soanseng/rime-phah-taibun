#!/usr/bin/env node
// TGGL 語法點索引——只取「書目級」中繼資料（編號／語法點名／臺羅／群組／頁碼），
// 語法說明與例句原文依 TGGL 授權條款不落地、不重刊，一律連回原系統查閱。
// 來源：臺灣台語語料庫應用檢索系統 https://tggl.naer.edu.tw/grammars（國家教育研究院）
// 用法：node tools/fetch-grammar.mjs  （寫出 data-public/grammars.json）

import { writeFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");
const BASE = "https://tggl.naer.edu.tw";
const UA = { headers: { "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) tl-poj-convert/grammar-index" } };
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const strip = (s) => s.replace(/&nbsp;/g, " ").replace(/&amp;/g, "&").replace(/&lt;/g, "<")
  .replace(/&gt;/g, ">").replace(/&quot;/g, '"').replace(/&#39;/g, "'").trim();

async function get(url) {
  const r = await fetch(url, UA);
  if (!r.ok) throw new Error(`${r.status} ${url}`);
  return r.text();
}

// —— 語法點列表：mobile 版塊（div.md:hidden … <table 前）結構最單純 ——
// 群組外框 x-data="{ groupOpened: true }"；群組標題列 @click="groupOpened = !groupOpened"
// 條目 x-data="{ opened: false }"，前三格葉 div：w-13.5=編號、w-24=語法點、w-30=臺羅。
// 刻意「不」擷取展開區（語法說明／例句）。
function parseList(html) {
  const start = html.indexOf('<div class="md:hidden">');
  const end = html.indexOf("<table", start);
  if (start < 0 || end < 0) throw new Error("listing structure not found");
  const mob = html.slice(start, end);
  const out = [];
  const groups = new Map();
  const chunks = mob.split(/x-data="\{ groupOpened: true \}"/).slice(1);
  for (const chunk of chunks) {
    const firstEntry = chunk.indexOf('x-data="{ opened: false }"');
    const head = firstEntry < 0 ? chunk : chunk.slice(0, firstEntry);
    const gTitle = head.match(/@click="groupOpened = !groupOpened"[\s\S]{0,600}?w-24[^>]*>([^<]+)</);
    const gTitleText = gTitle ? strip(gTitle[1]) : null;
    const bodies = (firstEntry < 0 ? "" : chunk.slice(firstEntry))
      .split(/x-data="\{ opened: false \}"/).slice(1);
    for (const body of bodies) {
      const visible = body.slice(0, body.indexOf("語法說明")); // 展開區之前的中繼欄位
      if (visible < 0 || !visible) continue;
      const id = visible.match(/<div class="[^"]*w-13\.5[^"]*">\s*([^<]+?)\s*</);
      const name = visible.match(/<div class="[^"]*w-24[^"]*">\s*([^<]+?)\s*</);
      const roman = visible.match(/<div class="[^"]*w-30[^"]*">\s*([^<]+?)\s*</);
      if (!id || !name) continue;
      const gid = strip(id[1]);
      const g = gid.split("-")[0];
      if (gTitleText) groups.set(g, gTitleText);
      out.push({ id: gid, name: strip(name[1]), roman: roman ? strip(roman[1]) : "", group: g, groupTitle: gTitleText });
    }
  }
  return { entries: out, groups: [...groups.entries()].map(([no, title]) => ({ no, title })) };
}

// —— 語法小專欄：列表頁標題＋日期＋連結（內文不落地） ——
function parseSnippets(html) {
  const out = [];
  const seen = new Set();
  const re = /<a[^>]*href="\/grammar_snippets\/(\d+)"[^>]*>[\s\S]{0,400}?([^<>]{2,80})<\/[\sa]/g;
  // 標題可能在 <a> 內層 span；退而求其次：對每個連結取鄰近文字
  for (const m of html.matchAll(/href="\/grammar_snippets\/(\d+)"/g)) {
    const id = m[1];
    if (seen.has(id)) continue;
    seen.add(id);
    const around = html.slice(m.index, m.index + 1200);
    const date = around.match(/(\d{4}-\d{2}-\d{2})/);
    const titleM = around.match(/grammar_snippets\/\d+"[^>]*>\s*(?:<[^>]+>\s*)*([^<>]{2,120})/);
    out.push({ id: Number(id), title: titleM ? strip(titleM[1]) : "", date: date ? date[1] : "", url: `${BASE}/grammar_snippets/${id}` });
  }
  return out;
}

const listPages = [];
for (let page = 1; page <= 6; page++) { // n=100；跑完為止（2026-09 實測 >200 筆）
  const html = await get(`${BASE}/grammars?n=100&page=${page}`);
  const { entries, groups } = parseList(html);
  if (!entries.length) break;
  for (const e of entries) e.page = page;
  listPages.push({ entries, groups });
  await sleep(600);
}
const entries = [];
const gmap = new Map();
for (const p of listPages) {
  entries.push(...p.entries);
  for (const g of p.groups) gmap.set(g.no, g.title);
}

// 檢索深連結欄位（導覽表單，非語料內容）：type=word|roman ＋ 文字欄
const probe = await get(`${BASE}/grammars?n=20&page=1`);
const fieldM = probe.match(/action="\/grammars"[\s\S]{0,4000}?<input[^>]*type="text"[^>]*name="([^"]+)"/);

const snipHtml = await get(`${BASE}/grammar_snippets`);
const snippets = parseSnippets(snipHtml);

const payload = {
  meta: {
    source: "臺灣台語語料庫應用檢索系統 TGGL（國家教育研究院）",
    url: `${BASE}/grammars`,
    snippetsUrl: `${BASE}/grammar_snippets`,
    fetched: new Date().toISOString().slice(0, 10),
    license: "TGGL 語料庫授權條款（著作權屬原始著作人；條款約定不得移轉第三人）",
    note: "本檔只收語法點書目索引（編號／名稱／臺羅／群組／頁碼）；語法說明佮例句原文不落地、不重刊，請點連結去原系統查閱。謹此致謝教育部。",
  },
  search: { field: fieldM ? fieldM[1] : null, url: `${BASE}/grammars` },
  entries,
  groups: [...gmap.entries()].map(([no, title]) => ({ no, title })).sort((a, b) => a.no.localeCompare(b.no)),
  snippets,
};
writeFileSync(join(ROOT, "data-public", "grammars.json"), JSON.stringify(payload));
const missing = entries.filter((e) => !e.name || !e.id).length;
console.log(`entries=${entries.length} groups=${payload.groups.length} snippets=${snippets.length} searchField=${payload.search.field} missingNameOrId=${missing}`);
const dup = new Set(entries.map((e) => e.id)).size;
if (dup !== entries.length) console.error(`WARN: duplicate ids ${entries.length - dup}`);
