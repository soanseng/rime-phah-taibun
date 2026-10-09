// 寫作檢查語料評估（開發用，毋是單元測試）：用真實文本量誤報佮檢出率。
// A. 教典例句（docs/study/data/listen.json）台文漢字 → 應該「真少問題」（誤報）
// B. 仝批例句的華語翻譯 → 應該「大部分有標」（檢出率）
// C. 台灣教會公報 漢羅版（data/Khin-hoan_2010_pojbh，本機有才跑）→ 誤報
// D. 白話字：十項管見（wikisource，無檔自動掠）＋教會公報 POJ 版 → 拼寫檢查誤報
// 執行：bun scripts/thak/check-eval.mjs [--n 200] [--show 15]
import { readFileSync, existsSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import {
  runChecks, buildSyllableSet, buildMultiReadings, buildAltMap, buildLkkMap,
  buildCharMap, buildWordReadings, buildGlossIndex,
} from "../../docs/check/check-core.js?v=5";
import { segment, buildReverseIndex } from "../../docs/thak/js/dict.js?v=26";

const arg = (k, d) => {
  const i = process.argv.indexOf(k);
  return i > 0 ? Number(process.argv[i + 1]) : d;
};
const N = arg("--n", 200);
const SHOW = arg("--show", 15);

const repo = new URL("../../", import.meta.url).pathname;
const J = (p) => JSON.parse(readFileSync(join(repo, p), "utf8"));
const dict = J("docs/thak/data-public/dict.json");
const rev = buildReverseIndex(dict);
const iongji = J("docs/study/data/iongji.json");
const yongji = J("docs/study/data/yongji.json");
const base = {
  syllableSet: buildSyllableSet(dict),
  multiReadings: buildMultiReadings(dict, new Set(J("docs/check/data/hyphen-words.json").words)),
  altMap: buildAltMap(iongji.items),
  lkkMap: buildLkkMap(yongji.items),
  charMap: buildCharMap(yongji.items),
  wordReadings: buildWordReadings(yongji.items),
  recWords: new Set(yongji.items.map((it) => it.word)),
  glossIndex: buildGlossIndex(dict),
  dict,
  hints: J("docs/thak/data-public/hints.json"),
};
const check = (t, mode = "moe") => runChecks(t, { ...base, mode, segments: segment(t, dict, rev) });

function report(title, texts, mode, { expectFlag = false } = {}) {
  const byCat = {};
  let flagged = 0;
  const samples = [];
  for (const t of texts) {
    const iss = check(t, mode);
    if (iss.length) flagged += 1;
    for (const i of iss) {
      byCat[i.cat] = (byCat[i.cat] ?? 0) + 1;
      if (samples.length < SHOW && !expectFlag) samples.push(`  [${i.cat}] ${t.slice(i.start, i.end)} ← ${t.slice(0, 40)} ｜ ${i.msg}`);
    }
    if (expectFlag && !iss.length && samples.length < SHOW) samples.push(`  （漏）${t}`);
  }
  const pct = ((100 * flagged) / Math.max(1, texts.length)).toFixed(1);
  console.log(`\n== ${title}（${mode}）：${texts.length} 句，有標 ${flagged}（${pct}%）`, JSON.stringify(byCat));
  for (const s of samples) console.log(s);
  return { n: texts.length, flagged, byCat };
}

// ---- A/B/E 教典例句 ----
// 均勻抽樣（頭尾攏有份、固定可重現），毋是頭 N 句
const spread = (arr, n) => (arr.length <= n ? arr : Array.from({ length: n }, (_, i) => arr[Math.floor((i * arr.length) / n)]));
const leku = spread(J("docs/study/data/listen.json").items, N);
console.log(`抽樣：教典例句 ${leku.length} 句（全 ${J("docs/study/data/listen.json").items.length} 句均勻抽）`);
report("A 教典台文", leku.map((x) => x.han), "moe");
report("A 教典台文", leku.map((x) => x.han), "lkk");
report("B 教典華語翻譯", leku.map((x) => x.hoa), "moe", { expectFlag: true });
report("E 教典台羅（教育部寫法＝標準）", leku.map((x) => x.tl), "moe");

// ---- C/D 教會公報 ----
const pojbhPath = join(repo, "data/Khin-hoan_2010_pojbh/pojbh.json");
if (existsSync(pojbhPath)) {
  const arts = JSON.parse(readFileSync(pojbhPath, "utf8")).filter((a) => a.hanlo?.length && a.tailo?.length);
  const pick = (field) => spread(arts, 400).flatMap((a) => a[field].slice(3, 6))
    .map((s) => s.trim()).filter((s) => s.length > 6);
  report("C 教會公報 漢羅", spread(pick("hanlo"), N), "lkk");
  report("D 教會公報 POJ", spread(pick("tailo"), N), "moe");
} else console.log("\n（data/Khin-hoan_2010_pojbh 無，C/D 略過）");

// ---- D 十項管見 ----
const wsDir = join(repo, "scripts/thak/wikisource");
const paras = [];
for (let i = 1; i <= 10; i++) {
  const f = join(wsDir, `te${i}.wiki`);
  if (!existsSync(f)) {
    const url = `https://zh-min-nan.wikisource.org/wiki/Cha%CC%8Dp-h%C4%81ng_Ko%C3%A1n-ki%C3%A0n/T%C4%93_${i}_h%C4%81ng?action=raw`;
    const t = await (await fetch(url)).text();
    if (!t.includes("Koán-kiàn")) throw new Error(`下載失敗 te${i}`);
    writeFileSync(f, t);
  }
  const raw = readFileSync(f, "utf8")
    .replace(/\{\{[\s\S]*?\}\}/g, "")
    .replace(/\[\[[^\]|]*\|([^\]]*)\]\]/g, "$1")
    .replace(/\[\[([^\]]*)\]\]/g, "$1")
    .replace(/'''?/g, "").replace(/^=+.*=+$/gm, "");
  paras.push(...raw.split(/\n+/).map((s) => s.trim()).filter((s) => s.length > 20));
}
report("D 十項管見 POJ", spread(paras, N), "moe");
