// 羅→漢評測（bun tools/measure-r2h.mjs）
import { buildReverseIndex, buildLM, decodeTlToHan, tlToHan } from "../js/dict.js";
import { readFileSync } from "node:fs";
const root = "/home/scipio/projects/tl-poj-convert/";
const dict = JSON.parse(readFileSync(root + "data-public/dict.json", "utf8"));
const rev = buildReverseIndex(dict);
const lm = buildLM(JSON.parse(readFileSync(root + "data-public/bigrams.json", "utf8")));
const isHanC = (ch) => { const o = ch.codePointAt(0); return (o >= 0x3400 && o <= 0x9fff) || (o >= 0x20000 && o <= 0x3ffff); };
const lcs = (a, b) => {
  if (!a.length || !b.length) return 1;
  let prev = new Array(b.length + 1).fill(0);
  for (let i = 1; i <= a.length; i++) {
    const cur = new Array(b.length + 1).fill(0);
    for (let j = 1; j <= b.length; j++) cur[j] = a[i-1] === b[j-1] ? prev[j-1]+1 : Math.max(prev[j], cur[j-1]);
    prev = cur;
  }
  return (2*prev[b.length])/(a.length+b.length);
};
const text = readFileSync(root + "tools/weightloss-corpus.txt", "utf8");
const paras = text.split(/\n\s*\n/).map(s=>s.trim()).filter(Boolean);
const pairs = [];
let pending = null;
for (const p of paras) {
  const hR = [...p].filter(isHanC).length / [...p].length;
  if (hR > 0.5) { pending = p; continue; }
  if (hR < 0.15 && pending) { pairs.push([pending, p]); pending = null; }
}
console.log(`pairs=${pairs.length}（首字：${pairs.map(([h])=>h.slice(0,4)).join("／")}）`);
const variants = [
  ["greedy", (tl)=>tlToHan(tl, rev)],
  ["lattice base", (tl)=>decodeTlToHan(tl, rev, lm)],
  ["interp .6", (tl)=>decodeTlToHan(tl, rev, lm, {interp:0.6})],
  ["interp .8", (tl)=>decodeTlToHan(tl, rev, lm, {interp:0.8})],
  ["unk 6", (tl)=>decodeTlToHan(tl, rev, lm, {unknownCost:6})],
  ["gloss 0", (tl)=>decodeTlToHan(tl, rev, lm, {glossBonus:0})],
  ["beam 16", (tl)=>decodeTlToHan(tl, rev, lm, {beamWidth:16})],
];
for (const [label, fn] of variants) {
  let sum=0, m=0, t=0;
  for (const [g, tl] of pairs) {
    const r = fn(tl);
    sum += lcs([...r.han].filter(isHanC).join(""), [...g].filter(isHanC).join(""));
    m += r.matched; t += r.total;
  }
  console.log(`${label.padEnd(12)} char-sim=${((sum/pairs.length)*100).toFixed(1)}%  covered=${((m/t)*100).toFixed(1)}%`);
}
const s1 = decodeTlToHan(pairs[0][1], rev, lm);
console.log("\n樣本:", s1.han.slice(0, 90));
console.log("金標:", [...pairs[0][0]].filter(isHanC).join("").slice(0, 90));
console.log("\n保留:", JSON.stringify(decodeTlToHan("Goá kin-á-ji̍t beh khì Tâi-pak.\nLí kám ē? xyz!", rev, lm).han));
