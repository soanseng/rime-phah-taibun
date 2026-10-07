// 讀音條件化 unigram（runi）：對齊教典例句（漢字數＝音節數的句），
// 逐字累計 (漢字, 去調音節) 次數 → 寫入 data-public/bigrams.json 的 "runi"。
// 動機：uni 只有字詞頻——「到」的 373 全是 kau 用法，煞嘛替 tio̍h 鍵加分；
// runi 予解碼器用「這字佇這音」的實計數（著@tioh > 到@tioh）。
// 執行：bun tools/build-runi.mjs  （冪等：重跑覆寫 runi）
import { toNumeric, pojToTl } from "../js/roman.js?v=21";
import { readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";

const root = new URL("..", import.meta.url).pathname;
const dir = join(root, "data-public");
const dict = JSON.parse(readFileSync(join(dir, "dict.json"), "utf8"));
const sents = JSON.parse(readFileSync(join(dir, "sentences.json"), "utf8")).s;

const isHanC = (ch) => {
  const o = ch.codePointAt(0);
  return (o >= 0x3400 && o <= 0x9fff) || (o >= 0x20000 && o <= 0x3ffff);
};
const ROM = /[A-Za-z0-9\u00C0-\u024F\u0300-\u036f\u0358\u207F-]+/g;
const sylls = (tl) => {
  const out = [];
  for (const m of tl.matchAll(ROM))
    for (const p of m[0].split(/-+/)) {
      const num = toNumeric(p);
      if (num) out.push(pojToTl(num).toLowerCase().replace(/[0-9]/g, ""));
    }
  return out;
};
// 逐字單音節讀音索引（教典為準）
const charRead = new Map();
for (const [w, e] of Object.entries(dict)) {
  if ([...w].length !== 1 || !isHanC(w)) continue;
  for (const r of e.r) {
    const b = pojToTl(r).replace(/[0-9]/g, "");
    if (!charRead.has(w)) charRead.set(w, new Set());
    charRead.get(w).add(b);
  }
}
const runi = {};
let used = 0, pairs = 0;
for (const [han, tl] of sents) {
  const H = [...han].filter(isHanC), S = sylls(String(tl));
  if (!H.length || H.length !== S.length) continue;
  pairs++;
  H.forEach((c, k) => {
    if (charRead.get(c)?.has(S[k])) {
      const key = `${c}\t${S[k]}`;
      runi[key] = (runi[key] ?? 0) + 1;
    }
  });
}
used = Object.values(runi).reduce((a, b) => a + b, 0);
const lm = JSON.parse(readFileSync(join(dir, "bigrams.json"), "utf8"));
lm.runi = runi;
writeFileSync(join(dir, "bigrams.json"), JSON.stringify(lm));
console.log(`runi: ${pairs} 對齊句, ${Object.keys(runi).length} 鍵, ${used} 次數 → bigrams.json`);
