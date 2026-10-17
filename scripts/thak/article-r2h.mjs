// 讀文章官方讀音 → 漢字回歸：bun scripts/thak/article-r2h.mjs [bundle]
// 語料：docs/read/data/articles.json 官方讀音（vocab 有 tl 的詞條＋逐段 readings），
// 用 measure-r2h 仝款的 decodeTlToHan＋buildLM 逐詞解碼，exact-match 對冊內漢字；
// 低於下跤釘牢的基準就 exit 1（test_thak_tools.py 佇 bun 有才跑）。
import { buildReverseIndex, buildLM, decodeTlToHan } from "../../docs/thak/js/dict.js?v=21";
import { readFileSync } from "node:fs";
import { isAbsolute, join } from "node:path";

const root = new URL("../../docs/thak/", import.meta.url).pathname;
const arg = process.argv[2] || "data-public";
const bundle = isAbsolute(arg) ? arg : join(root, arg);
const dict = JSON.parse(readFileSync(join(bundle, "dict.json"), "utf8"));
const rev = buildReverseIndex(dict);
const lm = buildLM(JSON.parse(readFileSync(join(bundle, "bigrams.json"), "utf8")));

const repo = new URL("../../", import.meta.url).pathname;
const arts = JSON.parse(readFileSync(join(repo, "docs/read/data/articles.json"), "utf8")).articles;
// 官方讀音對（漢字, 台羅調符）：詞彙表＋逐段官方讀音
const pairs = [];
for (const a of arts) {
  for (const v of a.vocab) if (v.tl) pairs.push([v.han, v.tl]);
  for (const p of a.paragraphs) for (const r of p.readings ?? []) pairs.push([r.han, r.tl]);
}

// 干焦比漢字（解碼結果可能帶原始標點／空白）
const isHanC = (ch) => {
  const o = ch.codePointAt(0);
  return (o >= 0x3400 && o <= 0x9fff) || (o >= 0x20000 && o <= 0x3ffff);
};
const hanOnly = (s) => [...String(s)].filter(isHanC).join("");

let hit = 0;
const miss = [];
for (const [han, tl] of pairs) {
  const got = hanOnly(decodeTlToHan(tl, rev, lm).han);
  if (got === hanOnly(han)) hit++;
  else if (miss.length < 12) miss.push(`  ${tl}：欲 ${han}，得 ${got}`);
}
const rate = hit / pairs.length;
// 基準照 2026-10-16 實測釘牢（data-public bundle：1295 詞、749 中＝57.8%；詞典若閣加料才會當重釘）
const BASELINE = 749 / 1295;
console.log(`讀文章官方讀音 r2h：${pairs.length} 詞，exact-match ${(rate * 100).toFixed(1)}%（基準 ≥ ${(BASELINE * 100).toFixed(1)}%）`);
if (miss.length) console.log("樣本 miss：\n" + miss.join("\n"));
if (rate < BASELINE) console.log("低於基準——羅→漢解碼退化");
process.exit(rate >= BASELINE ? 0 : 1);
