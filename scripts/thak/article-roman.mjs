// 讀文章蓋趣味 全文羅馬字：bun scripts/thak/article-roman.mjs
// 讀 docs/read/data/articles.json（build_article_data.py 產生）＋轉換詞典 docs/thak/data-public/dict.json，
// 逐段轉台羅／白話字，寫 docs/read/data/roman.json。手冊括號註的官方讀音優先，其他照詞典自動轉換。
import { readFileSync, writeFileSync } from "node:fs";
import { buildReverseIndex } from "../../docs/thak/js/dict.js?v=26";
import { romanizeParagraph } from "../../docs/read/read-core.js";

const docs = new URL("../../docs/", import.meta.url).pathname;
const articles = JSON.parse(readFileSync(`${docs}read/data/articles.json`, "utf8")).articles;
const dict = JSON.parse(readFileSync(`${docs}thak/data-public/dict.json`, "utf8"));
const rev = buildReverseIndex(dict);

const nfc = (s) => s.normalize("NFC");
const out = {};
let words = 0, official = 0, miss = 0;
for (const art of articles) {
  out[art.id] = art.paragraphs.map((p) => {
    const r = romanizeParagraph(p.text, p.readings, dict, rev);
    words += r.words.length;
    official += r.words.filter((w) => w.o).length;
    miss += r.words.filter((w) => w.miss).length;
    return { tl: nfc(r.tl), poj: nfc(r.poj), w: r.words };
  });
}
const meta = {
  note: "台羅／白話字由寫台文轉換詞典自動轉換，手冊括號註明的詞用官方讀音；其他讀音可能有誤，請以音檔為準",
  dict: "docs/thak/data-public/dict.json",
};
writeFileSync(`${docs}read/data/roman.json`, JSON.stringify({ meta, articles: out }) + "\n");
console.log(`${articles.length} 篇, ${words} 詞 (官方讀音 ${official}, 查無 ${miss}) → docs/read/data/roman.json`);
