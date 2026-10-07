// 最後測試：Wiki Tô·-su-kóan「Cha̍p-hāng Koán-kiàn」（蔡培火 1925，純 POJ）
// 十章全文跑羅→漢解碼。獨立語料：無入 LM 訓練、無調參。
// 指標：無 crash、音節涵蓋率（matched/total）、逐章輸出樣本（無漢字金標準，
// 袂算字元準確率）。來源佮授權：tools/wikisource/SOURCE.md。
// 語料袂入版控——無檔就自動掠（idempotent）。執行：bun tools/wikisource-r2h.mjs
import { buildReverseIndex, buildLM, decodeTlToHan } from "../js/dict.js?v=21";
import { existsSync, readFileSync, readdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";

const root = new URL("..", import.meta.url).pathname;
const wsDir = join(root, "tools/wikisource");

for (let i = 1; i <= 10; i++) {
  const f = join(wsDir, `te${i}.wiki`);
  if (existsSync(f)) continue;
  const url = `https://zh-min-nan.wikisource.org/wiki/Cha%CC%8Dp-h%C4%81ng_Ko%C3%A1n-ki%C3%A0n/T%C4%93_${i}_h%C4%81ng?action=raw`;
  const t = await (await fetch(url)).text();
  if (!t.includes("Koán-kiàn")) throw new Error(`下載失敗 te${i}: ${t.slice(0, 80)}`);
  writeFileSync(f, t);
}

const dict = JSON.parse(readFileSync(join(root, "data-public/dict.json"), "utf8"));
const rev = buildReverseIndex(dict);
const lm = buildLM(JSON.parse(readFileSync(join(root, "data-public/bigrams.json"), "utf8")));

// 輕量 wikitext 清理：header 模板、連結、粗斜體拿掉；== 標題 == 留內文。
const clean = (raw) => raw
  .replace(/\{\{header[\s\S]*?\}\}/, "")
  .replace(/\[\[[^\]|]*\|([^\]]*)\]\]/g, "$1")
  .replace(/\[\[([^\]]*)\]\]/g, "$1")
  .replace(/'''?/g, "")
  .trim();

const files = readdirSync(wsDir).filter((f) => f.endsWith(".wiki")).sort();
let mSum = 0, tSum = 0;
for (const f of files) {
  const text = clean(readFileSync(join(wsDir, f), "utf8"));
  const t0 = performance.now();
  const r = decodeTlToHan(text, rev, lm);
  const ms = (performance.now() - t0).toFixed(0);
  mSum += r.matched; tSum += r.total;
  console.log(`${f}  涵蓋=${(100 * r.matched / r.total).toFixed(1)}%  (${r.matched}/${r.total})  ${ms}ms`);
  console.log(`  樣本: ${r.han.slice(0, 90).replace(/\n/g, " ")}`);
}
console.log(`總計涵蓋=${(100 * mSum / tSum).toFixed(1)}%  (${mSum}/${tSum})`);
