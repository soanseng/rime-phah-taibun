// A/B：trigram 開vs關（同 bundle、同解碼參數）——四語料 char-sim
import { buildReverseIndex, buildLM, decodeTlToHan } from "../js/dict.js?v=12";
import { toNumeric } from "../js/roman.js?v=12";
import { readFileSync } from "node:fs";
import { join } from "node:path";

const root = new URL("..", import.meta.url).pathname;
const dict = JSON.parse(readFileSync(join(root, "data-public/dict.json"), "utf8"));
const rev = buildReverseIndex(dict);
const lmFull = buildLM(JSON.parse(readFileSync(join(root, "data-public/bigrams.json"), "utf8")));
const lmOff = { ...lmFull, trigrams: new Map() };

const isHanC = (ch) => {
  const o = ch.codePointAt(0);
  return (o >= 0x3400 && o <= 0x9fff) || (o >= 0x20000 && o <= 0x3ffff);
};
const lcs = (a, b) => {
  if (!a.length || !b.length) return 1;
  let prev = new Array(b.length + 1).fill(0);
  for (let i = 1; i <= a.length; i++) {
    const cur = new Array(b.length + 1).fill(0);
    for (let j = 1; j <= b.length; j++)
      cur[j] = a[i - 1] === b[j - 1] ? prev[j - 1] + 1 : Math.max(prev[j], cur[j - 1]);
    prev = cur;
  }
  return prev[b.length];
};
// 例句語料 A/B（trigram 覆蓋的日常域）：用 sentences.json 抽 400 句，
// 漢句經辭典→TL（teach 中的循環風險低：h2r 用 r2h 不參與）再解回。
// 簡化：直接取例句 TL 解碼 vs 金標漢句。
const sents = JSON.parse(readFileSync(join(root, "data-public/sentences.json"), "utf8")).s;
const sample = [];
for (let i = 0; i < sents.length && sample.length < 400; i += 29) sample.push(sents[i]);

const run = (lm) => {
  let sum = 0, t = 0;
  for (const [han, tl] of sample) {
    const gold = [...han].filter(isHanC).join("");
    if (!gold) continue;
    const out = decodeTlToHan(tl, rev, lm).han;
    sum += lcs([...out].filter(isHanC).join(""), gold);
    t += gold.length;
  }
  return (sum / t) * 100;
};
console.log(`例句域(400句): tri-off=${run(lmOff).toFixed(2)}%  tri-on=${run(lmFull).toFixed(2)}%`);

for (const c of ["weightloss", "brownfat", "epigenetics", "nobel"]) {
  const paras = readFileSync(join(root, `tools/${c}-corpus.txt`), "utf8")
    .split(/\n\s*\n/).map((s) => s.trim()).filter(Boolean);
  const pairs = [];
  let pending = null;
  for (const p of paras) {
    const hR = [...p].filter(isHanC).length / [...p].length;
    if (hR > 0.45) { pending = p; continue; }
    if (hR < 0.15 && pending) { pairs.push([pending, p]); pending = null; }
  }
  const runC = (lm) => {
    let sum = 0, t = 0;
    for (const [goldTxt, tl] of pairs) {
      const gold = [...goldTxt].filter(isHanC).join("");
      if (!gold) continue;
      const out = decodeTlToHan(tl, rev, lm).han;
      sum += lcs([...out].filter(isHanC).join(""), gold);
      t += gold.length;
    }
    return (sum / t) * 100;
  };
  console.log(`${c.padEnd(12)} tri-off=${runC(lmOff).toFixed(2)}%  tri-on=${runC(lmFull).toFixed(2)}%`);
}
