// 雙向評測：bun tools/measure-r2h.mjs [bundle] [corpus]
// bundle 預設 data-public；corpus 預設 weightloss（開發集）
import {
  segment, render, buildReverseIndex, buildLM, decodeTlToHan, tlToHan,
} from "../js/dict.js?v=2";
import { toNumeric } from "../js/roman.js?v=2";
import { readFileSync } from "node:fs";

const root = new URL("..", import.meta.url).pathname;
const bundle = process.argv[2] || "data-public";
const corpus = process.argv[3] || "weightloss-corpus.txt";

const dict = JSON.parse(readFileSync(`${root}${bundle}/dict.json`, "utf8"));
const rev = buildReverseIndex(dict);
const lm = buildLM(JSON.parse(readFileSync(`${root}${bundle}/bigrams.json`, "utf8")));

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
  return (2 * prev[b.length]) / (a.length + b.length);
};
const syls = (t) =>
  toNumeric(t.replace(/--/g, " ")).split(/[\s\-,.;:!?()"“”《》〈〉·]+/).filter((x) => /^[a-z0-9]+$/.test(x));
const tlJoin = (arr) => arr.map((s) => s.replace(/[0-9]/g, "")).join("");

const paras = readFileSync(`${root}tools/${corpus}`, "utf8")
  .split(/\n\s*\n/).map((s) => s.trim()).filter(Boolean);
const pairs = [];
let pending = null;
for (const p of paras) {
  const hR = [...p].filter(isHanC).length / [...p].length;
  if (hR > 0.5) { pending = p; continue; }
  if (hR < 0.15 && pending) { pairs.push([pending, p]); pending = null; }
}
console.log(`[${bundle}｜${corpus}] pairs=${pairs.length}`);

// ---- A：漢→TL ----
let aSim = 0, aMiss = 0, aHan = 0;
for (const [h, tlGold] of pairs) {
  const segs = segment(h, dict);
  const out = render(segs).tl;
  aMiss += segs.filter((s) => s.t === "miss").length;
  aHan += [...h].filter(isHanC).length;
  aSim += lcs(tlJoin(syls(toNumeric(out))), tlJoin(syls(toNumeric(tlGold))));
}
console.log(`A 漢→TL   toneless-sim=${((aSim / pairs.length) * 100).toFixed(1)}%  涵蓋=${((1 - aMiss / aHan) * 100).toFixed(1)}%`);

// ---- B：羅→漢 ----
for (const [label, fn] of [
  ["B greedy", (tl) => tlToHan(tl, rev)],
  ["B lattice", (tl) => decodeTlToHan(tl, rev, lm)],
]) {
  let sum = 0, m = 0, t = 0;
  for (const [g, tl] of pairs) {
    const r = fn(tl);
    sum += lcs([...r.han].filter(isHanC).join(""), [...g].filter(isHanC).join(""));
    m += r.matched; t += r.total;
  }
  console.log(`${label.padEnd(9)} char-sim=${((sum / pairs.length) * 100).toFixed(1)}%  covered=${((m / t) * 100).toFixed(1)}%`);
}
const s1 = decodeTlToHan(pairs[0][1], rev, lm);
console.log("樣本:", s1.han.slice(0, 80));
console.log("金標:", [...pairs[0][0]].filter(isHanC).join("").slice(0, 80));
